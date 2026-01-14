# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.metrics import CLUSTER_STATS_METRICS_REQUIRED, HOST_STATS_METRICS_REQUIRED, VM_STATS_METRICS_REQUIRED

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]

CLUSTER_METRICS = [
    "nutanix.cluster.count",
    "nutanix.cluster.nbr_nodes",
    "nutanix.cluster.vm.count",
    "nutanix.cluster.vm.inefficient_count",
]

HOST_METRICS = [
    "nutanix.host.count",
]

VM_METRICS = [
    "nutanix.vm.count",
]


def test_health_check(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1)
    aggregator.assert_metric_has_tag_prefix("nutanix.health.up", tag_prefix="prism_central:")


def test_cluster_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id',
        'ntnx_cluster_name',
        'prism_central',
    ]

    for metric in CLUSTER_METRICS:
        aggregator.assert_metric(metric, at_least=1)
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric, tag_prefix=f"{tag}:")


def test_cluster_stats_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id',
        'ntnx_cluster_name',
        'prism_central',
    ]

    for metric in CLUSTER_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1)
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric, tag_prefix=f"{tag}:")


def test_host_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id',
        'ntnx_cluster_name',
        'ntnx_host_name',
        'ntnx_host_type',
        'ntnx_hypervisor_name',
        'ntnx_hypervisor_type',
        'ntnx_host_id',
        'prism_central',
    ]

    for metric in HOST_METRICS:
        aggregator.assert_metric(metric, at_least=1)
        aggregator.assert_metric_has_tag(metric, tag="ntnx_type:host")
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric, tag_prefix=f"{tag}:")


def test_host_stats_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id',
        'ntnx_cluster_name',
        'ntnx_host_name',
        'ntnx_host_type',
        'ntnx_hypervisor_name',
        'ntnx_hypervisor_type',
        'ntnx_host_id',
        'prism_central',
    ]

    for metric in HOST_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1)
        aggregator.assert_metric_has_tag(metric, tag="ntnx_type:host")
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric, tag_prefix=f"{tag}:")


def test_vm_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id',
        'ntnx_cluster_name',
        'ntnx_generation_uuid',
        'ntnx_host_id',
        'ntnx_host_name',
        'ntnx_owner_id',
        'ntnx_vm_id',
        'ntnx_vm_name',
        'prism_central',
    ]

    for metric in VM_METRICS:
        aggregator.assert_metric(metric, at_least=1)
        aggregator.assert_metric_has_tag(metric, tag="ntnx_type:vm")
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric, tag_prefix=f"{tag}:")


def test_vm_stats_metrics(dd_run_check, aggregator, aws_instance):
    check = NutanixCheck('nutanix', {}, [aws_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id',
        'ntnx_cluster_name',
        'ntnx_generation_uuid',
        'ntnx_host_id',
        'ntnx_host_name',
        'ntnx_owner_id',
        'ntnx_vm_id',
        'ntnx_vm_name',
        'prism_central',
    ]

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1)
        aggregator.assert_metric_has_tag(metric, tag="ntnx_type:vm")
        for tag in expected_tags:
            aggregator.assert_metric_has_tag_prefix(metric, tag_prefix=f"{tag}:")
