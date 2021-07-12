# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import threading
from contextlib import closing

import psycopg2
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.postgres.metrics_cache import PostgresMetricsCache
from datadog_checks.postgres.relationsmanager import RELATION_METRICS, RelationsManager
from datadog_checks.postgres.statement_samples import PostgresStatementSamples
from datadog_checks.postgres.statements import PostgresStatementMetrics

from .config import PostgresConfig
from .util import CONNECTION_METRICS, FUNCTION_METRICS, REPLICATION_METRICS, fmt, get_schema_field
from .version_utils import V9, VersionUtils

MAX_CUSTOM_RESULTS = 100

TRACK_ACTIVITY_QUERY_SIZE_QUERY = "SELECT setting FROM pg_settings WHERE name='track_activity_query_size'"
TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE = -1


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    SOURCE_TYPE_NAME = 'postgresql'
    SERVICE_CHECK_NAME = 'postgres.can_connect'
    METADATA_TRANSFORMERS = {'version': VersionUtils.transform_version}

    def __init__(self, name, init_config, instances):
        super(PostgreSql, self).__init__(name, init_config, instances)
        self.db = None
        self._version = None
        self._is_aurora = None
        self._version_utils = VersionUtils()
        # Deprecate custom_metrics in favor of custom_queries
        if 'custom_metrics' in self.instance:
            self.warning(
                "DEPRECATION NOTICE: Please use the new custom_queries option "
                "rather than the now deprecated custom_metrics"
            )
        self._config = PostgresConfig(self.instance)
        self.metrics_cache = PostgresMetricsCache(self._config)
        self.statement_metrics = PostgresStatementMetrics(self, self._config, shutdown_callback=self._close_db_pool)
        self.statement_samples = PostgresStatementSamples(self, self._config, shutdown_callback=self._close_db_pool)
        self._relations_manager = RelationsManager(self._config.relations)
        self._clean_state()
        self.check_initializations.append(lambda: RelationsManager.validate_relations_config(self._config.relations))
        # The value is loaded when connecting to the main database
        self._db_configured_track_activity_query_size = TRACK_ACTIVITY_QUERY_SIZE_UNKNOWN_VALUE

        # map[dbname -> psycopg connection]
        self._db_pool = {}
        self._db_pool_lock = threading.Lock()

    def cancel(self):
        self.statement_samples.cancel()
        self.statement_metrics.cancel()

    def _clean_state(self):
        self.log.debug("Cleaning state")
        self._version = None
        self._is_aurora = None
        self.metrics_cache.clean_state()

    def _get_replication_role(self):
        cursor = self.db.cursor()
        cursor.execute('SELECT pg_is_in_recovery();')
        role = cursor.fetchone()[0]
        # value fetched for role is of <type 'bool'>
        return "standby" if role else "master"

    @property
    def version(self):
        if self._version is None:
            raw_version = self._version_utils.get_raw_version(self.db)
            self._version = self._version_utils.parse_version(raw_version)
            self.set_metadata('version', raw_version)
        return self._version

    @property
    def is_aurora(self):
        if self._is_aurora is None:
            self._is_aurora = self._version_utils.is_aurora(self.db)
        return self._is_aurora

    def _run_query_scope(self, cursor, scope, is_custom_metrics, cols, descriptors):
        if scope is None:
            return None
        if scope == REPLICATION_METRICS or not self.version >= V9:
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        results = None
        is_relations = scope.get('relation') and self._relations_manager.has_relations
        try:
            query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
            # if this is a relation-specific query, we need to list all relations last
            if is_relations:
                schema_field = get_schema_field(descriptors)
                formatted_query = self._relations_manager.filter_relation_query(query, schema_field)
                cursor.execute(formatted_query)
            else:
                self.log.debug("Running query: %s", str(query))
                cursor.execute(query.replace(r'%', r'%%'))

            results = cursor.fetchall()
        except psycopg2.errors.FeatureNotSupported as e:
            # This happens for example when trying to get replication metrics from readers in Aurora. Let's ignore it.
            log_func(e)
            self.db.rollback()
            self.log.debug("Disabling replication metrics")
            self._is_aurora = False
            self.metrics_cache.replication_metrics = {}
        except psycopg2.errors.UndefinedFunction as e:
            log_func(e)
            log_func(
                "It seems the PG version has been incorrectly identified as %s. "
                "A reattempt to identify the right version will happen on next agent run." % self._version
            )
            self._clean_state()
            self.db.rollback()
        except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
            log_func("Not all metrics may be available: %s" % str(e))
            self.db.rollback()

        if not results:
            return None

        if is_custom_metrics and len(results) > MAX_CUSTOM_RESULTS:
            self.warning(
                "Query: %s returned more than %s results (%s). Truncating", query, MAX_CUSTOM_RESULTS, len(results)
            )
            results = results[:MAX_CUSTOM_RESULTS]

        if is_relations and len(results) > self._config.max_relations:
            self.warning(
                "Query: %s returned more than %s results (%s). "
                "Truncating. You can edit this limit by setting the `max_relations` config option",
                query,
                self._config.max_relations,
                len(results),
            )
            results = results[: self._config.max_relations]

        return results

    def _query_scope(self, cursor, scope, instance_tags, is_custom_metrics):
        if scope is None:
            return None
        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        # A descriptor is the association of a Postgres column name (e.g. 'schemaname')
        # to a tag name (e.g. 'schema').
        descriptors = scope['descriptors']
        results = self._run_query_scope(cursor, scope, is_custom_metrics, cols, descriptors)
        if not results:
            return None

        # Parse and submit results.

        num_results = 0

        for row in results:
            # A row contains descriptor values on the left (used for tagging), and
            # metric values on the right (used as values for metrics).
            # E.g.: (descriptor, descriptor, ..., value, value, value, value, ...)

            expected_number_of_columns = len(descriptors) + len(cols)
            if len(row) != expected_number_of_columns:
                raise RuntimeError(
                    'Row does not contain enough values: '
                    'expected {} ({} descriptors + {} columns), got {}'.format(
                        expected_number_of_columns, len(descriptors), len(cols), len(row)
                    )
                )

            descriptor_values = row[: len(descriptors)]
            column_values = row[len(descriptors) :]

            # build a map of descriptors and their values
            desc_map = {name: value for (_, name), value in zip(descriptors, descriptor_values)}

            # Build tags.

            # Add tags from the instance.
            # Special-case the "db" tag, which overrides the one that is passed as instance_tag
            # The reason is that pg_stat_database returns all databases regardless of the
            # connection.
            if not scope['relation'] and not scope.get('use_global_db_tag', False):
                tags = [t for t in instance_tags if not t.startswith("db:")]
            else:
                tags = copy.copy(instance_tags)

            # Add tags from descriptors.
            tags += [("%s:%s" % (k, v)) for (k, v) in iteritems(desc_map)]

            # Submit metrics to the Agent.
            for column, value in zip(cols, column_values):
                name, submit_metric = scope['metrics'][column]
                submit_metric(self, name, value, tags=set(tags))

            num_results += 1

        return num_results

    def _collect_stats(self, instance_tags):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """
        db_instance_metrics = self.metrics_cache.get_instance_metrics(self.version)
        bgw_instance_metrics = self.metrics_cache.get_bgw_metrics(self.version)
        archiver_instance_metrics = self.metrics_cache.get_archiver_metrics(self.version)

        metric_scope = [CONNECTION_METRICS]

        if self._config.collect_function_metrics:
            metric_scope.append(FUNCTION_METRICS)
        if self._config.collect_count_metrics:
            metric_scope.append(self.metrics_cache.get_count_metrics())

        # Do we need relation-specific metrics?
        if self._config.relations:
            metric_scope.extend(RELATION_METRICS)

        replication_metrics = self.metrics_cache.get_replication_metrics(self.version, self.is_aurora)
        if replication_metrics:
            replication_metrics_query = copy.deepcopy(REPLICATION_METRICS)
            replication_metrics_query['metrics'] = replication_metrics
            metric_scope.append(replication_metrics_query)

        replication_stats_metrics = self.metrics_cache.get_replication_stats_metrics(self.version)
        if replication_stats_metrics:
            metric_scope.append(replication_stats_metrics)

        cursor = self.db.cursor()
        results_len = self._query_scope(cursor, db_instance_metrics, instance_tags, False)
        if results_len is not None:
            self.gauge("postgresql.db.count", results_len, tags=[t for t in instance_tags if not t.startswith("db:")])

        self._query_scope(cursor, bgw_instance_metrics, instance_tags, False)
        self._query_scope(cursor, archiver_instance_metrics, instance_tags, False)

        if self._config.collect_activity_metrics:
            activity_metrics = self.metrics_cache.get_activity_metrics(self.version)
            self._query_scope(cursor, activity_metrics, instance_tags, False)

        for scope in list(metric_scope) + self._config.custom_metrics:
            self._query_scope(cursor, scope, instance_tags, scope in self._config.custom_metrics)

        cursor.close()

    def _new_connection(self, dbname):
        if self._config.host == 'localhost' and self._config.password == '':
            # Use ident method
            connection_string = "user=%s dbname=%s application_name=%s" % (
                self._config.user,
                dbname,
                self._config.application_name,
            )
            if self._config.query_timeout:
                connection_string += " options='-c statement_timeout=%s'" % self._config.query_timeout
            conn = psycopg2.connect(connection_string)
        else:
            args = {
                'host': self._config.host,
                'user': self._config.user,
                'password': self._config.password,
                'database': dbname,
                'sslmode': self._config.ssl_mode,
                'application_name': self._config.application_name,
            }
            if self._config.port:
                args['port'] = self._config.port
            if self._config.query_timeout:
                args['options'] = '-c statement_timeout=%s' % self._config.query_timeout
            conn = psycopg2.connect(**args)
        # Autocommit is enabled by default for safety for all new connections (to prevent long-lived transactions).
        conn.set_session(autocommit=True)
        return conn

    def _connect(self):
        """Get and memoize connections to instances"""
        if self.db and self.db.closed:
            # Reset the connection object to retry to connect
            self.db = None

        if self.db:
            if self.db.status != psycopg2.extensions.STATUS_READY:
                # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
                self.db.rollback()
        else:
            self.db = self._new_connection(self._config.dbname)

    # Reload the track_activity_query_size setting on a new connection to the main db
    def _load_query_max_text_size(self, db):
        try:
            with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                self.log.debug("Running query [%s]", TRACK_ACTIVITY_QUERY_SIZE_QUERY)
                cursor.execute(TRACK_ACTIVITY_QUERY_SIZE_QUERY)
                row = cursor.fetchone()
                self._db_configured_track_activity_query_size = int(row['setting'])
        except (psycopg2.DatabaseError, psycopg2.OperationalError) as e:
            self.log.warning("cannot read track_activity_query_size from pg_settings: %s", repr(e))
            self._check.count(
                "dd.postgres.statement_samples.error",
                1,
                tags=self._tags + ["error:load-track-activity-query-size"],
            )

    def _get_db(self, dbname):
        """
        Returns a memoized psycopg2 connection to `dbname` with autocommit
        Threadsafe as long as no transactions are used
        :param dbname:
        :return: a psycopg2 connection
        """
        # TODO: migrate the rest of this check to use a connection from this pool
        with self._db_pool_lock:
            db = self._db_pool.get(dbname)
            if not db or db.closed:
                self.log.debug("initializing connection to dbname=%s", dbname)
                db = self._new_connection(dbname)
                db.set_session(autocommit=True)
                self._db_pool[dbname] = db
            if db.status != psycopg2.extensions.STATUS_READY:
                # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
                db.rollback()
            if self._config.dbname == dbname:
                self._load_query_max_text_size(db)
            return db

    def _close_db_pool(self):
        # TODO: add automatic aging out of connections after some time
        with self._db_pool_lock:
            for dbname, db in self._db_pool.items():
                if db and not db.closed:
                    try:
                        db.close()
                    except Exception:
                        self._log.exception("failed to close DB connection for db=%s", dbname)
                self._db_pool[dbname] = None

    def _collect_custom_queries(self, tags):
        """
        Given a list of custom_queries, execute each query and parse the result for metrics
        """
        for custom_query in self._config.custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:
                self.log.error("custom query field `metric_prefix` is required")
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:
                self.log.error("custom query field `query` is required for metric_prefix `%s`", metric_prefix)
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error("custom query field `columns` is required for metric_prefix `%s`", metric_prefix)
                continue

            cursor = self.db.cursor()
            with closing(cursor) as cursor:
                try:
                    self.log.debug("Running query: %s", query)
                    cursor.execute(query)
                except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
                    self.log.error("Error executing query for metric_prefix %s: %s", metric_prefix, str(e))
                    self.db.rollback()
                    continue

                for row in cursor:
                    if not row:
                        self.log.debug("query result for metric_prefix %s: returned an empty result", metric_prefix)
                        continue

                    if len(columns) != len(row):
                        self.log.error(
                            "query result for metric_prefix %s: expected %s columns, got %s",
                            metric_prefix,
                            len(columns),
                            len(row),
                        )
                        continue

                    metric_info = []
                    query_tags = list(custom_query.get('tags', []))
                    query_tags.extend(tags)

                    for column, value in zip(columns, row):
                        # Columns can be ignored via configuration.
                        if not column:
                            continue

                        name = column.get('name')
                        if not name:
                            self.log.error("column field `name` is required for metric_prefix `%s`", metric_prefix)
                            break

                        column_type = column.get('type')
                        if not column_type:
                            self.log.error(
                                "column field `type` is required for column `%s` of metric_prefix `%s`",
                                name,
                                metric_prefix,
                            )
                            break

                        if column_type == 'tag':
                            query_tags.append('{}:{}'.format(name, value))
                        else:
                            if not hasattr(self, column_type):
                                self.log.error(
                                    "invalid submission method `%s` for column `%s` of metric_prefix `%s`",
                                    column_type,
                                    name,
                                    metric_prefix,
                                )
                                break
                            try:
                                metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                            except (ValueError, TypeError):
                                self.log.error(
                                    "non-numeric value `%s` for metric column `%s` of metric_prefix `%s`",
                                    value,
                                    name,
                                    metric_prefix,
                                )
                                break

                    # Only submit metrics if there were absolutely no errors - all or nothing.
                    else:
                        for info in metric_info:
                            metric, value, method = info
                            getattr(self, method)(metric, value, tags=set(query_tags))

    def check(self, _):
        tags = copy.copy(self._config.tags)
        # Collect metrics
        try:
            # Check version
            self._connect()
            if self._config.tag_replication_role:
                tags.extend(["replication_role:{}".format(self._get_replication_role())])
            self.log.debug("Running check against version %s: is_aurora: %s", str(self.version), str(self.is_aurora))
            self._collect_stats(tags)
            self._collect_custom_queries(tags)
            if self._config.dbm_enabled:
                self.statement_metrics.run_job_loop(tags)
                self.statement_samples.run_job_loop(tags)

        except Exception as e:
            self.log.exception("Unable to collect postgres metrics.")
            self._clean_state()
            self.db = None
            message = u'Error establishing connection to postgres://{}:{}/{}, error is {}'.format(
                self._config.host, self._config.port, self._config.dbname, str(e)
            )
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.service_check_tags, message=message
            )
            raise e
        else:
            message = u'Established connection to postgres://%s:%s/%s' % (
                self._config.host,
                self._config.port,
                self._config.dbname,
            )
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.service_check_tags, message=message
            )
            try:
                # commit to close the current query transaction
                self.db.commit()
            except Exception as e:
                self.log.warning("Unable to commit: %s", e)
            self._version = None  # We don't want to cache versions between runs to capture minor updates for metadata
