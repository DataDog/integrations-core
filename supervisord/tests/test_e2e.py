# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.base import AgentCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    aggregator.assert_metric("supervisord.process.count", count=3)
    aggregator.assert_metric("supervisord.process.uptime", count=3)
    aggregator.assert_service_check("supervisord.process.status", count=3)
    aggregator.assert_service_check("supervisord.can_connect", status=AgentCheck.OK, count=1)

    aggregator.assert_all_metrics_covered()
