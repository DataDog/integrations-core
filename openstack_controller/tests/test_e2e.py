# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os

import pytest

from datadog_checks.base import AgentCheck

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
]


def test_connect_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.cinder.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)
    aggregator.assert_service_check('openstack.glance.api.up', status=AgentCheck.OK)
