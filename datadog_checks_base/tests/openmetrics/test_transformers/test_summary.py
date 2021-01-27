# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ...utils import requires_py3
from ..utils import get_check

pytestmark = [
    requires_py3,
    pytest.mark.openmetrics,
    pytest.mark.openmetrics_transformers,
    pytest.mark.openmetrics_transformers_summary,
]


def assert_metric_counts(aggregator, payload):
    num_quantile_metrics = 0
    num_sum_metrics = 0
    num_count_metrics = 0

    lines = [line.strip() for line in payload.strip().splitlines()]
    metric_name = lines[0].split()[2]
    lines = lines[2:]

    for line in lines:
        if line.startswith('{}_sum'.format(metric_name)):
            num_sum_metrics += 1
        elif line.startswith('{}_count'.format(metric_name)):
            num_count_metrics += 1
        elif 'quantile="' in line:
            num_quantile_metrics += 1

    assert len(aggregator.metrics('test.{}.quantile'.format(metric_name))) == num_quantile_metrics
    assert len(aggregator.metrics('test.{}.sum'.format(metric_name))) == num_sum_metrics
    assert len(aggregator.metrics('test.{}.count'.format(metric_name))) == num_count_metrics


def test_default(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP http_request_duration_microseconds The HTTP request latencies in microseconds.
        # TYPE http_request_duration_microseconds summary
        http_request_duration_microseconds{handler="prometheus",quantile="0.5"} 1599.011
        http_request_duration_microseconds{handler="prometheus",quantile="0.9"} 1599.011
        http_request_duration_microseconds{handler="prometheus",quantile="0.99"} 1599.011
        http_request_duration_microseconds_sum{handler="prometheus"} 65093.229
        http_request_duration_microseconds_count{handler="prometheus"} 25
        """
    mock_http_response(payload)
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.http_request_duration_microseconds.quantile',
        1599.011,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:prometheus', 'quantile:0.5'],
    )
    aggregator.assert_metric(
        'test.http_request_duration_microseconds.quantile',
        1599.011,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:prometheus', 'quantile:0.9'],
    )
    aggregator.assert_metric(
        'test.http_request_duration_microseconds.quantile',
        1599.011,
        metric_type=aggregator.GAUGE,
        tags=['endpoint:test', 'handler:prometheus', 'quantile:0.99'],
    )
    aggregator.assert_metric(
        'test.http_request_duration_microseconds.sum',
        65093.229,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:prometheus'],
    )
    aggregator.assert_metric(
        'test.http_request_duration_microseconds.count',
        25,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:prometheus'],
    )

    aggregator.assert_all_metrics_covered()
    assert_metric_counts(aggregator, payload)


def test_no_quantiles(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP http_request_duration_microseconds The HTTP request latencies in microseconds.
        # TYPE http_request_duration_microseconds summary
        http_request_duration_microseconds_sum{handler="prometheus"} 65093.229
        http_request_duration_microseconds_count{handler="prometheus"} 25
        """
    mock_http_response(payload)
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.http_request_duration_microseconds.sum',
        65093.229,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:prometheus'],
    )
    aggregator.assert_metric(
        'test.http_request_duration_microseconds.count',
        25,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'handler:prometheus'],
    )

    aggregator.assert_all_metrics_covered()
