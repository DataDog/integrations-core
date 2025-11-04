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

EVENT_TYPE_TO_TITLE = {
    'vzstart': 'Container Started',
    'vzshutdown': 'Container Shutdown',
    'vzsuspend': 'Container Suspened',
    'qmstart': 'VM Started',
    'qhstop': 'VM Stopped',
    'qmshutdown': 'VM Shutdown',
    'qmreboot': 'VM Rebooted',
    'qmigrate': 'VM Migrated',
    'qmsuspend': 'VM Hibernated',
    'startall': 'Bulk start VMs and Containers',
    'stopall': 'Bulk stop VMs and Containers',
    'suspendall': 'Bulk suspend VMs and Containers',
    'aptupdate': 'Update package database',
    'vncproxy': 'Console started',
}

ALLOWED_FILTER_PROPERTIES = ['resource_name']
ADDITIONAL_FILTER_PROPERTIES = ['hostname']
ALLOWED_FILTER_TYPES = ['include', 'exclude']
