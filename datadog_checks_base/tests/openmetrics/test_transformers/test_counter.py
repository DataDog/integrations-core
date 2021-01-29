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
    pytest.mark.openmetrics_transformers_counter,
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
