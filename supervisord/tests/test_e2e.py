# (C) Datadog, Inc. 2019-present
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


def test_e2e_discovery(dd_agent_check_discovery):
    # NOTE: For discovery to work, the supervisord container must use an image
    # whose name contains 'supervisord' (e.g. vimagick/supervisord).
    # The test environment uses datadog/docker-library which won't match.
    pytest.skip("Test environment uses 'datadog/docker-library'; discovery requires an image with 'supervisord' in its name")
    aggregator = dd_agent_check_discovery(check_rate=True)

    aggregator.assert_service_check("supervisord.can_connect", status=AgentCheck.OK)
