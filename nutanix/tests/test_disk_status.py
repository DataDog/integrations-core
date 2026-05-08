# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import HOST_NAME, HOST_TAGS

pytestmark = [pytest.mark.unit]


def test_disks_endpoint_failure_falls_back_to_unknown(dd_run_check, aggregator, mock_instance, mock_http_get, mocker):
    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._list_all_disks",
        side_effect=RuntimeError("boom"),
    )
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.host.storage_capacity",
        at_least=1,
        tags=HOST_TAGS + ['ntnx_disk_status:unknown'],
        hostname=HOST_NAME,
    )


def test_degraded_disk_status_flows_to_storage_metrics(dd_run_check, aggregator, mock_instance, mock_http_get, mocker):
    host_id = "d8787814-4fe8-4ba5-931f-e1ee31c294a6"
    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._list_all_disks",
        return_value=[{"nodeExtId": host_id, "status": "DETACHABLE"}],
    )
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.host.storage_capacity",
        at_least=1,
        tags=HOST_TAGS + ['ntnx_disk_status:degraded'],
        hostname=HOST_NAME,
    )
