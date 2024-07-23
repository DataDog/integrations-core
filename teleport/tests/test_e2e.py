# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from .common import COMMON_METRICS, INSTANCE

pytestmark = pytest.mark.e2e

CONFIG = {
    'init_config': {},
    'instances': [INSTANCE],
}


def test_teleport_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)
    aggregator.assert_metric("teleport.health.up", value=1, count=1, tags=["teleport_status:ok"])
    aggregator.assert_metric(f"teleport.{COMMON_METRICS[0]}")
