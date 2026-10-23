# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.teleport import TeleportCheck

from .common import BPF_METRICS

pytestmark = [pytest.mark.unit]


def test_bpf_teleport_metrics(dd_run_check, aggregator, instance, mock_metrics):
    check = TeleportCheck("teleport", {}, [instance])
    dd_run_check(check)

    for metric in BPF_METRICS:
        aggregator.assert_metric(f"teleport.{metric}")
