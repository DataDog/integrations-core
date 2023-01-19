# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Discovery class requires 'include' to be a dict, so this function is needed to normalize the config
def normalize_discover_config_include(log, clusters_config):
    config = {}
    log.debug("normalize_config_clusters_include: %s", type(clusters_config))
    include_list = (
        clusters_config.get('include')
        if isinstance(clusters_config, dict)
        else clusters_config.include
        if clusters_config
        else []
    )
    log.debug("normalize_config_clusters_include: %s", include_list)
    if not isinstance(include_list, list):
        raise TypeError('Setting `include` must be an array')
    for entry in include_list:
        if isinstance(entry, str):
            config[entry] = None
        elif isinstance(entry, dict):
            for key, value in entry.items():
                config[key] = value.copy()
    return config
