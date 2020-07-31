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

RESOURCE_METRICS_AVAILABLE = {
    'forest': {'status': True, 'storage': True, 'requests': False},
    'database': {'status': True, 'storage': True, 'requests': False},
    'host': {'status': True, 'storage': True, 'requests': True},
    'server': {'status': False, 'storage': False, 'requests': True},
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

# The integration only checks the databases and forests health
STATE_HEALTH_MAPPER = {
    "info": AgentCheck.OK,
    "at-risk": AgentCheck.WARNING,
    "offline": AgentCheck.WARNING,
    "maintenance": AgentCheck.WARNING,
    "critical": AgentCheck.CRITICAL,
}
