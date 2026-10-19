# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here
from datadog_checks.dev.utils import get_metadata_metrics

HERE = get_here()


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


CHECK_NAME = 'kueue'
INSTANCE_STATE_KEY = 'kueue_instance'

MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:8080/metrics',
    'tags': ['test:tag'],
}

# Tags defined in the YAML files for the e2e tests
CLUSTER_QUEUE_TAGS = ['kueue_cluster_queue:cluster-queue', 'replica_role:leader']
CLUSTER_QUEUE_COHORT_TAGS = [*CLUSTER_QUEUE_TAGS, 'cohort:shared-cohort']
CLUSTER_QUEUE_FLAVOR_TAGS = [*CLUSTER_QUEUE_COHORT_TAGS, 'kueue_resource_flavor:default-flavor']
LOCAL_QUEUE_TAGS = ['kueue_local_queue:user-queue', 'namespace:default', 'replica_role:leader']
LOCAL_QUEUE_FLAVOR_TAGS = [*LOCAL_QUEUE_TAGS, 'kueue_resource_flavor:default-flavor']
COHORT_TAGS = ['cohort:shared-cohort', 'replica_role:leader']
COHORT_FLAVOR_TAGS = [*COHORT_TAGS, 'kueue_resource_flavor:default-flavor']

# Keys: metrics we assert in both unit (mock metrics.txt) and e2e (live cluster).
# Values: tags that must appear on at least one series for that metric (empty = metric presence only, no tags checked).
EXPECTED_METRIC_TAGS = {
    'kueue.build_info': [],
    'kueue.go.goroutines': [],
    'kueue.go.info': ['go_version:go1.26.3'],
    'kueue.cluster_queue.info': ['kueue_cluster_queue:cluster-queue', 'root_cohort:shared-cohort'],
    'kueue.cluster_queue.status': [*CLUSTER_QUEUE_TAGS, 'status:active'],
    'kueue.cluster_queue.nominal_quota.cpu': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.nominal_quota.memory': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.resource_pending.cpu': CLUSTER_QUEUE_TAGS,
    'kueue.cluster_queue.resource_pending.memory': CLUSTER_QUEUE_TAGS,
    'kueue.cluster_queue.resource_reservation.cpu': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.resource_reservation.memory': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.resource_usage.cpu': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.resource_usage.memory': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.local_queue.status': [*LOCAL_QUEUE_TAGS, 'active:True'],
    'kueue.admitted.active_workloads': CLUSTER_QUEUE_TAGS,
    'kueue.local_queue.admitted.active_workloads': LOCAL_QUEUE_TAGS,
    'kueue.pending_workloads': [*CLUSTER_QUEUE_TAGS, 'status:inadmissible'],
    'kueue.local_queue.pending_workloads': [*LOCAL_QUEUE_TAGS, 'status:inadmissible'],
    'kueue.local_queue.resource_reservation.cpu': LOCAL_QUEUE_FLAVOR_TAGS,
    'kueue.local_queue.resource_reservation.memory': LOCAL_QUEUE_FLAVOR_TAGS,
    'kueue.local_queue.resource_usage.cpu': LOCAL_QUEUE_FLAVOR_TAGS,
    'kueue.local_queue.resource_usage.memory': LOCAL_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.weighted_share': CLUSTER_QUEUE_COHORT_TAGS,
    'kueue.cohort.info': ['cohort:shared-cohort', 'root_cohort:shared-cohort'],
    'kueue.cohort.weighted_share': COHORT_TAGS,
    'kueue.cohort_subtree.quota.cpu': COHORT_FLAVOR_TAGS,
    'kueue.cohort_subtree.resource_reservations.cpu': COHORT_FLAVOR_TAGS,
    'kueue.cohort_subtree.admitted.active_workloads': COHORT_TAGS,
    'kueue.cluster_queue.nominal_quota.gpu': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.resource_usage.gpu': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.cluster_queue.resource_usage.other': CLUSTER_QUEUE_FLAVOR_TAGS,
    'kueue.finished_workloads': [],
    'kueue.preempted_workloads.count': ['reason:InClusterQueue'],
    'kueue.evicted_workloads.count': ['reason:Preempted'],
    'kueue.evicted_workloads_once.count': ['reason:Preempted'],
    'kueue.finished_workloads.count': [],
    'kueue.local_queue.finished_workloads.count': [],
    'kueue.controller.runtime.active_workers': [],
    'kueue.process.uptime.seconds': [],
    'kueue.workqueue.depth': [],
}

# Same metrics as EXPECTED_METRIC_TAGS keys (single source of truth for unit + e2e).
UNIT_E2E_METRICS = tuple(EXPECTED_METRIC_TAGS)

# Extra Datadog metric names covered by tests/fixtures/metrics.txt but not required on the e2e cluster.
FIXTURE_ONLY_METRICS = ('kueue.cluster_queue.resource_pending.gpu',)

# All metrics for unit test_check presence + instance tag assertions.
UNIT_METRICS = (*UNIT_E2E_METRICS, *FIXTURE_ONLY_METRICS)

CONFIG_GATED_METRIC_PREFIXES = (
    'kueue.ready_wait_time.seconds',
    'kueue.local_queue.ready_wait_time.seconds',
    'kueue.admitted_until_ready.wait_time.seconds',
    'kueue.local_queue.admitted_until_ready.wait_time.seconds',
    'kueue.pods_ready_to_evicted_time.seconds',
    'kueue.admission_checks.wait_time.seconds',
    'kueue.local_queue.admission_checks.wait_time.seconds',
    'kueue.admission_cycle.preemption_skips',
    'kueue.replaced_workload_slices.count',
)


def live_metadata_metrics():
    """Return the metadata.csv metrics the live cluster emits, plus the config-gated names to exclude.

    Splitting them lets the e2e assert symmetric inclusion: every other metadata.csv row has to be
    emitted by the cluster, and every emitted metric has to have a row. `exclude` alone is not enough,
    because `assert_metrics_using_metadata` only applies it to submitted metrics, never to the
    metadata.csv keys it checks for absence.
    """
    all_metadata = get_metadata_metrics()
    config_gated = [name for name in all_metadata if name.startswith(CONFIG_GATED_METRIC_PREFIXES)]
    return {name: metadata for name, metadata in all_metadata.items() if name not in config_gated}, config_gated


INACTIVE_CLUSTER_QUEUE_TAGS = ['kueue_cluster_queue:invalid-queue', 'replica_role:leader', 'status:pending']
