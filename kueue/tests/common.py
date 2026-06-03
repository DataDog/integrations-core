# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'tags': ['test:tag'],
}

TEST_METRICS = [
    'kueue.go.goroutines',
    'kueue.cluster_queue.resource_usage.cpu',
    'kueue.cluster_queue.resource_usage.gpu',
    'kueue.cluster_queue.resource_usage.other',
    'kueue.cluster_queue.resource_pending.gpu',
    'kueue.cluster_queue.pending_workloads',
    'kueue.local_queue.pending_workloads',
    'kueue.resource_flavor.quota_reserved_workloads',
]
