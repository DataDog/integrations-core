# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import time
from typing import TYPE_CHECKING, Tuple, Union

from datadog_checks.base import ConfigurationError
from datadog_checks.clickhouse.config_models import InstanceConfig, defaults, dict_defaults
from datadog_checks.clickhouse.features import Feature, FeatureKey, FeatureNames

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck


class ValidationResult:
    """
    A simple class to represent the result of a validation.
    It can be extended in the future to include more details about the validation.
    """

    def __init__(self, valid: bool = True):
        """
        :param valid: Whether the validation passed.
        """
        self.valid = valid
        self.features: list[Feature] = []
        self.errors: list[ConfigurationError] = []
        self.warnings: list[str] = []
        self.created_at: int = int(time.time() * 1000)

    def add_feature(self, feature: FeatureKey, enabled: bool = True, description: str | None = None):
        """
        Add a feature to the validation result.

        :param feature: The feature key to add.
        :param enabled: Whether the feature is enabled.
        :param description: Optional description (e.g., why it's disabled).
        """
        self.features.append(
            {"key": feature.value, "name": FeatureNames[feature], "enabled": enabled, "description": description}
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


def build_config(check: ClickhouseCheck) -> Tuple[InstanceConfig, ValidationResult]:
    """
    Build the ClickHouse configuration from the check instance.

    :param check: The check instance.
    :return: Tuple of (InstanceConfig, ValidationResult)
    """
    instance = check.instance
    init_config = check.init_config

    validation_result = ValidationResult()

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

    # Handle deprecated 'user' option
    # If both 'user' and 'username' are present, 'username' takes precedence
    if 'user' in instance:
        validation_result.add_warning('The `user` option is deprecated. Use `username` instead.')
        if 'username' not in instance:
            args['username'] = instance['user']

    # Handle deprecated 'host' option
    # If both 'host' and 'server' are present, 'server' takes precedence
    if 'host' in instance:
        validation_result.add_warning('The `host` option is deprecated. Use `server` instead.')
        if 'server' not in instance:
            args['server'] = instance['host']

    # Set values for args that have dict defaults or other complexities
    # If you change a literal value here, make sure to update spec.yaml
    args.update(
        {
            # Database identifier configuration
            "database_identifier": {
                **dict_defaults.instance_database_identifier().model_dump(),
                **(instance.get('database_identifier', {})),
            },
            # DBM configurations - merge defaults with user config
            "query_samples": {
                **dict_defaults.instance_query_samples().model_dump(),
                **(instance.get('query_samples', {})),
            },
            "query_metrics": {
                **dict_defaults.instance_query_metrics().model_dump(),
                **(instance.get('query_metrics', {})),
            },
            "query_completions": {
                **dict_defaults.instance_query_completions().model_dump(),
                **(instance.get('query_completions', {})),
            },
            # Tags - ensure we have a list, not None
            "tags": list(instance.get('tags', [])),
            # Other settings
            "service": instance.get('service', init_config.get('service', None)),
        }
    )

    # Apply various validations and fallbacks
    _apply_validated_defaults(args, instance, validation_result)

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

    # Instantiate InstanceConfig using pydantic model_validate
    try:
        config = InstanceConfig.model_validate(args, context={"configured_fields": instance_config_fields})
    except Exception as e:
        # Catch Pydantic validation errors and convert to ValidationResult errors
        validation_result.add_error(str(e))
        # Return a config with minimal valid values so the check can still be instantiated
        # We'll use defaults for required fields that are missing
        if 'server' not in args or args['server'] is None:
            args['server'] = 'localhost'
        config = InstanceConfig.model_validate(args, context={"configured_fields": instance_config_fields})

    _validate_config(config, instance, validation_result)

    return config, validation_result


def _apply_validated_defaults(args: dict, instance: dict, validation_result: ValidationResult):
    """Check provided values and revert to defaults if they are invalid."""
    # Validate compression type
    if args.get('compression') and args['compression'] not in ['lz4', 'zstd', 'br', 'gzip']:
        validation_result.add_error(
            f'Invalid compression type "{args["compression"]}". Valid values are: lz4, zstd, br, gzip'
        )

    # Validate collection intervals are positive
    if _safefloat(args.get('query_metrics', {}).get('collection_interval')) <= 0:
        default_value = dict_defaults.instance_query_metrics().collection_interval
        args['query_metrics']['collection_interval'] = default_value
        validation_result.add_warning(
            f"query_metrics.collection_interval must be greater than 0, defaulting to {default_value} seconds."
        )

    if _safefloat(args.get('query_samples', {}).get('collection_interval')) <= 0:
        default_value = dict_defaults.instance_query_samples().collection_interval
        args['query_samples']['collection_interval'] = default_value
        validation_result.add_warning(
            f"query_samples.collection_interval must be greater than 0, defaulting to {default_value} seconds."
        )

    if _safefloat(args.get('query_completions', {}).get('collection_interval')) <= 0:
        default_value = dict_defaults.instance_query_completions().collection_interval
        args['query_completions']['collection_interval'] = default_value
        validation_result.add_warning(
            f"query_completions.collection_interval must be greater than 0, defaulting to {default_value} seconds."
        )


def _validate_config(config: InstanceConfig, instance: dict, validation_result: ValidationResult):
    """Validate the configuration and add warnings/errors."""
    # Validate server is provided
    if not config.server:
        validation_result.add_error('the `server` setting is required')

    # Warn if DBM features are enabled without dbm flag
    dbm_features = [
        ('query_metrics', config.query_metrics.enabled if config.query_metrics else False),
        ('query_samples', config.query_samples.enabled if config.query_samples else False),
        (
            'query_completions',
            config.query_completions.enabled if config.query_completions else False,
        ),
    ]
    for feature_name, _is_enabled in dbm_features:
        if instance.get(feature_name, {}).get('enabled') and not config.dbm:
            validation_result.add_warning(f'The `{feature_name}` feature requires the `dbm` option to be enabled.')

    # Apply features to validation result for health reporting
    _apply_features(config, validation_result)


def _apply_features(config: InstanceConfig, validation_result: ValidationResult):
    """
    Apply feature flags to the validation result for health event reporting.

    This follows the Postgres pattern for consistent feature tracking across DBM integrations.
    """
    validation_result.add_feature(FeatureKey.DBM, config.dbm)
    validation_result.add_feature(
        FeatureKey.QUERY_METRICS,
        config.query_metrics.enabled and config.dbm,
        None if config.dbm else "Requires `dbm: true`",
    )
    validation_result.add_feature(
        FeatureKey.QUERY_SAMPLES,
        config.query_samples.enabled and config.dbm,
        None if config.dbm else "Requires `dbm: true`",
    )
    validation_result.add_feature(
        FeatureKey.QUERY_COMPLETIONS,
        config.query_completions.enabled and config.dbm,
        None if config.dbm else "Requires `dbm: true`",
    )
    validation_result.add_feature(FeatureKey.SINGLE_ENDPOINT_MODE, config.single_endpoint_mode)


def _safefloat(value) -> float:
    """Safely convert a value to float, returning 0.0 on failure."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def sanitize(config: Union[InstanceConfig, dict]) -> dict:
    """
    Sanitize a configuration object or dict for safe logging/health event submission.
    """
    if isinstance(config, InstanceConfig):
        # Convert InstanceConfig to dict
        config = config.model_dump()

    sanitized = copy.deepcopy(config)

    # Mask sensitive fields (matching Postgres pattern: '***' if present, else None)
    # Note: tls_ca_cert is just a file path, not sensitive data, so we don't mask it
    sanitized['password'] = '***' if sanitized.get('password') else None

    return sanitized
