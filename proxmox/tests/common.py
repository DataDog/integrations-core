# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
INSTANCE = {'proxmox_server': 'http://localhost:8006/api2/json', 'tags': ['testing']}

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

ALL_METRICS = BASE_METRICS + RESOURCE_METRICS + PERF_METRICS
