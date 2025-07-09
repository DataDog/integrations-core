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


def get_check(status_label: str, target_info: bool = False):
    class Check(OpenMetricsBaseCheckV2):
        __NAMESPACE__ = "test"

        def create_scraper(self, config):
            scraper = OpenMetricsScraper(self, config)
            return decorators.WithHttpCodeClass(scraper, http_status_tag=status_label)

    return Check("test", {}, [{"metrics": [".*"], "openmetrics_endpoint": "test", "target_info": target_info}])


def response(status_label: str, status_code: str, target_info: bool) -> str:
    template = Template(RESPONSE_TEMPLATE)

    parsed_response = template.substitute(status_label=status_label, status_code=status_code)
    if target_info:
        target_info_text = """

        # HELP target_info Target metadata
        # TYPE target_info gauge
        target_info{service_version="1.0.0"} 1
        """
        parsed_response += target_info_text
    return parsed_response


def parameterize_test_http_status_class_scraper():
    return [
        pytest.param("http_response_status_code", "101", "1xx", id="1xx"),
        pytest.param("http_response_status_code", "200", "2xx", id="2xx"),
        pytest.param("http_response_status_code", "302", "3xx", id="3xx"),
        pytest.param("http_response_status_code", "404", "4xx", id="4xx"),
        pytest.param("http_response_status_code", "523", "5xx", id="5xx"),
        pytest.param("code", "201", "2xx", id="Custom label 2xx"),
        pytest.param("code", "403", "4xx", id="Custom label 4xx"),
        pytest.param("http_response_status_code", "abc", None, id="Invalid status code (abc)"),
        pytest.param("http_response_status_code", "99", None, id="Invalid status code (99)"),
    ]


@pytest.mark.parametrize(
    "status_label, status_code, expected_class",
    parameterize_test_http_status_class_scraper(),
)
@pytest.mark.parametrize("target_info", [True, False], ids=["with_target_info", "without_target_info"])
def test_http_status_class_scraper(
    status_label: str,
    status_code: str,
    expected_class: Optional[str],
    aggregator: AggregatorStub,
    mock_http_response: Callable,
    dd_run_check: Callable,
    target_info: bool,
):
    mock_http_response(response(status_label, status_code, target_info))

    check = get_check(status_label=status_label, target_info=target_info)
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

    # Shared tags are respected using the inner state of the decorated scraper
    # The first time it runs there is no tag
    aggregator.assert_metric_has_tag("test.http_client_request_size.count", "info_tag:shared_tag_value", count=0)

    # After running a second time we collect the target_info tags
    dd_run_check(check)
    target_info_tag_count = 1 if target_info else 0
    aggregator.assert_metric_has_tag(
        "test.http_client_request_size.count", "service_version:1.0.0", count=target_info_tag_count
    )
