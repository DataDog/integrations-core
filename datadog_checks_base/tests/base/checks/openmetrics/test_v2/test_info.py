# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .utils import get_check


def test_target_info_tags_propagation(aggregator, dd_run_check, mock_http_response):
    # Initialize the check
    check = get_check({'metrics': ['.+']})

    # Mock the HTTP response with target_info and another metric
    mock_http_response(
        """
        # HELP go_memstats_alloc_bytes Number of bytes allocated and still in use.
        # TYPE go_memstats_alloc_bytes gauge
        go_memstats_alloc_bytes{foo="bar"} 6.396288e+06
        # HELP target Target metadata
        # TYPE target info
        target_info{env="prod", region="europe"} 1.0
        """
    )

    # Run the check
    dd_run_check(check)

    # Assert that the tags from target_info are applied to the other metric
    aggregator.assert_metric(
        'test.go_memstats_alloc_bytes',
        value=6396288,
        tags=['endpoint:test', 'foo:bar', 'env:prod', 'region:europe'],
        metric_type=aggregator.GAUGE,
    )

    # Assert all metrics are covered
    aggregator.assert_all_metrics_covered()
