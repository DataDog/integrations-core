# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from unittest import mock

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nvidia_nim import NvidiaNIMCheck

from .common import METRICS_MOCK, get_fixture_path

pytestmark = pytest.mark.unit


def test_check_nvidia_nim(dd_run_check, aggregator, datadog_agent, instance):
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    check.check_id = "test:123"
    with mock.patch(
        'requests.Session.get',
        side_effect=[
            MockResponse(file_path=get_fixture_path("nim_metrics.txt")),
            MockResponse(file_path=get_fixture_path("nim_version.json")),
        ],
    ):
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


def test_emits_critical_openemtrics_service_check_when_service_is_down(
    dd_run_check, aggregator, instance, mock_http_response
):
    """
    If we fail to reach the openmetrics endpoint the openmetrics service check should report as critical
    """
    mock_http_response(status_code=404)
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("nvidia_nim.openmetrics.health", ServiceCheck.CRITICAL)


def test_default_metric_limit():
    # Kills the core/NumberReplacer mutant at check.py:10 (DEFAULT_METRIC_LIMIT 0 -> -1).
    assert NvidiaNIMCheck.DEFAULT_METRIC_LIMIT == 0


def test_version_metadata_skipped_when_metadata_collection_disabled(datadog_agent, instance):
    # Kills the core/RemoveDecorator mutant at check.py:20 (dropping @AgentCheck.metadata_entrypoint
    # would submit version metadata even though metadata collection is disabled).
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    check.check_id = "test:123"
    datadog_agent._config["enable_metadata_collection"] = False
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data={"release": "1.2.3"})):
        check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)


def test_version_metadata_uses_first_three_components(datadog_agent, instance):
    # Kills the core/ReplaceComparisonOperator_GtE_Eq and core/ReplaceComparisonOperator_GtE_LtE
    # mutants at check.py:29 (>= 3 -> == 3 / <= 3), plus the core/NumberReplacer mutants at
    # check.py:31 and check.py:32 (minor/patch reading the wrong version_split index).
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    check.check_id = "test:123"
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data={"release": "1.2.3.4"})):
        check._submit_version_metadata()

    version_metadata = {
        "version.scheme": "semver",
        "version.major": "1",
        "version.minor": "2",
        "version.patch": "3",
        "version.raw": "1.2.3",
    }
    datadog_agent.assert_metadata("test:123", version_metadata)


def test_version_metadata_skipped_for_short_version(datadog_agent, instance):
    # Kills the core/NumberReplacer mutant at check.py:29 (len(version_split) >= 3 -> >= 2), which
    # would index version_split[2] on a two-component version and raise instead of skipping.
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    check.check_id = "test:123"
    with mock.patch('requests.Session.get', return_value=MockResponse(json_data={"release": "1.2"})):
        check._submit_version_metadata()

    datadog_agent.assert_metadata_count(0)
