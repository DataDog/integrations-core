from typing import Callable

import pytest

from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.prefect import PrefectCheck

pytestmark = [pytest.mark.usefixtures("dd_environment"), pytest.mark.integration]


@pytest.fixture
def ready_check(dd_environment, dd_run_check: Callable, aggregator: AggregatorStub):
    instance = dd_environment['instances'][0]
    check = PrefectCheck("prefect", {}, [instance])

    dd_run_check(check)
    return check


@pytest.mark.usefixtures("ready_check")
def test_all_metadata_metrics_found(aggregator: AggregatorStub):
    histogram_suffixes = ('.avg', '.max', '.median', '.95percentile')
    metadata_metrics = {k: v for k, v in get_metadata_metrics().items() if not k.endswith(histogram_suffixes)}
    aggregator.assert_metrics_using_metadata(
        metadata_metrics, check_submission_type=True, check_metric_type=False, check_symmetric_inclusion=True
    )


@pytest.mark.usefixtures("ready_check")
def test_events_collected(aggregator: AggregatorStub):
    flow_run_events = [e for e in aggregator.events if e.get('event_type', '').startswith('prefect.flow-run')]
    task_run_events = [e for e in aggregator.events if e.get('event_type', '').startswith('prefect.task-run')]

    assert len(flow_run_events) > 0, "Expected at least one prefect.flow-run event"
    assert len(task_run_events) > 0, "Expected at least one prefect.task-run event"
