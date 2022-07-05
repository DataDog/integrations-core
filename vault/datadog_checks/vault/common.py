# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import namedtuple

DEFAULT_API_VERSION = '1'
API_METHODS = ('check_health', 'check_leader')

# Expected HTTP Error codes for /sys/health endpoint
# https://www.vaultproject.io/api/system/health.html
SYS_HEALTH_DEFAULT_CODES = {
    200,  # initialized, unsealed, and active
    429,  # unsealed and standby
    472,  # data recovery mode replication secondary and active
    473,  # performance standby
    501,  # not initialized
    503,  # sealed
}

SYS_LEADER_DEFAULT_CODES = {
    503,  # sealed
}

Api = namedtuple('Api', ('check_health', 'check_leader'))
Leader = namedtuple('Leader', ('leader_addr', 'leader_cluster_addr'))
