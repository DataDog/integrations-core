# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datetime import datetime
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


# Mock datetime to cover full alerts fixture window
MOCK_ALERT_DATETIME = datetime.fromisoformat("2026-01-04T21:09:00.000000Z")

EXPECTED_ALERTS = [
    {
        'alert_type': 'warning',
        'event_type': 'nutanix',
        'msg_text': 'Disk space usage for {mount_path} on {entity} {ip_address} has exceeded {threshold}%. {ref_msg}',
        'msg_title': 'Alert: Disk space usage high for {mount_path} on {entity} {ip_address}',
        'source_type_name': 'nutanix',
        'tags': [
            'nutanix',
            'prism_central:10.0.0.197',
            'ntnx_alert_type:A1031',
            'ntnx_alert_severity:WARNING',
            'ntnx_alert_classification:Storage',
            'ntnx_alert_impact:SYSTEM_INDICATOR',
            'ntnx_node_name:10-0-0-103-aws-us-east-1a',
            'ntnx_type:alert',
        ],
        'timestamp': 1767560958,
    },
    {
        'alert_type': 'warning',
        'event_type': 'nutanix',
        'msg_text': 'Disk space usage for {mount_path} on {entity} {ip_address} has exceeded {threshold}%. {ref_msg}',
        'msg_title': 'Alert: Disk space usage high for {mount_path} on {entity} {ip_address}',
        'source_type_name': 'nutanix',
        'tags': [
            'nutanix',
            'prism_central:10.0.0.197',
            'ntnx_alert_type:A1031',
            'ntnx_alert_severity:WARNING',
            'ntnx_alert_classification:Storage',
            'ntnx_alert_impact:SYSTEM_INDICATOR',
            'ntnx_node_name:10-0-0-103-aws-us-east-1a',
            'ntnx_type:alert',
        ],
        'timestamp': 1767691459,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Recovery Point for VM {vm_name} failed to capture associated policies '
        'and categories because {reason}.',
        'msg_title': 'Alert: Degraded VM Recovery Point.',
        'source_type_name': 'nutanix',
        'tags': [
            'nutanix',
            'prism_central:10.0.0.197',
            'ntnx_alert_type:A130172',
            'ntnx_alert_severity:INFO',
            'ntnx_alert_classification:DR',
            'ntnx_alert_impact:SYSTEM_INDICATOR',
            'ntnx_vm_name:ubuntu-vm',
            'ntnx_type:alert',
        ],
        'timestamp': 1768302387,
    },
]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_collection(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that alerts are collected and have basic structure."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]

    assert len(alerts) > 0, "Expected alerts to be collected"
    # Check that alerts have the expected structure
    for alert in alerts:
        assert alert['event_type'] == 'nutanix'
        assert alert['source_type_name'] == 'nutanix'
        assert 'ntnx_type:alert' in alert['tags']
        assert 'ntnx_alert_type' in str(alert['tags'])


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no alerts are collected when there are no new alerts since last collection."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0, "Expected alerts to be collected on first run"

    aggregator.reset()

    # second check run, no new alerts to be collected
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

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0, "Expected some WARNING alerts to be collected"
    # All collected alerts should have WARNING severity
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
        {"resource": "alert", "property": "alertType", "patterns": ["^A130172$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) == 1
    assert "ntnx_alert_type:A130172" in alerts[0]["tags"]


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
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0

    alert = alerts[0]
    msg_text = alert["msg_text"]

    assert "{alert_msg}" not in msg_text, "Template variable should be rendered"
    assert "Admin user password will expire soon" in msg_text, "Rendered message should contain actual value"


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

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
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
def test_alert_a130172_vm_recovery_complete_output(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test complete alert output for A130172 (VM recovery) with rendered message."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": ["^A130172$"]},
    ]

    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) == 1, "Expected exactly one A130172 alert"

    alert = alerts[0]

    # Verify message rendering
    expected_message = (
        "Recovery Point for VM ubuntu-vm failed to capture associated policies "
        "and categories because Management plane is not available to get the configuration."
    )
    assert alert["msg_text"] == expected_message
    assert "{vm_name}" not in alert["msg_text"]
    assert "{reason}" not in alert["msg_text"]

    # Verify alert structure
    assert alert["event_type"] == "nutanix"
    assert alert["alert_type"] == "info"
    assert alert["source_type_name"] == "nutanix"
    assert alert["msg_title"] == "Alert: Degraded VM Recovery Point."

    # Verify tags
    assert "ntnx_type:alert" in alert["tags"]
    assert "ntnx_alert_type:A130172" in alert["tags"]
    assert "ntnx_alert_severity:INFO" in alert["tags"]
    assert "ntnx_alert_classification:DR" in alert["tags"]
    assert "ntnx_alert_impact:SYSTEM_INDICATOR" in alert["tags"]
    assert "ntnx_vm_name:ubuntu-vm" in alert["tags"]


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
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) >= 1, "Expected at least one A6227 alert"

    alert = alerts[0]

    # Verify message rendering
    expected_message = "Admin user password will expire soon. Please change the admin password."
    assert alert["msg_text"] == expected_message
    assert "{alert_msg}" not in alert["msg_text"]

    # Verify alert structure
    assert alert["event_type"] == "nutanix"
    assert alert["alert_type"] == "warning"
    assert alert["source_type_name"] == "nutanix"
    assert alert["msg_title"] == "Alert: The PC admin user password is going to expire soon or has already expired."

    # Verify tags
    assert "ntnx_type:alert" in alert["tags"]
    assert "ntnx_alert_type:A6227" in alert["tags"]
    assert "ntnx_alert_severity:WARNING" in alert["tags"]
    assert "ntnx_alert_classification:Cluster" in alert["tags"]
    assert "ntnx_alert_impact:CONFIGURATION" in alert["tags"]
    assert "ntnx_cluster_name:prism-central-deployment" in alert["tags"]


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

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
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
