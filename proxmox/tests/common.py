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
    'proxmox.container.cpu',
    'proxmox.container.disk',
    'proxmox.container.diskread',
    'proxmox.container.diskwrite',
    'proxmox.container.maxcpu',
    'proxmox.container.maxdisk',
    'proxmox.container.maxmem',
    'proxmox.container.mem',
    'proxmox.container.netin',
    'proxmox.container.netout',
    'proxmox.container.uptime',
    'proxmox.node.cpu',
    'proxmox.node.disk',
    'proxmox.node.maxcpu',
    'proxmox.node.maxdisk',
    'proxmox.node.maxmem',
    'proxmox.node.mem',
    'proxmox.node.uptime',
    'proxmox.storage.disk',
    'proxmox.storage.maxdisk',
    'proxmox.vm.cpu',
    'proxmox.vm.disk',
    'proxmox.vm.diskread',
    'proxmox.vm.diskwrite',
    'proxmox.vm.maxcpu',
    'proxmox.vm.maxdisk',
    'proxmox.vm.maxmem',
    'proxmox.vm.mem',
    'proxmox.vm.netin',
    'proxmox.vm.netout',
    'proxmox.vm.uptime',
]

ALL_METRICS = BASE_METRICS + RESOURCE_METRICS
