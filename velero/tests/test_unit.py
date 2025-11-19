# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.velero import VeleroCheck

from .common import OPTIONAL_METRICS, TEST_METRICS, get_fixture_path


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('velero_payload.txt'))

    check = VeleroCheck('velero', {}, [instance])
    dd_run_check(check)

    for metric, metric_type in (TEST_METRICS | OPTIONAL_METRICS).items():
        aggregator.assert_metric(metric, metric_type=aggregator.METRIC_ENUM_MAP[metric_type])
        aggregator.assert_metric_has_tag(metric, 'test:tag')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = VeleroCheck('velero', {}, [{}])
        dd_run_check(check)


def test_incorrect_openmetrics_endpoint(dd_run_check):
    endpoint = 'velero:2112/metrics'
    with pytest.raises(
        Exception,
        match='openmetrics_endpoint: {} is incorrectly configured'.format(endpoint),
    ):
        check = VeleroCheck('velero', {}, [{'openmetrics_endpoint': endpoint}])
        dd_run_check(check)
