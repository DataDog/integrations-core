from collections.abc import Collection

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.containers import hash_mutable_stable


def config_set_persistent_cache_id(
    check: AgentCheck,
    init_config_options: Collection[str] | None = None,
    instance_config_options: Collection[str] | None = None,
):
    """
    Returns an ID for the persisitent cache derives from a subset of the check's config options.

    If the value of any of the provided options changes, the generate cache ID will change.

    Parameters:
        check: the check instance the key is going to be used for.
        init_config_options: the subset of init_config options to use to generate the cache ID.
        instance_config_options: the subset of config options to use to generate the cache ID.
    """

    if not init_config_options and not instance_config_options:
        raise ValueError("At least one of init_config_options or instance_config_options must be provided")

    set_init_config_options = set(init_config_options) if init_config_options else set()
    set_instance_config_options = set(instance_config_options) if instance_config_options else set()

    init_config_values = tuple(value for key, value in check.init_config.items() if key in set_init_config_options)
    instance_config_values = tuple(value for key, value in check.instance.items() if key in set_instance_config_options)

    selected_values = init_config_values + instance_config_values

    return hash_mutable_stable(selected_values)
