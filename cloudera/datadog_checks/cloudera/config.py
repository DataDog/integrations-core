# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.models.types import copy_raw


# Discovery class requires 'include' to be a dict, so this function is needed to normalize the config
def normalize_discover_config_include(log, config):
    normalized_config = {}
    log.debug("normalize_discover_config_include config: %s", config)
    include_list = config.get('include') if isinstance(config, dict) else copy_raw(config.include) if config else []
    log.debug("normalize_discover_config_include include_list: %s", include_list)
    if not isinstance(include_list, list):
        raise TypeError('Setting `include` must be an array')
    for entry in include_list:
        if isinstance(entry, str):
            normalized_config[entry] = None
        elif isinstance(entry, dict):
            for key, value in entry.items():
                normalized_config[key] = value.copy()
        else:
            raise TypeError('`include` entries must be a map or a string')
    return normalized_config
