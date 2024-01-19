# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics

from .common import MOCKED_METRICS, mock_http_responses


def test_check(dd_run_check, aggregator, mocker, check, instance):
    mocker.patch("requests.get", wraps=mock_http_responses)
    dd_run_check(check(instance))

    for expected_metric in MOCKED_METRICS:
        aggregator.assert_metric(f"tekton.{expected_metric}")

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check("tekton.openmetrics.health", status=AgentCheck.OK, count=1)
    assert len(aggregator.service_check_names) == 1


def test_invalid_url(dd_run_check, aggregator, check, instance, mocker):
    instance["openmetrics_endpoint"] = "http://unknowwn"

    mocker.patch("requests.get", wraps=mock_http_responses)
    with pytest.raises(Exception):
        dd_run_check(check(instance))

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check("tekton.openmetrics.health", status=AgentCheck.CRITICAL, count=1)
