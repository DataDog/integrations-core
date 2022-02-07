# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(aggregator, instance, dd_agent_check):
    # Prevent the integration from failing before even running the check
    instance['ticket_location'] = '.'

    dd_agent_check(instance, rate=True)

    aggregator.assert_service_check('mapr.can_connect', AgentCheck.OK, count=2)
