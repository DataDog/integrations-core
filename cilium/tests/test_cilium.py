# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.cilium import CiliumCheck

from .common import ADDL_AGENT_METRICS, AGENT_DEFAULT_METRICS, CILIUM_VERSION, OPERATOR_AWS_METRICS, OPERATOR_METRICS


def test_agent_check(aggregator, agent_instance, mock_agent_data):
    c = CiliumCheck('cilium', {}, [agent_instance])

    c.check(agent_instance)
    for m in AGENT_DEFAULT_METRICS + ADDL_AGENT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_operator_check(aggregator, operator_instance, mock_operator_data):
    c = CiliumCheck('cilium', {}, [operator_instance])

    c.check(operator_instance)
    for m in OPERATOR_METRICS + OPERATOR_AWS_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_version_metadata(datadog_agent, agent_instance, mock_agent_data):
    check = CiliumCheck('cilium', {}, [agent_instance])
    check.check_id = 'test:123'
    check.check(agent_instance)

    major, minor, patch = CILIUM_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': CILIUM_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
