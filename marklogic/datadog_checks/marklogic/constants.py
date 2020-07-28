# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Dict

from six import iteritems

from datadog_checks.base import AgentCheck

RESOURCE_TYPES = {
    'cluster': {'plural': None},
    'forest': {'plural': 'forests'},
    'database': {'plural': 'databases'},
    'host': {'plural': 'hosts'},
    'server': {'plural': 'servers'},
}  # type: Dict[str, Dict]

RESOURCE_SINGULARS = {plural['plural']: key for key, plural in iteritems(RESOURCE_TYPES) if plural['plural']}

# TODO: check again
RESOURCE_AVAILABLE_METRICS = {
    'forests': {'status': True, 'storage': True, 'requests': False},
    'databases': {'status': True, 'storage': True, 'requests': False},
    'hosts': {'status': True, 'storage': True, 'requests': True},
    'servers': {'status': False, 'storage': False, 'requests': True},
}

GAUGE_UNITS = [
    '%',
    'hits/sec',
    'locks/sec',
    'MB',
    'MB/sec',
    'misses/sec',
    'quantity',
    'quantity/sec',
    'sec',
    'sec/sec',
]

# TODO: Remap serverity levels
STATUS_CODE_HEALTH = {
    'HEALTH-CLUSTER-ERROR': AgentCheck.CRITICAL,
    'HEALTH-CLUSTER-HOSTS-ERROR': AgentCheck.CRITICAL,
    'HEALTH-CLUSTER-OPSDIRECTOR-LOGGING-DISABLED': AgentCheck.WARNING,
    'HEALTH-CLUSTER-OPSDIRECTOR-METERING-DISABLED': AgentCheck.WARNING,
    'HEALTH-DATABASE-ACTIVE-REPLICAS': AgentCheck.WARNING,
    'HEALTH-DATABASE-DBREP-MASTER-ERROR': AgentCheck.CRITICAL,
    'HEALTH-DATABASE-DBREP-REPLICA-ERROR': AgentCheck.CRITICAL,
    'HEALTH-DATABASE-DISABLED': AgentCheck.WARNING,
    'HEALTH-DATABASE-ERROR': AgentCheck.CRITICAL,
    'HEALTH-DATABASE-FAILED-MASTER-FORESTS': AgentCheck.CRITICAL,
    'HEALTH-DATABASE-FAILED-REPLICAS': AgentCheck.CRITICAL,
    'HEALTH-DATABASE-NO-BACKUP': AgentCheck.OK,
    'HEALTH-DATABASE-NO-FORESTS': AgentCheck.OK,
    'HEALTH-DATABASE-NOT-AVAILABLE': AgentCheck.UNKNOWN,
    'HEALTH-DATABASE-NOT-ENABLED': AgentCheck.OK,
    'HEALTH-DATABASE-OFFLINE': AgentCheck.WARNING,
    'HEALTH-DATABASE-STALE-BACKUP': AgentCheck.WARNING,
    'HEALTH-DATABASE-STALE-INCR-BACKUP': AgentCheck.WARNING,
    'HEALTH-DATABASE-UNAVAILABLE': AgentCheck.WARNING,
    'HEALTH-FOREST-DISABLED': AgentCheck.WARNING,
    'HEALTH-FOREST-ERROR': AgentCheck.CRITICAL,
    'HEALTH-FOREST-FOREIGN-REPLICA-ERROR': AgentCheck.CRITICAL,
    'HEALTH-FOREST-HOST-NETWORK-UNAVAILABLE': AgentCheck.WARNING,
    'HEALTH-FOREST-HOST-OFFLINE': AgentCheck.WARNING,
    'HEALTH-FOREST-MASTER-DISABLED': AgentCheck.WARNING,
    'HEALTH-FOREST-MAX-FOREST-SIZE': AgentCheck.WARNING,
    'HEALTH-FOREST-MAX-STANDS': AgentCheck.WARNING,
    'HEALTH-FOREST-MERGE-BLACKOUTS-ENABLED': AgentCheck.OK,
    'HEALTH-FOREST-NOT-AVAILABLE': AgentCheck.UNKNOWN,
    'HEALTH-FOREST-NOT-ENABLED': AgentCheck.OK,
    'HEALTH-FOREST-OBSOLETE': AgentCheck.WARNING,
    'HEALTH-FOREST-OFFLINE': AgentCheck.WARNING,
    'HEALTH-FOREST-REBALANCER-DISABLED': AgentCheck.WARNING,
    'HEALTH-FOREST-REBALANCER-ERROR': AgentCheck.CRITICAL,
    'HEALTH-FOREST-REPLICA-DISABLED': AgentCheck.WARNING,
    'HEALTH-FOREST-REPLICA-OPEN': AgentCheck.WARNING,
    'HEALTH-FOREST-SHARED-DISK-FAILOVER': AgentCheck.CRITICAL,
    'HEALTH-FOREST-STANDS': AgentCheck.WARNING,
    'HEALTH-FOREST-STORAGE-LOW': AgentCheck.WARNING,
    'HEALTH-FOREST-UNMOUNTED': AgentCheck.WARNING,
    'HEALTH-GROUP-ALL-HOSTS-OFFLINE': AgentCheck.CRITICAL,
    'HEALTH-GROUP-ERROR': AgentCheck.CRITICAL,
    'HEALTH-GROUP-HOSTS-OFFLINE': AgentCheck.WARNING,
    'HEALTH-GROUP-NO-HOSTS': AgentCheck.WARNING,
    'HEALTH-GROUP-PERFORMANCE-METERING-DISABLED': AgentCheck.WARNING,
    'HEALTH-HOST-ERROR': AgentCheck.CRITICAL,
    'HEALTH-HOST-MAINTENANCE-HOST-MODE': AgentCheck.OK,
    'HEALTH-HOST-NETWORK-UNREACHABLE': AgentCheck.WARNING,
    'HEALTH-HOST-OFFLINE': AgentCheck.WARNING,
    'HEALTH-HOST-RECENT-RESTART': AgentCheck.OK,
    'HEALTH-MISSING-HOST-MODE': AgentCheck.WARNING,
    'HEALTH-PERFORMANCE-METERING-DISABLED': AgentCheck.WARNING,
    'HEALTH-REPLICA-FOREST': AgentCheck.OK,
    'HEALTH-SERVER-DATABASE-DISABLED': AgentCheck.WARNING,
    'HEALTH-SERVER-DISABLED': AgentCheck.WARNING,
    'HEALTH-SERVER-ERROR': AgentCheck.CRITICAL,
    'HEALTH-SERVER-HOST-NETWWORK-UNREACHABLE': AgentCheck.WARNING,
    'HEALTH-SERVER-HOST-OFFLINE': AgentCheck.WARNING,
    'HEALTH-SERVER-NOT-ENABLED': AgentCheck.WARNING,
    'HEALTH-SERVER-OFFLINE': AgentCheck.WARNING,
    'HEALTH-SERVER-PORT-LESS-1025': AgentCheck.WARNING,
}
