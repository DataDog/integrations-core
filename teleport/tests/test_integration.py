# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.teleport import TeleportCheck


pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

def test_connect_exception(aggregator, dd_run_check):
    instance = {
        "diagnostic_url": "http://127.0.0.1:3000"
    }
    check = TeleportCheck('teleport', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('teleport.health.up', status=AgentCheck.CRITICAL)

def test_connect_ok(aggregator, dd_run_check):
    instance = {
        "diagnostic_url": "http://127.0.0.1:3000"
    }
    check = TeleportCheck('teleport', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('teleport.health.up', status=AgentCheck.OK)