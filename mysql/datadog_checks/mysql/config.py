# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.base import ConfigurationError, is_affirmative
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint

DEFAULT_MAX_CUSTOM_QUERIES = 20


class MySQLConfig(object):
    def __init__(self, instance):
        self.log = get_check_logger()
        self.host = instance.get('host', instance.get('server', ''))
        self.port = int(instance.get('port', 0))
        self.reported_hostname = instance.get('reported_hostname', '')
        self.mysql_sock = instance.get('sock', '')
        self.defaults_file = instance.get('defaults_file', '')
        self.user = instance.get('username', instance.get('user', ''))
        self.password = str(instance.get('password', instance.get('pass', '')))
        self.tags = self._build_tags(instance.get('tags', []))
        self.options = instance.get('options', {}) or {}  # options could be None if empty in the YAML
        replication_channel = self.options.get('replication_channel')
        if replication_channel:
            self.tags.append("channel:{0}".format(replication_channel))
        self.queries = instance.get('queries', [])
        self.ssl = instance.get('ssl', {})
        self.additional_status = instance.get('additional_status', [])
        self.additional_variable = instance.get('additional_variable', [])
        self.connect_timeout = instance.get('connect_timeout', 10)
        self.read_timeout = instance.get('read_timeout', 10)
        self.max_custom_queries = instance.get('max_custom_queries', DEFAULT_MAX_CUSTOM_QUERIES)
        self.charset = instance.get('charset')
        self.dbm_enabled = is_affirmative(instance.get('dbm', instance.get('deep_database_monitoring', False)))
        self.table_rows_stats_enabled = is_affirmative(self.options.get('table_rows_stats_metrics', False))
        self.statement_metrics_limits = instance.get('statement_metrics_limits', None)
        self.full_statement_text_cache_max_size = instance.get('full_statement_text_cache_max_size', 10000)
        self.full_statement_text_samples_per_hour_per_query = instance.get(
            'full_statement_text_samples_per_hour_per_query', 1
        )
        self.statement_samples_config = instance.get('query_samples', instance.get('statement_samples', {})) or {}
        self.statement_metrics_config = instance.get('query_metrics', {}) or {}
        self.settings_config = instance.get('collect_settings', {}) or {}
        self.activity_config = instance.get('query_activity', {}) or {}
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
        self.min_collection_interval = instance.get('min_collection_interval', 15)
        self.only_custom_queries = is_affirmative(instance.get('only_custom_queries', False))
        obfuscator_options_config = instance.get('obfuscator_options', {}) or {}
        self.obfuscator_options = {
            # Valid values for this can be found at
            # https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/trace/semantic_conventions/database.md#connection-level-attributes
            'dbms': 'mysql',
            'replace_digits': is_affirmative(
                obfuscator_options_config.get(
                    'replace_digits', obfuscator_options_config.get('quantize_sql_tables', False)
                )
            ),
            'keep_sql_alias': is_affirmative(obfuscator_options_config.get('keep_sql_alias', True)),
            'return_json_metadata': is_affirmative(obfuscator_options_config.get('collect_metadata', True)),
            'table_names': is_affirmative(obfuscator_options_config.get('collect_tables', True)),
            'collect_commands': is_affirmative(obfuscator_options_config.get('collect_commands', True)),
            'collect_comments': is_affirmative(obfuscator_options_config.get('collect_comments', True)),
            # Config to enable/disable obfuscation of sql statements with go-sqllexer pkg
            # Valid values for this can be found at https://github.com/DataDog/datadog-agent/blob/main/pkg/obfuscate/obfuscate.go#L108
            'obfuscation_mode': obfuscator_options_config.get('obfuscation_mode', 'obfuscate_and_normalize'),
            'remove_space_between_parentheses': is_affirmative(
                obfuscator_options_config.get('remove_space_between_parentheses', False)
            ),
            'keep_null': is_affirmative(obfuscator_options_config.get('keep_null', False)),
            'keep_boolean': is_affirmative(obfuscator_options_config.get('keep_boolean', False)),
            'keep_positional_parameter': is_affirmative(
                obfuscator_options_config.get('keep_positional_parameter', False)
            ),
            'keep_trailing_semicolon': is_affirmative(obfuscator_options_config.get('keep_trailing_semicolon', False)),
            'keep_identifier_quotation': is_affirmative(
                obfuscator_options_config.get('keep_identifier_quotation', False)
            ),
        }
        self.log_unobfuscated_queries = is_affirmative(instance.get('log_unobfuscated_queries', False))
        self.log_unobfuscated_plans = is_affirmative(instance.get('log_unobfuscated_plans', False))
        self.database_instance_collection_interval = instance.get('database_instance_collection_interval', 1800)
        self.configuration_checks()

    def _build_tags(self, custom_tags):
        tags = list(set(custom_tags)) or []

        rds_tags = rds_parse_tags_from_endpoint(self.host)
        if rds_tags:
            tags.extend(rds_tags)
        return tags

    def configuration_checks(self):
        if self.queries or self.max_custom_queries != DEFAULT_MAX_CUSTOM_QUERIES:
            self.log.warning(
                'The options `queries` and `max_custom_queries` are deprecated and will be '
                'removed in a future release. Use the `custom_queries` option instead.'
            )

        if not (self.host and self.user) and not self.defaults_file:
            raise ConfigurationError("Mysql host and user or a defaults_file are needed.")

        if (self.host or self.user or self.port or self.mysql_sock) and self.defaults_file:
            self.log.warning(
                "Both connection details and defaults_file have been specified, connection details will be ignored"
            )

        if self.mysql_sock and self.host:
            self.log.warning("Both socket and host have been specified, socket will be used")
