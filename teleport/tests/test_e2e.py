# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.teleport import TeleportCheck

from .common import COMMON_METRICS, INSTANCE, USE_TELEPORT_CADDY

pytestmark = [pytest.mark.e2e]


CONFIG = {
    "init_config": {},
    "instances": [INSTANCE],
}


@pytest.mark.skipif(not USE_TELEPORT_CADDY, reason="test_teleport_e2e requires the caddy mock environment")
def test_teleport_e2e(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("teleport.health.up", value=1, count=1, tags=["teleport_status:ok"])
    aggregator.assert_metric(f"teleport.{COMMON_METRICS[0]}")


# Discovery targets the real teleport-distroless container, not the caddy mock (see the
# ad_identifiers value in assets/configuration/spec.yaml), so these tests run against the
# non-caddy environment instead.
@pytest.mark.skipif(
    USE_TELEPORT_CADDY, reason="discovery targets the real teleport-distroless container, not the caddy mock"
)
def test_e2e_discovery(dd_agent_check_discovery):
    aggregator = dd_agent_check_discovery()
    aggregator.assert_metric("teleport.health.up", value=1, count=1, tags=["teleport_status:ok"])
    aggregator.assert_metric(f"teleport.{COMMON_METRICS[0]}")


@pytest.mark.skipif(
    USE_TELEPORT_CADDY, reason="discovery targets the real teleport-distroless container, not the caddy mock"
)
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, TeleportCheck, compose_service="teleport-service")
