# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck

from . import common


@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()
    for metric in common.DEFAULT_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('openstack.neutron.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.nova.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.keystone.api.up', AgentCheck.OK, count=1)
