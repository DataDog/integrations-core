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
    instance_only_custom_queries,
    instance_pg_stat_activity_view,
    instance_pg_stat_statements_view,
    instance_port,
    instance_propagate_agent_tags,
    instance_query_encodings,
    instance_query_timeout,
    instance_relations,
    instance_reported_hostname,
    instance_ssl,
    instance_table_count_limit,
    instance_tag_replication_role,
    instance_use_global_custom_queries,
    shared_propagate_agent_tags,
)
from datadog_checks.postgres.metadata import (
    DEFAULT_SCHEMAS_COLLECTION_INTERVAL,
    DEFAULT_SETTINGS_COLLECTION_INTERVAL,
    DEFAULT_SETTINGS_IGNORED_PATTERNS,
)
from datadog_checks.postgres.statement_samples import (
    DEFAULT_ACTIVITY_COLLECTION_INTERVAL as DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL,
)
from datadog_checks.postgres.statement_samples import (
    DEFAULT_COLLECTION_INTERVAL as DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL,
)
from datadog_checks.postgres.statements import DEFAULT_COLLECTION_INTERVAL as DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL

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
        self.features: list[Feature] = []
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
        "dbm": instance.get(
            'dbm', instance.get('deep_database_monitoring', instance_dbm())
        ),  # Deprecated, use `dbm` instead
        "custom_metrics": map_custom_metrics(
            instance.get('custom_metrics', [])
        ),  # Deprecated, use `custom_queries` instead
        "custom_queries": instance.get('custom_queries', []),
        "use_global_custom_queries": instance.get("use_global_custom_queries", instance_use_global_custom_queries()),
        "only_custom_queries": instance.get('only_custom_queries', instance_only_custom_queries()),
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
        "query_metrics": {
            **{
                "enabled": True,
                "collection_interval": DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL,
                "pg_stat_statements_max_warning_threshold": 10000,
                "incremental_query_metrics": False,
                "baseline_metrics_expiry": 300,
                "full_statement_text_cache_max_size": 10000,
                "full_statement_text_samples_per_hour_per_query": 10000,
                "run_sync": False,
                "batch_max_content_size": init_config.get('metrics', {}).get('batch_max_content_size', 20_000_000),
            },
            **(instance.get('query_metrics', {})),
        },
        "query_samples": {
            **{
                "enabled": True,
                "collection_interval": DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL,
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
        "query_activity": {
            **{
                "enabled": True,
                "collection_interval": DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL,
                "payload_row_limit": 3500,
            },
            **(instance.get('query_activity', {})),
        },
        "query_encodings": instance.get('query_encodings', instance_query_encodings()),
        # Metadata collection
        "collect_settings": {
            **{
                "enabled": False,
                "collection_interval": DEFAULT_SETTINGS_COLLECTION_INTERVAL,
                "ignored_settings_patterns": DEFAULT_SETTINGS_IGNORED_PATTERNS,
            },
            **(instance.get('collect_settings') or {}),
        },
        "collect_schemas": {
            **{
                "enabled": False,
                "max_tables": 300,
                "max_columns": 50,
                "collection_interval": DEFAULT_SCHEMAS_COLLECTION_INTERVAL,
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
                "deployment_type": "",
                "fully_qualified_domain_name": "",
                "managed_authentication": {
                    **{
                        "enabled": False,
                        "client_id": "",
                        "identity_scope": "",
                    },
                    # Handle legacy managed_authentication
                    **instance.get('managed_authentication', {}),
                },
            },
            **(instance.get('azure', {})),
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
        "propagate_agent_tags": instance.get('propagate_agent_tags', instance_propagate_agent_tags())
        or init_config.get('propagate_agent_tags', shared_propagate_agent_tags()),
        "empty_default_hostname": instance.get('empty_default_hostname', instance_empty_default_hostname()),
        "service": instance.get('service', init_config.get('service', None)),
        # Metric filtering by pattern is implemented downstream, theoretically
        "metric_patterns": instance.get('metric_patterns', None),
    }

    validation_result = ValidationResult()

    if args['query_metrics']['collection_interval'] <= 0:
        args['query_metrics']['collection_interval'] = DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL
        validation_result.add_warning(
            "query_metrics.collection_interval must be greater than 0, defaulting to"
            f"{DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL} seconds."
        )

    if args['query_samples']['collection_interval'] <= 0:
        args['query_samples']['collection_interval'] = DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL
        validation_result.add_warning(
            "query_samples.collection_interval must be greater than 0, defaulting to"
            f"{DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL} seconds."
        )

    if args['query_activity']['collection_interval'] <= 0:
        args['query_activity']['collection_interval'] = DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL
        validation_result.add_warning(
            "query_activity.collection_interval must be greater than 0, defaulting to"
            f"{DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL} seconds."
        )

    tags, tag_errors = build_tags(instance=instance, init_config=init_config, config=args)
    args['tags'] = tags
    for error in tag_errors:
        # If there are errors in the tags, we add them to the validation result
        # but we don't raise an exception here, as we want to validate the rest of the configuration
        validation_result.add_error(error)

    # AWS backfill and validation
    if (
        not instance.get("aws", {}).get("managed_authentication", None)
        and args['aws']['region']
        and not args['aws']['password']
    ):
        # if managed_authentication is not set, we assume it is enabled if region is set and password is not set
        args['aws']['managed_authentication']['enabled'] = True

    if args['aws']['managed_authentication']['enabled'] and not args['aws']['region']:
        validation_result.add_error('AWS region must be set when using AWS managed authentication')

    # Azure backfill and validation
    if (
        not instance.get("azure", {}).get("managed_authentication", None)
        and args['azure']['managed_authentication']['client_id']
    ):
        # if managed_authentication is not set, we assume it is enabled if client_id is set
        args['azure']['managed_authentication']['enabled'] = True

    if args['azure']['managed_authentication']['enabled'] and not args['azure']['managed_authentication']['client_id']:
        validation_result.add_error('Azure client_id must be set when using Azure managed authentication')

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

    if not args.get('collect_default_database'):
        args['ignore_databases'] = [d for d in args['ignore_databases'] if d != 'postgres']

    # Validate config arguments for invalid or deprecated options
    if args['ssl'] not in SSL_MODES:
        warning = f"Invalid ssl option '{args['ssl']}', should be one of {SSL_MODES}. Defaulting to 'allow'."
        validation_result.add_warning(warning)
        args['ssl'] = "allow"

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

    # Validate required fields
    if not config.host:
        validation_result.add_error("Please specify a valid host to connect to using the `host` parameter.")

    if not config.username:
        validation_result.add_error("Please specify a user to connect to the database using the `username` parameter.")

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

    validation_result.add_feature(FeatureKey.QUERY_ACTIVITY, config.query_activity.enabled and config.dbm)
    if config.query_activity.enabled and not config.dbm:
        validation_result.add_warning('The `query_activity` feature requires the `dbm` option to be enabled.')

    validation_result.add_feature(FeatureKey.QUERY_SAMPLES, config.query_samples.enabled and config.dbm)
    if config.query_samples.enabled and not config.dbm:
        validation_result.add_warning('The `query_samples` feature requires the `dbm` option to be enabled.')

    validation_result.add_feature(FeatureKey.QUERY_METRICS, config.query_metrics.enabled and config.dbm)
    if config.query_metrics.enabled and not config.dbm:
        validation_result.add_warning('The `query_metrics` feature requires the `dbm` option to be enabled.')

    validation_result.add_feature(FeatureKey.COLLECT_SETTINGS, config.collect_settings.enabled and config.dbm)
    if config.collect_settings.enabled and not config.dbm:
        validation_result.add_warning('The `collect_settings` feature requires the `dbm` option to be enabled.')

    validation_result.add_feature(FeatureKey.COLLECT_SCHEMAS, config.collect_schemas.enabled and config.dbm)
    if config.collect_schemas.enabled and not config.dbm:
        validation_result.add_warning('The `collect_schemas` feature requires the `dbm` option to be enabled.')

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


def map_custom_metrics(custom_metrics):
    # Pre-process custom metrics and verify definition
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
                        'Collector method {} is not known. Known methods are RATE, GAUGE, MONOTONIC'.format(cap_mtype)
                    )

                m['metrics'][ref][1] = getattr(PostgresConfig, cap_mtype)
        except Exception as e:
            raise Exception('Error processing custom metric `{}`: {}'.format(m, e))
    return custom_metrics


def sanitize(config: InstanceConfig) -> dict:
    sanitized = config.model_dump(exclude=['custom_metrics', 'custom_queries'])
    sanitized['password'] = '***' if sanitized.get('password') else None
    sanitized['ssl_password'] = '***' if sanitized.get('ssl_password') else None
    
    return sanitized
