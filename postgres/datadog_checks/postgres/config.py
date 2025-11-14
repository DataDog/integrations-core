# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Optional, Tuple

from datadog_checks.postgres.config_models import InstanceConfig, defaults, dict_defaults
from datadog_checks.postgres.config_models.instance import (
    Aws,
    Azure,
    Gcp,
    ManagedAuthentication,
    ManagedAuthentication1,
    Union,
)
from datadog_checks.postgres.relationsmanager import RelationsManager

# We need to use TYPE_CHECKING to avoid circular imports, which are ok while type checking
# but not while executing
if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

import time

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint
from datadog_checks.base.utils.db.utils import get_agent_host_tags
from datadog_checks.postgres.features import Feature, FeatureKey, FeatureNames

SSL_MODES = {'disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full'}
TABLE_COUNT_LIMIT = 200


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
        self.created_at: int = int(time.time() * 1000)

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


def build_config(check: PostgreSql) -> Tuple[InstanceConfig, ValidationResult]:
    """
    Build the Postgres configuration.
    :param check: The check instance.
    :return: InstanceConfig, ValidationResult
        The instance configuration object and validation result.
    """

    # The `instance` is the user provided configuration for this particular Postgres instance
    instance = check.instance
    # The `init_config` is the user provided configuration for the check that applies to all instances
    init_config = check.init_config

    args = {}

    # Automatically set values that support defaults or that have simple values in the instance
    instance_config_fields = set(InstanceConfig.__annotations__.keys())

    for f in instance_config_fields:
        try:
            args[f] = getattr(defaults, f"instance_{f}")()
        except AttributeError:
            args[f] = None
        if f in instance:
            args[f] = instance[f]

    # Build database_autodiscovery config first, as we may need it for dbname defaulting
    database_autodiscovery_config = {
        **dict_defaults.instance_database_autodiscovery().model_dump(),
        **(instance.get('database_autodiscovery', {})),
    }

    if 'dbname' not in instance and database_autodiscovery_config.get('enabled'):
        args['dbname'] = database_autodiscovery_config.get('global_view_db')

    # Set values for args that have deprecated fallbacks, are not supported by the spec model
    # or have other complexities
    # If you change a literal value here, make sure to update spec.yaml
    args.update(
        {
            # Database configuration
            "dbm": instance.get(
                'dbm', instance.get('deep_database_monitoring', defaults.instance_dbm())
            ),  # Deprecated, use `dbm` instead
            "custom_metrics": map_custom_metrics(
                instance.get('custom_metrics', [])
            ),  # Deprecated, use `custom_queries` instead
            "custom_queries": instance.get('custom_queries', []),
            "database_identifier": {
                **dict_defaults.instance_database_identifier().model_dump(),
                **(instance.get('database_identifier', {})),
            },
            "database_autodiscovery": database_autodiscovery_config,
            "query_metrics": {
                **dict_defaults.instance_query_metrics().model_dump(),
                **{
                    "batch_max_content_size": init_config.get('metrics', {}).get('batch_max_content_size', 20_000_000),
                },
                **(instance.get('query_metrics', {})),
            },
            "query_samples": {
                **dict_defaults.instance_query_samples().model_dump(),
                **(instance.get('statement_samples', {})),  # Deprecated, use `query_samples` instead
                **(instance.get('query_samples', {})),
            },
            "query_activity": {
                **dict_defaults.instance_query_activity().model_dump(),
                **(instance.get('query_activity', {})),
            },
            # Metadata collection
            "collect_settings": {
                **dict_defaults.instance_collect_settings().model_dump(),
                **(instance.get('collect_settings') or {}),
            },
            "collect_schemas": {
                **dict_defaults.instance_collect_schemas().model_dump(),
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
                **dict_defaults.instance_obfuscator_options().model_dump(),
                **(instance.get('obfuscator_options', {})),
            },
            "collect_raw_query_statement": {
                **dict_defaults.instance_collect_raw_query_statement().model_dump(),
                **(instance.get('collect_raw_query_statement', {})),
            },
            "locks_idle_in_transaction": {
                **dict_defaults.instance_locks_idle_in_transaction().model_dump(),
                **(instance.get('locks_idle_in_transaction', {})),
            },
            "propagate_agent_tags": should_propagate_agent_tags(instance=instance, init_config=init_config),
            "service": instance.get('service', init_config.get('service', None)),
            # Metric filtering by pattern is implemented downstream, theoretically
            "metric_patterns": instance.get('metric_patterns', None),
        }
    )

    # Backfill old key to new key
    if instance.get('obfuscator_options', {}).get('quantize_sql_tables'):
        args['obfuscator_options']['replace_digits'] = True

    validation_result = ValidationResult()

    # Generate and validate tags
    tags, tag_errors = build_tags(instance=instance, init_config=init_config, config=args)
    args['tags'] = tags
    for error in tag_errors:
        # If there are errors in the tags, we add them to the validation result
        # but we don't raise an exception here, as we want to validate the rest of the configuration
        validation_result.add_error(error)

    # Apply various validations and fallbacks
    apply_validated_defaults(args, instance, validation_result)
    apply_deprecation_warnings(instance, validation_result)

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

    validate_config(config, instance, validation_result)

    try:
        RelationsManager.validate_relations_config(list(config.relations))
    except ConfigurationError as e:
        validation_result.add_error(e)

    apply_features(config, validation_result)

    return config, validation_result


def build_tags(instance: dict, init_config: dict, config: dict) -> Tuple[list[str], list[ConfigurationError]]:
    tags = list(set(instance.get('tags', [])))

    # preset tags to host
    if not instance.get('disable_generic_tags', defaults.instance_disable_generic_tags()):
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


def apply_validated_defaults(args: dict, instance: dict, validation_result: ValidationResult):
    # Check provided values and revert to defaults if they are invalid

    # Validate config arguments for invalid or deprecated options
    if args['ssl'] not in SSL_MODES:
        warning = f"Invalid ssl option '{args['ssl']}', should be one of {SSL_MODES}. Defaulting to 'allow'."
        validation_result.add_warning(warning)
        args['ssl'] = "allow"

    if safefloat(args['query_metrics']['collection_interval']) <= 0:
        default_value = dict_defaults.instance_query_metrics().collection_interval
        args['query_metrics']['collection_interval'] = default_value
        validation_result.add_warning(
            f"query_metrics.collection_interval must be greater than 0, defaulting to {default_value} seconds."
        )

    if safefloat(args['query_samples']['collection_interval']) <= 0:
        default_value = dict_defaults.instance_query_samples().collection_interval
        args['query_samples']['collection_interval'] = default_value
        validation_result.add_warning(
            f"query_samples.collection_interval must be greater than 0, defaulting to {default_value} seconds."
        )

    if safefloat(args['query_activity']['collection_interval']) <= 0:
        default_value = dict_defaults.instance_query_activity().collection_interval
        args['query_activity']['collection_interval'] = default_value
        validation_result.add_warning(
            f"query_activity.collection_interval must be greater than 0, defaulting to {default_value} seconds."
        )

    if args.get('collect_default_database'):
        args['ignore_databases'] = [d for d in args['ignore_databases'] if d != 'postgres']

    apply_cloud_defaults(args, instance, validation_result)


def apply_cloud_defaults(args: dict, instance: dict, validation_result: ValidationResult):
    # AWS backfill and validation
    if (
        not instance.get("aws", {}).get("managed_authentication", None)
        and args.get('aws', {}).get('region')
        and not args.get('password')
    ):
        # if managed_authentication is not set, we assume it is enabled if region is set and password is not set
        args['aws'] = {
            **args['aws'],
            'managed_authentication': {**args['aws'].get('managed_authentication', {}), 'enabled': True},
        }

    if args.get('aws', {}).get('managed_authentication', {}).get('enabled') and not args.get('aws', {}).get('region'):
        validation_result.add_error('AWS region must be set when using AWS managed authentication')

    # Azure backfill and validation
    if instance.get("managed_identity"):
        args['azure'] = {
            **args.get('azure', {}),
            'managed_authentication': {
                **args.get('azure', {}).get('managed_authentication', {}),
                **instance.get('managed_identity', {}),
            },
        }

    if not instance.get("azure", {}).get("managed_authentication", None) and (
        args.get('azure', {}).get('managed_authentication', {}).get('client_id')
        or instance.get('managed_identity', {}).get('client_id')
    ):
        # if managed_authentication is not set, we assume it is enabled if client_id is set
        args['azure'] = {
            **args.get('azure', {}),
            'managed_authentication': {**args.get('azure', {}).get('managed_authentication', {}), 'enabled': True},
        }

    if args.get('azure', {}).get('managed_authentication', {}).get('enabled') and not args.get('azure', {}).get(
        'managed_authentication', {}
    ).get('client_id'):
        validation_result.add_error('Azure client_id must be set when using Azure managed authentication')


def deprecation_warning(option: str, replacement: str):
    return f'The `{option}` option is deprecated. Use `{replacement}` instead.'


def apply_deprecation_warnings(instance: dict, validation_result: ValidationResult):
    # Simple deprecated options
    deprecations = [
        ['custom_metrics', 'custom_queries'],
        ['deep_database_monitoring', 'dbm'],
        ['managed_identity', 'azure.managed_authentication'],
        ['statement_samples', 'query_samples'],
        ['collect_default_database', 'postgres'],
    ]

    for deprecation in deprecations:
        if deprecation[0] in instance:
            validation_result.add_warning(deprecation_warning(deprecation[0], deprecation[1]))


def validate_config(config: InstanceConfig, instance: dict, validation_result: ValidationResult):
    # Validate config after defaults and other validations have been applied
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

    # Validate dbname is not excluded when using autodiscovery
    if config.database_autodiscovery.enabled and config.dbname:
        import re

        for exclude_pattern in config.database_autodiscovery.exclude:
            try:
                if re.search(exclude_pattern, config.dbname, re.IGNORECASE):
                    # Check if user explicitly set dbname
                    if 'dbname' in instance:
                        validation_result.add_error(
                            f'The configured dbname "{config.dbname}" matches the autodiscovery '
                            f'exclude pattern "{exclude_pattern}". Either remove dbname from '
                            f'configuration or adjust the exclude patterns.'
                        )
                    else:
                        # Auto-defaulted dbname conflicts - suggest setting global_view_db
                        validation_result.add_error(
                            f'The default dbname "{config.dbname}" is excluded by autodiscovery pattern '
                            f'"{exclude_pattern}". Set database_autodiscovery.global_view_db to a '
                            f'non-excluded database.'
                        )
                    break
            except re.error:
                validation_result.add_warning(f'Invalid regex pattern in autodiscovery exclude: {exclude_pattern}')

    # If the user provided config explicitly enables these features, we add a warning if dbm is not enabled
    dbm_required = ['query_activity', 'query_samples', 'query_metrics', 'collect_settings', 'collect_schemas']
    for feature in dbm_required:
        if instance.get(feature, {}).get('enabled') and not config.dbm:
            validation_result.add_warning(f'The `{feature}` feature requires the `dbm` option to be enabled.')


def apply_features(config: InstanceConfig, validation_result: ValidationResult):
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
                raise ConfigurationError(f'Missing {param} parameter in custom metric {m}')

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
                        f"Collector method {cap_mtype} for custom metric {m} is not known. "
                        "Known methods are RATE, GAUGE, MONOTONIC"
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
    return defaults.instance_propagate_agent_tags()


def sanitize(config: Union[InstanceConfig, dict]) -> dict:
    if isinstance(config, InstanceConfig):
        # If config is an InstanceConfig object, convert it to a dict
        config = config.model_dump(exclude={'custom_metrics', 'custom_queries'})
    sanitized = copy.deepcopy(config)
    sanitized['password'] = '***' if sanitized.get('password') else None
    sanitized['ssl_password'] = '***' if sanitized.get('ssl_password') else None
    # For the deprecated custom_metrics we inject a function into the instance
    # The function isn't serializable so we have to strip it
    for custom_metric in sanitized.get('custom_metrics', []):
        for key in custom_metric.get('metrics', {}):
            custom_metric.get('metrics')[key][1] = ''

    return sanitized


def safefloat(value: any) -> float:
    if value is None:
        return 0.0
    try:
        f = float(value)
        return f
    except Exception:
        return 0.0
