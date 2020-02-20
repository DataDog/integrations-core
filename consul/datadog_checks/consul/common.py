# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from math import ceil, sqrt

from datadog_checks.base import AgentCheck

CONSUL_CHECK = 'consul.up'
CONSUL_CAN_CONNECT = 'consul.can_connect'
HEALTH_CHECK = 'consul.check'

CONSUL_CATALOG_CHECK = 'consul.catalog'

SOURCE_TYPE_NAME = 'consul'

# seconds
MAX_CONFIG_TTL = 300

# cap on distinct Consul ServiceIDs to interrogate
MAX_SERVICES = 50

STATUS_SC = {
    'up': AgentCheck.OK,
    'passing': AgentCheck.OK,
    'warning': AgentCheck.WARNING,
    'critical': AgentCheck.CRITICAL,
}

STATUS_SEVERITY = {AgentCheck.UNKNOWN: 0, AgentCheck.OK: 1, AgentCheck.WARNING: 2, AgentCheck.CRITICAL: 3}


# More information in https://www.consul.io/docs/internals/coordinates.html,
# code is based on the snippet there.
def distance(a, b):
    a = a['Coord']
    b = b['Coord']
    total = 0
    b_vec = b['Vec']
    for i, a_p in enumerate(a['Vec']):
        diff = a_p - b_vec[i]
        total += diff * diff
    rtt = sqrt(total) + a['Height'] + b['Height']

    adjusted = rtt + a['Adjustment'] + b['Adjustment']
    if adjusted > 0.0:
        rtt = adjusted

    return rtt * 1000.0


def ceili(v):
    return int(ceil(v))
