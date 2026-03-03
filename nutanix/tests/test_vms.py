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
        'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:d45a36e7-1c4c-40d6-ba6f-c2f52c211460',
        'ntnx_host_id:d8787814-4fe8-4ba5-931f-e1ee31c294a6',
        'ntnx_host_name:10-0-0-103-aws-us-east-1a',
        'ntnx_is_agent_vm:False',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:63e222ec-87ff-491b-b7ba-9247752d44a3',
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
        'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:d45a36e7-1c4c-40d6-ba6f-c2f52c211460',
        'ntnx_host_id:d8787814-4fe8-4ba5-931f-e1ee31c294a6',
        'ntnx_host_name:10-0-0-103-aws-us-east-1a',
        'ntnx_is_agent_vm:False',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:63e222ec-87ff-491b-b7ba-9247752d44a3',
        'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
        'nutanix',
        'prism_central:10.0.0.197',
    ]

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_vm_status_off(dd_run_check, aggregator, mock_instance, mock_http_get):
    """VM fixture has powerState=OFF which maps to status value 2."""
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "powerState", "patterns": ["^(ON|OFF)$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:002f833c-7d92-4818-a3ab-e3f45f02979d',
        'ntnx_is_agent_vm:False',
        'ntnx_owner_id:773ffab1-a60b-52e7-bdab-a62c75151cb1',
        'ntnx_power_state:OFF',
        'ntnx_vm_id:2e59dd98-3bf9-4369-838f-3a589ee1d6df',
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
                'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
                'ntnx_cluster_name:datadog-nutanix-dev',
                'ntnx_generation_uuid:d45a36e7-1c4c-40d6-ba6f-c2f52c211460',
                'ntnx_host_id:d8787814-4fe8-4ba5-931f-e1ee31c294a6',
                'ntnx_host_name:10-0-0-103-aws-us-east-1a',
                'ntnx_is_agent_vm:False',
                'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
                'ntnx_vm_id:63e222ec-87ff-491b-b7ba-9247752d44a3',
                'ntnx_vm_name:NTNX-10-0-0-165-PCVM-1767014640',
                'nutanix',
                'prism_central:10.0.0.197',
            ]
        },
    )
