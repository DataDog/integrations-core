# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from pathlib import Path
from typing import Any, Callable, Dict  # noqa: F401

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.quarkus import QuarkusCheck

EXPECTED_METRICS = [
    'quarkus.http_server.requests.seconds.count',
    'quarkus.http_server.requests.seconds.sum',
    'quarkus.http_server.requests.seconds.max',
]


def test_check(dd_run_check, aggregator, instance, mock_http_response):
    # Given
    mock_http_response(file_path=Path(__file__).parent.absolute() / "fixtures" / "quarkus_auto_metrics.txt")
    check = QuarkusCheck('quarkus', {}, [instance])
    # When
    dd_run_check(check)
    # Then
    for m in EXPECTED_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, mock_http_response):
    # Given
    mock_http_response(status_code=404)
    check = QuarkusCheck('quarkus', {}, [instance])
    # When
    with pytest.raises(Exception, match="requests.exceptions.HTTPError"):
        dd_run_check(check)
    # Then
    aggregator.assert_service_check('quarkus.openmetrics.health', QuarkusCheck.CRITICAL)
