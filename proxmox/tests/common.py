# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

INSTANCE = {'proxmox_server': 'http://localhost:8006/api2/json', 'tags': ['testing']}

ALL_METRICS = [
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
