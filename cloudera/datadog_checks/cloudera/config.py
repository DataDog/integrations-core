# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Discovery class requires 'include' to be a dict, so this function is needed to normalize the config
def normalize_config_clusters_include(log, clusters_config):
    config = {}
    if clusters_config and clusters_config.include:
        if not isinstance(clusters_config.include, list):
            raise TypeError('Setting `include` must be an array')
        for entry in clusters_config.include:
            log.debug("entry: %s", type(entry))
            if isinstance(entry, str):
                config[entry] = None
            elif isinstance(entry, dict):
                for key, value in entry.items():
                    config[key] = value.copy()
    return config
