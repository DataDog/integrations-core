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

METRIC_NAME = {
    'netout': 'net.out',
    'uptime': 'uptime',
    'net_in': 'net.in',
    'cpu_aavg1': 'cpu.avg1',
    'cpu_avg5': 'cpu.avg5',
    'cpu_avg15': 'cpu.avg15',
    'cpu_max': 'cpu.max',
    'cpu_current': 'cpu.current',
    'cpu_iowait': 'cpu.iowait',
    'mem_total': 'mem.total',
    'mem_used': 'mem.used',
    'swap_total': 'swap.total',
    'swap_used': 'swap.used',
    'disk_total': 'disk.total',
    'disk_used': 'disk.used',
}
