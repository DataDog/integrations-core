# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.metrics import CLUSTER_STATS_METRICS_REQUIRED, HOST_STATS_METRICS_REQUIRED, VM_STATS_METRICS_REQUIRED

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_health_check(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1)


def test_cluster_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'prism_central:https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com',
    ]

    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.nbr_nodes", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.count", value=2, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.inefficient_count", value=0, tags=expected_tags)


def test_cluster_stats_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'prism_central:https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com',
    ]

    for metric in CLUSTER_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_host_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_host_type:HYPER_CONVERGED',
        'ntnx_hypervisor_name:AHV 10.0.1.4',
        'ntnx_hypervisor_type:AHV',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'prism_central:https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com',
    ]

    aggregator.assert_metric("nutanix.host.count", value=1, tags=expected_tags)


def test_host_stats_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadoghq.com-Default-Org-dkhrzg',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_host_type:HYPER_CONVERGED',
        'ntnx_hypervisor_name:AHV 10.0.1.4',
        'ntnx_hypervisor_type:AHV',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'prism_central:https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com',
    ]

    for metric in HOST_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_vm_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
        'ntnx_vm_name:PC-OptionName-1',
        'prism_central:https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com',
    ]

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=expected_tags)


def test_vm_stats_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
        'ntnx_vm_name:PC-OptionName-1',
        'prism_central:https://prism-central-public-nlb-4685b8c07b0c12a2.elb.us-east-1.amazonaws.com',
    ]

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)
