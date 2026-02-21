# (C) Datadog, Inc. 2025-present
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
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
        'ntnx_vm_name:PC-OptionName-1',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=expected_tags)


def test_vm_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
        'ntnx_vm_name:PC-OptionName-1',
        'prism_central:10.0.0.197',
    ]

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_external_tags_for_vm(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    datadog_agent.assert_external_tags(
        'PC-OptionName-1',
        {
            'nutanix': [
                'ntnx_type:vm',
                'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
                'ntnx_cluster_name:datadog-nutanix-dev',
                'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
                'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
                'ntnx_host_name:10-0-0-9-aws-us-east-1a',
                'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
                'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
                'ntnx_vm_name:PC-OptionName-1',
                'prism_central:10.0.0.197',
            ]
        },
    )
