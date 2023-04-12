# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Dict  # noqa: F401

from datadog_checks.base import AgentCheck

ALLOWED_RESOURCES_FOR_FILTERS = ['database', 'forest', 'host', 'server']

BASE_ENDPOINT = '/manage/v2'

RESOURCE_TYPES = {
    'cluster': {'plural': 'clusters', 'singular': 'cluster', 'tag_name': 'cluster_name'},
    'clusters': {'plural': 'clusters', 'singular': 'cluster', 'tag_name': 'cluster_name'},
    'forest': {'plural': 'forests', 'singular': 'forest', 'tag_name': 'forest_name'},
    'forests': {'plural': 'forests', 'singular': 'forest', 'tag_name': 'forest_name'},
    'database': {'plural': 'databases', 'singular': 'database', 'tag_name': 'database_name'},
    'databases': {'plural': 'databases', 'singular': 'database', 'tag_name': 'database_name'},
    'group': {'plural': 'groups', 'singular': 'group', 'tag_name': 'group_name'},
    'groups': {'plural': 'groups', 'singular': 'group', 'tag_name': 'group_name'},
    'host': {'plural': 'hosts', 'singular': 'host', 'tag_name': 'marklogic_host_name'},
    'hosts': {'plural': 'hosts', 'singular': 'host', 'tag_name': 'marklogic_host_name'},
    'server': {'plural': 'servers', 'singular': 'server', 'tag_name': 'server_name'},
    'servers': {'plural': 'servers', 'singular': 'server', 'tag_name': 'server_name'},
}  # type: Dict[str, Dict]

# Storage metrics are duplications
RESOURCE_METRICS_AVAILABLE = {
    'forest': {'status': True, 'storage': True, 'requests': False},
    'database': {'status': True, 'storage': False, 'requests': False},
    'host': {'status': True, 'storage': False, 'requests': True},
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

SERVICE_CHECK_RESOURCES = ['database', 'forest']
