# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from pathlib import Path
from typing import Any

INSTANCE = {'proxmox_server': 'http://localhost:8006/api2/json', 'tags': ['testing']}

# The tags every point carries: the server tag plus the instance-level `tags` from INSTANCE.
# Derived from INSTANCE so the two can't drift apart.
BASE_TAGS = [f'proxmox_server:{INSTANCE["proxmox_server"]}'] + INSTANCE['tags']

CLUSTER_RESOURCES_FIXTURE = (
    Path(__file__).parent / 'fixtures' / 'GET' / 'api2' / 'json' / 'cluster' / 'resources' / 'response.json'
)


def _cluster_resources_fixture() -> dict[str, Any]:
    """Return a fresh copy of the shipped `/cluster/resources` payload.

    Mutating the real fixture rather than substituting a minimal one keeps the rest of the
    inventory in play, so a test asserting one resource's absence can still assert that other
    resources were collected — otherwise the assertion would also pass if the override
    silently stopped matching.
    """
    with CLUSTER_RESOURCES_FIXTURE.open() as f:
        return json.load(f)


def cluster_resources_with_offline_node() -> dict[str, Any]:
    """Return the shipped `/cluster/resources` payload with the node flipped to `offline`."""
    payload = _cluster_resources_fixture()
    for resource in payload['data']:
        if resource.get('type') == 'node':
            resource['status'] = 'offline'
    return payload


def cluster_resources_with_vm_maxcpu(maxcpu: int | None) -> dict[str, Any]:
    """Return the shipped payload with VM `qemu/100`'s `maxcpu` set to `maxcpu`, or removed if None.

    Proxmox omits `maxcpu` for a node the token lacks `Sys.Audit` on
    (`PVE/API2/Cluster.pm:622` → `PVE/API2Tools.pm:63`), so the check has to tell an absent
    field from a zero one.
    """
    payload = _cluster_resources_fixture()
    for resource in payload['data']:
        if resource.get('id') == 'qemu/100':
            if maxcpu is None:
                resource.pop('maxcpu', None)
            else:
                resource['maxcpu'] = maxcpu
    return payload


BASE_METRICS = [
    'proxmox.node.count',
    'proxmox.vm.count',
    'proxmox.container.count',
    'proxmox.pool.count',
    'proxmox.storage.count',
    'proxmox.sdn.count',
    'proxmox.node.up',
    'proxmox.vm.up',
    'proxmox.container.up',
    'proxmox.storage.up',
    'proxmox.sdn.up',
]

RESOURCE_METRICS = [
    'proxmox.cpu',
    'proxmox.disk',
    'proxmox.cpu.max',
    'proxmox.disk.max',
    'proxmox.mem.max',
    'proxmox.mem',
    'proxmox.uptime',
]

PERF_METRICS = [
    'proxmox.cpu.avg1',
    'proxmox.cpu.avg15',
    'proxmox.cpu.avg5',
    'proxmox.cpu.current',
    'proxmox.cpu.iowait',
    'proxmox.cpu.max',
    'proxmox.disk.total',
    'proxmox.disk.used',
    'proxmox.disk.read',
    'proxmox.disk.write',
    'proxmox.mem.total',
    'proxmox.mem.used',
    'proxmox.net.in',
    'proxmox.net.out',
    'proxmox.swap.total',
    'proxmox.swap.used',
]

HA_METIRCS = ['proxmox.ha.quorate', 'proxmox.ha.quorum']

# Emitted only for VMs and nodes, with `proxmox_type` on the point, for usage metering.
METERING_METRICS = [
    'proxmox.vm.cpu.max',
    'proxmox.node.cpu.max',
]

NODE_RESOURCE_METRICS = set(RESOURCE_METRICS) - {
    'proxmox.diskread',
    'proxmox.diskwrite',
    'proxmox.netout',
    'proxmox.netin',
}

STORAGE_RESOURCE_METRICS = {'proxmox.disk.max', 'proxmox.disk'}

VM_PERF_METRICS = set(PERF_METRICS) - {
    'proxmox.cpu.avg1',
    'proxmox.cpu.avg15',
    'proxmox.cpu.avg5',
    'proxmox.cpu.iowait',
    'proxmox.disk.used',
    'proxmox.swap.total',
    'proxmox.swap.used',
}
NODE_PERF_METRICS = set(PERF_METRICS) - {'proxmox.disk.read', 'proxmox.disk.write'}

CONTAINER_PERF_METRICS = set(PERF_METRICS) - {
    'proxmox.cpu.avg1',
    'proxmox.cpu.avg5',
    'proxmox.cpu.avg15',
    'proxmox.swap.total',
    'proxmox.swap.used',
    'proxmox.cpu.iowait',
}

STORAGE_PERF_METRICS = {'proxmox.disk.total', 'proxmox.disk.used'}

ALL_METRICS = BASE_METRICS + RESOURCE_METRICS + PERF_METRICS + HA_METIRCS + METERING_METRICS

ALL_EVENTS = [
    {
        'timestamp': 1752721614,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Update package database on node ip-122-82-3-112',
        'msg_title': 'Update package database',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:aptupdate', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752690541,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Shutdown on node ip-122-82-3-112',
        'msg_title': 'Container Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzshutdown',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690475,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690408,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Shutdown on node ip-122-82-3-112',
        'msg_title': 'Container Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzshutdown',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690322,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690282,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Shutdown on node ip-122-82-3-112',
        'msg_title': 'Container Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzshutdown',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690215,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690205,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Shutdown on node ip-122-82-3-112',
        'msg_title': 'Container Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzshutdown',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752678425,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Bulk start VMs and Containers on node ip-122-82-3-112',
        'msg_title': 'Bulk start VMs and Containers',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:startall', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752628379,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Update package database on node ip-122-82-3-112',
        'msg_title': 'Update package database',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:aptupdate', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752604610,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752604592,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Shutdown on node ip-122-82-3-112',
        'msg_title': 'Container Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'test',
            'tag1',
            'proxmox_event_type:vzshutdown',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752854281,
        'event_type': 'proxmox',
        'host': 'debian',
        'msg_text': 'Vm VM 100: VM Shutdown on node ip-122-82-3-112',
        'msg_title': 'VM Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:qmshutdown', 'proxmox_user:root@pam'],
    },
]
START_UPDATE_EVENTS = [
    {
        'timestamp': 1752721614,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Update package database on node ip-122-82-3-112',
        'msg_title': 'Update package database',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:aptupdate', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752690475,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'tag1',
            'test',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690322,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'tag1',
            'test',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752690215,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'tag1',
            'test',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
    {
        'timestamp': 1752628379,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Update package database on node ip-122-82-3-112',
        'msg_title': 'Update package database',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:aptupdate', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752604610,
        'event_type': 'proxmox',
        'host': None,
        'msg_text': 'Container CT111: Container Started on node ip-122-82-3-112',
        'msg_title': 'Container Started',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': [
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'tag1',
            'test',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'proxmox_type:container',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_event_type:vzstart',
            'proxmox_user:root@pam',
        ],
    },
]


NO_CONTAINER_EVENTS = [
    {
        'timestamp': 1752721614,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Update package database on node ip-122-82-3-112',
        'msg_title': 'Update package database',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:aptupdate', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752678425,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Bulk start VMs and Containers on node ip-122-82-3-112',
        'msg_title': 'Bulk start VMs and Containers',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:startall', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752628379,
        'event_type': 'proxmox',
        'host': 'ip-122-82-3-112',
        'msg_text': 'Update package database on node ip-122-82-3-112',
        'msg_title': 'Update package database',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:aptupdate', 'proxmox_user:root@pam'],
    },
    {
        'timestamp': 1752854281,
        'event_type': 'proxmox',
        'host': 'debian',
        'msg_text': 'Vm VM 100: VM Shutdown on node ip-122-82-3-112',
        'msg_title': 'VM Shutdown',
        'alert_type': 'success',
        'source_type_name': 'proxmox',
        'tags': ['proxmox_event_type:qmshutdown', 'proxmox_user:root@pam'],
    },
]
