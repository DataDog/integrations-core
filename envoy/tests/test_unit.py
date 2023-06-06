# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.dev.testing import requires_py2, requires_py3
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.envoy.metrics import PROMETHEUS_METRICS_MAP

from .common import DEFAULT_INSTANCE, MOCKED_PROMETHEUS_METRICS, get_fixture_path

pytestmark = [pytest.mark.unit]


def test_unique_metrics():
    duplicated_metrics = set()

    for value in PROMETHEUS_METRICS_MAP.values():
        # We only have string with envoy so far
        assert isinstance(value, str)
        assert value not in duplicated_metrics, "metric `{}` already declared".format(value)
        duplicated_metrics.add(value)


@requires_py2
def test_check_with_py2(aggregator, dd_run_check, check, mock_http_response):
    with pytest.raises(ConfigurationError, match="This version of the integration is only available when using py3."):
        check(DEFAULT_INSTANCE)


@requires_py3
def test_check(aggregator, dd_run_check, check, mock_http_response):
    mock_http_response(file_path=get_fixture_path('openmetrics.txt'))

    c = check(DEFAULT_INSTANCE)

    dd_run_check(c)

    for metric in MOCKED_PROMETHEUS_METRICS:
        aggregator.assert_metric("envoy.{}".format(metric))

    aggregator.assert_service_check(
        "envoy.openmetrics.health", status=AgentCheck.OK, tags=['endpoint:http://localhost:8001/stats/prometheus']
    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_no_duplicate_metrics()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
