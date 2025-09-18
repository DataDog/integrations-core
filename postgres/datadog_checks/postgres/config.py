# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from __future__ import annotations

import copy
from enum import Enum
from typing import TYPE_CHECKING, Optional, Tuple, TypedDict

from datadog_checks.postgres.config_models import InstanceConfig
from datadog_checks.postgres.config_models.defaults import (
    instance_dbm,
    instance_disable_generic_tags,
    instance_port,
    instance_propagate_agent_tags,
)
from datadog_checks.postgres.config_models.instance import (
    Aws,
    Azure,
    Gcp,
    ManagedAuthentication,
    ManagedAuthentication1,
    Union,
)
from datadog_checks.postgres.discovery import (
    DEFAULT_MAX_DATABASES,
)
from datadog_checks.postgres.discovery import (
    DEFAULT_REFRESH as DEFAULT_AUTODISCOVERY_REFRESH_INTERVAL,
)
from datadog_checks.postgres.metadata import (
    DEFAULT_SCHEMAS_COLLECTION_INTERVAL,
    DEFAULT_SETTINGS_COLLECTION_INTERVAL,
    DEFAULT_SETTINGS_IGNORED_PATTERNS,
)
from datadog_checks.postgres.relationsmanager import RelationsManager
from datadog_checks.postgres.statement_samples import (
    DEFAULT_ACTIVITY_COLLECTION_INTERVAL as DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL,
)
from datadog_checks.postgres.statement_samples import (
    DEFAULT_COLLECTION_INTERVAL as DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL,
)
from datadog_checks.postgres.statements import DEFAULT_COLLECTION_INTERVAL as DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint
from datadog_checks.base.utils.db.utils import get_agent_host_tags

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200


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

    args = {}
    # Automatically set values that support defaults or that have simple values in the instance
    import importlib

    instance_config_fields = set(InstanceConfig.__annotations__.keys())
    defaults = importlib.import_module("datadog_checks.postgres.config_models.defaults")
    for f in instance_config_fields:
        try:
            args[f] = getattr(defaults, f"instance_{f}")()
        except AttributeError:
            args[f] = None
        if f in instance:
            args[f] = instance[f]

    # Set values for args that have deprecated fallbacks, are not supported by the spec model
    # or have other complexities
    args.update(
        {
            # Set the default port to None if the host is a socket path
            "port": instance.get('port', instance_port() if not instance.get('host', '').startswith('/') else None),
            # Set None values for ssl
            # Database configuration
            "dbm": instance.get(
                'dbm', instance.get('deep_database_monitoring', instance_dbm())
            ),  # Deprecated, use `dbm` instead
            "custom_metrics": map_custom_metrics(
                instance.get('custom_metrics', [])
            ),  # Deprecated, use `custom_queries` instead
            "custom_queries": instance.get('custom_queries', []),
            "database_identifier": instance.get('database_identifier', {"template": "$resolved_hostname"}),
            "database_autodiscovery": {
                **{
                    "enabled": False,
                    "global_view_db": "postgres",
                    "max_databases": DEFAULT_MAX_DATABASES,
                    "include": [".*"],
                    "exclude": ["cloudsqladmin"],
                    "refresh": DEFAULT_AUTODISCOVERY_REFRESH_INTERVAL,
                },
                **(instance.get('database_autodiscovery', {})),
            },
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
            # Metadata collection
            "collect_settings": {
                **{
                    "enabled": False,
                    "collection_interval": DEFAULT_SETTINGS_COLLECTION_INTERVAL,
                    "ignored_settings_patterns": DEFAULT_SETTINGS_IGNORED_PATTERNS,
                    "run_sync": False,
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
                **Aws(managed_authentication=ManagedAuthentication()).model_dump(),
                **(instance.get('aws', {})),
            },
            "gcp": {
                **Gcp().model_dump(),
                **(instance.get('gcp', {})),
            },
            "azure": {
                **Azure(managed_authentication=ManagedAuthentication1()).model_dump(),
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
            "locks_idle_in_transaction": {
                **{
                    "enabled": True,
                    "collection_interval": 300,
                    "max_rows": 100,
                },
                **(instance.get('locks_idle_in_transaction', {})),
            },
            "propagate_agent_tags": should_propagate_agent_tags(instance=instance, init_config=init_config),
            "service": instance.get('service', init_config.get('service', None)),
            # Metric filtering by pattern is implemented downstream, theoretically
            "metric_patterns": instance.get('metric_patterns', None),
        }
    )

    validation_result = ValidationResult()

    if safefloat(args['query_metrics']['collection_interval']) <= 0:
        args['query_metrics']['collection_interval'] = DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL
        validation_result.add_warning(
            "query_metrics.collection_interval must be greater than 0, defaulting to "
            f"{DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL} seconds."
        )

    if safefloat(args['query_samples']['collection_interval']) <= 0:
        args['query_samples']['collection_interval'] = DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL
        validation_result.add_warning(
            "query_samples.collection_interval must be greater than 0, defaulting to "
            f"{DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL} seconds."
        )

    if safefloat(args['query_activity']['collection_interval']) <= 0:
        args['query_activity']['collection_interval'] = DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL
        validation_result.add_warning(
            "query_activity.collection_interval must be greater than 0, defaulting to "
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
        and args['aws'].get('region')
        and not args['password']
    ):
        # if managed_authentication is not set, we assume it is enabled if region is set and password is not set
        args['aws']['managed_authentication']['enabled'] = True

    if args['aws']['managed_authentication']['enabled'] and not args['aws']['region']:
        validation_result.add_error('AWS region must be set when using AWS managed authentication')

    # Azure backfill and validation
    if not instance.get("azure", {}).get("managed_authentication", None) and (
        args['azure'].get('managed_authentication', {}).get('client_id')
        or instance.get('managed_identity', {}).get('client_id')
    ):
        # if managed_authentication is not set, we assume it is enabled if client_id is set
        args['azure']['managed_authentication']['enabled'] = True

    if instance.get("managed_identity"):
        validation_result.add_warning(
            'The `managed_identity` option is deprecated. Use `azure.managed_authentication` instead.'
        )
        args['azure']['managed_authentication'] = {
            **args['azure']['managed_authentication'],
            **instance.get('managed_identity', {}),
        }

    if args['azure'].get('managed_authentication', {}).get('enabled') and not args['azure'].get(
        'managed_authentication', {}
    ).get('client_id'):
        validation_result.add_error('Azure client_id must be set when using Azure managed authentication')

    if args.get('collect_default_database'):
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

    # Validate that the keys of args match the fields of InstanceConfig
    args_keys = set(args.keys())
    missing_fields = instance_config_fields - args_keys
    extra_fields = args_keys - instance_config_fields
    if missing_fields or extra_fields:
        # This should get caught at test time and never execute at runtime
        raise ConfigurationError(
            f"build_config: args keys do not match InstanceConfig fields. "
            f"Missing: {missing_fields}, Extra: {extra_fields}"
        )

    # The current InstanceConfig cannot be instantiated directly and integrations team is reluctant to fix it
    # in case existing integrations use the faulty behavior.
    # Instead we copy the behavior of the base check and instantiate this way
    config = InstanceConfig.model_validate(args, context={"configured_fields": instance_config_fields})

    # Validate required fields
    if not config.host:
        validation_result.add_error("Please specify a valid host to connect to using the `host` parameter.")

    if not config.username:
        validation_result.add_error("Please specify a user to connect to the database using the `username` parameter.")

    # Validate config after defaults have been applied
    if not config.application_name.isascii():
        validation_result.add_error(f"Application name can include only ASCII characters: {config.application_name}")

    if config.relations and not (config.dbname or config.database_autodiscovery.enabled):
        validation_result.add_error(
            '"dbname" parameter must be set OR autodiscovery must be enabled when using the "relations" parameter.'
        )

    if config.empty_default_hostname:
        validation_result.add_warning(
            'The `empty_default_hostname` option has no effect in the Postgres check. '
            'Use the `exclude_hostname` option instead.'
        )

    try:
        RelationsManager.validate_relations_config(list(config.relations))
    except ConfigurationError as e:
        validation_result.add_error(e)

    # Features
    validation_result.add_feature(
        FeatureKey.RELATION_METRICS,
        bool(config.relations),
        "Relation metrics requires a value for `relations` in the configuration." if not config.relations else None,
    )
    validation_result.add_feature(FeatureKey.QUERY_ACTIVITY, config.query_activity.enabled and config.dbm)
    validation_result.add_feature(FeatureKey.QUERY_SAMPLES, config.query_samples.enabled and config.dbm)
    validation_result.add_feature(FeatureKey.QUERY_METRICS, config.query_metrics.enabled and config.dbm)
    validation_result.add_feature(FeatureKey.COLLECT_SETTINGS, config.collect_settings.enabled and config.dbm)
    validation_result.add_feature(FeatureKey.COLLECT_SCHEMAS, config.collect_schemas.enabled and config.dbm)

    # If instance config explicitly enables these features, we add a warning if dbm is not enabled
    if instance.get('query_activity', {}).get('enabled') and not config.dbm:
        validation_result.add_warning('The `query_activity` feature requires the `dbm` option to be enabled.')
    if instance.get('query_samples', {}).get('enabled') and not config.dbm:
        validation_result.add_warning('The `query_samples` feature requires the `dbm` option to be enabled.')
    if instance.get('query_metrics', {}).get('enabled') and not config.dbm:
        validation_result.add_warning('The `query_metrics` feature requires the `dbm` option to be enabled.')
    if instance.get('collect_settings', {}).get('enabled') and not config.dbm:
        validation_result.add_warning('The `collect_settings` feature requires the `dbm` option to be enabled.')
    if instance.get('collect_schemas', {}).get('enabled') and not config.dbm:
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
    if config.get('propagate_agent_tags'):
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


METRIC_TYPES = {
    'RATE': AgentCheck.rate,
    'GAUGE': AgentCheck.gauge,
    'MONOTONIC': AgentCheck.monotonic_count,
}


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

                m['metrics'][ref][1] = METRIC_TYPES[cap_mtype]
        except Exception as e:
            raise Exception('Error processing custom metric `{}`: {}'.format(m, e))
    return custom_metrics


def should_propagate_agent_tags(instance, init_config) -> bool:
    '''
    return True if the agent tags should be propagated to the check
    '''
    instance_propagate = instance.get('propagate_agent_tags')
    init_config_propagate = init_config.get('propagate_agent_tags')

    if instance_propagate is not None:
        # if the instance has explicitly set the value, return the boolean
        return instance_propagate
    if init_config_propagate is not None:
        # if the init_config has explicitly set the value, return the boolean
        return init_config_propagate
    # if neither the instance nor the init_config has set the value, return default for instance
    return instance_propagate_agent_tags()


def sanitize(config: Union[InstanceConfig, dict]) -> dict:
    if isinstance(config, InstanceConfig):
        # If config is an InstanceConfig object, convert it to a dict
        config = config.model_dump(exclude=['custom_metrics', 'custom_queries'])
    sanitized = copy.deepcopy(config)
    sanitized['password'] = '***' if sanitized.get('password') else None
    sanitized['ssl_password'] = '***' if sanitized.get('ssl_password') else None

    return sanitized


def safefloat(value: any) -> float:
    if value is None:
        return 0.0
    try:
        f = float(value)
        return f
    except Exception:
        return 0.0
