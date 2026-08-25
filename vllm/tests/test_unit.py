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
from datadog_checks.vllm import vLLMCheck

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


def test_check_vllm(dd_run_check, aggregator, datadog_agent, instance, mock_http):
    check = vLLMCheck("vLLM", {}, [instance])
    check.check_id = "test:123"

    mock_responses = [
        _text_response(get_fixture_path("vllm_metrics.txt")),
        FakeHTTPResponse(
            json_result=json.loads(Path(get_fixture_path("vllm_version.json")).read_text(encoding='utf-8'))
        ),
    ]

    mock_http.get.side_effect = mock_responses
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("vllm.openmetrics.health", ServiceCheck.OK)

    version_metadata = _get_version_metadata("0.4.3")
    datadog_agent.assert_metadata("test:123", version_metadata)


def test_check_vllm_w_ray_prefix(dd_run_check, aggregator, datadog_agent, ray_instance, mock_http):
    check = vLLMCheck("vLLM", {}, [ray_instance])
    check.check_id = "test:123"

    mock_responses = [
        _text_response(get_fixture_path("ray_vllm_metrics.txt")),
        FakeHTTPResponse(
            json_result=json.loads(Path(get_fixture_path("vllm_version.json")).read_text(encoding='utf-8'))
        ),
    ]

    mock_http.get.side_effect = mock_responses
    dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("vllm.openmetrics.health", ServiceCheck.OK)

    version_metadata = _get_version_metadata("0.4.3")
    datadog_agent.assert_metadata("test:123", version_metadata)


def _get_version_metadata(raw_version):
    major, minor, patch = raw_version.split(".")
    return {
        "version.scheme": "semver",
        "version.major": major,
        "version.minor": minor,
        "version.patch": patch,
        "version.raw": raw_version,
    }


def test_emits_critical_openemtrics_service_check_when_service_is_down(dd_run_check, aggregator, instance, mock_http):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http.get.return_value = FakeHTTPResponse(
        status_code=404,
        status_error=HTTPClientStatusError('404 Client Error'),
    )
    check = vLLMCheck("vllm", {}, [instance])
    with pytest.raises(Exception, match='HTTPClientStatusError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("vllm.openmetrics.health", ServiceCheck.CRITICAL)
