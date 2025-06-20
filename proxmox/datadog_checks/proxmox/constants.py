# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

RESOURCE_METRICS = [
    'netin',
    'maxmem',
    'mem',
    'maxdisk',
    'maxcpu',
    'disk',
    'netout',
    'uptime',
    'diskread',
    'cpu',
    'diskwrite',
]
RESOURCE_TYPE_MAP = {
    'qemu': 'vm',
    'lxc': 'container',
    'storage': 'storage',
    'node': 'node',
    'pool': 'pool',
    'sdn': 'sdn',
}
NODE_RESOURCE = 'node'
VM_RESOURCE = 'vm'

OK_STATUS = ['ok', 'available', 'running', 'online']
