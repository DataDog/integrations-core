# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Agent telemetry emitted when a check drops metrics after reaching ``max_returned_metrics``.

The generic ``openmetrics`` package is the only shipped OpenMetrics package that keeps the
positive ``2000`` base default in ``integrations-core``, so it is the dominant producer of this
signal. ``OpenMetricsCheck.__new__`` dispatches to OpenMetrics v2 for ``openmetrics_endpoint``
and to OpenMetrics v1 for ``prometheus_url``; both paths are covered here.
"""

import pytest

from datadog_checks.openmetrics import OpenMetricsCheck

REACHED_TELEMETRY = ('checks', 'max_returned_metrics_reached', 'counter')
DROPPED_TELEMETRY = ('checks', 'max_returned_metrics_dropped', 'counter')

V2_INSTANCE = {
    'openmetrics_endpoint': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1', 'counter2'],
}

V1_INSTANCE = {
    'prometheus_url': 'http://localhost:10249/metrics',
    'namespace': 'openmetrics',
    'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1_total'],
}

LIMIT_VERSIONS = [
    pytest.param(V2_INSTANCE, 'openmetrics_poll_mock', 5, id='v2'),
    pytest.param(V1_INSTANCE, 'prometheus_poll_mock', 2, id='v1'),
]


@pytest.mark.parametrize('instance, poll_mock_fixture, expected_dropped', LIMIT_VERSIONS)
def test_metric_limit_telemetry_emitted_when_limit_reached(
    dd_run_check, datadog_agent, request, instance, poll_mock_fixture, expected_dropped
):
    request.getfixturevalue(poll_mock_fixture)
    check = OpenMetricsCheck('openmetrics', {}, [dict(instance, max_returned_metrics=1)])

    dd_run_check(check)

    assert len(check.get_warnings()) == 1
    datadog_agent.assert_labeled_telemetry(*REACHED_TELEMETRY, 1, {'check_name': 'openmetrics'})
    datadog_agent.assert_labeled_telemetry(*DROPPED_TELEMETRY, expected_dropped, {'check_name': 'openmetrics'})
