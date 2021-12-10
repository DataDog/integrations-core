# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.cilium import CiliumCheck

from ..common import (
    ADDL_AGENT_METRICS,
    AGENT_DEFAULT_METRICS,
    CILIUM_VERSION,
    OPERATOR_AWS_METRICS,
    OPERATOR_METRICS,
    requires_legacy_environment,
)

pytestmark = [requires_legacy_environment]


def test_agent_check(aggregator, agent_instance_legacy, mock_agent_data, dd_run_check):
    c = CiliumCheck('cilium', {}, [agent_instance_legacy])

    dd_run_check(c)
    for m in AGENT_DEFAULT_METRICS + ADDL_AGENT_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_operator_check(aggregator, operator_instance_legacy, mock_operator_data, dd_run_check):
    c = CiliumCheck('cilium', {}, [operator_instance_legacy])

    dd_run_check(c)
    for m in OPERATOR_METRICS + OPERATOR_AWS_METRICS:
        aggregator.assert_metric(m)
    aggregator.assert_all_metrics_covered()


def test_version_metadata(datadog_agent, agent_instance_legacy, mock_agent_data, dd_run_check):
    check = CiliumCheck('cilium', {}, [agent_instance_legacy])
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
