# (C) Datadog, Inc.2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections.abc import Callable
from string import Template
from typing import Optional

import pytest

from datadog_checks.base.checks.openmetrics.v2.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper, decorators
from datadog_checks.base.stubs.aggregator import AggregatorStub

RESPONSE_TEMPLATE = """
# HELP http_client_request_size_total
# TYPE http_client_request_size_total counter
http_client_request_size_total{http_request_method="GET",$status_label="$status_code"} 0
# HELP http_client_request_started_count_total
# TYPE http_client_request_started_count_total counter
http_client_request_started_count_total{http_request_method="GET",$status_label="$status_code"} 5
# HELP http_client_routes_total
# TYPE http_client_routes_total counter
http_client_routes_total{} 5
"""


def get_check(status_label: str):
    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = "test"

        def create_scraper(self, config):
            scraper = OpenMetricsScraper(self, config)
            return decorators.WithHttpCodeClass(scraper, http_status_tag=status_label)

    return Check("test", {}, [{"metrics": [".*"], "openmetrics_endpoint": "test"}])


def response(status_label: str, status_code: str) -> str:
    template = Template(RESPONSE_TEMPLATE)

    return template.substitute(status_label=status_label, status_code=status_code)


@pytest.mark.parametrize(
    "status_label, status_code, expected_class",
    [
        ("http_response_status_code", "101", "1xx"),
        ("http_response_status_code", "200", "2xx"),
        ("http_response_status_code", "302", "3xx"),
        ("http_response_status_code", "404", "4xx"),
        ("http_response_status_code", "523", "5xx"),
        ("code", "201", "2xx"),
        ("code", "403", "4xx"),
        ("http_response_status_code", "abc", None),
        ("http_response_status_code", "99", None),
    ],
    ids=[
        "1xx",
        "2xx",
        "3xx",
        "4xx",
        "5xx",
        "Custom label 2xx",
        "Custom label 4xx",
        "Invalid status code (abc)",
        "Invalid status code (99)",
    ],
)
def test_http_status_class_scraper(
    status_label: str,
    status_code: str,
    expected_class: Optional[str],
    aggregator: AggregatorStub,
    mock_http_response: Callable,
    dd_run_check: Callable,
):
    mock_http_response(response(status_label, status_code))

    check = get_check(status_label=status_label)
    dd_run_check(check)

    expected_tag_count = 1 if expected_class else 0

    aggregator.assert_metric("test.http_client_request_size.count", count=1)
    aggregator.assert_metric_has_tag(
        "test.http_client_request_size.count", f"code_class:{expected_class}", count=expected_tag_count
    )

    aggregator.assert_metric("test.http_client_request_started_count.count", count=1)
    aggregator.assert_metric_has_tag(
        "test.http_client_request_started_count.count", f"code_class:{expected_class}", count=expected_tag_count
    )

    aggregator.assert_metric("test.http_client_routes.count", count=1)
    aggregator.assert_metric_has_tag("test.http_client_routes.count", f"code_class:{expected_class}", count=0)
