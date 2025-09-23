# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.dev.fs import read_file

HERE = get_here()
HOST = get_docker_hostname()
INSTANCE = {
    'host_address': 'http://{}:80'.format(HOST),
    'tags': ['test:silk'],
    'enable_blocksize_statistics': True,
    'enable_read_write_statistics': True,
}
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

BASE_TAGS = ['silk_host:localhost:80', 'test:silk']
SYSTEM_TAGS = ['system_id:5501', 'system_name:K2-5501']


def mock_get_data(url):
    file_contents = read_file(os.path.join(HERE, 'fixtures', 'stats', url))
    response = json.loads(file_contents)
    return [(response, 200)]


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
]

BLOCKSIZE_METRICS = [
    'silk.volume.block_size.io_ops.avg',
    'silk.volume.block_size.latency.inner',
    'silk.volume.block_size.latency.outer',
    'silk.volume.block_size.throughput.avg',
    'silk.system.block_size.io_ops.avg',
    'silk.system.block_size.latency.inner',
    'silk.system.block_size.latency.outer',
    'silk.system.block_size.throughput.avg',
]

READ_WRITE_METRICS = [
    'silk.volume.read.io_ops.avg',
    'silk.volume.read.latency.inner',
    'silk.volume.read.latency.outer',
    'silk.volume.read.throughput.avg',
    'silk.system.read.io_ops.avg',
    'silk.system.read.latency.inner',
    'silk.system.read.latency.outer',
    'silk.system.read.throughput.avg',
    'silk.volume.write.io_ops.avg',
    'silk.volume.write.latency.inner',
    'silk.volume.write.latency.outer',
    'silk.volume.write.throughput.avg',
    'silk.system.write.io_ops.avg',
    'silk.system.write.latency.inner',
    'silk.system.write.latency.outer',
    'silk.system.write.throughput.avg',
]
