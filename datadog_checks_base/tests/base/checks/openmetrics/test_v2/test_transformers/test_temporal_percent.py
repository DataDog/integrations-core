# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

from ..utils import get_check

pytestmark = [
    requires_py3,
]


def test_named(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
        # TYPE process_cpu_seconds_total counter
        process_cpu_seconds_total{foo="bar"} 5.2
        """
    )
    check = get_check(
        {
            'metrics': [
                {
                    'process_cpu_seconds': {
                        'name': 'process_cpu_usage',
                        'type': 'temporal_percent',
                        'scale': 'second',
                    }
                }
            ],
        }
    )
    dd_run_check(check)

    aggregator.assert_metric(
        'test.process_cpu_usage', 520, metric_type=aggregator.RATE, tags=['endpoint:test', 'foo:bar']
    )

    aggregator.assert_all_metrics_covered()


def test_integer(aggregator, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP process_cpu_seconds_total Total user and system CPU time spent in seconds.
        # TYPE process_cpu_seconds_total counter
        process_cpu_seconds_total{foo="bar"} 5.2
        """
    )
    check = get_check(
        {'metrics': [{'process_cpu_seconds': {'name': 'process_cpu_usage', 'type': 'temporal_percent', 'scale': 1}}]}
    )
    dd_run_check(check)

    aggregator.assert_metric(
        'test.process_cpu_usage', 520, metric_type=aggregator.RATE, tags=['endpoint:test', 'foo:bar']
    )

    aggregator.assert_all_metrics_covered()
