# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

from .common import COMMON_METRICS

pytestmark = pytest.mark.e2e

CONFIG = {
    'init_config': {},
    'instances': [{'diagnostic_url': "http://127.0.0.1:3000"}],
}


def test_teleport_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)
    aggregator.assert_service_check('teleport.health.up', status=TeleportCheck.OK, count=1)
    aggregator.assert_metric(f"teleport.{COMMON_METRICS[0]}")
