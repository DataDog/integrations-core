# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import ipaddress

# Here you can include additional config validators or transformers
#
# def initialize_instance(values, **kwargs):
#     if 'my_option' not in values and 'my_legacy_option' in values:
#         values['my_option'] = values['my_legacy_option']
#     if values.get('my_number') > 10:
#         raise ValueError('my_number max value is 10, got %s' % str(values.get('my_number')))
#
#     return values


def instance_appliance_ips(value, **kwargs):
    if not value:
        return value

    for field in ('include', 'exclude'):
        for pattern in value.get(field) or ():
            _validate_ip_pattern(pattern)

    return value


def _validate_ip_pattern(pattern: str) -> None:
    try:
        if '/' in pattern:
            ipaddress.ip_network(pattern, strict=False)
        else:
            ipaddress.ip_address(pattern)
    except ValueError:
        raise ValueError(f'Invalid appliance_ips pattern: {pattern}')


def check_instance(model):
    has_username = model.orchestrator_username is not None
    has_password = model.orchestrator_password is not None
    if has_username != has_password:
        raise ValueError('`orchestrator_username` and `orchestrator_password` must be set together.')

    # An empty key is treated as unset so a blank templated secret fails here, not as a 401 later.
    has_api_key = bool(model.orchestrator_api_key)
    if has_api_key and has_username:
        raise ValueError(
            'Set `orchestrator_api_key` or `orchestrator_username` and `orchestrator_password`, not both. '
            'With an API key, configure appliance credentials in `appliance_credentials_overrides`.'
        )
    if not has_api_key and not has_username:
        raise ValueError(
            'Set either `orchestrator_api_key` or both `orchestrator_username` and `orchestrator_password`.'
        )

    # Appliances only accept username and password, so in API key mode every appliance has to be
    # covered by an override.
    if has_api_key and not model.appliance_credentials_overrides:
        raise ValueError(
            'With `orchestrator_api_key`, `appliance_credentials_overrides` must provide credentials '
            'for the appliances.'
        )

    return model
