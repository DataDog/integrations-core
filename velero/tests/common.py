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
    'velero.pod_volume.data.download.cancel.count': 'monotonic_count',
    'velero.pod_volume.data.download.failure.count': 'monotonic_count',
    'velero.pod_volume.data.download.success.count': 'monotonic_count',
    'velero.pod_volume.data.upload.cancel.count': 'monotonic_count',
    'velero.pod_volume.data.upload.failure.count': 'monotonic_count',
    'velero.pod_volume.data.upload.success.count': 'monotonic_count',
    'velero.pod_volume.backup.dequeue.count': 'monotonic_count',
    'velero.pod_volume.backup.enqueue.count': 'monotonic_count',
    'velero.backup.attempt.count': 'monotonic_count',
    'velero.backup.deletion.attempt.count': 'monotonic_count',
    'velero.backup.deletion.failure.count': 'monotonic_count',
    'velero.backup.deletion.success.count': 'monotonic_count',
    'velero.backup.failure.count': 'monotonic_count',
    'velero.backup.items.errors': 'gauge',
    'velero.backup.items': 'gauge',
    'velero.backup.last_status': 'gauge',
    'velero.backup.partial_failure.count': 'monotonic_count',
    'velero.backup.success.count': 'monotonic_count',
    'velero.backup.amount': 'gauge',
    'velero.backup.validation_failure.count': 'monotonic_count',
    'velero.backup.warning.count': 'monotonic_count',
    'velero.csi_snapshot.attempt.count': 'monotonic_count',
    'velero.csi_snapshot.failure.count': 'monotonic_count',
    'velero.csi_snapshot.success.count': 'monotonic_count',
    'velero.restore.attempt.count': 'monotonic_count',
    'velero.restore.failed.count': 'monotonic_count',
    'velero.restore.partial_failure.count': 'monotonic_count',
    'velero.restore.success.count': 'monotonic_count',
    'velero.restore.amount': 'gauge',
    'velero.restore.validation_failed.count': 'monotonic_count',
    'velero.volume_snapshot.attempt.count': 'monotonic_count',
    'velero.volume_snapshot.failure.count': 'monotonic_count',
    'velero.volume_snapshot.success.count': 'monotonic_count',
}

OPTIONAL_METRICS = {  # These metrics require a backup attempt to appear
    'velero.backup.duration.seconds.bucket': 'monotonic_count',
    'velero.backup.duration.seconds.sum': 'monotonic_count',
    'velero.backup.duration.seconds.count': 'monotonic_count',
    'velero.backup.last_successful_timestamp': 'gauge',
    'velero.backup.tarball_size_bytes': 'gauge',
}

ADDITIONAL_METRICS = {  # These metrics did not appear in any of the test payloads
    'velero.pod_volume.operation_latency_seconds.bucket': 'histogram',
    'velero.pod_volume.operation_latency_seconds.count': 'count',
    'velero.pod_volume.operation_latency_seconds.gauge': 'gauge',
    'velero.pod_volume.operation_latency_seconds.sum': 'count',
}
