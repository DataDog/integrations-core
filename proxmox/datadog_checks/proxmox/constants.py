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

PERF_METRIC_NAME = {
    'net_out': 'net.out',
    'uptime': 'uptime',
    'net_in': 'net.in',
    'cpu_avg1': 'cpu.avg1',
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
    'disk_read': 'disk.read',
    'disk_write': 'disk.write',
}

RESOURCE_METRIC_NAME = {
    'cpu': 'cpu',
    'maxmem': 'mem.max',
    'mem': 'mem',
    'maxdisk': 'disk.max',
    'maxcpu': 'cpu.max',
    'disk': 'disk',
}

RESOURCE_COUNT_METRICS = ['uptime']
