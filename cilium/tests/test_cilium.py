# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.cilium import CiliumCheck

from .common import (
    ADDL_AGENT_METRICS,
    AGENT_DEFAULT_METRICS,
    CILIUM_VERSION,
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


def test_version_metadata(datadog_agent, agent_instance, mock_agent_data, dd_run_check):
    check = CiliumCheck('cilium', {}, [agent_instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    major, minor, patch = CILIUM_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': CILIUM_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
