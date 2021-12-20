# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.cilium import CiliumCheck

from .common import (
    ADDL_AGENT_METRICS,
    AGENT_DEFAULT_METRICS,
    OPERATOR_AWS_METRICS_1_8,
    OPERATOR_AWS_METRICS_PRE_1_8,
    OPERATOR_METRICS,
)


def test_agent_check(aggregator, agent_instance, mock_agent_data, dd_run_check):
    c = CiliumCheck('cilium', {}, [agent_instance])

    dd_run_check(c)
    for m in AGENT_DEFAULT_METRICS + ADDL_AGENT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_operator_check(aggregator, operator_instance, mock_operator_data, dd_run_check):
    c = CiliumCheck('cilium', {}, [operator_instance])

    dd_run_check(c)
    for m in OPERATOR_METRICS + OPERATOR_AWS_METRICS_PRE_1_8 + OPERATOR_AWS_METRICS_1_8:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()
