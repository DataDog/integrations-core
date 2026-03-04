# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.metrics import VM_STATS_METRICS_REQUIRED

pytestmark = [pytest.mark.unit]


def test_vm_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_host_name:10-0-0-103-aws-us-east-1a',
        'ntnx_is_agent_vm:False',
        'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
        'nutanix',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=expected_tags)


def test_vm_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_host_name:10-0-0-103-aws-us-east-1a',
        'ntnx_is_agent_vm:False',
        'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
        'nutanix',
        'prism_central:10.0.0.197',
    ]

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_batch_vm_collection_skips_off_vms(dd_run_check, aggregator, mock_instance, mock_http_get):
    """Batch mode skips VMs with powerState OFF by default."""
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

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_is_agent_vm:False',
        'ntnx_power_state:OFF',
        'ntnx_vm_name:test-vm-that-should-remain-off',
        'nutanix',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric(
        "nutanix.vm.status", value=2, tags=expected_tags, hostname="test-vm-that-should-remain-off"
    )


def test_external_tags_for_vm(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    datadog_agent.assert_external_tags(
        'NTNX-10-0-0-165-PCVM-1767014640',
        {
            'nutanix': [
                'ntnx_type:vm',
                'ntnx_cluster_name:datadog-nutanix-dev',
                'ntnx_host_name:10-0-0-103-aws-us-east-1a',
                'ntnx_is_agent_vm:False',
                'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
                'nutanix',
                'prism_central:10.0.0.197',
            ]
        },
    )
