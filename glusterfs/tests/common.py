# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

GLUSTER_VERSION = os.getenv('GLUSTER_VERSION')

CHECK = 'glusterfs'
INSTANCE = {'use_sudo': False}
E2E_INIT_CONFIG = {'gstatus_path': 'docker exec gluster-node-1 gstatus'}
CONFIG = {'init_config': E2E_INIT_CONFIG, 'instances': [INSTANCE]}

EXPECTED_METRICS = [
    "glusterfs.brick.block_size",
    "glusterfs.brick.inodes.free",
    "glusterfs.brick.inodes.total",
    "glusterfs.brick.inodes.used",
    "glusterfs.brick.online",
    "glusterfs.brick.size.free",
    "glusterfs.brick.size.total",
    "glusterfs.brick.size.used",
    "glusterfs.cluster.nodes.active",
    "glusterfs.cluster.nodes.count",
    "glusterfs.cluster.volumes.count",
    "glusterfs.cluster.volumes.started",
    "glusterfs.heal_info.entries.count",
    "glusterfs.subvol.disperse",
    "glusterfs.subvol.disperse_redundancy",
    "glusterfs.subvol.replica",
    "glusterfs.volume.bricks.count",
    "glusterfs.volume.disperse",
    "glusterfs.volume.disperse_redundancy",
    "glusterfs.volume.distribute",
    "glusterfs.volume.inodes.free",
    "glusterfs.volume.inodes.total",
    "glusterfs.volume.inodes.used",
    "glusterfs.volume.online",
    "glusterfs.volume.replica",
    "glusterfs.volume.size.free",
    "glusterfs.volume.size.total",
    "glusterfs.volume.size.used",
    "glusterfs.volume.snapshot.count",
    "glusterfs.volume.used.percent",
]
