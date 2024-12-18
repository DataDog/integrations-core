# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ..utils import get_check


@pytest.mark.parametrize(
    'metric_type',
    [
        'counter',
        'gauge',
    ],
)
def test_untyped_counter(aggregator, dd_run_check, mock_http_response, metric_type):
    """
    The Agent's OpenMetrics parser uses the # TYPE line to determine the type of a metric. However, when it encounters
    an untyped metric, the Agent won't be able to derive the metric type, and the metric will be skipped. We can,
    however, force the Agent to collect it as a specific type. In this scenario, the Agent will ignore the metadata
    lines # HELP and # TYPE and will instead only look at the metric sample name.
    Below are some of the scenarios we might encounter:

    1. The metricset and metric sample does not end in '_total' and is untyped.
    2. The metricset and metric sample does end in '_total' and is untyped.
    3. The metricset does not end in '_total' and metric sample end in '_total' and is untyped.
    4. The metricset and metric samples don't match
    5. The metricset and metric samples are a non counter/gauge type

    The test will show how these can be configured to be collected as gauge or counters. The metric sample just
    has to match what the agent is looking for. The agent will then collect the metric as a we config
    provided type. Only testing for counter and gauge here because these are the only 2 types I see we can accurately
    collect with overrides.
    """

    mock_http_response(
        """
        # HELP foo The metricset and metric sample does not end in '_total' and is untyped.
        # TYPE foo untyped
        foo 0
        # HELP bar_total The metricset and metric sample does end in '_total' and is untyped.
        # TYPE bar_total untyped
        bar_total 1
        # HELP baz The metricset  does not end in '_total' and metric sample end in '_total' and is untyped.
        # TYPE baz untyped
        baz_total 2
        # HELP qux The metricset and metric samples don't match
        # TYPE qux untyped
        fiz 3
        # HELP bux The metricset and metric samples are a non counter type
        # TYPE bux histogram
        bux 4
        """
    )
    check = get_check(
        {
            'metrics': [
                {
                    'foo': {'name': 'foo', 'type': metric_type},
                    'bar_total': {'name': 'bar', 'type': metric_type},
                    'baz_total': {'name': 'baz', 'type': metric_type},
                    'fiz': {'name': 'fiz', 'type': metric_type},
                    'bux': {'name': 'bux', 'type': metric_type},
                }
            ]
        }
    )
    dd_run_check(check)

    metrics = ["test.foo", "test.bar", "test.baz", "test.fiz", "test.bux"]

    for metric in metrics:
        aggregator.assert_metric(
            '{}.count'.format(metric) if metric_type == 'counter' else metric,
            metrics.index(metric),
            metric_type=aggregator.MONOTONIC_COUNT if metric_type == 'counter' else aggregator.GAUGE,
            tags=['endpoint:test'],
        )

    aggregator.assert_all_metrics_covered()
