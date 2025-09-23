# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

CLUSTER_STATS = {
    'node_count': 'nodes.count',
    'nodes_active': 'nodes.active',
    'volumes_started': 'volumes.started',
    'volume_count': 'volumes.count',
}


GENERAL_STATS = {
    'size_used': 'size.used',
    'inodes_free': 'inodes.free',
    'size_free': 'size.free',
    'size_total': 'size.total',
    'inodes_used': 'inodes.used',
    'inodes_total': 'inodes.total',
    'online': 'online',
}

VOL_SUBVOL_STATS = {
    'disperse': 'disperse',
    'disperse_redundancy': 'disperse_redundancy',
    'replica': 'replica',
}

VOLUME_STATS = {
    'v_used_percent': 'used.percent',
    'num_bricks': 'bricks.count',
    'distribute': 'distribute',
    'v_size_used': 'size.used',
    'v_size': 'size.total',
    'snapshot_count': 'snapshot.count',
}

VOLUME_STATS.update(GENERAL_STATS)
VOLUME_STATS.update(VOL_SUBVOL_STATS)

BRICK_STATS = {'block_size': 'block_size'}
BRICK_STATS.update(GENERAL_STATS)

# Parse metric values that contain measurements, e.g "2.00 GiB"
PARSE_METRICS = ['v_size_used', 'v_size']
