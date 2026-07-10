# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.supervisord import SupervisordCheck


@pytest.mark.e2e
def test_e2e(dd_agent_check, instance):
    aggregator = dd_agent_check(instance)

    aggregator.assert_metric("supervisord.process.count", count=3)
    aggregator.assert_metric("supervisord.process.uptime", count=3)
    aggregator.assert_service_check("supervisord.process.status", count=3)
    aggregator.assert_service_check("supervisord.can_connect", status=AgentCheck.OK, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery()

    aggregator.assert_metric("supervisord.process.count", count=3)
    aggregator.assert_metric("supervisord.process.uptime", count=3)
    aggregator.assert_service_check("supervisord.process.status", count=3)
    aggregator.assert_service_check("supervisord.can_connect", status=AgentCheck.OK, count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, SupervisordCheck)
