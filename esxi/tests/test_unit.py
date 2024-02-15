# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

from datadog_checks.esxi import EsxiCheck


def test_emits_critical_service_check_when_service_is_down(dd_run_check, aggregator, instance, caplog):
    check = EsxiCheck('esxi', {}, [instance])
    caplog.set_level(logging.WARNING)
    dd_run_check(check)

    aggregator.assert_metric('esxi.host.can_connect', 0, tags=["esxi_url:localhost"])
    assert "Cannot connect to ESXi host" in caplog.text
