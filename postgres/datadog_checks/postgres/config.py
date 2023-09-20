# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from six import PY2, PY3, iteritems

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200

DEFAULT_IGNORE_DATABASES = [
    'template%',
    'rdsadmin',
    'azure_maintenance',
    'postgres',
]


class PostgresConfig:
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count

    def __init__(self, instance):
        self.host = instance.get('host', '')
        if not self.host:
            raise ConfigurationError('Specify a Postgres host to connect to.')
        self.port = instance.get('port', '')
        if self.port != '':
            self.port = int(self.port)
        self.user = instance.get('username', '')
        if not self.user:
            raise ConfigurationError('Please specify a user to connect to Postgres.')
        self.password = instance.get('password', '')
        self.dbname = instance.get('dbname', 'postgres')
        self.reported_hostname = instance.get('reported_hostname', '')
        self.dbstrict = is_affirmative(instance.get('dbstrict', False))
        self.disable_generic_tags = is_affirmative(instance.get('disable_generic_tags', False)) if instance else False

        self.discovery_config = instance.get('database_autodiscovery', {"enabled": False})
        if self.discovery_config['enabled'] and self.dbname != 'postgres':
            raise ConfigurationError(
                "'dbname' parameter should not be set when `database_autodiscovery` is enabled."
                "To monitor more databases, add them to the `database_autodiscovery` includelist."
            )

        self.application_name = instance.get('application_name', 'datadog-agent')
        if not self.isascii(self.application_name):
            raise ConfigurationError("Application name can include only ASCII characters: %s", self.application_name)

        self.query_timeout = int(instance.get('query_timeout', 5000))
        self.idle_connection_timeout = instance.get('idle_connection_timeout', 60000)
        self.relations = instance.get('relations', [])
        if self.relations and not (self.dbname or self.discovery_config['enabled']):
            raise ConfigurationError(
                '"dbname" parameter must be set OR autodiscovery must be enabled when using the "relations" parameter.'
            )
        self.max_connections = instance.get('max_connections', 30)
        connection_timeout_ms = instance.get('connection_timeout', 5000)
        # Convert milliseconds to seconds and ensure a minimum of 2 seconds, which is enforced by psycopg
        self.connection_timeout = max(2, connection_timeout_ms / 1000)
        self.tags = self._build_tags(instance.get('tags', []))

        ssl = instance.get('ssl', "disable")
        if ssl in SSL_MODES:
            self.ssl_mode = ssl

        self.ssl_cert = instance.get('ssl_cert', None)
        self.ssl_root_cert = instance.get('ssl_root_cert', None)
        self.ssl_key = instance.get('ssl_key', None)
        self.ssl_password = instance.get('ssl_password', None)
        self.table_count_limit = instance.get('table_count_limit', TABLE_COUNT_LIMIT)
        self.collect_function_metrics = is_affirmative(instance.get('collect_function_metrics', False))
        # Default value for `count_metrics` is True for backward compatibility
        self.collect_count_metrics = is_affirmative(instance.get('collect_count_metrics', True))
        self.collect_activity_metrics = is_affirmative(instance.get('collect_activity_metrics', False))
        self.activity_metrics_excluded_aggregations = instance.get('activity_metrics_excluded_aggregations', [])
        self.collect_database_size_metrics = is_affirmative(instance.get('collect_database_size_metrics', True))
        self.collect_wal_metrics = is_affirmative(instance.get('collect_wal_metrics', False))
        self.collect_bloat_metrics = is_affirmative(instance.get('collect_bloat_metrics', False))
        self.data_directory = instance.get('data_directory', None)
        self.ignore_databases = instance.get('ignore_databases', DEFAULT_IGNORE_DATABASES)
        if is_affirmative(instance.get('collect_default_database', True)):
            self.ignore_databases = [d for d in self.ignore_databases if d != 'postgres']
        self.custom_queries = instance.get('custom_queries', [])
        self.tag_replication_role = is_affirmative(instance.get('tag_replication_role', False))
        self.custom_metrics = self._get_custom_metrics(instance.get('custom_metrics', []))
        self.max_relations = int(instance.get('max_relations', 300))
        self.min_collection_interval = instance.get('min_collection_interval', 15)
        # database monitoring adds additional telemetry for query metrics & samples
        self.dbm_enabled = is_affirmative(instance.get('dbm', instance.get('deep_database_monitoring', False)))
        self.full_statement_text_cache_max_size = instance.get('full_statement_text_cache_max_size', 10000)
        self.full_statement_text_samples_per_hour_per_query = instance.get(
            'full_statement_text_samples_per_hour_per_query', 1
        )
        # Support a custom view when datadog user has insufficient privilege to see queries
        self.pg_stat_statements_view = instance.get('pg_stat_statements_view', 'pg_stat_statements')
        # statement samples & execution plans
        self.pg_stat_activity_view = instance.get('pg_stat_activity_view', 'pg_stat_activity')
        self.statement_samples_config = instance.get('query_samples', instance.get('statement_samples', {})) or {}
        self.settings_metadata_config = instance.get('collect_settings', {}) or {}
        self.schemas_metadata_config = instance.get('collect_schemas', {"enabled": False})
        if not self.relations and self.schemas_metadata_config['enabled']:
            raise ConfigurationError(
                'In order to collect schemas on this database, you must enable relation metrics collection.'
            )

        self.resources_metadata_config = instance.get('collect_resources', {}) or {}
        self.statement_activity_config = instance.get('query_activity', {}) or {}
        self.statement_metrics_config = instance.get('query_metrics', {}) or {}
        self.managed_identity = instance.get('managed_identity', {})
        self.cloud_metadata = {}
        aws = instance.get('aws', {})
        gcp = instance.get('gcp', {})
        azure = instance.get('azure', {})
        # Remap fully_qualified_domain_name to name
        azure = {k if k != 'fully_qualified_domain_name' else 'name': v for k, v in azure.items()}
        if aws:
            self.cloud_metadata.update({'aws': aws})
        if gcp:
            self.cloud_metadata.update({'gcp': gcp})
        if azure:
            self.cloud_metadata.update({'azure': azure})
        obfuscator_options_config = instance.get('obfuscator_options', {}) or {}
        self.obfuscator_options = {
            # Valid values for this can be found at
            # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/database.md#connection-level-attributes
            'dbms': 'postgresql',
            'replace_digits': is_affirmative(
                obfuscator_options_config.get(
                    'replace_digits', obfuscator_options_config.get('quantize_sql_tables', False)
                )
            ),
            'dollar_quoted_func': is_affirmative(obfuscator_options_config.get('keep_dollar_quoted_func', True)),
            'keep_sql_alias': is_affirmative(obfuscator_options_config.get('keep_sql_alias', True)),
            'return_json_metadata': is_affirmative(obfuscator_options_config.get('collect_metadata', True)),
            'table_names': is_affirmative(obfuscator_options_config.get('collect_tables', True)),
            'collect_commands': is_affirmative(obfuscator_options_config.get('collect_commands', True)),
            'collect_comments': is_affirmative(obfuscator_options_config.get('collect_comments', True)),
        }
        self.log_unobfuscated_queries = is_affirmative(instance.get('log_unobfuscated_queries', False))
        self.log_unobfuscated_plans = is_affirmative(instance.get('log_unobfuscated_plans', False))
        self.database_instance_collection_interval = instance.get('database_instance_collection_interval', 1800)
        self.max_connections_per_thread = self._get_max_connections_per_thread()

    def _build_tags(self, custom_tags):
        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if custom_tags is None:
            tags = []
        else:
            tags = list(set(custom_tags))

        # preset tags to host
        if not self.disable_generic_tags:
            tags.append('server:{}'.format(self.host))
        if self.port:
            tags.append('port:{}'.format(self.port))
        else:
            tags.append('port:socket')

        # preset tags to the database name
        tags.extend(["db:%s" % self.dbname])

        rds_tags = rds_parse_tags_from_endpoint(self.host)
        if rds_tags:
            tags.extend(rds_tags)
        return tags

    def _get_max_connections_per_thread(self):
        """
        Returns the maximum number of connections per thread.
        i.e.
        max_connections = 30
        When dbm_enabled = True, we have 4 threads:
            - 1 thread for the main integration
            - 1 thread for statement_metrics
        main thread opens 1 connection to the main db.
        when autodiscovery is enabled, main thread opens multiple connections to various dbs.
        when schema collection is enabled, metadata thread opens multiple connections to various dbs.
        statement_samples opens multiple connections to various dbs to collect query plans.
        This way we have a total of 2 connections to the main db and 3 threads share the rest of the connections.
        When dbm_enabled = False, we have 1 thread:
            - 1 thread for the main integration
        main thread opens 1 connection to the main db.
        when autodiscovery is enabled, main thread opens multiple connections to various dbs.
        This way we have a total of 1 connections to the main db and multiple connections to various dbs.
        """
        total_max_conns = self.max_connections
        base_conns = 1  # 4 base connections to the main db
        total_multi_db_threads = 0
        if self.discovery_config['enabled']:
            total_multi_db_threads += 1  # autodiscovery is enabled, main thread opens multiple connections
        if self.dbm_enabled:
            base_conns += 1  # 1 additional connections for statement_metrics
            if self.schemas_metadata_config['enabled']:
                total_multi_db_threads += 1  # schema collection is enabled, metadata thread opens multiple connections
            else:
                base_conns += 1  # 1 additional connections for metadata_samples when schema collection is disabled
            total_multi_db_threads += 1  # statement_samples
        total_conns_to_share = total_max_conns - base_conns
        if total_multi_db_threads == 0:
            return total_conns_to_share
        if total_conns_to_share <= 0:
            raise ConfigurationError(
                'The number of max connections per thread must be greater than 0. '
                'Please increase the `max_connections` parameter.'
            )
        return (total_max_conns - base_conns) // total_multi_db_threads  # floor division

    @staticmethod
    def _get_custom_metrics(custom_metrics):
        # Otherwise pre-process custom metrics and verify definition
        required_parameters = ("descriptors", "metrics", "query", "relation")

        for m in custom_metrics:
            for param in required_parameters:
                if param not in m:
                    raise ConfigurationError('Missing {} parameter in custom metric'.format(param))

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

                    m['metrics'][ref][1] = getattr(PostgresConfig, cap_mtype)
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))
        return custom_metrics

    @staticmethod
    def isascii(application_name):
        if PY3:
            return application_name.isascii()
        elif PY2:
            try:
                application_name.encode('ascii')
                return True
            except UnicodeEncodeError:
                return False
