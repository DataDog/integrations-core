# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from pathlib import Path

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.base.stubs.http import FakeHTTPResponse
from datadog_checks.base.utils.http_exceptions import HTTPClientStatusError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nvidia_nim import NvidiaNIMCheck

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


def test_check_nvidia_nim(dd_run_check, aggregator, datadog_agent, instance, fake_http):
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    check.check_id = "test:123"
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'],
        _text_response(get_fixture_path("nim_metrics.txt")),
        match_options={'stream': True},
    )
    fake_http.register_response(
        'GET',
        instance['openmetrics_endpoint'].replace('/metrics', '/v1/version'),
        FakeHTTPResponse(
            json_result=json.loads(Path(get_fixture_path("nim_version.json")).read_text(encoding='utf-8'))
        ),
    )
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("nvidia_nim.openmetrics.health", ServiceCheck.OK)

    raw_version = "1.0.0"
    major, minor, patch = raw_version.split(".")
    version_metadata = {
        "version.scheme": "semver",
        "version.major": major,
        "version.minor": minor,
        "version.patch": patch,
        "version.raw": raw_version,
    }
    datadog_agent.assert_metadata("test:123", version_metadata)
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
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    with pytest.raises(Exception, match="HTTPClientStatusError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("nvidia_nim.openmetrics.health", ServiceCheck.CRITICAL)
    fake_http.assert_all_responses_consumed()
