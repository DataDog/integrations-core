# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
from contextlib import closing

import psycopg2
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.postgres.metric_utils import PostgresMetrics

from .config import PostgresConfig
from .util import (
    ALL_SCHEMAS,
    CONNECTION_METRICS,
    FUNCTION_METRICS,
    IDX_METRICS,
    LOCK_METRICS,
    REL_METRICS,
    REPLICATION_METRICS,
    SIZE_METRICS,
    STATIO_METRICS,
    build_relations_filter,
    fmt,
    get_schema_field,
)
from .version_utils import V9, get_raw_version, parse_version, transform_version

MAX_CUSTOM_RESULTS = 100


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    SOURCE_TYPE_NAME = 'postgresql'
    SERVICE_CHECK_NAME = 'postgres.can_connect'
    METADATA_TRANSFORMERS = {'version': transform_version}

    def __init__(self, name, init_config, instances):
        super(PostgreSql, self).__init__(name, init_config, instances)
        self.db = None
        self._version = None
        # Deprecate custom_metrics in favor of custom_queries
        if 'custom_metrics' in self.instance:
            self.warning(
                "DEPRECATION NOTICE: Please use the new custom_queries option "
                "rather than the now deprecated custom_metrics"
            )
        self.config = PostgresConfig(self.instance)
        self.metric_utils = PostgresMetrics(self.config)
        self._clean_state()

    def _clean_state(self):
        self._version = None
        self.metric_utils.clean_state()

    def get_replication_role(self):
        cursor = self.db.cursor()
        cursor.execute('SELECT pg_is_in_recovery();')
        role = cursor.fetchone()[0]
        # value fetched for role is of <type 'bool'>
        return "standby" if role else "master"

    @property
    def version(self):
        if self._version is None:
            raw_version = get_raw_version(self.db)
            self._version = parse_version(raw_version)
            self.set_metadata('version', raw_version)
        return self._version

    def _build_relations_config(self, yamlconfig):
        """Builds a dictionary from relations configuration while maintaining compatibility
        """
        config = {}

        for element in yamlconfig:
            if isinstance(element, str):
                config[element] = {'relation_name': element, 'schemas': [ALL_SCHEMAS]}
            elif isinstance(element, dict):
                if not ('relation_name' in element or 'relation_regex' in element):
                    self.log.warning(
                        "Parameter 'relation_name' or 'relation_regex' is required for relation element %s", element
                    )
                    continue
                if 'relation_name' in element and 'relation_regex' in element:
                    self.log.warning(
                        "Expecting only of parameters 'relation_name', 'relation_regex' for relation element %s",
                        element,
                    )
                    continue
                schemas = element.get('schemas', [])
                if not isinstance(schemas, list):
                    self.log.warning("Expected a list of schemas for %s", element)
                    continue
                name = element.get('relation_name') or element['relation_regex']
                config[name] = element.copy()
                if len(schemas) == 0:
                    config[name]['schemas'] = [ALL_SCHEMAS]
            else:
                self.log.warning('Unhandled relations config type: %s', element)
        return config

    def _run_query_scope(self, cursor, scope, is_custom_metrics, relations_config, cols, descriptors, is_relations):
        if scope is None:
            return None
        if scope == REPLICATION_METRICS or not self.version >= V9:
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        results = None
        try:
            query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
            # if this is a relation-specific query, we need to list all relations last
            if is_relations:
                schema_field = get_schema_field(descriptors)
                relations_filter = build_relations_filter(relations_config, schema_field)
                self.log.debug("Running query: %s with relations matching: %s", query, relations_filter)
                cursor.execute(query.format(relations=relations_filter))
            else:
                self.log.debug("Running query: %s", query)
                cursor.execute(query.replace(r'%', r'%%'))

            results = cursor.fetchall()
        except psycopg2.errors.FeatureNotSupported as e:
            # This happens for example when trying to get replication metrics
            # from readers in Aurora. Let's ignore it.
            log_func(e)
            self.db.rollback()
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

        if is_relations and len(results) > self.config.max_relations:
            self.warning(
                "Query: %s returned more than %s results (%s). Truncating",
                query,
                self.config.max_relations,
                len(results),
            )
            results = results[: self.config.max_relations]

        return results

    def _query_scope(self, cursor, scope, instance_tags, is_custom_metrics, relations_config):
        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        # A descriptor is the association of a Postgres column name (e.g. 'schemaname')
        # to a tag name (e.g. 'schema').
        descriptors = scope['descriptors']
        is_relations = scope['relation'] and len(relations_config) > 0

        results = self._run_query_scope(
            cursor, scope, is_custom_metrics, relations_config, cols, descriptors, is_relations
        )
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

    def _collect_stats(
        self, instance_tags,
    ):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """
        db_instance_metrics = self.metric_utils.get_instance_metrics(self.version)
        bgw_instance_metrics = self.metric_utils.get_bgw_metrics(self.version)
        archiver_instance_metrics = self.metric_utils.get_archiver_metrics(self.version)

        metric_scope = [CONNECTION_METRICS]

        if self.config.collect_function_metrics:
            metric_scope.append(FUNCTION_METRICS)
        if self.config.collect_count_metrics:
            metric_scope.append(self.metric_utils.get_count_metrics())

        # Do we need relation-specific metrics?
        relations_config = {}
        if self.config.relations:
            metric_scope += [LOCK_METRICS, REL_METRICS, IDX_METRICS, SIZE_METRICS, STATIO_METRICS]
            relations_config = self._build_relations_config(self.config.relations)

        replication_metrics = self.metric_utils.get_replication_metrics(self.version)
        if replication_metrics is not None:
            replication_metrics_query = copy.deepcopy(REPLICATION_METRICS)
            replication_metrics_query['metrics'] = replication_metrics
            metric_scope.append(replication_metrics_query)

        cursor = self.db.cursor()
        results_len = self._query_scope(cursor, db_instance_metrics, instance_tags, False, relations_config)
        if results_len is not None:
            self.gauge("postgresql.db.count", results_len, tags=[t for t in instance_tags if not t.startswith("db:")])

        self._query_scope(cursor, bgw_instance_metrics, instance_tags, False, relations_config)
        self._query_scope(cursor, archiver_instance_metrics, instance_tags, False, relations_config)

        if self.config.collect_activity_metrics:
            activity_metrics = self.metric_utils.get_activity_metrics(self.version)
            self._query_scope(cursor, activity_metrics, instance_tags, False, relations_config)

        for scope in list(metric_scope) + self.config.custom_metrics:
            self._query_scope(cursor, scope, instance_tags, scope in self.config.custom_metrics, relations_config)

        cursor.close()

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
            if self.config.host == 'localhost' and self.config.password == '':
                # Use ident method
                connection_string = "user=%s dbname=%s, application_name=%s" % (
                    self.config.user,
                    self.config.dbname,
                    "datadog-agent",
                )
                if self.config.query_timeout:
                    connection_string += " options='-c statement_timeout=%s'" % self.config.query_timeout
                self.db = psycopg2.connect(connection_string)
            else:
                args = {
                    'host': self.config.host,
                    'user': self.config.user,
                    'password': self.config.password,
                    'database': self.config.dbname,
                    'sslmode': self.config.ssl_mode,
                    'application_name': "datadog-agent",
                }
                if self.config.port:
                    args['port'] = self.config.port
                if self.config.query_timeout:
                    args['options'] = '-c statement_timeout=%s' % self.config.query_timeout
                self.db = psycopg2.connect(**args)

    def _collect_custom_queries(self, tags):
        """
        Given a list of custom_queries, execute each query and parse the result for metrics
        """
        for custom_query in self.config.custom_queries:
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
        tags = copy.copy(self.config.tags)
        # Collect metrics
        try:
            # Check version
            self._connect()
            if self.config.tag_replication_role:
                tags.extend(["replication_role:{}".format(self._get_replication_role())])
            self.log.debug("Running check against version %s", str(self.version))
            self._collect_stats(tags)
            self._collect_custom_queries(tags)
        except Exception as e:
            self.log.error("Unable to collect postgres metrics.")
            self._clean_state()
            self.db = None
            message = u'Error establishing connection to postgres://{}:{}/{}, error is {}'.format(
                self.config.host, self.config.port, self.config.dbname, str(e)
            )
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.config.service_check_tags, message=message
            )
            raise e
        else:
            message = u'Established connection to postgres://%s:%s/%s' % (
                self.config.host,
                self.config.port,
                self.config.dbname,
            )
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.config.service_check_tags, message=message
            )
            try:
                # commit to close the current query transaction
                self.db.commit()
            except Exception as e:
                self.log.warning("Unable to commit: %s", e)
            self._version = None  # We don't want to cache versions between runs to capture minor updates for metadata
