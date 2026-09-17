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
