# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck

from . import common


@common.openstack_e2e_legacy
@pytest.mark.e2e
def test_check(dd_agent_check):
    aggregator = dd_agent_check()

    # assert default metrics
    for metric in common.DEFAULT_METRICS:
        aggregator.assert_metric(metric)
    aggregator.assert_all_metrics_covered()

    # assert service checks
    aggregator.assert_service_check('openstack.neutron.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.nova.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.keystone.api.up', AgentCheck.OK, count=1)
    aggregator.assert_service_check('openstack.nova.hypervisor.up', AgentCheck.OK, count=10)
    aggregator.assert_service_check('openstack.neutron.network.up', AgentCheck.OK, count=2)
