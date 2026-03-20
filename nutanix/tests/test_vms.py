# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import OFF_VM_NAME, OFF_VM_TAGS, PCVM_NAME, PCVM_TAGS
from tests.metrics import VM_STATS_METRICS_REQUIRED

pytestmark = [pytest.mark.unit]


def test_vm_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=PCVM_TAGS)


def test_vm_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=PCVM_TAGS)


@pytest.mark.parametrize("batch_vm_collection", [True, False])
def test_off_vms_skipped_by_default(dd_run_check, aggregator, mock_instance, mock_http_get, batch_vm_collection):
    """VMs with powerState OFF are skipped by default regardless of collection mode."""
    mock_instance["batch_vm_collection"] = batch_vm_collection
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) == 3
    vm_names = {tag.split(":")[1] for m in vm_metrics for tag in m.tags if tag.startswith("ntnx_vm_name:")}
    assert "test-vm-that-should-remain-off" not in vm_names


def test_vm_status_off(dd_run_check, aggregator, mock_instance, mock_http_get):
    """VM fixture has powerState=OFF which maps to status value 2."""
    mock_instance["batch_vm_collection"] = False
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "powerState", "patterns": ["^(ON|OFF)$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "nutanix.vm.status", value=2, tags=OFF_VM_TAGS + ['ntnx_power_state:OFF'], hostname=OFF_VM_NAME
    )


def test_external_tags_for_vm(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    datadog_agent.assert_external_tags(
        PCVM_NAME,
        {'nutanix': PCVM_TAGS},
    )
