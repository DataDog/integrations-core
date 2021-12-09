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
    'silk.host.views_count',
    'silk.host.volumes_count',
    'silk.stats.system.io_ops.avg',
    'silk.stats.system.io_ops.max',
    'silk.stats.system.latency.inner',
    'silk.stats.system.latency.outer',
    'silk.stats.system.resolution',
    'silk.stats.system.throughput.avg',
    'silk.stats.system.throughput.max',
    'silk.stats.volume.io_ops.avg',
    'silk.stats.volume.io_ops.max',
    'silk.stats.volume.latency.inner',
    'silk.stats.volume.latency.outer',
    'silk.stats.volume.resolution',
    'silk.stats.volume.throughput.avg',
    'silk.stats.volume.throughput.max',
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
]

SAMPLE_RAW_EVENT = {
    "event_id": 11,
    "id": 2,
    "labels": "EVENT, ACTION",
    "level": "INFO",
    "message": "Event logging started",
    "name": "EVENT_LOGGING_STARTED",
    "timestamp": 1638831003.782305,
    "user": "Internal",
}

EXPECTED_EVENT_PAYLOAD = {
    "msg_title": "EVENT_LOGGING_STARTED",
    "msg_text": "Event logging started",
    "timestamp": 1638831003.782305,
    "tags": ["test:silk", "user:Internal"],
    "event_type": "EVENT, ACTION",
    "alert_type": "info",
    "source_type_name": "silk",
}
