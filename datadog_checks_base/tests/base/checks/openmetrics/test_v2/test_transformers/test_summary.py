# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

from ..utils import get_check

pytestmark = [
    requires_py3,
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


def test_quantiles_remapped_metric_name(aggregator, dd_run_check, mock_http_response):
    payload = """
        # HELP prometheus_target_interval_length_seconds Actual intervals between scrapes.
        # TYPE prometheus_target_interval_length_seconds summary
        prometheus_target_interval_length_seconds{interval="1s",quantile="0.01"} 0.9950473
        prometheus_target_interval_length_seconds{interval="1s",quantile="0.05"} 0.9970795
        prometheus_target_interval_length_seconds{interval="1s",quantile="0.5"} 0.9999885
        prometheus_target_interval_length_seconds{interval="1s",quantile="0.9"} 1.0020113
        prometheus_target_interval_length_seconds{interval="1s",quantile="0.99"} 1.0046735
        prometheus_target_interval_length_seconds_sum{interval="1s"} 26649.83516454906
        prometheus_target_interval_length_seconds_count{interval="1s"} 26032
        """
    mock_http_response(payload)
    check = get_check({'metrics': [{'prometheus_target_interval_length_seconds': 'target_interval_seconds'}]})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.target_interval_seconds.sum',
        26649.83516454906,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'interval:1s'],
    )
    aggregator.assert_metric(
        'test.target_interval_seconds.count',
        26032,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'interval:1s'],
    )

    aggregator.assert_metric(
        'test.target_interval_seconds.quantile',
        metric_type=aggregator.GAUGE,
        count=5,
    )

    aggregator.assert_all_metrics_covered()
