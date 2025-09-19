# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-PARAMKEYWORDS
from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Optional, Tuple

from datadog_checks.postgres.config_models import InstanceConfig
# Defaults are now handled by Pydantic automatically from spec.yaml
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

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.utils.aws import rds_parse_tags_from_endpoint
from datadog_checks.base.utils.db.utils import get_agent_host_tags
from datadog_checks.postgres.features import Feature, FeatureKey, FeatureNames
from datadog_checks.postgres.statement_samples import (
    DEFAULT_ACTIVITY_COLLECTION_INTERVAL as DEFAULT_QUERY_ACTIVITY_COLLECTION_INTERVAL,
)
from datadog_checks.postgres.statement_samples import (
    DEFAULT_COLLECTION_INTERVAL as DEFAULT_QUERY_SAMPLES_COLLECTION_INTERVAL,
)
from datadog_checks.postgres.statements import DEFAULT_COLLECTION_INTERVAL as DEFAULT_QUERY_METRICS_COLLECTION_INTERVAL

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


def _handle_deprecated_fields(instance: dict) -> dict:
    """
    Handle deprecated field mappings before Pydantic validation.
    """
    processed = instance.copy()

    # Handle deprecated field mappings
    if 'deep_database_monitoring' in processed and 'dbm' not in processed:
        processed['dbm'] = processed['deep_database_monitoring']

    if 'statement_samples' in processed and 'query_samples' not in processed:
        processed['query_samples'] = processed['statement_samples']

    if 'managed_authentication' in processed and 'azure' not in processed:
        # This will be handled in the Azure validation logic
        pass

    # Handle custom_metrics -> custom_queries mapping
    if 'custom_metrics' in processed:
        processed['custom_metrics'] = map_custom_metrics(processed['custom_metrics'])

    return processed


def _handle_special_cases(instance: dict, init_config: dict) -> dict:
    """
    Handle special cases that need custom logic before Pydantic validation.
    """
    processed = instance.copy()

    # Handle port logic for socket paths
    if 'port' not in processed and processed.get('host', '').startswith('/'):
        processed['port'] = None
    # If port is not set, Pydantic will apply the default from spec.yaml (5432)

    # Handle batch_max_content_size from init_config
    if 'query_metrics' in processed:
        query_metrics = processed['query_metrics'].copy()
        if 'batch_max_content_size' not in query_metrics:
            batch_size = init_config.get('metrics', {}).get('batch_max_content_size', 20_000_000)
            query_metrics['batch_max_content_size'] = batch_size
        processed['query_metrics'] = query_metrics

    # Handle service from init_config
    if 'service' not in processed and 'service' in init_config:
        processed['service'] = init_config['service']

    # Handle propagate_agent_tags logic
    processed['propagate_agent_tags'] = should_propagate_agent_tags(
        instance=instance, init_config=init_config
    )

    # Handle invalid numbers gracefully (for backward compatibility)
    processed = _handle_invalid_numbers(processed)

    # Ensure nested objects are properly initialized with defaults
    processed = _ensure_nested_defaults(processed)

    return processed


def _handle_invalid_numbers(instance: dict) -> dict:
    """
    Handle invalid numbers by converting them to defaults (for backward compatibility).
    """
    processed = instance.copy()

    # Handle query_metrics collection_interval
    if 'query_metrics' in processed:
        query_metrics = processed['query_metrics'].copy()
        if 'collection_interval' in query_metrics:
            try:
                # Try to convert to float, if it fails, set to default
                float(query_metrics['collection_interval'])
            except (ValueError, TypeError):
                # Set to default value instead of removing
                query_metrics['collection_interval'] = 10  # Default from spec.yaml
        processed['query_metrics'] = query_metrics

    # Handle query_samples collection_interval
    if 'query_samples' in processed:
        query_samples = processed['query_samples'].copy()
        if 'collection_interval' in query_samples:
            try:
                float(query_samples['collection_interval'])
            except (ValueError, TypeError):
                query_samples['collection_interval'] = 1  # Default from spec.yaml
        processed['query_samples'] = query_samples

    # Handle query_activity collection_interval
    if 'query_activity' in processed:
        query_activity = processed['query_activity'].copy()
        if 'collection_interval' in query_activity:
            try:
                float(query_activity['collection_interval'])
            except (ValueError, TypeError):
                query_activity['collection_interval'] = 10  # Default from spec.yaml
        processed['query_activity'] = query_activity

    return processed


def _ensure_nested_defaults(instance: dict) -> dict:
    """
    Ensure that nested objects are properly initialized with defaults.
    This is needed because Pydantic doesn't automatically create nested objects with defaults.
    """
    processed = instance.copy()

    # List of nested objects that need default initialization
    nested_objects = [
        'query_activity',
        'query_samples',
        'query_metrics',
        'collect_settings',
        'collect_schemas',
        'database_autodiscovery',
        'obfuscator_options',
        'collect_raw_query_statement',
        'locks_idle_in_transaction',
        'aws',
        'gcp',
        'azure'
    ]

    for obj_name in nested_objects:
        if obj_name not in processed:
            # Initialize with empty dict so Pydantic will apply defaults
            processed[obj_name] = {}
        else:
            # Ensure that existing nested objects have their required fields set
            obj = processed[obj_name]
            if isinstance(obj, dict):
                # For query_samples, ensure enabled is set to default if not present
                if obj_name == 'query_samples' and 'enabled' not in obj:
                    obj['enabled'] = True  # Default from spec.yaml
                elif obj_name == 'query_activity' and 'enabled' not in obj:
                    obj['enabled'] = True  # Default from spec.yaml
                elif obj_name == 'query_metrics' and 'enabled' not in obj:
                    obj['enabled'] = True  # Default from spec.yaml
                elif obj_name == 'collect_settings' and 'enabled' not in obj:
                    obj['enabled'] = True  # Default from spec.yaml
                elif obj_name == 'collect_schemas' and 'enabled' not in obj:
                    obj['enabled'] = False  # Default from spec.yaml

    return processed


def _add_invalid_number_warnings(instance: dict, config: InstanceConfig, validation_result: ValidationResult):
    """
    Add warnings for invalid numbers that were converted to defaults.
    """
    from datadog_checks.postgres.statements import DEFAULT_COLLECTION_INTERVAL
    from datadog_checks.postgres.statement_samples import DEFAULT_COLLECTION_INTERVAL as DEFAULT_SAMPLES_COLLECTION_INTERVAL
    from datadog_checks.postgres.statement_samples import DEFAULT_ACTIVITY_COLLECTION_INTERVAL

    # Check query_metrics collection_interval
    if 'query_metrics' in instance:
        query_metrics = instance['query_metrics']
        if 'collection_interval' in query_metrics:
            try:
                float(query_metrics['collection_interval'])
            except (ValueError, TypeError):
                validation_result.add_warning(
                    f"query_metrics.collection_interval must be greater than 0, defaulting to "
                    f"{DEFAULT_COLLECTION_INTERVAL} seconds."
                )

    # Check query_samples collection_interval
    if 'query_samples' in instance:
        query_samples = instance['query_samples']
        if 'collection_interval' in query_samples:
            try:
                float(query_samples['collection_interval'])
            except (ValueError, TypeError):
                validation_result.add_warning(
                    f"query_samples.collection_interval must be greater than 0, defaulting to "
                    f"{DEFAULT_SAMPLES_COLLECTION_INTERVAL} seconds."
                )

    # Check query_activity collection_interval
    if 'query_activity' in instance:
        query_activity = instance['query_activity']
        if 'collection_interval' in query_activity:
            try:
                float(query_activity['collection_interval'])
            except (ValueError, TypeError):
                validation_result.add_warning(
                    f"query_activity.collection_interval must be greater than 0, defaulting to "
                    f"{DEFAULT_ACTIVITY_COLLECTION_INTERVAL} seconds."
                )


def build_config(check: PostgreSql) -> Tuple[InstanceConfig, ValidationResult]:
    """
    Build the Postgres configuration using Pydantic's built-in default system.
    :param check: The check instance.
    :param init_config: The init_config for the Postgres check.
    :param instance: The instance configuration for the Postgres check.
    :return: InstanceConfig
        The instance configuration object.
    """

    instance = check.instance
    init_config = check.init_config

    # Handle deprecated field mappings before Pydantic validation
    processed_instance = _handle_deprecated_fields(instance)

    # Handle special cases that need custom logic
    processed_instance = _handle_special_cases(processed_instance, init_config)

    # Let Pydantic handle all default application and validation
    config = InstanceConfig.model_validate(processed_instance, context={
        'init_config': init_config,
        'configured_fields': set(processed_instance.keys())
    })

    validation_result = ValidationResult()

    # Generate and validate tags
    tags, tag_errors = build_tags(instance=instance, init_config=init_config, config=config.model_dump())
    # Update config with tags (this is a special case that can't be handled by Pydantic defaults)
    config = config.model_copy(update={'tags': tags})
    for error in tag_errors:
        # If there are errors in the tags, we add them to the validation result
        # but we don't raise an exception here, as we want to validate the rest of the configuration
        validation_result.add_error(error)

    # AWS backfill and validation
    if (
        not instance.get("aws", {}).get("managed_authentication", None)
        and config.aws and config.aws.region
        and not config.password
    ):
        # if managed_authentication is not set, we assume it is enabled if region is set and password is not set
        if config.aws.managed_authentication:
            config.aws.managed_authentication.enabled = True
        else:
            from datadog_checks.postgres.config_models.instance import ManagedAuthentication
            config.aws.managed_authentication = ManagedAuthentication(enabled=True)

    if config.aws and config.aws.managed_authentication and config.aws.managed_authentication.enabled and not config.aws.region:
        validation_result.add_error('AWS region must be set when using AWS managed authentication')

    # Azure backfill and validation
    if not instance.get("azure", {}).get("managed_authentication", None) and (
        (config.azure and config.azure.managed_authentication and config.azure.managed_authentication.client_id)
        or instance.get('managed_identity', {}).get('client_id')
    ):
        # if managed_authentication is not set, we assume it is enabled if client_id is set
        if config.azure and config.azure.managed_authentication:
            config.azure.managed_authentication.enabled = True
        else:
            from datadog_checks.postgres.config_models.instance import ManagedAuthentication1
            config.azure.managed_authentication = ManagedAuthentication1(enabled=True)

    if instance.get("managed_identity"):
        validation_result.add_warning(
            'The `managed_identity` option is deprecated. Use `azure.managed_authentication` instead.'
        )
        # Merge managed_identity into azure.managed_authentication
        if config.azure and config.azure.managed_authentication:
            managed_identity = instance.get('managed_identity', {})
            if 'client_id' in managed_identity:
                config.azure.managed_authentication.client_id = managed_identity['client_id']
            if 'identity_scope' in managed_identity:
                config.azure.managed_authentication.identity_scope = managed_identity['identity_scope']

    if config.azure and config.azure.managed_authentication and config.azure.managed_authentication.enabled and not config.azure.managed_authentication.client_id:
        validation_result.add_error('Azure client_id must be set when using Azure managed authentication')

    if config.collect_default_database:
        # Remove 'postgres' from ignore_databases if collect_default_database is True
        if config.ignore_databases and 'postgres' in config.ignore_databases:
            ignore_list = list(config.ignore_databases)
            ignore_list.remove('postgres')
            config = config.model_copy(update={'ignore_databases': tuple(ignore_list)})

    # Validate config arguments for invalid or deprecated options
    if config.ssl not in SSL_MODES:
        warning = f"Invalid ssl option '{config.ssl}', should be one of {SSL_MODES}. Defaulting to 'allow'."
        validation_result.add_warning(warning)
        config = config.model_copy(update={'ssl': 'allow'})

    # Deprecated options warnings
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

    # Additional validation after Pydantic has processed the config
    # Note: Most validation is now handled by Pydantic validators in validators.py

    # Validate application_name for ASCII characters
    if not config.application_name.isascii():
        validation_result.add_error(f"Application name can include only ASCII characters: {config.application_name}")

    # Add warnings for invalid numbers that were converted to defaults
    _add_invalid_number_warnings(instance, config, validation_result)

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
    if not instance.get('disable_generic_tags', False):  # Default is False from spec.yaml
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

    collect_raw_query_statement = config.get('collect_raw_query_statement')
    if collect_raw_query_statement and collect_raw_query_statement.get("enabled"):
        tags.extend(["raw_query_statement:enabled"])

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
    return False  # Default is False from spec.yaml


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
