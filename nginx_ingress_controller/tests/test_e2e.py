# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


# Minimal E2E testing
@pytest.mark.e2e
def test_e2e(dd_agent_check, aggregator, instance):
    with pytest.raises(Exception):
        dd_agent_check(instance, rate=True)

    aggregator.assert_service_check(
        "nginx_ingress.prometheus.health",
        AgentCheck.CRITICAL,
        tags=['endpoint:{}'.format(instance['prometheus_url'])],
        count=2,
    )
