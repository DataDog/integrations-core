# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nvidia_triton import NvidiaTritonCheck

from . common import METRICS_MOCK, get_fixture_path


def test_check_mock_nvidia_triton(dd_run_check, aggregator, instance, mock_http_response):
    """
    The instance is a deepcopy of the INSTANCE_MOCK in common
    """
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    mock_http_response(file_path=get_fixture_path('nvidia_triton_openmetrics.txt'))
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'pytest:test')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.OK)

def test_check_nvidia_triton_metadata(datadog_agent, instance, mock_http_response):

    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    mock_http_response(file_path=get_fixture_path('nvidia_triton_metadata.json'))

    check._submit_version_metadata()
    check.check_id = 'test:123'
    raw_version = "2.38.0"

    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }
    datadog_agent.assert_metadata('test:123', version_metadata)

def test_emits_critical_openemtrics_service_check_when_service_is_down(dd_run_check, aggregator, instance, mock_http_response):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance]) 
    dd_run_check(check)

    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.CRITICAL)


def test_emits_critical_api_service_check_when_service_is_down(aggregator, instance, mock_http_response):
    """
    If we fail to reach the API endpoint the health service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    check._check_server_health()

    aggregator.assert_service_check('nvidia_triton.health.status', ServiceCheck.CRITICAL)

def test_empty_instance(dd_run_check):
    with pytest.raises(
        Exception,
        match='InstanceConfig`:\nopenmetrics_endpoint\n  Field required',
    ):
        check = NvidiaTritonCheck('nvidia_triton', {}, [])
        dd_run_check(check)