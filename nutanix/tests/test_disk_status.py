# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import HOST_NAME, HOST_TAGS

pytestmark = [pytest.mark.unit]


def test_disks_endpoint_failure_still_emits_storage_metrics_without_tag(
    dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    mocker.patch(
        "datadog_checks.nutanix.infrastructure_monitor.InfrastructureMonitor._list_all_disks",
        side_effect=RuntimeError("boom"),
    )
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.host.storage_capacity", at_least=1, tags=HOST_TAGS, hostname=HOST_NAME)
    for metric in aggregator.metrics("nutanix.host.storage_capacity"):
        assert not any(t.startswith("ntnx_disk_status:") for t in metric.tags)


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
