# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.kueue import KueueCheck

from .common import TEST_METRICS, get_fixture_path


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    mock_http_response(file_path=get_fixture_path('metrics.txt'))

    check = KueueCheck('kueue', {}, [instance])
    dd_run_check(check)

    for metric in TEST_METRICS:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='openmetrics_endpoint\\n  Field required',
    ):
        check = KueueCheck('kueue', {}, [{}])
        dd_run_check(check)
