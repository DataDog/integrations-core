# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
from contextlib import closing

import psycopg2
from six import iteritems

from datadog_checks.base import AgentCheck, ConfigurationError

from .config import PostgresConfig
from .util import (
    ACTIVITY_DD_METRICS,
    ACTIVITY_METRICS_8_3,
    ACTIVITY_METRICS_9_2,
    ACTIVITY_METRICS_9_6,
    ACTIVITY_METRICS_LT_8_3,
    ACTIVITY_QUERY_10,
    ACTIVITY_QUERY_LT_10,
    ALL_SCHEMAS,
    COMMON_ARCHIVER_METRICS,
    COMMON_BGW_METRICS,
    COMMON_METRICS,
    CONNECTION_METRICS,
    COUNT_METRICS,
    DATABASE_SIZE_METRICS,
    FUNCTION_METRICS,
    IDX_METRICS,
    LOCK_METRICS,
    NEWER_91_BGW_METRICS,
    NEWER_92_BGW_METRICS,
    NEWER_92_METRICS,
    REL_METRICS,
    REPLICATION_METRICS,
    REPLICATION_METRICS_9_1,
    REPLICATION_METRICS_9_2,
    REPLICATION_METRICS_10,
    SIZE_METRICS,
    STATIO_METRICS,
    build_relations_filter,
    fmt,
    get_schema_field,
)
from .version_utils import V8_3, V9, V9_1, V9_2, V9_4, V9_6, V10, get_raw_version, parse_version, transform_version

MAX_CUSTOM_RESULTS = 100


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    SOURCE_TYPE_NAME = 'postgresql'
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count
    SERVICE_CHECK_NAME = 'postgres.can_connect'
    METADATA_TRANSFORMERS = {'version': transform_version}

    def __init__(self, name, init_config, instances):
        super(PostgreSql, self).__init__(name, init_config, instances)
        self._clean_state()
        self.db = None
        self._version = None
        self._custom_metrics = None
        # Deprecate custom_metrics in favor of custom_queries
        if 'custom_metrics' in self.instance:
            self.warning(
                "DEPRECATION NOTICE: Please use the new custom_queries option "
                "rather than the now deprecated custom_metrics"
            )
        self.config = PostgresConfig(self.instance)

    def _clean_state(self):
        self._version = None
        self.instance_metrics = None
        self.bgw_metrics = None
        self.archiver_metrics = None
        self.db_bgw_metrics = []
        self.db_archiver_metrics = []
        self.replication_metrics = None
        self.activity_metrics = None

    def _get_replication_role(self):
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

    def _get_instance_metrics(self):
        """
        Add NEWER_92_METRICS to the default set of COMMON_METRICS when server
        version is 9.2 or later.

        Store the list of metrics in the check instance to avoid rebuilding it at
        every collection cycle.

        In case we have multiple instances pointing to the same postgres server
        monitoring different databases, we want to collect server metrics
        only once. See https://github.com/DataDog/dd-agent/issues/1211
        """
        metrics = self.instance_metrics
        if metrics is None:
            # select the right set of metrics to collect depending on postgres version
            if self.version >= V9_2:
                self.instance_metrics = dict(COMMON_METRICS, **NEWER_92_METRICS)
            else:
                self.instance_metrics = dict(COMMON_METRICS)

            # add size metrics if needed
            if self.config.collect_database_size_metrics:
                self.instance_metrics.update(DATABASE_SIZE_METRICS)

            metrics = self.instance_metrics

        res = {
            'descriptors': [('psd.datname', 'db')],
            'metrics': metrics,
            'query': "SELECT psd.datname, {metrics_columns} "
            "FROM pg_stat_database psd "
            "JOIN pg_database pd ON psd.datname = pd.datname "
            "WHERE psd.datname not ilike 'template%%' "
            "  AND psd.datname not ilike 'rdsadmin' "
            "  AND psd.datname not ilike 'azure_maintenance' ",
            'relation': False,
        }

        if not self.config.collect_default_db:
            res["query"] += "  AND psd.datname not ilike 'postgres'"

        return res

    def _get_bgw_metrics(self):
        """Use either COMMON_BGW_METRICS or COMMON_BGW_METRICS + NEWER_92_BGW_METRICS
        depending on the postgres version.
        Uses a dictionary to save the result for each instance
        """
        # Extended 9.2+ metrics if needed
        metrics = self.bgw_metrics

        if metrics is None:
            # Hack to make sure that if we have multiple instances that connect to
            # the same host, port, we don't collect metrics twice
            # as it will result in https://github.com/DataDog/dd-agent/issues/1211
            sub_key = self.config.key[:2]
            if sub_key in self.db_bgw_metrics:
                self.bgw_metrics = None
                self.log.debug(
                    "Not collecting bgw metrics for key: %s as they are already collected by another instance",
                    self.config.key,
                )
                return None

            self.db_bgw_metrics.append(sub_key)
            self.bgw_metrics = dict(COMMON_BGW_METRICS)

            if self.version >= V9_1:
                self.bgw_metrics.update(NEWER_91_BGW_METRICS)
            if self.version >= V9_2:
                self.bgw_metrics.update(NEWER_92_BGW_METRICS)

            metrics = self.bgw_metrics

        if not metrics:
            return None

        return {
            'descriptors': [],
            'metrics': metrics,
            'query': "select {metrics_columns} FROM pg_stat_bgwriter",
            'relation': False,
        }

    def _get_count_metrics(self):
        metrics = dict(COUNT_METRICS)
        metrics['query'] = COUNT_METRICS['query'].format(
            metrics_columns="{metrics_columns}", table_count_limit=self.config.table_count_limit
        )
        return metrics

    def _get_archiver_metrics(self):
        """Use COMMON_ARCHIVER_METRICS to read from pg_stat_archiver as
        defined in 9.4 (first version to have this table).
        Uses a dictionary to save the result for each instance
        """
        # While there's only one set for now, prepare for future additions to
        # the table, mirroring _get_bgw_metrics()
        metrics = self.archiver_metrics

        if metrics is None and self.version >= V9_4:
            # Collect from only one instance. See _get_bgw_metrics() for details on why.
            sub_key = self.config.key[:2]
            if sub_key in self.db_archiver_metrics:
                self.archiver_metrics = None
                self.log.debug(
                    "Not collecting archiver metrics for key: %s as they are already collected by another instance",
                    self.config.key,
                )
                return None

            self.db_archiver_metrics.append(sub_key)

            self.archiver_metrics = dict(COMMON_ARCHIVER_METRICS)
            metrics = self.archiver_metrics

        if not metrics:
            return None

        return {
            'descriptors': [],
            'metrics': metrics,
            'query': "select {metrics_columns} FROM pg_stat_archiver",
            'relation': False,
        }

    def _get_replication_metrics(self):
        """ Use either REPLICATION_METRICS_10, REPLICATION_METRICS_9_1, or
        REPLICATION_METRICS_9_1 + REPLICATION_METRICS_9_2, depending on the
        postgres version.
        Uses a dictionnary to save the result for each instance
        """
        metrics = self.replication_metrics
        if self.version >= V10 and metrics is None:
            self.replication_metrics = dict(REPLICATION_METRICS_10)
            metrics = self.replication_metrics
        elif self.version >= V9_1 and metrics is None:
            self.replication_metrics = dict(REPLICATION_METRICS_9_1)
            if self.version >= V9_2:
                self.replication_metrics.update(REPLICATION_METRICS_9_2)
            metrics = self.replication_metrics
        return metrics

    def _get_activity_metrics(self):
        """ Use ACTIVITY_METRICS_LT_8_3 or ACTIVITY_METRICS_8_3 or ACTIVITY_METRICS_9_2
        depending on the postgres version in conjunction with ACTIVITY_QUERY_10 or ACTIVITY_QUERY_LT_10.
        Uses a dictionnary to save the result for each instance
        """
        metrics_data = self.activity_metrics

        if metrics_data is None:
            query = ACTIVITY_QUERY_10 if self.version >= V10 else ACTIVITY_QUERY_LT_10
            if self.version >= V9_6:
                metrics_query = ACTIVITY_METRICS_9_6
            elif self.version >= V9_2:
                metrics_query = ACTIVITY_METRICS_9_2
            elif self.version >= V8_3:
                metrics_query = ACTIVITY_METRICS_8_3
            else:
                metrics_query = ACTIVITY_METRICS_LT_8_3

            for i, q in enumerate(metrics_query):
                if '{dd__user}' in q:
                    metrics_query[i] = q.format(dd__user=self.config.user)

            metrics = {k: v for k, v in zip(metrics_query, ACTIVITY_DD_METRICS)}
            self.activity_metrics = (metrics, query)
        else:
            metrics, query = metrics_data

        return {'descriptors': [('datname', 'db')], 'metrics': metrics, 'query': query, 'relation': False}

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

    def _query_scope(self, cursor, scope, instance_tags, is_custom_metrics, relations_config):
        if scope is None:
            return None
        if scope == REPLICATION_METRICS or not self.version >= V9:
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        # A descriptor is the association of a Postgres column name (e.g. 'schemaname')
        # to a tag name (e.g. 'schema').
        descriptors = scope['descriptors']

        results = None
        try:
            query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
            # if this is a relation-specific query, we need to list all relations last
            if scope['relation'] and len(relations_config) > 0:
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
        db_instance_metrics = self._get_instance_metrics()
        bgw_instance_metrics = self._get_bgw_metrics()
        archiver_instance_metrics = self._get_archiver_metrics()

        metric_scope = [CONNECTION_METRICS]

        if self.config.collect_function_metrics:
            metric_scope.append(FUNCTION_METRICS)
        if self.config.collect_count_metrics:
            metric_scope.append(self._get_count_metrics())

        # Do we need relation-specific metrics?
        relations_config = {}
        if self.config.relations:
            metric_scope += [LOCK_METRICS, REL_METRICS, IDX_METRICS, SIZE_METRICS, STATIO_METRICS]
            relations_config = self._build_relations_config(self.config.relations)

        replication_metrics = self._get_replication_metrics()
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
            activity_metrics = self._get_activity_metrics()
            self._query_scope(cursor, activity_metrics, instance_tags, False, relations_config)

        for scope in list(metric_scope) + self.custom_metrics:
            self._query_scope(cursor, scope, instance_tags, scope in self.custom_metrics, relations_config)

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
                    'port': self.config.port,
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

    @property
    def custom_metrics(self):
        # Pre-processed cached custom_metrics
        if self._custom_metrics is not None:
            self.log.debug("Custom metrics: %s", self._custom_metrics)
            return self._custom_metrics

        # Otherwise pre-process custom metrics and verify definition
        required_parameters = ("descriptors", "metrics", "query", "relation")

        custom_metrics = self.instance.get('custom_metrics', [])
        for m in custom_metrics:
            for param in required_parameters:
                if param not in m:
                    raise ConfigurationError('Missing {} parameter in custom metric'.format(param))

            self.log.debug("Metric: %s", m)

            # Old formatting to new formatting. The first params is always the columns names from which to
            # read metrics. The `relation` param instructs the check to replace the next '%s' with the list of
            # relations names.
            if m['relation']:
                m['query'] = m['query'] % ('{metrics_columns}', '{relations_names}')
            else:
                m['query'] = m['query'] % '{metrics_columns}'

            try:
                for ref, (_, mtype) in iteritems(m['metrics']):
                    cap_mtype = mtype.upper()
                    if cap_mtype not in ('RATE', 'GAUGE', 'MONOTONIC'):
                        raise ConfigurationError(
                            'Collector method {} is not known. '
                            'Known methods are RATE, GAUGE, MONOTONIC'.format(cap_mtype)
                        )

                    m['metrics'][ref][1] = getattr(PostgreSql, cap_mtype)
                    self.log.debug("Method: %s", mtype)
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))

        self._custom_metrics = custom_metrics
        self.log.debug("Custom metrics: %s", custom_metrics)
        return custom_metrics

    def check(self, _):
        tags = copy.copy(self.config.tags)
        (host, port, dbname) = self.config.key
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
                host, port, dbname, str(e)
            )
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.config.service_check_tags, message=message
            )
            raise e
        else:
            message = u'Established connection to postgres://%s:%s/%s' % (host, port, dbname)
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.config.service_check_tags, message=message
            )
            try:
                # commit to close the current query transaction
                self.db.commit()
            except Exception as e:
                self.log.warning("Unable to commit: %s", e)
            self._version = None  # We don't want to cache versions between runs to capture minor updates for metadata
