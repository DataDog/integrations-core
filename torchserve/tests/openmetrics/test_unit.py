# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.utils import get_metadata_metrics

from ..conftest import mock_http_responses
from .metrics import METRICS

pytestmark = pytest.mark.unit


def test_check(dd_run_check, aggregator, check, mocked_openmetrics_instance, mocker):
    mocker.patch('requests.get', wraps=mock_http_responses())
    dd_run_check(check(mocked_openmetrics_instance))

    for name, expected_values in METRICS.items():
        aggregator.assert_metric(
            f"torchserve.openmetrics.{name}",
            value=expected_values.get("value"),
            tags=expected_values.get("tags"),
            count=expected_values.get("count", 1),
        )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_all()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())

    aggregator.assert_service_check(
        "torchserve.openmetrics.health",
        status=AgentCheck.OK,
    )
