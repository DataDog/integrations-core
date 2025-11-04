# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers


def initialize_instance(values, **kwargs):
    """
    Initialize and validate instance configuration.
    Maps 'host' to 'server' for backwards compatibility.
    """
    # Map 'host' to 'server' for backwards compatibility
    if 'server' not in values and 'host' in values:
        values['server'] = values['host']

    # Validate that either server or host was provided
    if 'server' not in values:
        raise ValueError("Either 'server' or 'host' must be specified in the configuration")

    return values
