# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

RESOURCE_TYPE_MAP = {
    'qemu': 'vm',
    'lxc': 'container',
    'openvz': 'container',
    'storage': 'storage',
    'node': 'node',
    'pool': 'pool',
    'sdn': 'sdn',
}
NODE_RESOURCE = 'node'
VM_RESOURCE = 'vm'

OK_STATUS = ['ok', 'available', 'running', 'online']
