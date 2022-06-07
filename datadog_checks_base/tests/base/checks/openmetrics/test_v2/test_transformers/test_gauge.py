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
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes 6.396288e+06
        # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
        # TYPE go_memstats_gc_sys_bytes gauge
        go_memstats_gc_sys_bytes 901120
        """
    )
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test']
    )
    aggregator.assert_metric(
        'test.go_memstats_gc_sys_bytes', 901120, metric_type=aggregator.GAUGE, tags=['endpoint:test']
    )

    aggregator.assert_all_metrics_covered()


def test_tags(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
        # HELP go_memstats_gc_sys_bytes Number of bytes used for garbage collection system metadata.
        # TYPE go_memstats_gc_sys_bytes gauge
        go_memstats_gc_sys_bytes{bar="foo"} 901120
        """
    )
    check = get_check({'metrics': ['.+']})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 6396288, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'foo:bar']
    )
    aggregator.assert_metric(
        'test.go_memstats_gc_sys_bytes', 901120, metric_type=aggregator.GAUGE, tags=['endpoint:test', 'bar:foo']
    )

    aggregator.assert_all_metrics_covered()
