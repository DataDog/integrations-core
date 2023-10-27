# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.nvidia_triton import NvidiaTritonCheck

from .common import METRICS_MOCK, get_fixture_path


def test_check_metrics_nvidia_triton(dd_run_check, aggregator, instance_metrics, mock_http_response):
    """
    Use static files for the metrics and version tests.
    """

    check = NvidiaTritonCheck('nvidia_triton', {}, [instance_metrics])
    mock_http_response(file_path=get_fixture_path('metrics/metrics'))
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(name=metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.OK)


def test_emits_critical_openemtrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, mock_http_response
):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.CRITICAL)


def test_emits_critical_api_service_check_when_service_is_down(aggregator, instance, mock_http_response):
    """
    If we fail to reach the API endpoint the health service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check._check_server_health()

    aggregator.assert_service_check('nvidia_triton.health.status', ServiceCheck.CRITICAL)


def test_check_nvidia_triton_metadata(datadog_agent, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('info/v2'))
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])

    check.check_id = 'test:123'
    check._submit_version_metadata()
    raw_version = '2.38.0'

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
        'version.scheme': 'semver',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)
