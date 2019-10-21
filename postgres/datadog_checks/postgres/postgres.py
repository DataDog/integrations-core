# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import re
import socket
from contextlib import closing

import psycopg2
from six import iteritems
from six.moves import zip_longest

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

from .util import (
    ACTIVITY_DD_METRICS,
    ACTIVITY_METRICS_8_3,
    ACTIVITY_METRICS_9_2,
    ACTIVITY_METRICS_9_6,
    ACTIVITY_METRICS_LT_8_3,
    ACTIVITY_QUERY_10,
    ACTIVITY_QUERY_LT_10,
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
    fmt,
)

MAX_CUSTOM_RESULTS = 100
TABLE_COUNT_LIMIT = 200

ALL_SCHEMAS = object()

# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics"""

    SOURCE_TYPE_NAME = 'postgresql'
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count
    SERVICE_CHECK_NAME = 'postgres.can_connect'

    def __init__(self, name, init_config, instances):
        AgentCheck.__init__(self, name, init_config, instances)
        self._clean_state()
        self.db = None
        self.custom_metrics = None

        # Deprecate custom_metrics in favor of custom_queries
        if any('custom_metrics' in instance for instance in instances):
            self.warning(
                "DEPRECATION NOTICE: Please use the new custom_queries option "
                "rather than the now deprecated custom_metrics"
            )
        host = self.instance.get('host', '')
        port = self.instance.get('port', '')
        if port != '':
            port = int(port)
        dbname = self.instance.get('dbname', 'postgres')
        self.relations = self.instance.get('relations', [])
        if self.relations and not dbname:
            raise ConfigurationError('"dbname" parameter must be set when using the "relations" parameter.')

        self.key = (host, port, dbname)
        self.tags = self._build_tags(self.instance.get('tags', []), host, port, dbname)

    def _build_tags(self, custom_tags, host, port, dbname):
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if custom_tags is None:
            tags = []
        else:
            tags = list(set(custom_tags))

        # preset tags to host
        tags.append('server:{}'.format(host))
        if port:
            tags.append('port:{}'.format(port))
        else:
            tags.append('port:socket')

        # preset tags to the database name
        tags.extend(["db:%s" % dbname])
        return tags

    def _clean_state(self):
        self.version = None
        self.instance_metrics = None
        self.bgw_metrics = None
        self.archiver_metrics = None
        self.db_bgw_metrics = []
        self.db_archiver_metrics = []
        self.replication_metrics = None
        self.activity_metrics = None

    def _get_replication_role(self, db):
        cursor = db.cursor()
        cursor.execute('SELECT pg_is_in_recovery();')
        role = cursor.fetchone()[0]
        # value fetched for role is of <type 'bool'>
        return "standby" if role else "master"

    def _get_version(self, db):
        if self.version is None:
            cursor = db.cursor()
            cursor.execute('SHOW SERVER_VERSION;')
            version = cursor.fetchone()[0]
            try:
                version_parts = version.split(' ')[0].split('.')
                version = [int(part) for part in version_parts]
            except Exception:
                # Postgres might be in development, with format \d+[beta|rc]\d+
                match = re.match(r'(\d+)([a-zA-Z]+)(\d+)', version)
                if match:
                    version_parts = list(match.groups())

                    # We found a valid development version
                    if len(version_parts) == 3:
                        # Replace development tag with a negative number to properly compare versions
                        version_parts[1] = -1
                        version = [int(part) for part in version_parts]

            self.version = version

        self.service_metadata('version', self.version)
        return self.version

    def _is_above(self, db, version_to_compare):
        version = self._get_version(db)
        if type(version) == list:
            # iterate from major down to bugfix
            for v, vc in zip_longest(version, version_to_compare, fillvalue=0):
                if v == vc:
                    continue

                return v > vc

            # return True if version is the same
            return True
        return False

    def _is_8_3_or_above(self, db):
        return self._is_above(db, [8, 3, 0])

    def _is_9_1_or_above(self, db):
        return self._is_above(db, [9, 1, 0])

    def _is_9_2_or_above(self, db):
        return self._is_above(db, [9, 2, 0])

    def _is_9_4_or_above(self, db):
        return self._is_above(db, [9, 4, 0])

    def _is_9_6_or_above(self, db):
        return self._is_above(db, [9, 6, 0])

    def _is_10_or_above(self, db):
        return self._is_above(db, [10, 0, 0])

    def _get_instance_metrics(self, database_size_metrics, collect_default_db):
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
            if self._is_9_2_or_above():
                self.instance_metrics = dict(COMMON_METRICS, **NEWER_92_METRICS)
            else:
                self.instance_metrics = dict(COMMON_METRICS)

            # add size metrics if needed
            if database_size_metrics:
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

        if not collect_default_db:
            res["query"] += "  AND psd.datname not ilike 'postgres'"

        return res

    def _get_bgw_metrics(self, db):
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
            sub_key = self.key[:2]
            if sub_key in self.db_bgw_metrics:
                self.bgw_metrics = None
                self.log.debug(
                    "Not collecting bgw metrics for key: {0} as "
                    "they are already collected by another instance".format(self.key)
                )
                return None

            self.db_bgw_metrics.append(sub_key)

            self.bgw_metrics = dict(COMMON_BGW_METRICS)
            if self._is_9_1_or_above(db):
                self.bgw_metrics.update(NEWER_91_BGW_METRICS)
            if self._is_9_2_or_above(db):
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

    def _get_count_metrics(self, table_count_limit):
        metrics = dict(COUNT_METRICS)
        metrics['query'] = COUNT_METRICS['query'].format(
            metrics_columns="{metrics_columns}", table_count_limit=table_count_limit
        )
        return metrics

    def _get_archiver_metrics(self, db):
        """Use COMMON_ARCHIVER_METRICS to read from pg_stat_archiver as
        defined in 9.4 (first version to have this table).
        Uses a dictionary to save the result for each instance
        """
        # While there's only one set for now, prepare for future additions to
        # the table, mirroring _get_bgw_metrics()
        metrics = self.archiver_metrics

        if metrics is None and self._is_9_4_or_above(db):
            # Collect from only one instance. See _get_bgw_metrics() for details on why.
            sub_key = self.key[:2]
            if sub_key in self.db_archiver_metrics:
                self.archiver_metrics = None
                self.log.debug(
                    "Not collecting archiver metrics for key: {0} as "
                    "they are already collected by another instance".format(self.key)
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

    def _get_replication_metrics(self, db):
        """ Use either REPLICATION_METRICS_10, REPLICATION_METRICS_9_1, or
        REPLICATION_METRICS_9_1 + REPLICATION_METRICS_9_2, depending on the
        postgres version.
        Uses a dictionnary to save the result for each instance
        """
        metrics = self.replication_metrics
        if self._is_10_or_above(db) and metrics is None:
            self.replication_metrics = dict(REPLICATION_METRICS_10)
            metrics = self.replication_metrics
        elif self._is_9_1_or_above(db) and metrics is None:
            self.replication_metrics = dict(REPLICATION_METRICS_9_1)
            if self._is_9_2_or_above(db):
                self.replication_metrics.update(REPLICATION_METRICS_9_2)
            metrics = self.replication_metrics
        return metrics

    def _get_activity_metrics(self, db, user):
        """ Use ACTIVITY_METRICS_LT_8_3 or ACTIVITY_METRICS_8_3 or ACTIVITY_METRICS_9_2
        depending on the postgres version in conjunction with ACTIVITY_QUERY_10 or ACTIVITY_QUERY_LT_10.
        Uses a dictionnary to save the result for each instance
        """
        metrics_data = self.activity_metrics

        if metrics_data is None:
            query = ACTIVITY_QUERY_10 if self._is_10_or_above(db) else ACTIVITY_QUERY_LT_10
            if self._is_9_6_or_above(db):
                metrics_query = ACTIVITY_METRICS_9_6
            elif self._is_9_2_or_above(db):
                metrics_query = ACTIVITY_METRICS_9_2
            elif self._is_8_3_or_above(db):
                metrics_query = ACTIVITY_METRICS_8_3
            else:
                metrics_query = ACTIVITY_METRICS_LT_8_3

            for i, q in enumerate(metrics_query):
                if '{dd__user}' in q:
                    metrics_query[i] = q.format(dd__user=user)

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
                self.log.warning('Unhandled relations config type: {}'.format(element))
        return config

    def _query_scope(self, cursor, scope, db, instance_tags, is_custom_metrics, relations_config):
        if scope is None:
            return None

        if scope == REPLICATION_METRICS or not self._is_above(db, [9, 0, 0]):
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        results = None
        try:
            query = fmt.format(scope['query'], metrics_columns=", ".join(cols))
            # if this is a relation-specific query, we need to list all relations last
            if scope['relation'] and len(relations_config) > 0:
                rel_names = ', '.join("'{0}'".format(k) for k, v in relations_config.items() if 'relation_name' in v)
                rel_regex = ', '.join("'{0}'".format(k) for k, v in relations_config.items() if 'relation_regex' in v)
                self.log.debug("Running query: {} with relations matching: {}".format(query, rel_names + rel_regex))
                cursor.execute(query.format(relations_names=rel_names, relations_regexes=rel_regex))
            else:
                self.log.debug("Running query: %s" % query)
                cursor.execute(query.replace(r'%', r'%%'))

            results = cursor.fetchall()

        except psycopg2.errors.UndefinedFunction as e:
            log_func(e)
            log_func(
                "It seems the PG version has been incorrectly identified as %s. "
                "A reattempt to identify the right version will happen on next agent run." % self.version
            )
            self._clean_state()
            db.rollback()
        except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
            log_func("Not all metrics may be available: %s" % str(e))
            db.rollback()

        if not results:
            return None

        if is_custom_metrics and len(results) > MAX_CUSTOM_RESULTS:
            self.warning(
                "Query: {0} returned more than {1} results ({2}). Truncating".format(
                    query, MAX_CUSTOM_RESULTS, len(results)
                )
            )
            results = results[:MAX_CUSTOM_RESULTS]

        desc = scope['descriptors']

        # parse & submit results
        # A row should look like this
        # (descriptor, descriptor, ..., value, value, value, value, ...)
        # with descriptor a PG relation or index name, which we use to create the tags
        valid_results_size = 0
        for row in results:
            # Check that all columns will be processed
            assert len(row) == len(cols) + len(desc)

            # build a map of descriptors and their values
            desc_map = dict(zip([x[1] for x in desc], row[0 : len(desc)]))

            # if relations *and* schemas are set, filter out table not
            # matching the schema in the configuration
            if scope['relation'] and len(relations_config) > 0 and 'schema' in desc_map and 'table' in desc_map:
                row_table = desc_map['table']
                row_schema = desc_map['schema']

                if row_table in relations_config:
                    config_table_objects = [relations_config[row_table]]
                else:
                    # Find all matching regexes. Required if the same table matches two different regex
                    regex_configs = (v for v in relations_config.values() if 'relation_regex' in v)
                    config_table_objects = [r for r in regex_configs if re.match(r['relation_regex'], row_table)]

                if not config_table_objects:
                    self.log.info("Got row %s.%s, but not relation", row_schema, row_table)
                else:
                    # Create set of all schemas by flattening and removing duplicates
                    config_schemas = {s for r in config_table_objects for s in r['schemas']}
                    if ALL_SCHEMAS in config_schemas:
                        self.log.debug("All schemas are allowed for table %s.%s", row_schema, row_table)
                    elif row_schema not in config_schemas:
                        self.log.debug("Skipping non matched schema %s for table %s", desc_map['schema'], row_table)
                        continue

            # Build tags
            # descriptors are: (pg_name, dd_tag_name): value
            # Special-case the "db" tag, which overrides the one that is passed as instance_tag
            # The reason is that pg_stat_database returns all databases regardless of the
            # connection.
            if not scope['relation'] and not scope.get('use_global_db_tag', False):
                tags = [t for t in instance_tags if not t.startswith("db:")]
            else:
                tags = [t for t in instance_tags]

            tags += [("%s:%s" % (k, v)) for (k, v) in iteritems(desc_map)]

            # [(metric-map, value), (metric-map, value), ...]
            # metric-map is: (dd_name, "rate"|"gauge")
            # shift the results since the first columns will be the "descriptors"
            # To submit simply call the function for each value v
            # v[0] == (metric_name, submit_function)
            # v[1] == the actual value
            # tags are
            for v in zip([scope['metrics'][c] for c in cols], row[len(desc) :]):
                v[0][1](self, v[0][0], v[1], tags=tags)
            valid_results_size += 1

        return valid_results_size

    def _collect_stats(
        self,
        db,
        user,
        instance_tags,
        relations,
        custom_metrics,
        table_count_limit,
        collect_function_metrics,
        collect_count_metrics,
        collect_activity_metrics,
        collect_database_size_metrics,
        collect_default_db,
    ):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """

        db_instance_metrics = self._get_instance_metrics(collect_database_size_metrics, collect_default_db)
        bgw_instance_metrics = self._get_bgw_metrics(db)
        archiver_instance_metrics = self._get_archiver_metrics(db)

        metric_scope = [CONNECTION_METRICS, LOCK_METRICS]

        if collect_function_metrics:
            metric_scope.append(FUNCTION_METRICS)
        if collect_count_metrics:
            metric_scope.append(self._get_count_metrics(table_count_limit))

        # Do we need relation-specific metrics?
        relations_config = {}
        if relations:
            metric_scope += [REL_METRICS, IDX_METRICS, SIZE_METRICS, STATIO_METRICS]
            relations_config = self._build_relations_config(relations)

        replication_metrics = self._get_replication_metrics(db)
        if replication_metrics is not None:
            replication_metrics_query = copy.deepcopy(REPLICATION_METRICS)
            replication_metrics_query['metrics'] = replication_metrics
            metric_scope.append(replication_metrics_query)

        cursor = db.cursor()
        results_len = self._query_scope(cursor, db_instance_metrics, db, instance_tags, False, relations_config)
        if results_len is not None:
            self.gauge("postgresql.db.count", results_len, tags=[t for t in instance_tags if not t.startswith("db:")])

        self._query_scope(cursor, bgw_instance_metrics, db, instance_tags, False, relations_config)
        self._query_scope(cursor, archiver_instance_metrics, db, instance_tags, False, relations_config)

        if collect_activity_metrics:
            activity_metrics = self._get_activity_metrics(db, user)
            self._query_scope(cursor, activity_metrics, db, instance_tags, False, relations_config)

        for scope in list(metric_scope) + custom_metrics:
            self._query_scope(cursor, scope, db, instance_tags, scope in custom_metrics, relations_config)

        cursor.close()

    @classmethod
    def _get_service_check_tags(cls, host, tags):
        service_check_tags = ["host:%s" % host]
        service_check_tags.extend(tags)
        service_check_tags = list(set(service_check_tags))
        return service_check_tags

    def get_connection(self, host, port, user, password, dbname, ssl, tags, use_cached=True):
        """Get and memoize connections to instances"""
        if self.db and use_cached:
            conn = self.db
            if conn.status != psycopg2.extensions.STATUS_READY:
                # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
                conn.rollback()
            return conn
        elif host != "" and user != "":
            try:
                if host == 'localhost' and password == '':
                    # Use ident method
                    connection = psycopg2.connect(
                        "user=%s dbname=%s, application_name=%s" % (user, dbname, "datadog-agent")
                    )
                elif port != '':
                    connection = psycopg2.connect(
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        database=dbname,
                        sslmode=ssl,
                        application_name="datadog-agent",
                    )
                else:
                    connection = psycopg2.connect(
                        host=host,
                        user=user,
                        password=password,
                        database=dbname,
                        sslmode=ssl,
                        application_name="datadog-agent",
                    )
                self.db = connection
                return connection
            except Exception as e:
                message = u'Error establishing postgres connection: %s' % (str(e))
                service_check_tags = self._get_service_check_tags(host, tags)
                self.service_check(
                    self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=message
                )
                raise
        else:
            if not host:
                raise ConfigurationError('Please specify a Postgres host to connect to.')
            elif not user:
                raise ConfigurationError('Please specify a user to connect to Postgres as.')

    def _get_custom_queries(self, db, tags, custom_queries):
        """
        Given a list of custom_queries, execute each query and parse the result for metrics
        """
        for custom_query in custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:
                self.log.error("custom query field `metric_prefix` is required")
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:
                self.log.error("custom query field `query` is required for metric_prefix `{}`".format(metric_prefix))
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error("custom query field `columns` is required for metric_prefix `{}`".format(metric_prefix))
                continue

            cursor = db.cursor()
            with closing(cursor) as cursor:
                try:
                    self.log.debug("Running query: {}".format(query))
                    cursor.execute(query)
                except (psycopg2.ProgrammingError, psycopg2.errors.QueryCanceled) as e:
                    self.log.error("Error executing query for metric_prefix {}: {}".format(metric_prefix, str(e)))
                    db.rollback()
                    continue

                for row in cursor:
                    if not row:
                        self.log.debug(
                            "query result for metric_prefix {}: returned an empty result".format(metric_prefix)
                        )
                        continue

                    if len(columns) != len(row):
                        self.log.error(
                            "query result for metric_prefix {}: expected {} columns, got {}".format(
                                metric_prefix, len(columns), len(row)
                            )
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
                            self.log.error(
                                "column field `name` is required for metric_prefix `{}`".format(metric_prefix)
                            )
                            break

                        column_type = column.get('type')
                        if not column_type:
                            self.log.error(
                                "column field `type` is required for column `{}` "
                                "of metric_prefix `{}`".format(name, metric_prefix)
                            )
                            break

                        if column_type == 'tag':
                            query_tags.append('{}:{}'.format(name, value))
                        else:
                            if not hasattr(self, column_type):
                                self.log.error(
                                    "invalid submission method `{}` for column `{}` of "
                                    "metric_prefix `{}`".format(column_type, name, metric_prefix)
                                )
                                break
                            try:
                                metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                            except (ValueError, TypeError):
                                self.log.error(
                                    "non-numeric value `{}` for metric column `{}` of "
                                    "metric_prefix `{}`".format(value, name, metric_prefix)
                                )
                                break

                    # Only submit metrics if there were absolutely no errors - all or nothing.
                    else:
                        for info in metric_info:
                            metric, value, method = info
                            getattr(self, method)(metric, value, tags=query_tags)

    def _get_custom_metrics(self, custom_metrics):
        # Pre-processed cached custom_metrics
        if self.custom_metrics is not None:
            return self.custom_metrics

        # Otherwise pre-process custom metrics and verify definition
        required_parameters = ("descriptors", "metrics", "query", "relation")

        for m in custom_metrics:
            for param in required_parameters:
                if param not in m:
                    raise ConfigurationError('Missing {} parameter in custom metric'.format(param))

            self.log.debug("Metric: {0}".format(m))

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
                    self.log.debug("Method: %s" % (str(mtype)))
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))

        self.custom_metrics = custom_metrics
        return custom_metrics

    def check(self, instance):
        ssl = self.instance.get('ssl', False)
        if ssl not in SSL_MODES:
            ssl = 'require' if is_affirmative(ssl) else 'disable'

        user = self.instance.get('username', '')
        password = self.instance.get('password', '')

        table_count_limit = self.instance.get('table_count_limit', TABLE_COUNT_LIMIT)
        collect_function_metrics = is_affirmative(self.instance.get('collect_function_metrics', False))
        # Default value for `count_metrics` is True for backward compatibility
        collect_count_metrics = is_affirmative(self.instance.get('collect_count_metrics', True))
        collect_activity_metrics = is_affirmative(self.instance.get('collect_activity_metrics', False))
        collect_database_size_metrics = is_affirmative(self.instance.get('collect_database_size_metrics', True))
        collect_default_db = is_affirmative(self.instance.get('collect_default_database', False))

        custom_metrics = self._get_custom_metrics(instance.get('custom_metrics', []))
        custom_queries = instance.get('custom_queries', [])

        (host, port, dbname) = self.key

        self.log.debug("Custom metrics: %s" % custom_metrics)

        tag_replication_role = is_affirmative(self.instance.get('tag_replication_role', False))
        tags = self.tags

        # Collect metrics
        db = None
        try:
            # Check version
            db = self.get_connection(host, port, user, password, dbname, ssl, tags)
            if tag_replication_role:
                tags.extend(["replication_role:{}".format(self._get_replication_role(db))])
            version = self._get_version(db)
            self.log.debug("Running check against version %s" % version)
            self._collect_stats(
                db,
                user,
                tags,
                self.relations,
                custom_metrics,
                table_count_limit,
                collect_function_metrics,
                collect_count_metrics,
                collect_activity_metrics,
                collect_database_size_metrics,
                collect_default_db,
            )
            self._get_custom_queries(db, tags, custom_queries)
        except (psycopg2.InterfaceError, socket.error):
            self.log.info("Connection error, will retry on next agent run")
            self._clean_state()

        if db is not None:
            service_check_tags = self._get_service_check_tags(host, tags)
            message = u'Established connection to postgres://%s:%s/%s' % (host, port, dbname)
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags, message=message)
            try:
                # commit to close the current query transaction
                db.commit()
            except Exception as e:
                self.log.warning("Unable to commit: {0}".format(e))
