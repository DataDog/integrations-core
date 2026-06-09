# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import assert_service_checks, get_metadata_metrics


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check()

    aggregator.assert_metrics_using_metadata(
        get_metadata_metrics(),
        check_submission_type=True,
        exclude=['kueue.go.gc.duration.seconds.quantile'],
    )

    for metric in (
        'kueue.build_info',
        'kueue.go.goroutines',
        'kueue.go.info',
        'kueue.cluster_queue.info',
        'kueue.cluster_queue.status',
        'kueue.local_queue.status',
        'kueue.controller.runtime.active_workers',
        'kueue.process.uptime.seconds',
        'kueue.workqueue.depth',
    ):
        aggregator.assert_metric(metric, at_least=1)

    for metric in ('kueue.cluster_queue.info', 'kueue.cluster_queue.status'):
        aggregator.assert_metric_has_tag(metric, 'kueue_cluster_queue:cluster-queue')

    aggregator.assert_service_check('kueue.openmetrics.health', ServiceCheck.OK, count=1)
    assert_service_checks(aggregator)
