# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers
#
# def initialize_instance(values, **kwargs):
#     if 'my_option' not in values and 'my_legacy_option' in values:
#         values['my_option'] = values['my_legacy_option']
#     if values.get('my_number') > 10:
#         raise ValueError('my_number max value is 10, got %s' % str(values.get('my_number')))
#
#     return values


def initialize_instance(values, **kwargs):
    """
    Initialize and validate instance configuration.
    Handles silent value transformations for backwards compatibility.

    Note: Deprecation warnings should be added in config.py's build_config(),
    not here, as validators don't have access to ValidationResult.
    """
    # Map deprecated 'user' to 'username' for backwards compatibility
    if 'username' not in values and 'user' in values:
        values['username'] = values['user']

    # Map 'host' to 'server' for backwards compatibility
    if 'server' not in values and 'host' in values:
        values['server'] = values['host']

    return values
