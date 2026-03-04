# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics

from .fixtures.e2e_metric_tags import E2E_METRIC_TAGS


@pytest.mark.e2e
def test_e2e_metrics(dd_agent_check):
    aggregator = dd_agent_check()

    cross_check_metrics = (
        'flow_runs.retry_gaps_duration',
        'task_runs.dependency_wait_duration',
        'flow_runs.queue_wait_duration',
        'work_queue.concurrency.in_use',
        'flow_runs.execution_duration',
        'task_runs.execution_duration',
    )
    all_metadata = get_metadata_metrics()
    metadata_metrics = {k: v for k, v in all_metadata.items() if not any(m in k for m in cross_check_metrics)}
    exclude = [k for k in all_metadata if any(m in k for m in cross_check_metrics)]
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_metric_type=False,
        check_symmetric_inclusion=True,
        exclude=exclude,
    )

    for metric_name, expected_tags in E2E_METRIC_TAGS.items():
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric_name, tag)
