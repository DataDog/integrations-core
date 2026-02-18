# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.prefect import PrefectCheck

from .fixtures.e2e_metric_tags import E2E_METRIC_TAGS


@pytest.fixture
def ready_check(dd_environment, dd_run_check: Callable, aggregator: AggregatorStub):
    instance = dd_environment['instances'][0]
    check = PrefectCheck("prefect", {}, [instance])

    dd_run_check(check)

    return check


@pytest.mark.e2e
def test_e2e_metrics_as_metadata(dd_agent_check):
    aggregator = dd_agent_check()

    cross_check_metrics = ('flow_runs.retry_gaps_duration', 'task_runs.dependency_wait_duration')
    metadata_metrics = {k: v for k, v in get_metadata_metrics().items() if not any(m in k for m in cross_check_metrics)}
    aggregator.assert_metrics_using_metadata(
        metadata_metrics,
        check_metric_type=False,
        check_symmetric_inclusion=True,
    )


@pytest.mark.e2e
def test_e2e_metric_tags(dd_agent_check):
    aggregator = dd_agent_check()

    for metric_name, expected_tags in E2E_METRIC_TAGS.items():
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric_name, tag)
