# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
INSTANCE = {
    'host_address': 'http://{}:80'.format(HOST),
    'tags': ['test:silk'],
}
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')


METRICS = [
    'silk.system.views_count',
    'silk.system.volumes_count',
    'silk.system.io_ops.avg',
    'silk.system.io_ops.max',
    'silk.system.latency.inner',
    'silk.system.latency.outer',
    'silk.system.throughput.avg',
    'silk.system.throughput.max',
    'silk.volume.io_ops.avg',
    'silk.volume.io_ops.max',
    'silk.volume.latency.inner',
    'silk.volume.latency.outer',
    'silk.volume.throughput.avg',
    'silk.volume.throughput.max',
    'silk.system.capacity.allocated',
    'silk.system.capacity.allocated_snapshots_and_views',
    'silk.system.capacity.allocated_volumes',
    'silk.system.capacity.curr_dt_chunk',
    'silk.system.capacity.free',
    'silk.system.capacity.logical',
    'silk.system.capacity.physical',
    'silk.system.capacity.provisioned',
    'silk.system.capacity.provisioned_snapshots',
    'silk.system.capacity.provisioned_views',
    'silk.system.capacity.provisioned_volumes',
    'silk.system.capacity.reserved',
    'silk.system.capacity.total',
    'silk.volume.logical_capacity',
    'silk.volume.no_dedup',
    'silk.volume.size',
    'silk.volume.snapshots_logical_capacity',
    'silk.volume.stream_average_compressed_bytes',
    'silk.volume.compressed_ratio.avg',
    'silk.replication.system.logical_in',
    'silk.replication.system.logical_out',
    'silk.replication.system.physical_in',
    'silk.replication.system.physical_out',
    'silk.replication.volume.logical_in',
    'silk.replication.volume.logical_out',
    'silk.replication.volume.physical_in',
    'silk.replication.volume.physical_out',
    'silk.volume.block_size.io_ops.avg',
    'silk.volume.block_size.latency.inner',
    'silk.volume.block_size.latency.outer',
    'silk.volume.block_size.throughput.avg',
    'silk.system.block_size.io_ops.avg',
    'silk.system.block_size.latency.inner',
    'silk.system.block_size.latency.outer',
    'silk.system.block_size.throughput.avg',
]
