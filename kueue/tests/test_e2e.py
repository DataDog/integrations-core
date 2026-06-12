# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_submission_type=True)

    cluster_queue_tags = ['kueue_cluster_queue:cluster-queue', 'replica_role:leader']
    cluster_queue_flavor_tags = [*cluster_queue_tags, 'kueue_resource_flavor:default-flavor']
    local_queue_tags = ['kueue_local_queue:user-queue', 'namespace:default', 'replica_role:leader']
    local_queue_flavor_tags = [*local_queue_tags, 'kueue_resource_flavor:default-flavor']

    expected_metric_tags = {
        'kueue.build_info': [],
        'kueue.go.goroutines': [],
        'kueue.go.info': [],
        'kueue.cluster_queue.info': ['kueue_cluster_queue:cluster-queue'],
        'kueue.cluster_queue.status': ['kueue_cluster_queue:cluster-queue'],
        'kueue.cluster_queue.nominal_quota.cpu': cluster_queue_flavor_tags,
        'kueue.cluster_queue.nominal_quota.memory': cluster_queue_flavor_tags,
        'kueue.cluster_queue.resource_pending.cpu': cluster_queue_tags,
        'kueue.cluster_queue.resource_pending.memory': cluster_queue_tags,
        'kueue.cluster_queue.resource_reservation.cpu': cluster_queue_flavor_tags,
        'kueue.cluster_queue.resource_reservation.memory': cluster_queue_flavor_tags,
        'kueue.cluster_queue.resource_usage.cpu': cluster_queue_flavor_tags,
        'kueue.cluster_queue.resource_usage.memory': cluster_queue_flavor_tags,
        'kueue.local_queue.status': [],
        'kueue.admitted.active_workloads': cluster_queue_tags,
        'kueue.local_queue.admitted.active_workloads': local_queue_tags,
        'kueue.pending_workloads': [*cluster_queue_tags, 'status:inadmissible'],
        'kueue.local_queue.pending_workloads': [*local_queue_tags, 'status:inadmissible'],
        'kueue.local_queue.resource_reservation.cpu': local_queue_flavor_tags,
        'kueue.local_queue.resource_reservation.memory': local_queue_flavor_tags,
        'kueue.local_queue.resource_usage.cpu': local_queue_flavor_tags,
        'kueue.local_queue.resource_usage.memory': local_queue_flavor_tags,
        'kueue.controller.runtime.active_workers': [],
        'kueue.process.uptime.seconds': [],
        'kueue.workqueue.depth': [],
    }

    for metric, tags in expected_metric_tags.items():
        aggregator.assert_metric(metric, at_least=1)
        for tag in tags:
            aggregator.assert_metric_has_tag(metric, tag)
