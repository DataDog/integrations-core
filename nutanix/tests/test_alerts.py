# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json
import os
from datetime import datetime
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


# Mock datetime to cover full alerts fixture window
MOCK_ALERT_DATETIME = datetime.fromisoformat("2026-01-04T21:09:00.000000Z")

# Datetime after all alerts in the fixture (latest lastUpdatedTime is 2026-04-14T20:42:25Z)
MOCK_ALERT_DATETIME_AFTER_ALL = datetime.fromisoformat("2026-05-01T00:00:00.000000Z")


def _fixture_alert(alert_type, **overrides):
    """Load the first fixture alert with the given alertType and apply overrides.

    Used to build synthetic unresolved alerts for tests targeting alertTypes
    that only appear as resolved in the fixture. Reconciliation now sources
    its truth from `_list_alerts_unresolved`, so tests inject through that.
    """
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'alerts.json')
    with open(fixture_path) as f:
        pages = json.load(f)
    for page in pages:
        for alert in page.get('data', []):
            if alert.get('alertType') == alert_type:
                copy = dict(alert)
                copy.update(overrides)
                return copy
    raise ValueError(f"No alert with alertType={alert_type} in fixture")


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_collection(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that alerts are collected and have basic structure on first run (unresolved only)."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]

    assert len(alerts) > 0, "Expected alerts to be collected"
    for alert in alerts:
        assert alert['event_type'] == 'nutanix'
        assert alert['source_type_name'] == 'nutanix'
        assert 'ntnx_type:alert' in alert['tags']
        assert any(t in alert['tags'] for t in ('ntnx_alert_status:open', 'ntnx_alert_status:acknowledged'))
        assert 'ntnx_alert_type' in str(alert['tags'])


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no alerts are collected when there are no new alerts since last collection."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    # Use a datetime after all alerts so the cursor is beyond all fixture data
    get_current_datetime.return_value = MOCK_ALERT_DATETIME_AFTER_ALL

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0, "Expected alerts to be collected on first run"

    aggregator.reset()

    # Second run: cursor is now after all alerts, so nothing new
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) == 0, "Expected no alerts when there are no new alerts since last collection"


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_filtered_by_resource_filters_exclude_cluster(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that alerts for excluded clusters are not collected."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {
            "resource": "cluster",
            "property": "extId",
            "type": "exclude",
            "patterns": ["^00064715-c043-5d8f-ee4b-176ec875554d$"],
        },
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    # No alerts should have the excluded cluster
    assert all("ntnx_cluster_name:datadog-nutanix-dev" not in e["tags"] for e in alerts)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_filtered_by_resource_filters_include_cluster(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that only alerts for included clusters are collected."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "cluster", "property": "extId", "patterns": ["^00064715-c043-5d8f-ee4b-176ec875554d$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0, "Expected some alerts to be collected"
    # All collected alerts should have the included cluster ID
    assert all("ntnx_cluster_name:datadog-nutanix-dev" in e["tags"] for e in alerts)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_filtered_by_activity_filter_severity(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that only alerts matching the severity filter are collected."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "severity", "patterns": ["^WARNING$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
    ]
    assert len(alerts) > 0, "Expected some WARNING alerts to be collected"
    assert all("ntnx_alert_severity:WARNING" in e["tags"] for e in alerts)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_filtered_by_inexistent_property_nothing_collected(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that filtering by an inexistent property collects no alerts."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "nonexistentField", "patterns": [".*"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) == 0


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_filtered_by_activity_filter_alertType(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that only alerts matching the alertType filter are collected.

    Uses property 'alertType' to match the Nutanix API field name.
    A200335 only exists as a resolved alert in the fixture; inject an
    unresolved synthetic copy so reconciliation surfaces it.
    """
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A200335$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    synthetic = _fixture_alert("A200335", isResolved=False, isAcknowledged=False)
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=[synthetic])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", [])
        and any(t in e.get("tags", []) for t in ("ntnx_alert_status:open", "ntnx_alert_status:acknowledged"))
    ]
    assert len(alerts) == 1
    assert "ntnx_alert_type:A200335" in alerts[0]["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_message_template_rendering(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that alert messages with template variables are rendered correctly."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A6227$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    synthetic = _fixture_alert("A6227", isResolved=False, isAcknowledged=False)
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=[synthetic])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", [])
        and any(t in e.get("tags", []) for t in ("ntnx_alert_status:open", "ntnx_alert_status:acknowledged"))
    ]
    assert len(alerts) > 0

    alert = alerts[0]
    msg_text = alert["msg_text"]

    assert "{alert_msg}" not in msg_text, "Template variable should be rendered"
    assert "Admin user password has expired." in msg_text, "Rendered message should contain actual value"


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_a1031_disk_space_complete_output(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test complete alert output for A1031 (disk space) with rendered message."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A1031$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:acknowledged" in e.get("tags", [])
    ]
    assert len(alerts) >= 1, "Expected at least one A1031 alert"

    alert = alerts[0]

    # Verify message rendering
    assert "Disk space usage for /var/log on Controller VM 10.0.0.108 has exceeded 75%" in alert["msg_text"]
    assert "{mount_path}" not in alert["msg_text"]
    assert "{entity}" not in alert["msg_text"]
    assert "{ip_address}" not in alert["msg_text"]
    assert "{threshold}" not in alert["msg_text"]

    # Verify title rendering
    assert "Disk space usage high for /var/log on Controller VM 10.0.0.108" in alert["msg_title"]

    # Verify alert structure
    assert alert["event_type"] == "nutanix"
    assert alert["alert_type"] == "warning"
    assert alert["source_type_name"] == "nutanix"

    # Verify tags
    assert "ntnx_type:alert" in alert["tags"]
    assert "ntnx_alert_type:A1031" in alert["tags"]
    assert "ntnx_alert_severity:WARNING" in alert["tags"]
    assert "ntnx_alert_classification:Storage" in alert["tags"]
    assert "ntnx_alert_impact:SYSTEM_INDICATOR" in alert["tags"]
    assert any("ntnx_cluster_name:" in tag for tag in alert["tags"])
    assert any("ntnx_node_name:" in tag for tag in alert["tags"])


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_a111050_default_password_complete_output(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test complete alert output for A111050 (default password) with rendered message."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A111050$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    # A111050 (c7dbae76) is resolved+acknowledged in the fixture; inject an
    # unresolved+acknowledged synthetic copy so reconciliation surfaces it.
    synthetic = _fixture_alert("A111050", isResolved=False, isAcknowledged=True)
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=[synthetic])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:acknowledged" in e.get("tags", [])
    ]
    assert len(alerts) >= 1, "Expected at least one A111050 alert"

    alert = alerts[0]

    # Verify message rendering
    assert "nutanix" in alert["msg_text"]
    assert "{users}" not in alert["msg_text"]
    assert "{pcvm_ip}" not in alert["msg_title"]
    assert "10.0.0.165" in alert["msg_title"]

    # Verify alert structure
    assert alert["event_type"] == "nutanix"
    assert alert["alert_type"] == "warning"  # acknowledged alerts use "warning" regardless of severity
    assert alert["source_type_name"] == "nutanix"

    # Verify tags
    assert "ntnx_type:alert" in alert["tags"]
    assert "ntnx_alert_type:A111050" in alert["tags"]
    assert "ntnx_alert_severity:CRITICAL" in alert["tags"]
    assert "ntnx_alert_classification:Cluster" in alert["tags"]
    assert "ntnx_alert_impact:CONFIGURATION" in alert["tags"]
    assert "ntnx_cluster_name:prism-central-deployment" in alert["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_a6227_password_expiry_complete_output(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test complete alert output for A6227 (password expiry) with rendered message."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A6227$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    # A6227 alerts in the fixture are resolved+acknowledged; inject an
    # unresolved+acknowledged synthetic copy.
    synthetic = _fixture_alert("A6227", isResolved=False, isAcknowledged=True)
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=[synthetic])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:acknowledged" in e.get("tags", [])
    ]
    assert len(alerts) >= 1, "Expected at least one A6227 alert"

    alert = alerts[0]

    # Verify message rendering
    expected_message = "Admin user password has expired. Please change the admin password."
    assert alert["msg_text"] == expected_message
    assert "{alert_msg}" not in alert["msg_text"]

    # Verify alert structure
    assert alert["event_type"] == "nutanix"
    assert alert["alert_type"] == "warning"  # acknowledged alerts use "warning" regardless of severity
    assert alert["source_type_name"] == "nutanix"
    assert alert["msg_title"] == "Alert: The PC admin user password is going to expire soon or has already expired."

    # Verify tags
    assert "ntnx_type:alert" in alert["tags"]
    assert "ntnx_alert_type:A6227" in alert["tags"]
    assert "ntnx_alert_severity:CRITICAL" in alert["tags"]
    assert "ntnx_alert_classification:Cluster" in alert["tags"]
    assert "ntnx_alert_impact:CONFIGURATION" in alert["tags"]
    assert "ntnx_cluster_name:prism-central-deployment" in alert["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_event_has_aggregation_key_and_status_tag(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that alert events include aggregation_key and ntnx_alert_status:open tag."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0

    for alert in alerts:
        assert "aggregation_key" in alert, "Alert event must have aggregation_key"
        assert alert["aggregation_key"].startswith("nutanix-alert-")
        assert any(t in alert["tags"] for t in ("ntnx_alert_status:open", "ntnx_alert_status:acknowledged"))


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_emit_resolution_event(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that _emit_resolution_event produces a success event with correct fields."""
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.reset()

    resolved_alert = {
        "extId": "test-alert-123",
        "title": "Test Alert Title",
        "message": "Test alert message",
        "severity": "WARNING",
        "alertType": "A1031",
        "clusterUUID": "00064715-c043-5d8f-ee4b-176ec875554d",
        "creationTime": "2026-03-04T00:46:29.532987Z",
        "lastUpdatedTime": "2026-03-04T00:49:39.034079Z",
        "isResolved": True,
        "resolvedTime": "2026-03-04T00:49:39.030653Z",
        "resolvedByUsername": "noueman",
        "isAutoResolved": False,
        "classifications": ["Storage"],
        "impactTypes": ["SYSTEM_INDICATOR"],
    }

    check.activity_monitor._emit_resolution_event(resolved_alert)

    events = aggregator.events
    assert len(events) == 1

    event = events[0]
    assert event["alert_type"] == "success"
    assert event["aggregation_key"] == "nutanix-alert-test-alert-123"
    assert event["msg_title"] == "Alert Resolved: Test Alert Title"
    assert "Resolved by noueman" in event["msg_text"]
    assert "ntnx_alert_status:resolved" in event["tags"]
    assert "ntnx_alert_auto_resolved:false" in event["tags"]
    assert "ntnx_type:alert" in event["tags"]
    assert "ntnx_alert_severity:WARNING" in event["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_emit_resolution_event_auto_resolved(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test resolution event for auto-resolved alerts."""
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.reset()

    resolved_alert = {
        "extId": "auto-resolved-456",
        "title": "CPU Usage High",
        "message": "CPU usage exceeded threshold",
        "severity": "CRITICAL",
        "alertType": "A9999",
        "creationTime": "2026-03-04T00:46:29.532987Z",
        "lastUpdatedTime": "2026-03-04T00:49:39.034079Z",
        "isResolved": True,
        "resolvedTime": "2026-03-04T01:00:00.000000Z",
        "isAutoResolved": True,
        "classifications": [],
        "impactTypes": [],
    }

    check.activity_monitor._emit_resolution_event(resolved_alert)

    event = aggregator.events[0]
    assert event["msg_text"] == "Auto-resolved"
    assert "ntnx_alert_auto_resolved:true" in event["tags"]
    assert event["aggregation_key"] == "nutanix-alert-auto-resolved-456"


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_with_ip_address_rendering(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that ip_address template variable is rendered correctly in alert messages."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A1031$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:acknowledged" in e.get("tags", [])
    ]
    assert len(alerts) >= 1, "Expected at least one A1031 alert with ip_address"

    alert = alerts[0]

    # Verify ip_address is rendered in message
    assert "10.0.0.108" in alert["msg_text"], "IP address should be rendered in message"
    assert "{ip_address}" not in alert["msg_text"], "Template variable should be replaced"

    # Verify ip_address is rendered in title
    assert "10.0.0.108" in alert["msg_title"], "IP address should be rendered in title"
    assert "{ip_address}" not in alert["msg_title"], "Template variable should be replaced"

    # Verify complete rendered message contains ip_address in proper context
    assert "Disk space usage for /var/log on Controller VM 10.0.0.108" in alert["msg_text"], (
        "Message should contain rendered ip_address in context"
    )


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_first_run_collects_only_unresolved(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """First check cycle should track only currently-unresolved alerts."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]

    # All emitted alerts should be unresolved (open or acknowledged)
    assert len(alerts) > 0
    for alert in alerts:
        assert any(t in alert["tags"] for t in ("ntnx_alert_status:open", "ntnx_alert_status:acknowledged"))

    # No resolution events on first run
    resolved = [e for e in aggregator.events if "ntnx_alert_status:resolved" in e.get("tags", [])]
    assert len(resolved) == 0

    # In-memory cache populated with one entry per unresolved alert
    assert len(check.activity_monitor._open_alerts) == len(alerts)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_resolution_detected_on_subsequent_run(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """When a previously-tracked alert disappears from the unresolved list, a resolution event is emitted."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])

    # First run: populate _open_alerts from real fixture
    dd_run_check(check)

    open_events = [e for e in aggregator.events if "ntnx_alert_status:open" in e.get("tags", [])]
    assert len(open_events) > 0

    target_ext_id = next(iter(check.activity_monitor._open_alerts))

    aggregator.reset()

    resolved_alert = {
        "$objectType": "monitoring.v4.serviceability.Alert",
        "extId": target_ext_id,
        "isResolved": True,
        "resolvedTime": "2026-03-04T01:10:00.000000Z",
        "resolvedByUsername": "admin",
        "isAutoResolved": False,
        "isAcknowledged": False,
        "title": "Resolved Test Alert",
        "alertType": "A1031",
        "severity": "WARNING",
        "creationTime": "2026-03-04T00:46:29.532987Z",
        "lastUpdatedTime": "2026-03-04T01:10:00.000000Z",
        "classifications": ["Storage"],
        "impactTypes": ["SYSTEM_INDICATOR"],
    }

    # Second run: target alert is no longer in the unresolved list (others remain).
    remaining = [a for a in check.activity_monitor._open_alerts.values() if a.get("extId") != target_ext_id]
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=remaining)
    # _get_alert returns the resolved metadata for the resolution event.
    mocker.patch.object(check.activity_monitor, '_get_alert', return_value=resolved_alert)

    dd_run_check(check)

    resolved_events = [e for e in aggregator.events if "ntnx_alert_status:resolved" in e.get("tags", [])]
    assert len(resolved_events) == 1

    event = resolved_events[0]
    assert event["alert_type"] == "success"
    assert event["aggregation_key"] == f"nutanix-alert-{target_ext_id}"
    assert "Resolved by admin" in event["msg_text"]

    # In-memory cache no longer contains the target
    assert target_ext_id not in check.activity_monitor._open_alerts


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_still_open_no_duplicate_event(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Two consecutive cycles with the same unresolved list emit no duplicate events."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])

    dd_run_check(check)
    aggregator.reset()

    # Second run with the same fixture data: reconciliation diff is empty.
    dd_run_check(check)

    all_alert_events = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(all_alert_events) == 0, "Should not emit any event when no alert state has changed"


# --- nutanix.alert.open metric emission ---


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_open_metric_emitted_per_tracked_alert(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """One :1 emission per tracked alert, partitioned across .open and .acknowledged by state."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tracked = list(check.activity_monitor._open_alerts.values())
    expected_open = sum(1 for a in tracked if not a.get("isAcknowledged"))
    expected_ack = sum(1 for a in tracked if a.get("isAcknowledged"))
    assert expected_open + expected_ack > 0

    open_ones = [m for m in aggregator.metrics("nutanix.alert.open") if m.value == 1]
    ack_ones = [m for m in aggregator.metrics("nutanix.alert.acknowledged") if m.value == 1]
    open_zeros = [m for m in aggregator.metrics("nutanix.alert.open") if m.value == 0]
    ack_zeros = [m for m in aggregator.metrics("nutanix.alert.acknowledged") if m.value == 0]

    assert len(open_ones) == expected_open
    assert len(ack_ones) == expected_ack
    # First cycle: no resolutions, no transitions, so no zeroes
    assert len(open_zeros) == 0
    assert len(ack_zeros) == 0

    for m in open_ones + ack_ones:
        assert any(t.startswith("ext_id:") for t in m.tags)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_open_metric_zero_on_resolution(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """nutanix.alert.open=0 is submitted exactly once when an open alert resolves."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    target_ext_id = next(iter(check.activity_monitor._open_alerts))

    aggregator.reset()

    resolved_alert = {
        "$objectType": "monitoring.v4.serviceability.Alert",
        "extId": target_ext_id,
        "isResolved": True,
        "resolvedTime": "2026-03-04T01:10:00.000000Z",
        "resolvedByUsername": "admin",
        "isAutoResolved": False,
        "isAcknowledged": False,
        "title": "Resolved Test Alert",
        "alertType": "A1031",
        "severity": "WARNING",
        "creationTime": "2026-03-04T00:46:29.532987Z",
        "lastUpdatedTime": "2026-03-04T01:10:00.000000Z",
        "classifications": ["Storage"],
        "impactTypes": ["SYSTEM_INDICATOR"],
    }

    # Pin target's prior state (open) so we know which metric receives the :0.
    cached = check.activity_monitor._open_alerts[target_ext_id]
    prior_state = "acknowledged" if cached.get("isAcknowledged") else "open"

    remaining = [a for a in check.activity_monitor._open_alerts.values() if a.get("extId") != target_ext_id]
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=remaining)
    mocker.patch.object(check.activity_monitor, '_get_alert', return_value=resolved_alert)

    dd_run_check(check)

    zero_metric_name = f"nutanix.alert.{prior_state}"
    zero_metrics = [m for m in aggregator.metrics(zero_metric_name) if m.value == 0]
    assert len(zero_metrics) == 1
    assert f"ext_id:{target_ext_id}" in zero_metrics[0].tags

    # nutanix.alert.resolved is emitted as a one-shot signal for this ext_id.
    resolved_metrics = [
        m for m in aggregator.metrics("nutanix.alert.resolved") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(resolved_metrics) == 1

    # No further :1 for the target on either open-state metric this cycle
    target_ones = [
        m
        for name in ("nutanix.alert.open", "nutanix.alert.acknowledged")
        for m in aggregator.metrics(name)
        if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(target_ones) == 0


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_open_metric_re_emitted_each_cycle(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Gauges keep being submitted on subsequent cycles for still-tracked alerts."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME_AFTER_ALL

    check = NutanixCheck('nutanix', {}, [instance])

    def total_ones():
        return sum(
            1
            for name in ("nutanix.alert.open", "nutanix.alert.acknowledged")
            for m in aggregator.metrics(name)
            if m.value == 1
        )

    dd_run_check(check)
    first_cycle_count = total_ones()
    assert first_cycle_count > 0

    aggregator.reset()
    dd_run_check(check)
    second_cycle_count = total_ones()
    assert second_cycle_count == first_cycle_count


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_state_transition_open_to_acknowledged(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """open->acknowledged: 0 to nutanix.alert.open and 1 to nutanix.alert.acknowledged."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    # Pick an alert currently tracked as open (not acknowledged)
    target_ext_id = next(
        ext_id for ext_id, a in check.activity_monitor._open_alerts.items() if not a.get("isAcknowledged")
    )

    aggregator.reset()

    # Same unresolved set, but the target is now acknowledged
    refreshed = []
    for ext_id, a in check.activity_monitor._open_alerts.items():
        if ext_id == target_ext_id:
            updated = dict(a)
            updated["isAcknowledged"] = True
            updated["lastUpdatedTime"] = "2026-04-15T00:00:00.000000Z"
            refreshed.append(updated)
        else:
            refreshed.append(a)

    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=refreshed)

    dd_run_check(check)

    # :0 emitted to nutanix.alert.open for this ext_id
    open_zeros = [
        m for m in aggregator.metrics("nutanix.alert.open") if m.value == 0 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(open_zeros) == 1

    # :1 emitted to nutanix.alert.acknowledged for this ext_id
    ack_ones = [
        m
        for m in aggregator.metrics("nutanix.alert.acknowledged")
        if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(ack_ones) >= 1

    # No :1 to nutanix.alert.open for this ext_id this cycle
    open_ones = [
        m for m in aggregator.metrics("nutanix.alert.open") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(open_ones) == 0
