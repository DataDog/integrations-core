# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]

CLUSTER_ID = "00064715-c043-5d8f-ee4b-176ec875554d"
CLUSTER_NAME = "datadog-nutanix-dev"
HOST_ID = "d8787814-4fe8-4ba5-931f-e1ee31c294a6"
HOST_NAME = "10-0-0-103-aws-us-east-1a"
VM_ID = "63e222ec-87ff-491b-b7ba-9247752d44a3"

BASE_TAGS = ["nutanix", "prism_central:10.0.0.197"]


def test_default_collects_all(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    expected_tags = BASE_TAGS + ['ntnx_cluster_id:' + CLUSTER_ID, 'ntnx_cluster_name:' + CLUSTER_NAME]
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.host.count", at_least=1)
    aggregator.assert_metric("nutanix.vm.count", at_least=1)


def test_include_cluster_by_id(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "extId", "patterns": [f"^{CLUSTER_ID}$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    expected_tags = BASE_TAGS + ['ntnx_cluster_id:' + CLUSTER_ID, 'ntnx_cluster_name:' + CLUSTER_NAME]
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)


def test_include_host_by_name_regex(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "host", "property": "hostName", "patterns": ["10-0-0-103"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.assert_metric("nutanix.host.count", at_least=1)
    aggregator.assert_metric("nutanix.cluster.count", value=1)


def test_exclude_vm_by_id(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "extId", "type": "exclude", "patterns": [f"^{VM_ID}$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.assert_metric("nutanix.cluster.count", value=1)
    aggregator.assert_metric("nutanix.host.count", at_least=1)
    vm_counts = [m for m in aggregator.metrics("nutanix.vm.count") if m.value == 1]
    assert len(vm_counts) < 4


def test_exclude_cluster_by_name_regex(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "name", "type": "exclude", "patterns": ["^datadog-"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.assert_metric("nutanix.health.up", value=1)
    aggregator.assert_metric("nutanix.cluster.count", count=0)


def test_include_inexistent_cluster_id(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "extId", "patterns": ["^nonexistent-uuid$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.assert_metric("nutanix.health.up", value=1)
    aggregator.assert_metric("nutanix.cluster.count", count=0)


def test_multiple_include_patterns(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "extId", "patterns": [f"^{CLUSTER_ID}$"]},
        {"resource": "cluster", "property": "name", "patterns": ["^datadog"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    expected_tags = BASE_TAGS + ['ntnx_cluster_id:' + CLUSTER_ID, 'ntnx_cluster_name:' + CLUSTER_NAME]
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
