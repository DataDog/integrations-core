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


def test_check_nvidia_nim(dd_run_check, aggregator, datadog_agent, instance):
    check = NvidiaNIMCheck("nvidia_nim", {}, [instance])
    check.check_id = "test:123"
    with mock.patch(
        'requests.get',
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
