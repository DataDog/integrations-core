# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import COMMON_METRICS, INSTANCE, USE_TELEPORT_CADDY

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not USE_TELEPORT_CADDY, reason="Only run e2e tests on caddy environment"),
]


CONFIG = {
    "init_config": {},
    "instances": [INSTANCE],
}


def test_teleport_e2e(dd_agent_check):
    aggregator = dd_agent_check()
    aggregator.assert_metric("teleport.health.up", value=1, count=1, tags=["teleport_status:ok"])
    aggregator.assert_metric(f"teleport.{COMMON_METRICS[0]}")
