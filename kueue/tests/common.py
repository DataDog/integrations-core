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

# Tags defined in the YAML files for the e2e tests
_cluster_queue_tags = ['kueue_cluster_queue:cluster-queue', 'replica_role:leader']
_cluster_queue_flavor_tags = [*_cluster_queue_tags, 'kueue_resource_flavor:default-flavor']
_local_queue_tags = ['kueue_local_queue:user-queue', 'namespace:default', 'replica_role:leader']
_local_queue_flavor_tags = [*_local_queue_tags, 'kueue_resource_flavor:default-flavor']

# Keys: metrics we assert in both unit (mock metrics.txt) and e2e (live cluster).
# Values: tags that must appear on at least one series for that metric (empty = metric presence only, no tags checked).
EXPECTED_METRIC_TAGS = {
    'kueue.build_info': [],
    'kueue.go.goroutines': [],
    'kueue.go.info': ['go_version:go1.26.3'],
    'kueue.cluster_queue.info': ['kueue_cluster_queue:cluster-queue'],
    'kueue.cluster_queue.status': ['kueue_cluster_queue:cluster-queue'],
    'kueue.cluster_queue.nominal_quota.cpu': _cluster_queue_flavor_tags,
    'kueue.cluster_queue.nominal_quota.memory': _cluster_queue_flavor_tags,
    'kueue.cluster_queue.resource_pending.cpu': _cluster_queue_tags,
    'kueue.cluster_queue.resource_pending.memory': _cluster_queue_tags,
    'kueue.cluster_queue.resource_reservation.cpu': _cluster_queue_flavor_tags,
    'kueue.cluster_queue.resource_reservation.memory': _cluster_queue_flavor_tags,
    'kueue.cluster_queue.resource_usage.cpu': _cluster_queue_flavor_tags,
    'kueue.cluster_queue.resource_usage.memory': _cluster_queue_flavor_tags,
    'kueue.local_queue.status': [],
    'kueue.admitted.active_workloads': _cluster_queue_tags,
    'kueue.local_queue.admitted.active_workloads': _local_queue_tags,
    'kueue.pending_workloads': [*_cluster_queue_tags, 'status:inadmissible'],
    'kueue.local_queue.pending_workloads': [*_local_queue_tags, 'status:inadmissible'],
    'kueue.local_queue.resource_reservation.cpu': _local_queue_flavor_tags,
    'kueue.local_queue.resource_reservation.memory': _local_queue_flavor_tags,
    'kueue.local_queue.resource_usage.cpu': _local_queue_flavor_tags,
    'kueue.local_queue.resource_usage.memory': _local_queue_flavor_tags,
    'kueue.controller.runtime.active_workers': [],
    'kueue.process.uptime.seconds': [],
    'kueue.workqueue.depth': [],
}

# Same metrics as EXPECTED_METRIC_TAGS keys (single source of truth for unit + e2e).
UNIT_E2E_METRICS = tuple(EXPECTED_METRIC_TAGS)

# Extra Datadog metric names covered by tests/fixtures/metrics.txt but not required on the e2e cluster.
FIXTURE_ONLY_METRICS = (
    'kueue.cluster_queue.resource_usage.gpu',
    'kueue.cluster_queue.resource_usage.other',
    'kueue.cluster_queue.resource_pending.gpu',
    'kueue.resource_flavor.quota_reserved_workloads',
)

# All metrics for unit test_check presence + instance tag assertions.
UNIT_METRICS = (*UNIT_E2E_METRICS, *FIXTURE_ONLY_METRICS)
