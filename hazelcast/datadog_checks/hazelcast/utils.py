# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck

# https://docs.hazelcast.org/docs/management-center/latest/manual/html/index.html#cluster-state
MC_CLUSTER_STATES = {
    'Active': ServiceCheck.OK,
    'No Migration': ServiceCheck.WARNING,
    'Frozen': ServiceCheck.CRITICAL,
    'Passive': ServiceCheck.CRITICAL,
    'In Transition': ServiceCheck.WARNING,
}


class ServiceCheckStatus(object):
    def __init__(self, default_map, user_map):
        self.statuses = {key.lower(): status for key, status in default_map.items()}
        self.statuses.update(
            (key.lower(), getattr(ServiceCheck, status.upper(), ServiceCheck.UNKNOWN))
            for key, status in user_map.items()
        )

    def get(self, key):
        return self.statuses.get(key.lower(), ServiceCheck.UNKNOWN)
