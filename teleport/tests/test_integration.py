# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

from .common import COMMON_METRICS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


def test_connect_ok(aggregator, instance, dd_run_check):
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check("teleport.health.up", status=TeleportCheck.OK, count=1)
    aggregator.assert_service_check("teleport.health.up", status=TeleportCheck.CRITICAL, count=0)


def test_check_collects_teleport_common_metrics(aggregator, instance, dd_run_check):
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(f"teleport.{COMMON_METRICS[0]}")
