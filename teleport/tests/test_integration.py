# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
from typing import Any, Callable, Dict  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
import pytest
from datadog_checks.teleport import TeleportCheck

log = logging.getLogger(__file__)

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

def test_connect_exception(aggregator, dd_run_check, caplog):
    instance = {
        'diagnostic_url': 'http://127.0.0.1:3000',
    }
    check = TeleportCheck('teleport', {}, instance)
    dd_run_check(check)
    aggregator.assert_service_check('teleport.health.up', status=AgentCheck.CRITICAL)