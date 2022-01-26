# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck

from .common import AGENT_V2_METRICS, require_ci, requires_new_environment, skip_on_ci

pytestmark = [pytest.mark.e2e]


@skip_on_ci
@requires_new_environment
def test_check_ok(dd_agent_check):
    aggregator = dd_agent_check(rate=True)
    aggregator.assert_service_check("cilium.openmetrics.health", status=AgentCheck.OK)
    for metric in AGENT_V2_METRICS:
        aggregator.assert_metric(metric)


@require_ci
def test_check_not_ok(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_service_check("cilium.openmetrics.health", status=AgentCheck.CRITICAL)
