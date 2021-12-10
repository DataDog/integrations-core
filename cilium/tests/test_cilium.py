# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .common import (
    ADDL_AGENT_METRICS,
    AGENT_DEFAULT_METRICS,
    CILIUM_VERSION,
    OPERATOR_AWS_METRICS,
    OPERATOR_METRICS,
)

def test_agent_check(aggregator, agent_instance_use_openmetrics, mock_agent_data, dd_run_check, check):
    c = check(agent_instance_use_openmetrics(False))

    dd_run_check(c)
    for m in AGENT_DEFAULT_METRICS + ADDL_AGENT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_operator_check(aggregator, operator_instance_use_openmetrics, mock_operator_data, dd_run_check, check):
    c = check(operator_instance_use_openmetrics(False))

    dd_run_check(c)
    for m in OPERATOR_METRICS + OPERATOR_AWS_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
