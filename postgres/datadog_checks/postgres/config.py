# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional, TypedDict

from datadog_checks.postgres.config_models.defaults import instance_dbstrict, instance_exclude_hostname, instance_ignore_databases, instance_ignore_schemas_owned_by, instance_port

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint
from datadog_checks.base.utils.db.utils import get_agent_host_tags

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200


class PostgresConfig:
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count

    def __init__(self, check: PostgreSql, init_config: dict):
        self.check = check
        self.init_config = init_config

    def initialize(self, instance):
        # type: (dict) -> ValidationResult
        """
        Initialize the Postgres configuration.
        :param instance: dict
            The instance configuration for the Postgres check.
        :param init_config: dict
            The init_config for the Postgres check.
        :return: ConfigResult
            The result of the configuration initialization.
        """
        validation_result = ValidationResult()

        self.exclude_hostname = instance.get("exclude_hostname", instance_exclude_hostname())
        self.database_identifier = instance.get('database_identifier', {})
        self.reported_hostname = instance.get('reported_hostname', '')

        # Connection parameters
        self.host = instance.get('host', '')
        if not self.host:
            validation_result.add_error('Specify a Postgres host to connect to.')
        self.port = instance.get('port', instance_port())
        if self.port != '':
            self.port = int(self.port)
        self.user = instance.get('username', '')
        if not self.user:
            validation_result.add_error('Please specify a user to connect to Postgres.')
        self.password = instance.get('password', '')

        # Database discovery
        self.dbname = instance.get('dbname', 'postgres')
        self.dbstrict = is_affirmative(instance.get('dbstrict', instance_dbstrict()))
        self.discovery_config = instance.get('database_autodiscovery', {"enabled": False})
        if self.discovery_config['enabled'] and self.dbname != 'postgres':
            validation_result.add_error(
                "'dbname' parameter should not be set when `database_autodiscovery` is enabled."
                "To monitor more databases, add them to the `database_autodiscovery` includelist."
            )
        self.ignore_databases = instance.get('ignore_databases', instance_ignore_databases())
        self.collect_default_database = is_affirmative(instance.get('collect_default_database', True))
        if instance.get('collect_default_database') and 'postgres' in instance.get('ignore_databases', []):
            # Our default settings conflict, so we only warn the user if they've explicitly set these values to conflict
            validation_result.add_warning(
                'The `postgres` database cannot be ignored when `collect_default_database` is enabled.'
            )
        if not self.collect_default_database:
            self.ignore_databases = [d for d in self.ignore_databases if d != 'postgres']
        self.ignore_schemas_owned_by = instance.get('ignore_schemas_owned_by', instance_ignore_schemas_owned_by())

        # Connection details
        self.query_timeout = int(instance.get('query_timeout', 5000))
        self.idle_connection_timeout = instance.get('idle_connection_timeout', 60000)
        self.max_connections = instance.get('max_connections', 30)

        # SSL configuration
        ssl = instance.get('ssl', "allow")
        if ssl in SSL_MODES:
            self.ssl_mode = ssl
        else:
            warning = f"Invalid ssl option '{ssl}', should be one of {SSL_MODES}. Defaulting to 'allow'."
            self.check.warning(warning)
            validation_result.add_warning(warning)
            self.ssl_mode = "allow"
        self.ssl_cert = instance.get('ssl_cert', None)
        self.ssl_root_cert = instance.get('ssl_root_cert', None)
        self.ssl_key = instance.get('ssl_key', None)
        self.ssl_password = instance.get('ssl_password', None)

        # Tags and metadata
        self.disable_generic_tags = is_affirmative(instance.get('disable_generic_tags', False)) if instance else False
        self.application_name = instance.get('application_name', 'datadog-agent')
        if not self.application_name.isascii():
            validation_result.add_error(f"Application name can include only ASCII characters: {self.application_name}")
        self.tag_replication_role = is_affirmative(instance.get('tag_replication_role', True))

        # Relation metrics
        self.min_collection_interval = instance.get('min_collection_interval', 15)
        self.relations = instance.get('relations', [])
        self.table_count_limit = instance.get('table_count_limit', TABLE_COUNT_LIMIT)
        self.collect_buffercache_metrics = is_affirmative(instance.get('collect_buffercache_metrics', False))
        self.collect_function_metrics = is_affirmative(instance.get('collect_function_metrics', False))
        # Default value for `count_metrics` is True for backward compatibility
        self.collect_count_metrics = is_affirmative(instance.get('collect_count_metrics', True))
        self.collect_activity_metrics = is_affirmative(instance.get('collect_activity_metrics', False))
        self.collect_checksum_metrics = is_affirmative(instance.get('collect_checksum_metrics', False))
        self.activity_metrics_excluded_aggregations = instance.get('activity_metrics_excluded_aggregations', [])
        self.collect_database_size_metrics = is_affirmative(instance.get('collect_database_size_metrics', True))
        self.collect_wal_metrics = self._should_collect_wal_metrics(instance.get('collect_wal_metrics'))
        self.data_directory = instance.get('data_directory', None)
        if self.collect_wal_metrics and not self.data_directory:
            validation_result.add_error(
                'The `data_directory` parameter must be set when `collect_wal_metrics` is enabled.'
            )
        self.collect_bloat_metrics = is_affirmative(instance.get('collect_bloat_metrics', False))
        self.max_relations = int(instance.get('max_relations', 300))
        if self.relations and not (self.dbname or self.discovery_config['enabled']):
            validation_result.add_error(
                '"dbname" parameter must be set OR autodiscovery must be enabled when using the "relations" parameter.'
            )
        validation_result.add_feature(
            FeatureKey.RELATION_METRICS,
            bool(self.relations),
            "Relation metrics requires a value for `relations` in the configuration." if not self.relations else None,
        )

        self.custom_metrics = self._get_custom_metrics(instance.get('custom_metrics', []))

        # database monitoring adds additional telemetry for query metrics & samples
        self.dbm_enabled = is_affirmative(instance.get('dbm', instance.get('deep_database_monitoring', False)))
        if instance.get('deep_database_monitoring'):
            validation_result.add_warning('The `deep_database_monitoring` option is deprecated. Use `dbm` instead.')

        # Statement samples and explain plans
        self.full_statement_text_cache_max_size = instance.get('full_statement_text_cache_max_size', 10000)
        self.full_statement_text_samples_per_hour_per_query = instance.get(
            'full_statement_text_samples_per_hour_per_query', 1
        )
        # Support a custom view when datadog user has insufficient privilege to see queries
        self.pg_stat_statements_view = instance.get('pg_stat_statements_view', 'pg_stat_statements')
        self.pg_stat_activity_view = instance.get('pg_stat_activity_view', 'pg_stat_activity')
        self.statement_samples_config = instance.get('query_samples', instance.get('statement_samples', {})) or {}
        if instance.get('statement_samples'):
            validation_result.add_warning('The `statement_samples` option is deprecated. Use `query_samples` instead.')
        validation_result.add_feature(FeatureKey.QUERY_SAMPLES, self.statement_samples_config.get('enabled', False))
        if self.statement_samples_config.get('enabled', False) and not self.dbm_enabled:
            validation_result.add_warning('The `query_samples` feature requires the `dbm` option to be enabled.')
        self.settings_metadata_config = instance.get('collect_settings', {}) or {}
        validation_result.add_feature(FeatureKey.COLLECT_SETTINGS, self.settings_metadata_config.get('enabled', False))
        if self.settings_metadata_config.get('enabled', False) and not self.dbm_enabled:
            validation_result.add_warning('The `collect_settings` feature requires the `dbm` option to be enabled.')
        self.schemas_metadata_config = instance.get('collect_schemas', {"enabled": False})
        validation_result.add_feature(FeatureKey.COLLECT_SCHEMAS, self.schemas_metadata_config.get('enabled', False))
        if self.schemas_metadata_config.get('enabled', False) and not self.dbm_enabled:
            validation_result.add_warning('The `collect_schemas` feature requires the `dbm` option to be enabled.')
        self.resources_metadata_config = instance.get('collect_resources', {}) or {}
        validation_result.add_feature(
            FeatureKey.COLLECT_RESOURCES, self.resources_metadata_config.get('enabled', False)
        )
        if self.resources_metadata_config.get('enabled', False) and not self.dbm_enabled:
            validation_result.add_warning('The `collect_resources` feature requires the `dbm` option to be enabled.')
        self.statement_activity_config = instance.get('query_activity', {"enabled": True}) or {}
        validation_result.add_feature(FeatureKey.QUERY_ACTIVITY, self.statement_activity_config.get('enabled', False))
        if self.statement_activity_config.get('enabled', False) and not self.dbm_enabled:
            validation_result.add_warning('The `query_activity` feature requires the `dbm` option to be enabled.')
        self.statement_metrics_config = instance.get('query_metrics', {"enabled": True}) or {}
        validation_result.add_feature(FeatureKey.QUERY_METRICS, self.statement_metrics_config.get('enabled', False))
        if self.statement_metrics_config.get('enabled', False) and not self.dbm_enabled:
            validation_result.add_warning('The `query_metrics` feature requires the `dbm` option to be enabled.')
        self.query_encodings = instance.get('query_encodings')
        self.managed_identity = instance.get('managed_identity', {})
        self.cloud_metadata = {}
        aws = instance.get('aws', {})
        gcp = instance.get('gcp', {})
        azure = instance.get('azure', {})
        # Remap fully_qualified_domain_name to name
        azure = {k if k != 'fully_qualified_domain_name' else 'name': v for k, v in azure.items()}
        if aws:
            try:
                aws['managed_authentication'] = self._aws_managed_authentication(aws, self.password)
            except ConfigurationError as e:
                validation_result.add_error(e)
            self.cloud_metadata.update({'aws': aws})
        if gcp:
            self.cloud_metadata.update({'gcp': gcp})
        if azure:
            try:
                azure['managed_authentication'] = self._azure_managed_authentication(azure, self.managed_identity)
            except ConfigurationError as e:
                validation_result.add_error(e)
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
            'keep_json_path': is_affirmative(obfuscator_options_config.get('keep_json_path', False)),
        }
        collect_raw_query_statement_config: dict = instance.get('collect_raw_query_statement', {}) or {}
        self.collect_raw_query_statement = {
            "enabled": is_affirmative(collect_raw_query_statement_config.get('enabled', False)),
            "cache_max_size": int(collect_raw_query_statement_config.get('cache_max_size', 10000)),
            "samples_per_hour_per_query": int(collect_raw_query_statement_config.get('samples_per_hour_per_query', 1)),
        }
        self.log_unobfuscated_queries = is_affirmative(instance.get('log_unobfuscated_queries', False))
        self.log_unobfuscated_plans = is_affirmative(instance.get('log_unobfuscated_plans', False))
        self.database_instance_collection_interval = instance.get('database_instance_collection_interval', 300)
        self.incremental_query_metrics = is_affirmative(
            self.statement_metrics_config.get('incremental_query_metrics', False)
        )
        self.baseline_metrics_expiry = self.statement_metrics_config.get('baseline_metrics_expiry', 300)
        self.service = instance.get('service') or self.init_config.get('service') or ''

        try:
            self.tags = self._build_tags(
                custom_tags=instance.get('tags', []),
                propagate_agent_tags=self._should_propagate_agent_tags(instance, self.init_config),
                additional_tags=["raw_query_statement:enabled"] if self.collect_raw_query_statement["enabled"] else [],
            )
        except ConfigurationError as e:
            validation_result.add_error(e)

        # Add warnings for common extraneous values
        if instance.get('empty_default_hostname'):
            validation_result.add_warning(
                'The `empty_default_hostname` option has no effect in the Postgres check.'
                'Use the `exclude_hostname` option instead.'
            )

        return validation_result

    def _build_tags(self, custom_tags, propagate_agent_tags, additional_tags):
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

        if propagate_agent_tags:
            try:
                agent_tags = get_agent_host_tags()
                tags.extend(agent_tags)
            except Exception as e:
                raise ConfigurationError(
                    'propagate_agent_tags enabled but there was an error fetching agent tags {}'.format(e)
                )

        if additional_tags:
            tags.extend(additional_tags)
        return tags

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
                for ref, (_, mtype) in m['metrics'].items():
                    cap_mtype = mtype.upper()
                    if cap_mtype not in ('RATE', 'GAUGE', 'MONOTONIC'):
                        raise ConfigurationError(
                            'Collector method {} is not known. Known methods are RATE, GAUGE, MONOTONIC'.format(
                                cap_mtype
                            )
                        )

                    m['metrics'][ref][1] = getattr(PostgresConfig, cap_mtype)
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))
        return custom_metrics

    @staticmethod
    def _aws_managed_authentication(aws, password):
        if 'managed_authentication' not in aws:
            # for backward compatibility
            # if managed_authentication is not set, we assume it is enabled if region is set and password is not set
            managed_authentication = {}
            managed_authentication['enabled'] = 'region' in aws and not password
        else:
            managed_authentication = aws['managed_authentication']
            enabled = is_affirmative(managed_authentication.get('enabled', False))
            if enabled and 'region' not in aws:
                raise ConfigurationError('AWS region must be set when using AWS managed authentication')
            managed_authentication['enabled'] = enabled
        return managed_authentication

    @staticmethod
    def _azure_managed_authentication(azure, managed_identity):
        if 'managed_authentication' not in azure:
            # for backward compatibility
            # if managed_authentication is not set, we assume it is enabled if client_id is set in managed_identity
            managed_authentication = {}
            if managed_identity:
                managed_authentication['enabled'] = 'client_id' in managed_identity
                managed_authentication.update(managed_identity)
            else:
                managed_authentication['enabled'] = False
        else:
            # if managed_authentication is set, we ignore the legacy managed_identity config
            managed_authentication = azure['managed_authentication']
            enabled = is_affirmative(managed_authentication.get('enabled', False))
            if enabled and 'client_id' not in managed_authentication:
                raise ConfigurationError('Azure client_id must be set when using Azure managed authentication')
            managed_authentication['enabled'] = enabled
        return managed_authentication

    @staticmethod
    def _should_collect_wal_metrics(collect_wal_metrics) -> Optional[bool]:
        if collect_wal_metrics is not None:
            # if the user has explicitly set the value, return the boolean
            return is_affirmative(collect_wal_metrics)

        return None

    @staticmethod
    def _should_propagate_agent_tags(instance, init_config) -> bool:
        '''
        return True if the agent tags should be propagated to the check
        '''
        instance_propagate_agent_tags = instance.get('propagate_agent_tags')
        init_config_propagate_agent_tags = init_config.get('propagate_agent_tags')

        if instance_propagate_agent_tags is not None:
            # if the instance has explicitly set the value, return the boolean
            return instance_propagate_agent_tags
        if init_config_propagate_agent_tags is not None:
            # if the init_config has explicitly set the value, return the boolean
            return init_config_propagate_agent_tags
        # if neither the instance nor the init_config has set the value, return False
        return False


class FeatureKey(Enum):
    """
    Enum representing the keys for features in the Postgres configuration.
    """

    RELATION_METRICS = "relation_metrics"
    QUERY_SAMPLES = "query_samples"
    COLLECT_SETTINGS = "collect_settings"
    COLLECT_SCHEMAS = "collect_schemas"
    COLLECT_RESOURCES = "collect_resources"
    QUERY_ACTIVITY = "query_activity"
    QUERY_METRICS = "query_metrics"


FeatureNames = {
    FeatureKey.RELATION_METRICS: 'Relation Metrics',
    FeatureKey.QUERY_SAMPLES: 'Query Samples',
    FeatureKey.COLLECT_SETTINGS: 'Collect Settings',
    FeatureKey.COLLECT_SCHEMAS: 'Collect Schemas',
    FeatureKey.COLLECT_RESOURCES: 'Collect Resources',
    FeatureKey.QUERY_ACTIVITY: 'Query Activity',
    FeatureKey.QUERY_METRICS: 'Query Metrics',
}


class Feature(TypedDict):
    """
    A feature in the Postgres configuration that can be enabled or disabled.
    """

    key: str
    name: str
    enabled: bool
    description: str | None


class ValidationResult:
    """
    A simple class to represent the result of a validation.
    It can be extended in the future to include more details about the validation.
    """

    def __init__(self, valid=True):
        """
        :param valid: Whether the validation passed.
        :param features: A list of features that were validated.
        """
        self.valid = valid
        self.features = []
        self.errors: list[ConfigurationError] = []
        self.warnings: list[str] = []

    def add_feature(self, feature: FeatureKey, enabled=True, description: Optional[str] = None):
        """
        Add a feature to the validation result.
        :param feature: The feature to add.
        :param enabled: Whether the feature is enabled.
        """
        self.features.append(
            {"key": feature, "name": FeatureNames[feature], "enabled": enabled, "description": description}
        )

    def add_error(self, error: str | ConfigurationError):
        """
        Add an error to the validation result.
        :param error: The error message to add.
        """
        self.errors.append(ConfigurationError(error) if isinstance(error, str) else error)
        self.valid = False

    def add_warning(self, warning: str):
        """
        Add a warning to the validation result.
        :param warning: The warning message to add.
        """
        self.warnings.append(warning)
