# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

from .common import BAD_HOSTNAME_INSTANCE, COMMON_METRICS

pytestmark = [pytest.mark.unit]


def test_connect_exception(dd_run_check):
    with pytest.raises(Exception):
        check = TeleportCheck("teleport", {}, [BAD_HOSTNAME_INSTANCE])
        dd_run_check(check)


def test_common_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in COMMON_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
        aggregator.assert_metric_has_tag(f"teleport.{metric}", "teleport_service:teleport")
