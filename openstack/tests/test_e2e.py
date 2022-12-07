# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import MOCK_CONFIG


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator):
    dd_agent_check(MOCK_CONFIG, rate=True)

    aggregator.assert_service_check("openstack.keystone.api.up", AgentCheck.CRITICAL, count=2)
    aggregator.assert_service_check("openstack.nova.api.up", AgentCheck.UNKNOWN, count=2)
    aggregator.assert_service_check("openstack.neutron.api.up", AgentCheck.UNKNOWN, count=2)
