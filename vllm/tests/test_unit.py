# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.vllm import vLLMCheck

from .common import METRICS_MOCK, get_fixture_path

pytestmark = pytest.mark.unit


def test_default_metric_limit_is_zero():
    # Kills the core/NumberReplacer mutant at check.py:10 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert vLLMCheck.DEFAULT_METRIC_LIMIT == 0


def test_check_vllm(dd_run_check, aggregator, datadog_agent, instance):
    check = vLLMCheck("vLLM", {}, [instance])
    check.check_id = "test:123"

    mock_responses = [
        MockResponse(file_path=get_fixture_path("vllm_metrics.txt")),
        MockResponse(file_path=get_fixture_path("vllm_version.json")),
    ]

    with mock.patch('requests.Session.get', side_effect=mock_responses):
        dd_run_check(check)

    for metric in METRICS_MOCK:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, "test:test")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_service_check("vllm.openmetrics.health", ServiceCheck.OK)

    version_metadata = _get_version_metadata("0.4.3")
    datadog_agent.assert_metadata("test:123", version_metadata)


def test_check_vllm_w_ray_prefix(dd_run_check, aggregator, datadog_agent, ray_instance):
    check = vLLMCheck("vLLM", {}, [ray_instance])
    check.check_id = "test:123"

    mock_responses = [
        MockResponse(file_path=get_fixture_path("ray_vllm_metrics.txt")),
        MockResponse(file_path=get_fixture_path("vllm_version.json")),
    ]

    with mock.patch('requests.Session.get', side_effect=mock_responses):
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


def test_submit_version_metadata_skipped_when_metadata_collection_disabled(datadog_agent, mock_http_response, instance):
    # Kills the core/RemoveDecorator mutant at check.py:23 (removing @AgentCheck.metadata_entrypoint would run
    # version submission even though metadata collection is disabled).
    datadog_agent._config['enable_metadata_collection'] = False
    mock_http_response(json_data={"version": "1.2.3"})
    check = vLLMCheck("vLLM", {}, [instance])
    check.check_id = "test:123"

    check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_submit_version_metadata_with_too_few_parts_is_ignored(datadog_agent, mock_http_response, instance):
    # Kills the core/ReplaceComparisonOperator_GtE_LtE and core/NumberReplacer(3->2) mutants at check.py:32
    # (`len(version_split) >= 3` mutated to `<= 3` or `>= 2`), which would index a non-existent third
    # version part for a 2-part version and either raise or submit bogus metadata.
    mock_http_response(json_data={"version": "1.2"})
    check = vLLMCheck("vLLM", {}, [instance])
    check.check_id = "test:123"

    check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_submit_version_metadata_with_extra_parts_uses_first_three(datadog_agent, mock_http_response, instance):
    # Kills the core/ReplaceComparisonOperator_GtE_Eq mutant at check.py:32 (`len(version_split) >= 3` mutated to
    # `== 3`), which would skip metadata submission for a version with more than 3 dot-separated parts.
    mock_http_response(json_data={"version": "1.2.3.4"})
    check = vLLMCheck("vLLM", {}, [instance])
    check.check_id = "test:123"

    check._submit_version_metadata()

    datadog_agent.assert_metadata(
        "test:123",
        {
            "version.scheme": "semver",
            "version.major": "1",
            "version.minor": "2",
            "version.patch": "3",
            "version.raw": "1.2.3",
        },
    )


def test_emits_critical_openemtrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, mock_http_response
):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = vLLMCheck("vllm", {}, [instance])
    with pytest.raises(Exception, match='requests.exceptions.HTTPError'):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("vllm.openmetrics.health", ServiceCheck.CRITICAL)
