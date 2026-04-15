# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json
from datetime import datetime
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


# Mock datetime to cover full alerts fixture window
MOCK_ALERT_DATETIME = datetime.fromisoformat("2026-01-04T21:09:00.000000Z")

# Datetime after all alerts in the fixture (latest lastUpdatedTime is 2026-04-14T20:42:25Z)
MOCK_ALERT_DATETIME_AFTER_ALL = datetime.fromisoformat("2026-05-01T00:00:00.000000Z")


def _setup_subsequent_run(check, cursor="2026-01-04T21:09:00.000000Z"):
    """Configure the check's activity monitor to simulate a subsequent run (not first run)."""
    check.activity_monitor._is_first_alert_run = False
    check.activity_monitor._open_alert_ids = set()
    check.activity_monitor.last_alert_update_time = cursor


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
        assert 'ntnx_alert_status:open' in alert['tags']
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
    # Use subsequent-run mode so both resolved and unresolved alerts are processed
    _setup_subsequent_run(check)
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
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that only alerts matching the alertType filter are collected.

    Uses property 'alertType' to match the Nutanix API field name.
    """
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A200335$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    _setup_subsequent_run(check)
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
    ]
    assert len(alerts) == 1
    assert "ntnx_alert_type:A200335" in alerts[0]["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_message_template_rendering(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that alert messages with template variables are rendered correctly."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A6227$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    _setup_subsequent_run(check)
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
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
    _setup_subsequent_run(check)
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
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
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test complete alert output for A111050 (default password) with rendered message."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A111050$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
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
    assert alert["alert_type"] == "error"
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
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test complete alert output for A6227 (password expiry) with rendered message."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A6227$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    _setup_subsequent_run(check)
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
    ]
    assert len(alerts) >= 1, "Expected at least one A6227 alert"

    alert = alerts[0]

    # Verify message rendering
    expected_message = "Admin user password has expired. Please change the admin password."
    assert alert["msg_text"] == expected_message
    assert "{alert_msg}" not in alert["msg_text"]

    # Verify alert structure
    assert alert["event_type"] == "nutanix"
    assert alert["alert_type"] == "error"
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
        assert "ntnx_alert_status:open" in alert["tags"]


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
    _setup_subsequent_run(check)
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:open" in e.get("tags", [])
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
    """First run (no cache) should fetch only unresolved alerts and cache their IDs."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]

    # All emitted alerts should be open (unresolved)
    assert len(alerts) > 0
    for alert in alerts:
        assert "ntnx_alert_status:open" in alert["tags"]

    # No resolution events on first run
    resolved = [e for e in aggregator.events if "ntnx_alert_status:resolved" in e.get("tags", [])]
    assert len(resolved) == 0

    # Verify open alert IDs are persisted in cache
    cached = check.read_persistent_cache("open_alert_ids")
    assert cached, "open_alert_ids should be stored in persistent cache"
    open_ids = json.loads(cached)
    assert len(open_ids) == len(alerts)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_resolution_detected_on_subsequent_run(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that when a previously open alert becomes resolved, a resolution event is emitted."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])

    # First run: collect open alerts
    dd_run_check(check)

    open_alerts = [e for e in aggregator.events if "ntnx_alert_status:open" in e.get("tags", [])]
    assert len(open_alerts) > 0

    # Pick the first open alert's extId from cache
    cached_ids = json.loads(check.read_persistent_cache("open_alert_ids"))
    target_ext_id = cached_ids[0]

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

    # Patch _list_alerts_since to return just the resolved alert
    mocker.patch.object(
        check.activity_monitor,
        '_list_alerts_since',
        return_value=[resolved_alert],
    )

    # Second run: should detect resolution
    dd_run_check(check)

    resolved_events = [e for e in aggregator.events if "ntnx_alert_status:resolved" in e.get("tags", [])]
    assert len(resolved_events) == 1

    event = resolved_events[0]
    assert event["alert_type"] == "success"
    assert event["aggregation_key"] == f"nutanix-alert-{target_ext_id}"
    assert "Resolved by admin" in event["msg_text"]

    # Verify the ID was removed from cache
    updated_ids = json.loads(check.read_persistent_cache("open_alert_ids"))
    assert target_ext_id not in updated_ids


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_created_and_resolved_between_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Alert created and resolved between runs should emit both open and resolved events."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])

    # First run to initialize cache
    dd_run_check(check)
    aggregator.reset()

    new_resolved_alert = {
        "$objectType": "monitoring.v4.serviceability.Alert",
        "extId": "brand-new-already-resolved-789",
        "isResolved": True,
        "resolvedTime": "2026-03-04T01:15:00.000000Z",
        "resolvedByUsername": "system",
        "isAutoResolved": True,
        "isAcknowledged": False,
        "title": "Transient Alert",
        "message": "This alert was short-lived",
        "alertType": "A9999",
        "severity": "INFO",
        "creationTime": "2026-03-04T01:10:00.000000Z",
        "lastUpdatedTime": "2026-03-04T01:15:00.000000Z",
        "classifications": [],
        "impactTypes": [],
    }

    mocker.patch.object(
        check.activity_monitor,
        '_list_alerts_since',
        return_value=[new_resolved_alert],
    )

    dd_run_check(check)

    open_events = [e for e in aggregator.events if "ntnx_alert_status:open" in e.get("tags", [])]
    resolved_events = [e for e in aggregator.events if "ntnx_alert_status:resolved" in e.get("tags", [])]

    assert len(open_events) == 1, "Should emit open event for the newly seen alert"
    assert len(resolved_events) == 1, "Should emit resolution event since it's already resolved"
    assert open_events[0]["aggregation_key"] == "nutanix-alert-brand-new-already-resolved-789"
    assert resolved_events[0]["aggregation_key"] == "nutanix-alert-brand-new-already-resolved-789"
    assert resolved_events[0]["alert_type"] == "success"

    # Should NOT remain in open alert cache
    cached_ids = json.loads(check.read_persistent_cache("open_alert_ids"))
    assert "brand-new-already-resolved-789" not in cached_ids


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_still_open_no_duplicate_event(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """An already-tracked alert that's still open should not produce a duplicate event."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])

    # First run: collect open alerts
    dd_run_check(check)

    cached_ids = json.loads(check.read_persistent_cache("open_alert_ids"))
    target_ext_id = cached_ids[0]

    aggregator.reset()

    still_open_alert = {
        "$objectType": "monitoring.v4.serviceability.Alert",
        "extId": target_ext_id,
        "isResolved": False,
        "isAutoResolved": False,
        "isAcknowledged": False,
        "title": "Still Open Alert",
        "alertType": "A1031",
        "severity": "WARNING",
        "creationTime": "2026-03-04T00:46:29.532987Z",
        "lastUpdatedTime": "2026-03-04T01:20:00.000000Z",
        "classifications": [],
        "impactTypes": [],
    }

    mocker.patch.object(
        check.activity_monitor,
        '_list_alerts_since',
        return_value=[still_open_alert],
    )

    dd_run_check(check)

    all_alert_events = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(all_alert_events) == 0, "Should not emit any event for already-tracked still-open alert"
