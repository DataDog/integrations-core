# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from . import powerdns_recursor

PowerDNSRecursorCheck = powerdns_recursor.PowerDNSRecursorCheck

__all__ = [
    'PowerDNSRecursorCheck',
    '__version__'
]
