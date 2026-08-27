# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.nvidia_triton import NvidiaTritonCheck

from .common import METRICS_MOCK, get_fixture_path


def _text_response(file_path: str | Path) -> FakeHTTPResponse:
    content = Path(file_path).read_bytes()
    text = content.decode('utf-8')
    return FakeHTTPResponse(
        content=content,
        text=text,
        content_chunks=(content,),
        lines=text.splitlines(),
        headers={'Content-Type': 'text/plain'},
    )


def test_check_metrics_nvidia_triton(dd_run_check, aggregator, instance_metrics, fake_http):
    """
    Use static files for the metrics and version tests.
    """

    check = NvidiaTritonCheck('nvidia_triton', {}, [instance_metrics])
    fake_http.register_response(
        'GET',
        instance_metrics['openmetrics_endpoint'],
        _text_response(get_fixture_path('metrics/metrics')),
        match_options={'stream': True},
    )
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(name=metric)
        aggregator.assert_metric_has_tag(metric, 'test:test')

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.OK)
    fake_http.assert_all_responses_consumed()


def test_emits_critical_openemtrics_service_check_when_service_is_down(dd_run_check, aggregator, instance, fake_http):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'],
        FakeHTTPResponse(
            status_code=404,
            status_error=HTTPClientStatusError('404 Client Error'),
        ),
        match_options={'stream': True},
    )
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    with pytest.raises(Exception, match="HTTPClientStatusError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('nvidia_triton.openmetrics.health', ServiceCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()


def test_emits_critical_api_service_check_when_service_is_down(aggregator, instance, fake_http):
    """
    If we fail to reach the API endpoint the health service check should report as critical
    """
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    fake_http.register_response(
        'GET',
        f'{check.server_info_api}/v2/health/ready',
        FakeHTTPResponse(status_code=404),
    )
    check._check_server_health()

    aggregator.assert_service_check('nvidia_triton.health.status', ServiceCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()


def test_check_nvidia_triton_metadata(datadog_agent, instance, fake_http):
    check = NvidiaTritonCheck('nvidia_triton', {}, [instance])
    fake_http.register_response(
        'GET',
        f'{check.server_info_api}/v2',
        FakeHTTPResponse(json_result=json.loads(Path(get_fixture_path('info/v2')).read_text(encoding='utf-8'))),
    )

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
    fake_http.assert_all_responses_consumed()
