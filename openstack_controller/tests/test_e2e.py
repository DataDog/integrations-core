# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from tests.common import not_openstack_e2e_legacy


@not_openstack_e2e_legacy
@pytest.mark.e2e
def test_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.cinder.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)
