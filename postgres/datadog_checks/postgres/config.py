# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional, Tuple, TypedDict

from datadog_checks.postgres.config_models import InstanceConfig
from datadog_checks.postgres.config_models.defaults import (
    instance_activity_metrics_excluded_aggregations,
    instance_application_name,
    instance_collect_activity_metrics,
    instance_collect_bloat_metrics,
    instance_collect_buffercache_metrics,
    instance_collect_checksum_metrics,
    instance_collect_count_metrics,
    instance_collect_database_size_metrics,
    instance_collect_default_database,
    instance_collect_function_metrics,
    instance_collect_wal_metrics,
    instance_data_directory,
    instance_database_instance_collection_interval,
    instance_dbm,
    instance_dbname,
    instance_dbstrict,
    instance_disable_generic_tags,
    instance_empty_default_hostname,
    instance_exclude_hostname,
    instance_idle_connection_timeout,
    instance_ignore_databases,
    instance_ignore_schemas_owned_by,
    instance_log_unobfuscated_plans,
    instance_log_unobfuscated_queries,
    instance_max_connections,
    instance_max_relations,
    instance_min_collection_interval,
    instance_pg_stat_activity_view,
    instance_pg_stat_statements_view,
    instance_port,
    instance_propagate_agent_tags,
    instance_query_timeout,
    instance_relations,
    instance_reported_hostname,
    instance_ssl,
    instance_table_count_limit,
    instance_tag_replication_role,
    shared_propagate_agent_tags,
)

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint
from datadog_checks.base.utils.db.utils import get_agent_host_tags

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200


class PostgresConfig(InstanceConfig):
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count

    def __init__(self, check: PostgreSql, init_config: dict):
        self._check = check
        self._init_config = init_config

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
            self._check.warning(warning)
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
        self.min_collection_interval = instance.get('min_collection_interval', instance_min_collection_interval())
        self.relations = instance.get('relations', instance_relations())
        self.table_count_limit = instance.get('table_count_limit', instance_table_count_limit())
        self.collect_buffercache_metrics = is_affirmative(
            instance.get('collect_buffercache_metrics', instance_collect_buffercache_metrics())
        )
        self.collect_function_metrics = is_affirmative(
            instance.get('collect_function_metrics', instance_collect_function_metrics())
        )
        # Default value for `count_metrics` is True for backward compatibility
        self.collect_count_metrics = is_affirmative(
            instance.get('collect_count_metrics', instance_collect_count_metrics())
        )
        self.collect_activity_metrics = is_affirmative(
            instance.get('collect_activity_metrics', instance_collect_activity_metrics())
        )
        self.collect_checksum_metrics = is_affirmative(
            instance.get('collect_checksum_metrics', instance_collect_checksum_metrics())
        )
        self.activity_metrics_excluded_aggregations = instance.get(
            'activity_metrics_excluded_aggregations', instance_activity_metrics_excluded_aggregations()
        )
        self.collect_database_size_metrics = is_affirmative(
            instance.get('collect_database_size_metrics', instance_collect_database_size_metrics())
        )
        self.collect_wal_metrics = self._should_collect_wal_metrics(
            instance.get('collect_wal_metrics', instance_collect_wal_metrics())
        )
        self.data_directory = instance.get('data_directory', instance_data_directory())
        if self.collect_wal_metrics and not self.data_directory:
            validation_result.add_error(
                'The `data_directory` parameter must be set when `collect_wal_metrics` is enabled.'
            )
        self.collect_bloat_metrics = is_affirmative(
            instance.get('collect_bloat_metrics', instance_collect_bloat_metrics())
        )
        self.max_relations = int(instance.get('max_relations', instance_max_relations()))
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
        if instance.get('custom_metrics', []):
            validation_result.add_warning('The `custom_metrics` option is deprecated. Use `custom_queries` instead.')

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
        self.service = instance.get('service') or self._init_config.get('service') or ''

        try:
            self.tags = self._build_tags(
                custom_tags=instance.get('tags', []),
                propagate_agent_tags=self._should_propagate_agent_tags(instance, self._init_config),
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
    QUERY_ACTIVITY = "query_activity"
    QUERY_METRICS = "query_metrics"


FeatureNames = {
    FeatureKey.RELATION_METRICS: 'Relation Metrics',
    FeatureKey.QUERY_SAMPLES: 'Query Samples',
    FeatureKey.COLLECT_SETTINGS: 'Collect Settings',
    FeatureKey.COLLECT_SCHEMAS: 'Collect Schemas',
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


def build_config(check: PostgreSql, init_config: dict, instance: dict) -> Tuple[InstanceConfig, ValidationResult]:
    """
    Build the Postgres configuration.
    :param check: The check instance.
    :param init_config: The init_config for the Postgres check.
    :param instance: The instance configuration for the Postgres check.
    :return: InstanceConfig
        The instance configuration object.
    """

    # Spec doesn't support dictionary defaults, so we use dict literals here
    # Spec also doesn't support some hidden defaults
    # If you change a literal value here, make sure to update spec.yaml
    args = {
        # Basic connection parameters
        "host": instance.get('host'),
        # Set the default port to None if the host is a socket path
        "port": instance.get('port', instance_port() if not instance.get('host', '').startswith('/') else None),
        "username": instance.get('username'),
        "password": instance.get('password'),
        "dbname": instance.get('dbname', instance_dbname()),
        # SSL
        "ssl": instance.get('ssl', instance_ssl()),
        "ssl_cert": instance.get('ssl_cert'),
        "ssl_root_cert": instance.get('ssl_root_cert'),
        "ssl_key": instance.get('ssl_key'),
        "ssl_password": instance.get('ssl_password'),
        # Database configuration
        "dbm": instance.get('dbm', instance_dbm()),
        "deep_database_monitoring": instance.get('deep_database_monitoring', False),  # Deprecated, use `dbm` instead
        "custom_metrics": instance.get('custom_metrics', []),
        "application_name": instance.get('application_name', instance_application_name()),
        "exclude_hostname": instance.get('exclude_hostname', instance_exclude_hostname()),
        "database_identifier": instance.get('database_identifier', {"template": "$resolved_hostname"}),
        "reported_hostname": instance.get('reported_hostname', instance_reported_hostname()),
        "dbstrict": instance.get('dbstrict', instance_dbstrict()),
        "database_autodiscovery": {
            **{
                "enabled": False,
                "global_view_db": "postgres",
                "max_databases": 100,
                "include": [".*"],
                "exclude": ["cloudsqladmin"],
                "refresh": 600,
            },
            **(instance.get('database_autodiscovery', {})),
        },
        "ignore_databases": instance.get('ignore_databases', instance_ignore_databases()),
        "collect_default_database": instance.get('collect_default_database', instance_collect_default_database()),
        "ignore_schemas_owned_by": instance.get('ignore_schemas_owned_by', instance_ignore_schemas_owned_by()),
        "query_timeout": instance.get('query_timeout', instance_query_timeout()),
        "idle_connection_timeout": instance.get('idle_connection_timeout', instance_idle_connection_timeout()),
        "max_connections": instance.get('max_connections', instance_max_connections()),
        "disable_generic_tags": instance.get('disable_generic_tags', instance_disable_generic_tags()),
        "tag_replication_role": instance.get('tag_replication_role', instance_tag_replication_role()),
        # Query metrics
        "min_collection_interval": instance.get('min_collection_interval', instance_min_collection_interval()),
        "relations": instance.get('relations', instance_relations()),
        "table_count_limit": instance.get('table_count_limit', instance_table_count_limit()),
        "collect_buffercache_metrics": instance.get(
            'collect_buffercache_metrics', instance_collect_buffercache_metrics()
        ),
        "collect_function_metrics": instance.get('collect_function_metrics', instance_collect_function_metrics()),
        "collect_count_metrics": instance.get('collect_count_metrics', instance_collect_count_metrics()),
        "collect_activity_metrics": instance.get('collect_activity_metrics', instance_collect_activity_metrics()),
        "collect_checksum_metrics": instance.get('collect_checksum_metrics', instance_collect_checksum_metrics()),
        "activity_metrics_excluded_aggregations": instance.get(
            'activity_metrics_excluded_aggregations', instance_activity_metrics_excluded_aggregations()
        ),
        "collect_database_size_metrics": instance.get(
            'collect_database_size_metrics', instance_collect_database_size_metrics()
        ),
        "collect_wal_metrics": instance.get('collect_wal_metrics', instance_collect_wal_metrics()),
        "data_directory": instance.get('data_directory', instance_data_directory()),
        "collect_bloat_metrics": instance.get('collect_bloat_metrics', instance_collect_bloat_metrics()),
        "max_relations": instance.get('max_relations', instance_max_relations()),
        # Statement samples and explain plans
        "pg_stat_statements_view": instance.get('pg_stat_statements_view', instance_pg_stat_statements_view()),
        "pg_stat_activity_view": instance.get('pg_stat_activity_view', instance_pg_stat_activity_view()),
        "query_samples": {
            **{
                "enabled": True,
                "collection_interval": 1,
                "explain_function": "datadog.explain_statement",
                "explained_queries_per_hour_per_query": 60,
                "samples_per_hour_per_query": 15,
                "explained_queries_cache_maxsize": 5000,
                "seen_samples_cache_maxsize": 10000,
                "explain_parameterized_queries": True,
                "run_sync": False,
            },
            **(instance.get('statement_samples', {})),  # Deprecated, use `query_samples` instead
            **(instance.get('query_samples', {})),
        },
        # Metadata collection
        "collect_settings": {
            **{
                "enabled": False,
                "collection_interval": 600,
                "ignored_settings_patterns": ["plpgsql%"],
            },
            **(instance.get('collect_settings') or {}),
        },
        "collect_schemas": {
            **{
                "enabled": False,
                "max_tables": 300,
                "max_columns": 50,
                "collection_interval": 600,
                "include_databases": [],
                "exclude_databases": [],
                "include_schemas": [],
                "exclude_schemas": [],
                "include_tables": [],
                "exclude_tables": [],
            },
            **(instance.get('collect_schemas', {})),
        },
        # Cloud
        "aws": {
            **{
                "instance_endpoint": "",
                "region": None,
                "managed_authentication": {
                    "enabled": False,
                    "role_arn": "",
                },
            },
            **(instance.get('aws', {})),
        },
        "gcp": {
            **{
                "project_id": "",
                "instance_id": "",
            },
            **(instance.get('gcp', {})),
        },
        "azure": {
            **{
                "client_id": "",
                "identity_scope": "",
                "enabled": False,
            },
            **(
                instance.get('azure', instance.get('managed_authentication', {}))
            ),  # managed_authentication is deprecated
        },
        # Obfuscation and query logging
        "obfuscator_options": {
            **{
                "obfuscation_mode": "obfuscate_and_normalize",
                "replace_digits": False,
                "collect_metadata": True,
                "collect_tables": True,
                "collect_commands": True,
                "collect_comments": True,
                "keep_sql_alias": True,
                "keep_dollar_quoted_func": True,
                "remove_space_between_parentheses": False,
                "keep_null": False,
                "keep_boolean": False,
                "keep_positional_parameter": False,
                "keep_trailing_semicolon": False,
                "keep_identifier_quotation": False,
                "keep_json_path": False,
            },
            **(instance.get('obfuscator_options', {})),
        },
        "collect_raw_query_statement": {
            **{"enabled": False},
            **(instance.get('collect_raw_query_statement', {})),
        },
        "log_unobfuscated_queries": instance.get('log_unobfuscated_queries', instance_log_unobfuscated_queries()),
        "log_unobfuscated_plans": instance.get('log_unobfuscated_plans', instance_log_unobfuscated_plans()),
        "database_instance_collection_interval": instance.get(
            'database_instance_collection_interval', instance_database_instance_collection_interval()
        ),
        "incremental_query_metrics": instance.get('incremental_query_metrics', False),
        "baseline_metrics_expiry": instance.get('baseline_metrics_expiry', 300),
        "propagate_agent_tags": instance.get('propagate_agent_tags', instance_propagate_agent_tags())
        or init_config.get('propagate_agent_tags', shared_propagate_agent_tags()),
        "empty_default_hostname": instance.get('empty_default_hostname', instance_empty_default_hostname()),
    }

    validation_result = ValidationResult()

    tags, tag_errors = build_tags(instance=instance, init_config=init_config, config=args)
    args['tags'] = tags
    for error in tag_errors:
        # If there are errors in the tags, we add them to the validation result
        # but we don't raise an exception here, as we want to validate the rest of the configuration
        validation_result.add_error(error)

    # Validate that the keys of args match the fields of InstanceConfig
    instance_config_fields = set(InstanceConfig.__annotations__.keys())
    args_keys = set(args.keys())
    missing_fields = instance_config_fields - args_keys
    extra_fields = args_keys - instance_config_fields
    if missing_fields or extra_fields:
        # This should get caught at test time and never execute at runtime
        raise ConfigurationError(
            f"build_config: args keys do not match InstanceConfig fields. "
            f"Missing: {missing_fields}, Extra: {extra_fields}"
        )

    if not args.collect_default_database:
        args.ignore_databases = [d for d in args.ignore_databases if d != 'postgres']

    # Validate config arguments for invalid or deprecated options
    if args.ssl not in SSL_MODES:
        warning = f"Invalid ssl option '{args.ssl}', should be one of {SSL_MODES}. Defaulting to 'allow'."
        validation_result.add_warning(warning)
        args.ssl = "allow"

    if instance.get('custom_metrics'):
        validation_result.add_warning('The `custom_metrics` option is deprecated. Use `custom_queries` instead.')

    if instance.get('deep_database_monitoring'):
        validation_result.add_warning('The `deep_database_monitoring` option is deprecated. Use `dbm` instead.')

    if instance.get('managed_authentication'):
        validation_result.add_warning(
            'The `managed_authentication` option is deprecated. Use `azure.managed_authentication` instead.'
        )
    if instance.get('statement_samples'):
        validation_result.add_warning('The `statement_samples` option is deprecated. Use `query_samples` instead.')

    # Check user provided value because the default configuration would trigger this warning
    if instance.get('collect_default_database', False) and 'postgres' in instance.get('ignore_databases', []):
        validation_result.add_warning(
            'The `postgres` database cannot be ignored when `collect_default_database` is enabled.'
        )

    config = InstanceConfig(**args)

    # Validate config after defaults have been applied
    if not config.application_name.isascii():
        validation_result.add_error(f"Application name can include only ASCII characters: {config.application_name}")

    if config.collect_wal_metrics and not config.data_directory:
        validation_result.add_error('The `data_directory` parameter must be set when `collect_wal_metrics` is enabled.')

    if config.relations and not (config.dbname or config.database_autodiscovery.get('enabled', False)):
        validation_result.add_error(
            '"dbname" parameter must be set OR autodiscovery must be enabled when using the "relations" parameter.'
        )

    if config.empty_default_hostname:
        validation_result.add_warning(
            'The `empty_default_hostname` option has no effect in the Postgres check.'
            'Use the `exclude_hostname` option instead.'
        )

    # Features
    validation_result.add_feature(
        FeatureKey.RELATION_METRICS,
        bool(config.relations),
        "Relation metrics requires a value for `relations` in the configuration." if not config.relations else None,
    )

    statement_samples_config = config.query_samples or config.statement_samples or {}
    if config.statement_samples:
        validation_result.add_warning('The `statement_samples` option is deprecated. Use `query_samples` instead.')
    validation_result.add_feature(FeatureKey.QUERY_SAMPLES, statement_samples_config.get('enabled', False))
    if statement_samples_config.get('enabled', False) and not config.dbm:
        validation_result.add_warning('The `query_samples` feature requires the `dbm` option to be enabled.')

    settings_metadata_config = config.collect_settings or {}
    validation_result.add_feature(FeatureKey.COLLECT_SETTINGS, settings_metadata_config.get('enabled', False))
    if settings_metadata_config.get('enabled', False) and not config.dbm:
        validation_result.add_warning('The `collect_settings` feature requires the `dbm` option to be enabled.')

    schemas_metadata_config = config.collect_schemas or {"enabled": False}
    validation_result.add_feature(FeatureKey.COLLECT_SCHEMAS, schemas_metadata_config.get('enabled', False))
    if schemas_metadata_config.get('enabled', False) and not config.dbm:
        validation_result.add_warning('The `collect_schemas` feature requires the `dbm` option to be enabled.')

    statement_activity_config = config.query_activity or {"enabled": True}
    validation_result.add_feature(FeatureKey.QUERY_ACTIVITY, statement_activity_config.get('enabled', False))
    if statement_activity_config.get('enabled', False) and not config.dbm:
        validation_result.add_warning('The `query_activity` feature requires the `dbm` option to be enabled.')

    statement_metrics_config = config.query_metrics or {"enabled": True}
    validation_result.add_feature(FeatureKey.QUERY_METRICS, statement_metrics_config.get('enabled', False))
    if statement_metrics_config.get('enabled', False) and not config.dbm:
        validation_result.add_warning('The `query_metrics` feature requires the `dbm` option to be enabled.')

    return config, validation_result


def build_tags(instance: dict, init_config: dict, config: dict) -> Tuple[list[str], list[ConfigurationError]]:
    tags = list(set(instance.get('tags', [])))

    # preset tags to host
    if not instance.get('disable_generic_tags', instance_disable_generic_tags()):
        tags.append('server:{}'.format(config.get('host')))
    if config.get('port'):
        tags.append('port:{}'.format(config.get('port')))
    else:
        tags.append('port:socket')

    if instance.get('service'):
        tags.append('service:{}'.format(instance.get('service')))
    elif init_config.get('service'):
        tags.append('service:{}'.format(init_config.get('service')))

    # preset tags to the database name
    tags.extend(["db:%s" % config.get('dbname')])

    rds_tags = rds_parse_tags_from_endpoint(config.get('host'))
    if rds_tags:
        tags.extend(rds_tags)

    errors = []
    if instance.get('propagate_agent_tags'):
        try:
            agent_tags = get_agent_host_tags()
            tags.extend(agent_tags)
        except Exception as e:
            errors.append(
                ConfigurationError(
                    'propagate_agent_tags enabled but there was an error fetching agent tags {}'.format(e)
                )
            )

    tags.extend(["raw_query_statement:enabled"] if config.get('collect_raw_query_statement', {}).get("enabled") else [])

    return tags, errors
