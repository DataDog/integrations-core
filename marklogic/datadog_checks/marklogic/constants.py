# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Dict

from datadog_checks.base import AgentCheck

RESOURCE_TYPES = {
    'cluster': {'plural': None, 'singular': 'cluster'},
    'forest': {'plural': 'forests', 'singular': 'forest'},
    'forests': {'plural': 'forests', 'singular': 'forest'},
    'database': {'plural': 'databases', 'singular': 'database'},
    'databases': {'plural': 'databases', 'singular': 'database'},
    'group': {'plural': 'groups', 'singular': 'group'},
    'groups': {'plural': 'groups', 'singular': 'group'},
    'host': {'plural': 'hosts', 'singular': 'host'},
    'hosts': {'plural': 'hosts', 'singular': 'host'},
    'server': {'plural': 'servers', 'singular': 'server'},
    'servers': {'plural': 'servers', 'singular': 'server'},
}  # type: Dict[str, Dict]

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
