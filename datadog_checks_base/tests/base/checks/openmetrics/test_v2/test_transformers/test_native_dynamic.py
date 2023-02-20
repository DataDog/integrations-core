# (C) Datadog, Inc. 2021-present
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
        go_memstats_alloc_bytes 1.900688e+06
        # HELP go_memstats_alloc_bytes_total Total number of bytes allocated, even if freed.
        # TYPE go_memstats_alloc_bytes_total counter
        go_memstats_alloc_bytes_total 2.58684656e+08
        """
    )
    check = get_check({'metrics': [{'go_memstats_alloc_bytes': {'type': 'native_dynamic'}}]})
    dd_run_check(check)

    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes', 1900688, metric_type=aggregator.GAUGE, tags=['endpoint:test']
    )
    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes.count', 258684656, metric_type=aggregator.MONOTONIC_COUNT, tags=['endpoint:test']
    )

    aggregator.assert_all_metrics_covered()
