# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.vllm import vLLMCheck

from .common import METRICS_MOCK, get_fixture_path


def test_check_vllm(dd_run_check, aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('vllm_metrics.txt'))

    # Disable server info collection since we are mocking
    instance.update({'collect_server_info': False})
    check = vLLMCheck('vllm', {}, [instance])
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check('vllm.openmetrics.health', ServiceCheck.OK)


def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = vLLMCheck('vllm', {}, [{}])
        dd_run_check(check)


def test_emits_critical_openemtrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, mock_http_response
):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = vLLMCheck('vllm', {}, [instance])
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('vllm.openmetrics.health', ServiceCheck.CRITICAL)


def test_emits_critical_api_service_check_when_service_is_down(aggregator, instance, mock_http_response):
    """
    If we fail to reach the API endpoint the health service check should report as critical
    """
    mock_http_response(status_code=404)
    check = vLLMCheck('vllm', {}, [instance])
    check._check_server_health()

    aggregator.assert_service_check('vllm.health.status', ServiceCheck.CRITICAL)


def test_check_mock_vllm_metadata(datadog_agent, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('vllm_version.json'))
    check = vLLMCheck('vLLM', {}, [instance])
    check.check_id = 'test:123'
    check._submit_version_metadata()
    raw_version = '0.4.3'

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
