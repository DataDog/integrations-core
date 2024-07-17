# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

from ..utils import get_check

pytestmark = [
    requires_py3,
]


def test_basic(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
        # TYPE go_memstats_alloc_bytes_total counter
        go_memstats_alloc_bytes_total 9.339544592e+09
        # HELP go_memstats_frees_total Total number of frees.
        # TYPE go_memstats_frees_total counter
        go_memstats_frees_total 1.28219257e+08
        """
    )
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes.count', 9339544592, metric_type=aggregator.MONOTONIC_COUNT, tags=['endpoint:test']
    )
    aggregator.assert_metric(
        'test.go_memstats_frees.count', 128219257, metric_type=aggregator.MONOTONIC_COUNT, tags=['endpoint:test']
    )

    aggregator.assert_all_metrics_covered()


def test_basic_incorrect_suffix(aggregator, dd_run_check, mock_http_response):
    """
    We won't collect counter metrics unless they end in '_total'.

    We commonly see metrics that end in '_count' or ones that have no meaningful suffix at all.
    Here we make sure that by default these won't be collected.
    """

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes_count Total number of bytes allocated, even if freed.
        # TYPE go_memstats_alloc_bytes_count counter
        go_memstats_alloc_bytes_total 9.339544592e+09
        # HELP go_memstats_frees Total number of frees.
        # TYPE go_memstats_frees counter
        go_memstats_frees_total 1.28219257e+08
        """
    )
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    assert not aggregator.metrics('test.go_memstats_alloc_bytes.count')
    assert not aggregator.metrics('test.go_memstats_frees.count')
    aggregator.assert_all_metrics_covered()


def test_untyped_correct_suffix(aggregator, dd_run_check, mock_http_response):
    """
    We can force a metric that is 'untyped' in the raw payload to a counter as long as it ends in '_total'.
    """

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
        # TYPE go_memstats_alloc_bytes_total untyped
        go_memstats_alloc_bytes_total 9.339544592e+09
        """
    )
    check = get_check(
        {'metrics': [{'go_memstats_alloc_bytes_total': {'name': 'go_memstats_alloc_bytes', 'type': 'counter'}}]}
    )
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes.count', 9339544592, metric_type=aggregator.MONOTONIC_COUNT, tags=['endpoint:test']
    )
    aggregator.assert_all_metrics_covered()


def test_untyped_incorrect_suffix(aggregator, dd_run_check, mock_http_response):
    """
    Forcing an untyped metric as a counter won't work without it ending in '_total'.
    """

    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes_count Total number of bytes allocated, even if freed.
        # TYPE go_memstats_alloc_bytes_count counter
        go_memstats_alloc_bytes_total 9.339544592e+09
        # HELP go_memstats_frees Total number of frees.
        # TYPE go_memstats_frees counter
        go_memstats_frees_total 1.28219257e+08
        """
    )
    check = get_check(
        {
            'metrics': [
                {
                    'go_memstats_alloc_bytes': {'name': 'go_memstats_alloc_bytes', 'type': 'counter'},
                    'go_memstats_frees': {'name': 'go_memstats_frees', 'type': 'counter'},
                }
            ]
        }
    )
    dd_run_check(check)

    assert not aggregator.metrics('test.go_memstats_alloc_bytes.count')
    assert not aggregator.metrics('test.go_memstats_frees.count')
    aggregator.assert_all_metrics_covered()


def test_tags(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
        # TYPE go_memstats_alloc_bytes_total counter
        go_memstats_alloc_bytes_total{foo="bar"} 9.339544592e+09
        # HELP go_memstats_frees_total Total number of frees.
        # TYPE go_memstats_frees_total counter
        go_memstats_frees_total{bar="foo"} 1.28219257e+08
        """
    )
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes.count',
        9339544592,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'foo:bar'],
    )
    aggregator.assert_metric(
        'test.go_memstats_frees.count',
        128219257,
        metric_type=aggregator.MONOTONIC_COUNT,
        tags=['endpoint:test', 'bar:foo'],
    )

    aggregator.assert_all_metrics_covered()
