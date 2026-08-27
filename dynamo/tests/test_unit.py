# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.dynamo import DynamoCheck

from .common import FRONTEND_METRICS_MOCK, WORKER_METRICS_MOCK, get_fixture_path


def test_check_dynamo_frontend(dd_run_check, aggregator, frontend_instance):
    check = DynamoCheck("dynamo", {}, [frontend_instance])
    check.check_id = "test:123"

    mock_response = MockResponse(file_path=get_fixture_path("dynamo_frontend_metrics.txt"))

    with mock.patch('requests.Session.get', return_value=mock_response):
        dd_run_check(check)

    for metric in FRONTEND_METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("dynamo.openmetrics.health", ServiceCheck.OK)


def test_check_dynamo_worker(dd_run_check, aggregator, worker_instance):
    check = DynamoCheck("dynamo", {}, [worker_instance])
    check.check_id = "test:123"

    mock_response = MockResponse(file_path=get_fixture_path("dynamo_worker_metrics.txt"))

    with mock.patch('requests.Session.get', return_value=mock_response):
        dd_run_check(check)

    for metric in WORKER_METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

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
