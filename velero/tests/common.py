# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8085


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:tag'],
}

COMPOSE_FILE = os.path.join(HERE, 'compose', 'docker-compose.yaml')

TEST_METRICS = {
    'velero.go.gc.duration.seconds.quantile': 'gauge',
    'velero.go.gc.duration.seconds.sum': 'monotonic_count',
    'velero.go.gc.duration.seconds.count': 'monotonic_count',
    'velero.go.goroutines': 'gauge',
    'velero.go.memstats.alloc_bytes': 'gauge',
    'velero.go.memstats.alloc_bytes.count': 'monotonic_count',
    'velero.go.memstats.buck_hash.sys_bytes': 'gauge',
    'velero.go.memstats.frees.count': 'monotonic_count',
    'velero.go.memstats.gc.sys_bytes': 'gauge',
    'velero.go.memstats.heap.alloc_bytes': 'gauge',
    'velero.go.memstats.heap.idle_bytes': 'gauge',
    'velero.go.memstats.heap.inuse_bytes': 'gauge',
    'velero.go.memstats.heap.objects': 'gauge',
    'velero.go.memstats.heap.released_bytes': 'gauge',
    'velero.go.memstats.heap.sys_bytes': 'gauge',
    'velero.go.memstats.last_gc_time_seconds': 'gauge',
    'velero.go.memstats.lookups.count': 'monotonic_count',
    'velero.go.memstats.mallocs.count': 'monotonic_count',
    'velero.go.memstats.mcache.inuse_bytes': 'gauge',
    'velero.go.memstats.mcache.sys_bytes': 'gauge',
    'velero.go.memstats.mspan.inuse_bytes': 'gauge',
    'velero.go.memstats.mspan.sys_bytes': 'gauge',
    'velero.go.memstats.next.gc_bytes': 'gauge',
    'velero.go.memstats.other.sys_bytes': 'gauge',
    'velero.go.memstats.stack.inuse_bytes': 'gauge',
    'velero.go.memstats.stack.sys_bytes': 'gauge',
    'velero.go.memstats.sys_bytes': 'gauge',
    'velero.go.threads': 'gauge',
    'velero.podVolume.data.download.cancel.count': 'monotonic_count',
    'velero.podVolume.data.download.failure.count': 'monotonic_count',
    'velero.podVolume.data.download.success.count': 'monotonic_count',
    'velero.podVolume.data.upload.cancel.count': 'monotonic_count',
    'velero.podVolume.data.upload.failure.count': 'monotonic_count',
    'velero.podVolume.data.upload.success.count': 'monotonic_count',
    'velero.podVolume.pod_volume.backup.dequeue.count': 'monotonic_count',
    'velero.podVolume.pod_volume.backup.enqueue.count': 'monotonic_count',
    'velero.process.cpu.seconds.count': 'monotonic_count',
    'velero.process.max_fds': 'gauge',
    'velero.process.open_fds': 'gauge',
    'velero.process.resident_memory.bytes': 'gauge',
    'velero.process.start_time.seconds': 'gauge',
    'velero.process.virtual_memory.bytes': 'gauge',
    'velero.process.virtual_memory.max_bytes': 'gauge',
    'velero.promhttp_metric_handler_requests.in_flight': 'gauge',
    'velero.promhttp_metric_handler_requests.count': 'monotonic_count',
    'velero.backup.attempt.count': 'monotonic_count',
    'velero.backup.deletion.attempt.count': 'monotonic_count',
    'velero.backup.deletion.failure.count': 'monotonic_count',
    'velero.backup.deletion.success.count': 'monotonic_count',
    'velero.backup.duration.seconds.bucket': 'monotonic_count',
    'velero.backup.duration.seconds.sum': 'monotonic_count',
    'velero.backup.duration.seconds.count': 'monotonic_count',
    'velero.backup.failure.count': 'monotonic_count',
    'velero.backup.items.errors': 'gauge',
    'velero.backup.items': 'gauge',
    'velero.backup.last_status': 'gauge',
    'velero.backup.last_successful_timestamp': 'gauge',
    'velero.backup.partial_failure.count': 'monotonic_count',
    'velero.backup.success.count': 'monotonic_count',
    'velero.backup.tarball_size_bytes': 'gauge',
    'velero.backup': 'gauge',
    'velero.backup.validation_failure.count': 'monotonic_count',
    'velero.backup.warning.count': 'monotonic_count',
    'velero.csi_snapshot.attempt.count': 'monotonic_count',
    'velero.csi_snapshot.failure.count': 'monotonic_count',
    'velero.csi_snapshot.success.count': 'monotonic_count',
    'velero.restore.attempt.count': 'monotonic_count',
    'velero.restore.failed.count': 'monotonic_count',
    'velero.restore.partial_failure.count': 'monotonic_count',
    'velero.restore.success.count': 'monotonic_count',
    'velero.restore': 'gauge',
    'velero.restore.validation_failed.count': 'monotonic_count',
    'velero.volume_snapshot.attempt.count': 'monotonic_count',
    'velero.volume_snapshot.failure.count': 'monotonic_count',
    'velero.volume_snapshot.success.count': 'monotonic_count',
}
