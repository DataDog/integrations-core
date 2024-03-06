# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

pytestmark = [pytest.mark.unit]


def test_connect_exception(dd_run_check):
    instance = {}
    check = TeleportCheck("teleport", {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)


COMMON_METRICS = [
    "process.state",
    "certificate_mismatch.count",
    "rx.count",
    "server_interactive_sessions_total",
    "teleport.build_info",
    "teleport.cache_events.count",
    "teleport.cache_stale_events.count",
    "tx.count",
]


def test_common_teleport_metrics(dd_run_check, aggregator, instance, mock_http_response, metrics_path):
    mock_http_response(file_path=metrics_path)

    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in COMMON_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
