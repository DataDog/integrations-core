# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.errors import SkipInstanceError
from datadog_checks.base.stubs import datadog_agent
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.dynamo import DynamoCheck

from .common import (
    FRONTEND_HISTOGRAM_BUCKETS_MOCK,
    FRONTEND_METRICS_MOCK,
    WORKER_HISTOGRAM_BUCKETS_MOCK,
    WORKER_METRICS_MOCK,
    get_fixture_path,
)


@pytest.mark.parametrize(
    ('instance_fixture', 'fixture_file', 'metrics', 'histogram_buckets'),
    [
        pytest.param(
            'frontend_instance',
            'dynamo_frontend_metrics.txt',
            FRONTEND_METRICS_MOCK,
            FRONTEND_HISTOGRAM_BUCKETS_MOCK,
            id='frontend',
        ),
        pytest.param(
            'worker_instance',
            'dynamo_worker_metrics.txt',
            WORKER_METRICS_MOCK,
            WORKER_HISTOGRAM_BUCKETS_MOCK,
            id='worker',
        ),
    ],
)
def test_check_collects_mapped_metrics(
    dd_run_check, aggregator, request, instance_fixture, fixture_file, metrics, histogram_buckets
):
    check = DynamoCheck("dynamo", {}, [request.getfixturevalue(instance_fixture)])
    check.check_id = "test:123"

    mock_response = MockResponse(file_path=get_fixture_path(fixture_file))

    with mock.patch('requests.Session.get', return_value=mock_response):
        dd_run_check(check)

    for metric in metrics:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

    for metric in histogram_buckets:
        aggregator.assert_histogram_bucket(
            metric, None, None, None, monotonic=True, hostname=None, tags=None, at_least=1
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("dynamo.openmetrics.health", ServiceCheck.OK)


def test_emits_critical_openmetrics_service_check_when_service_is_down(
    dd_run_check, aggregator, frontend_instance, mock_http_response
):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = DynamoCheck("dynamo", {}, [frontend_instance])
    with pytest.raises(Exception, match='requests.exceptions.HTTPError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("dynamo.openmetrics.health", ServiceCheck.CRITICAL)


def test_check_skipped_when_gpu_monitoring_disabled(frontend_instance):
    with mock.patch.dict(datadog_agent._config, {'gpu.enabled': False}):
        with pytest.raises(SkipInstanceError):
            DynamoCheck("dynamo", {}, [frontend_instance])
