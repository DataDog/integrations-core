# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.nutanix import NutanixCheck
from datadog_checks.nutanix.resource_filters import parse_resource_filters, should_collect_activity

pytestmark = [pytest.mark.unit]

CLUSTER_ID = "0006411c-0286-bc71-9f02-191e334d457b"
CLUSTER_NAME = "datadog-nutanix-dev"
HOST_ID = "71877eae-8fc1-4aae-8d20-70196dfb2f8d"
HOST_NAME = "10-0-0-9-aws-us-east-1a"
VM_ID = "f3272103-ea1e-4a90-8318-899636993ed6"

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
        {"resource": "cluster", "property": "id", "patterns": [f"^{CLUSTER_ID}$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    expected_tags = BASE_TAGS + ['ntnx_cluster_id:' + CLUSTER_ID, 'ntnx_cluster_name:' + CLUSTER_NAME]
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)


def test_include_host_by_name_regex(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "host", "property": "name", "patterns": ["10-0-0-9"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.assert_metric("nutanix.host.count", at_least=1)
    aggregator.assert_metric("nutanix.cluster.count", value=1)


def test_exclude_vm_by_id(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "vm", "property": "id", "type": "exclude", "patterns": [f"^{VM_ID}$"]},
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
        {"resource": "cluster", "property": "id", "patterns": ["^nonexistent-uuid$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.assert_metric("nutanix.health.up", value=1)
    aggregator.assert_metric("nutanix.cluster.count", count=0)


def test_multiple_include_patterns(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "id", "patterns": [f"^{CLUSTER_ID}$"]},
        {"resource": "cluster", "property": "name", "patterns": ["^datadog"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    expected_tags = BASE_TAGS + ['ntnx_cluster_id:' + CLUSTER_ID, 'ntnx_cluster_name:' + CLUSTER_NAME]
    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)


def test_parse_resource_filters_activity_types():
    """Test that activity filter types (event, task, alert) are parsed correctly."""
    filters = parse_resource_filters(
        [
            {"resource": "event", "property": "type", "patterns": ["^PasswordAudit$"]},
            {"resource": "task", "property": "status", "patterns": ["^SUCCEEDED$"]},
            {"resource": "alert", "property": "alertType", "patterns": ["^A130172$"]},
        ]
    )
    assert len(filters) == 3
    assert filters[0]["resource"] == "event" and filters[0]["property"] == "type"
    assert filters[1]["resource"] == "task" and filters[1]["property"] == "status"
    assert filters[2]["resource"] == "alert" and filters[2]["property"] == "alerttype"


def test_should_collect_activity_event_type():
    """Test event filtering by type."""
    filters = parse_resource_filters(
        [
            {"resource": "event", "property": "type", "patterns": ["^PasswordAudit$"]},
        ]
    )
    assert should_collect_activity("event", {"eventType": "PasswordAudit"}, filters) is True
    assert should_collect_activity("event", {"eventType": "LicenseAudit"}, filters) is False


def test_should_collect_activity_alert_severity_exclude():
    """Test alert filtering by severity with exclude."""
    filters = parse_resource_filters(
        [
            {"resource": "alert", "property": "severity", "type": "exclude", "patterns": ["^INFO$"]},
        ]
    )
    assert should_collect_activity("alert", {"severity": "WARNING"}, filters) is True
    assert should_collect_activity("alert", {"severity": "INFO"}, filters) is False


def test_should_collect_activity_alert_uses_alertType_not_type():
    """Test that alert type filtering uses API field alertType, not type.

    Nutanix API uses 'alertType' for the alert type code. This test would fail if we
    mistakenly used item.get('type') instead of item.get('alertType').
    """
    filters = parse_resource_filters(
        [
            {"resource": "alert", "property": "alertType", "patterns": ["^A130172$"]},
        ]
    )
    # API-shaped item: has alertType, no top-level 'type' (type is for sourceEntity)
    item_with_alert_type = {"alertType": "A130172", "severity": "INFO"}
    assert should_collect_activity("alert", item_with_alert_type, filters) is True

    # Item that would wrongly pass if we used 'type': has type="vm" (sourceEntity) but alertType is different
    item_type_vm_alert_a1031 = {"alertType": "A1031", "type": "vm", "severity": "WARNING"}
    filters_a130172 = parse_resource_filters(
        [{"resource": "alert", "property": "alertType", "patterns": ["^A130172$"]}]
    )
    assert should_collect_activity("alert", item_type_vm_alert_a1031, filters_a130172) is False


def test_should_collect_activity_event_uses_eventType_not_type():
    """Test that event filtering uses API field eventType, not type.

    Nutanix API uses 'eventType' for the event type. Would fail if we used item.get('type').
    """
    filters = parse_resource_filters(
        [
            {"resource": "event", "property": "type", "patterns": ["^PasswordAudit$"]},
        ]
    )
    # API uses eventType; there is no top-level 'type' on events
    item = {"eventType": "PasswordAudit", "classifications": ["UserAction"]}
    assert should_collect_activity("event", item, filters) is True
    assert should_collect_activity("event", {"eventType": "LicenseAudit"}, filters) is False


def test_should_collect_activity_task_uses_status():
    """Test that task filtering uses API field status."""
    filters = parse_resource_filters(
        [
            {"resource": "task", "property": "status", "patterns": ["^SUCCEEDED$"]},
        ]
    )
    assert should_collect_activity("task", {"status": "SUCCEEDED"}, filters) is True
    assert should_collect_activity("task", {"status": "FAILED"}, filters) is False


def test_should_collect_activity_inexistent_property_nothing_collected():
    """Test that filtering by an inexistent property collects nothing.

    When property does not match any known API field, _get_activity_value returns ''
    so the filter never matches, and nothing is collected.
    """
    filters = parse_resource_filters(
        [
            {"resource": "alert", "property": "nonexistentField", "patterns": [".*"]},
        ]
    )
    # Even with pattern ".*" that would match anything, inexistent property yields ''
    # which doesn't match in include logic - so item is not collected
    alert_with_data = {"alertType": "A130172", "severity": "INFO"}
    assert should_collect_activity("alert", alert_with_data, filters) is False
