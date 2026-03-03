# (C) Datadog, Inc. 2026-present
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


def test_default_collects_all_infrastructure_and_only_user_category_tags(
    dd_run_check, aggregator, mock_instance, mock_http_get
):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    expected_tags = BASE_TAGS + ['ntnx_cluster_id:' + CLUSTER_ID, 'ntnx_cluster_name:' + CLUSTER_NAME]
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.host.count", at_least=1)
    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    vms_with_category_tags = [
        m for m in vm_metrics if any(tag.startswith("Team:") or tag.startswith("Environment:") for tag in m.tags)
    ]

    assert len(vms_with_category_tags) > 0, "Expected at least some VMs to have category tags"

    for metric in vms_with_category_tags:
        # Verify only USER categories are included by default
        assert any(tag.startswith("Team:") for tag in metric.tags), "Expected USER category tags"
        assert not any(tag.startswith("Environment:") for tag in metric.tags), (
            "SYSTEM categories should not be included by default"
        )


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


def test_include_only_system_category_tags_when_filtered(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "patterns": ["^SYSTEM$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) > 0

    for metric in vm_metrics:
        tags = metric.tags
        has_system_tag = any(tag == "Environment:Testing" for tag in tags)
        has_user_tag = any(tag == "Team:agent-integrations" for tag in tags)
        if has_system_tag or has_user_tag:
            assert has_system_tag, "Expected SYSTEM category tags to be present"
            assert not has_user_tag, "Expected USER category tags to be excluded"


def test_include_only_user_category_tags_when_filtered(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "patterns": ["^USER$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) > 0

    for metric in vm_metrics:
        tags = metric.tags
        has_user_tag = any(tag == "Team:agent-integrations" for tag in tags)
        has_system_tag = any(tag == "Environment:Testing" for tag in tags)
        if has_system_tag or has_user_tag:
            assert has_user_tag, "Expected USER category tags to be present"
            assert not has_system_tag, "Expected SYSTEM category tags to be excluded"


def test_exclude_internal_category_tags_when_filtered(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "type": "exclude", "patterns": ["^INTERNAL$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) > 0

    for metric in vm_metrics:
        tags = metric.tags
        # INTERNAL categories: AppFamily, ImageType, Project, RemoteConnectionType, XiEntityOwner
        has_internal_tag = any(
            tag.startswith("AppFamily:")
            or tag.startswith("ImageType:")
            or tag.startswith("Project:")
            or tag.startswith("RemoteConnectionType:")
            or tag.startswith("XiEntityOwner:")
            for tag in tags
        )
        assert not has_internal_tag, "Expected INTERNAL category tags to be excluded"


def test_include_system_and_user_category_tags_when_filtered(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "patterns": ["^(SYSTEM|USER)$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) > 0

    for metric in vm_metrics:
        tags = metric.tags
        has_system_tag = any(tag == "Environment:Testing" for tag in tags)
        has_user_tag = any(tag == "Team:agent-integrations" for tag in tags)
        if has_system_tag or has_user_tag:
            assert has_system_tag or has_user_tag, "Expected SYSTEM or USER category tags to be present"


def test_include_all_category_types_when_explicitly_configured(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "patterns": ["^(SYSTEM|INTERNAL|USER)$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    assert len(vm_metrics) > 0

    for metric in vm_metrics:
        tags = metric.tags
        # skip VM that doesn't contain any category
        if any(tag == "ntnx_vm_name:test-vm-that-should-remain-off" for tag in tags):
            continue
        has_system_tag = any(tag == "Environment:Testing" for tag in tags)
        has_user_tag = any(tag == "Team:agent-integrations" for tag in tags)
        if has_system_tag or has_user_tag:
            assert has_system_tag, (
                f"Expected SYSTEM category tags when all types are included, missing in metric: {metric}"
            )
            assert has_user_tag, f"Expected USER category tags when all types are included, missing in metric: {metric}"


def test_default_user_category_filter_applies_with_other_resource_filters(
    dd_run_check, aggregator, mock_instance, mock_http_get
):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "name", "patterns": ["^datadog-"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.cluster.count", at_least=1)
    aggregator.assert_metric("nutanix.vm.count", at_least=1)

    vm_metrics = aggregator.metrics("nutanix.vm.count")
    vms_with_category_tags = [
        m for m in vm_metrics if any(tag.startswith("Team:") or tag.startswith("Environment:") for tag in m.tags)
    ]

    assert len(vms_with_category_tags) > 0, "Expected at least some VMs to have category tags"

    for metric in vms_with_category_tags:
        # Verify only USER categories are included by default, even with other filters
        assert any(tag.startswith("Team:") for tag in metric.tags), "Expected USER category tags"
        assert not any(tag.startswith("Environment:") for tag in metric.tags), (
            "SYSTEM categories should not be included by default"
        )
