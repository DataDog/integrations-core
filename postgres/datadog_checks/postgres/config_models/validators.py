# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import ConfigurationError


def instance_query_metrics_collection_interval(value, *, field, **kwargs):
    """
    Validate that query_metrics collection_interval is greater than 0.
    """
    if value is not None and value <= 0:
        from datadog_checks.postgres.statements import DEFAULT_COLLECTION_INTERVAL
        # This will be handled by the build_config function for warnings
        return DEFAULT_COLLECTION_INTERVAL
    return value


def instance_query_samples_collection_interval(value, *, field, **kwargs):
    """
    Validate that query_samples collection_interval is greater than 0.
    """
    if value is not None and value <= 0:
        from datadog_checks.postgres.statement_samples import DEFAULT_COLLECTION_INTERVAL
        # This will be handled by the build_config function for warnings
        return DEFAULT_COLLECTION_INTERVAL
    return value


def instance_query_activity_collection_interval(value, *, field, **kwargs):
    """
    Validate that query_activity collection_interval is greater than 0.
    """
    if value is not None and value <= 0:
        from datadog_checks.postgres.statement_samples import DEFAULT_ACTIVITY_COLLECTION_INTERVAL
        # This will be handled by the build_config function for warnings
        return DEFAULT_ACTIVITY_COLLECTION_INTERVAL
    return value


def instance_application_name(value, *, field, **kwargs):
    """
    Validate that application_name contains only ASCII characters.
    Note: This validation is handled in build_config for warnings instead of exceptions.
    """
    return value


def check_instance(model):
    """
    Final validation after all fields have been processed.
    """
    # Validate relations configuration
    if model.relations and not (model.dbname or (model.database_autodiscovery and model.database_autodiscovery.enabled)):
        raise ConfigurationError(
            '"dbname" parameter must be set OR autodiscovery must be enabled when using the "relations" parameter.'
        )

    return model
