# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datetime import datetime
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

from .conftest import load_fixture

pytestmark = [pytest.mark.unit]


MOCK_ALERT_DATETIME = datetime.fromisoformat("2026-01-04T21:09:00.000000Z")
MOCK_ALERT_DATETIME_AFTER_ALL = datetime.fromisoformat("2026-05-01T00:00:00.000000Z")


def _fixture_alert(alert_type, **overrides):
    """Load the first fixture alert with the given alertType and apply overrides."""
    for page in load_fixture('alerts.json'):
        for alert in page.get('data', []):
            if alert.get('alertType') == alert_type:
                return {**alert, **overrides}
    raise ValueError(f"No alert with alertType={alert_type} in fixture")


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no alerts are collected when there are no new alerts since last collection."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True

    # Datetime past all fixture alerts, so the cursor doesn't surface anything new on re-run
    get_current_datetime.return_value = MOCK_ALERT_DATETIME_AFTER_ALL

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0, "Expected alerts to be collected on first run"

    aggregator.reset()

    # Second run with the same fixture state: reconciliation diff is empty
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
    mocker.patch(
        'datadog_checks.nutanix.activity_monitor.ActivityMonitor._list_alerts_unresolved',
        return_value=[synthetic],
    )
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
    mocker.patch(
        'datadog_checks.nutanix.activity_monitor.ActivityMonitor._list_alerts_unresolved',
        return_value=[synthetic],
    )
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


_COMPLETE_OUTPUT_CASES = [
    pytest.param(
        {
            # A1031 (ca546858) is unresolved+acknowledged in the fixture, no injection needed.
            "alert_type": "A1031",
            "inject_synthetic": False,
            "msg_text_contains": [
                "Disk space usage for /var/log on Controller VM 10.0.0.108 has exceeded 75%",
            ],
            "msg_text_excludes": ["{mount_path}", "{entity}", "{ip_address}", "{threshold}"],
            "msg_title_contains": ["Disk space usage high for /var/log on Controller VM 10.0.0.108"],
            "expected_tags": [
                "ntnx_alert_type:A1031",
                "ntnx_alert_severity:WARNING",
                "ntnx_alert_classification:Storage",
                "ntnx_alert_impact:SYSTEM_INDICATOR",
            ],
            "expected_tag_prefixes": ["ntnx_cluster_name:", "ntnx_node_name:"],
        },
        id="a1031_disk_space",
    ),
    pytest.param(
        {
            "alert_type": "A111050",
            "inject_synthetic": True,
            "msg_text_contains": ["nutanix"],
            "msg_text_excludes": ["{users}"],
            "msg_title_contains": ["10.0.0.165"],
            "msg_title_excludes": ["{pcvm_ip}"],
            "expected_tags": [
                "ntnx_alert_type:A111050",
                "ntnx_alert_severity:CRITICAL",
                "ntnx_alert_classification:Cluster",
                "ntnx_alert_impact:CONFIGURATION",
                "ntnx_cluster_name:prism-central-deployment",
            ],
        },
        id="a111050_default_password",
    ),
    pytest.param(
        {
            "alert_type": "A6227",
            "inject_synthetic": True,
            "msg_text_equals": "Admin user password has expired. Please change the admin password.",
            "msg_text_excludes": ["{alert_msg}"],
            "msg_title_equals": "Alert: The PC admin user password is going to expire soon or has already expired.",
            "expected_tags": [
                "ntnx_alert_type:A6227",
                "ntnx_alert_severity:CRITICAL",
                "ntnx_alert_classification:Cluster",
                "ntnx_alert_impact:CONFIGURATION",
                "ntnx_cluster_name:prism-central-deployment",
            ],
        },
        id="a6227_password_expiry",
    ),
]


@pytest.mark.parametrize("case", _COMPLETE_OUTPUT_CASES)
@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_complete_output(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker, case
):
    """Per-alertType golden test: rendered message/title and full tag set on the emitted event.

    Cases that are resolved-only in the fixture (A111050, A6227) inject a synthetic
    unresolved+acknowledged copy via _list_alerts_unresolved so reconciliation surfaces them.
    Acknowledged alerts always emit alert_type=warning regardless of severity.
    """
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    instance["resource_filters"] = [
        {"resource": "alert", "property": "alertType", "patterns": [f"^{case['alert_type']}$"]},
    ]
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    if case.get("inject_synthetic"):
        synthetic = _fixture_alert(case["alert_type"], isResolved=False, isAcknowledged=True)
        mocker.patch(
            'datadog_checks.nutanix.activity_monitor.ActivityMonitor._list_alerts_unresolved',
            return_value=[synthetic],
        )
    dd_run_check(check)

    alerts = [
        e
        for e in aggregator.events
        if "ntnx_type:alert" in e.get("tags", []) and "ntnx_alert_status:acknowledged" in e.get("tags", [])
    ]
    assert len(alerts) >= 1, f"Expected at least one {case['alert_type']} alert"
    alert = alerts[0]

    if "msg_text_equals" in case:
        assert alert["msg_text"] == case["msg_text_equals"]
    for substring in case.get("msg_text_contains", []):
        assert substring in alert["msg_text"]
    for substring in case.get("msg_text_excludes", []):
        assert substring not in alert["msg_text"]

    if "msg_title_equals" in case:
        assert alert["msg_title"] == case["msg_title_equals"]
    for substring in case.get("msg_title_contains", []):
        assert substring in alert["msg_title"]
    for substring in case.get("msg_title_excludes", []):
        assert substring not in alert["msg_title"]

    assert alert["event_type"] == "nutanix"
    assert alert["source_type_name"] == "nutanix"
    assert alert["alert_type"] == "warning"  # acknowledged → warning regardless of severity
    assert "ntnx_type:alert" in alert["tags"]
    for tag in case.get("expected_tags", []):
        assert tag in alert["tags"]
    for prefix in case.get("expected_tag_prefixes", []):
        assert any(t.startswith(prefix) for t in alert["tags"]), f"Missing tag with prefix {prefix}"


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


@pytest.mark.parametrize(
    "is_auto_resolved, expected_msg_text, expected_auto_tag",
    [
        (False, "Resolved by noueman", "ntnx_alert_auto_resolved:false"),
        (True, "Auto-resolved", "ntnx_alert_auto_resolved:true"),
    ],
)
@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_emit_resolution_event(
    get_current_datetime,
    dd_run_check,
    aggregator,
    mock_instance,
    mock_http_get,
    is_auto_resolved,
    expected_msg_text,
    expected_auto_tag,
):
    """_emit_resolution_event produces a success event with the right msg_text and auto_resolved tag."""
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)
    aggregator.reset()

    resolved_alert = {
        "extId": "test-alert-123",
        "title": "Test Alert Title",
        "severity": "WARNING",
        "alertType": "A1031",
        "isResolved": True,
        "resolvedTime": "2026-03-04T00:49:39.030653Z",
        "resolvedByUsername": "noueman",
        "isAutoResolved": is_auto_resolved,
        "classifications": ["Storage"],
        "impactTypes": ["SYSTEM_INDICATOR"],
    }

    check.activity_monitor._emit_resolution_event(resolved_alert)

    event = aggregator.events[0]
    assert event["alert_type"] == "success"
    assert event["aggregation_key"] == "nutanix-alert-test-alert-123"
    assert event["msg_title"] == "Alert Resolved: Test Alert Title"
    assert expected_msg_text in event["msg_text"]
    assert expected_auto_tag in event["tags"]
    assert "ntnx_alert_status:resolved" in event["tags"]
    assert "ntnx_type:alert" in event["tags"]
    assert "ntnx_alert_severity:WARNING" in event["tags"]


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
    assert len(alerts) > 0
    for alert in alerts:
        assert alert["event_type"] == "nutanix"
        assert alert["source_type_name"] == "nutanix"
        assert any(t in alert["tags"] for t in ("ntnx_alert_status:open", "ntnx_alert_status:acknowledged"))
        assert any(t.startswith("ntnx_alert_type:") for t in alert["tags"])

    resolved = [e for e in aggregator.events if "ntnx_alert_status:resolved" in e.get("tags", [])]
    assert len(resolved) == 0
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

    # First run: populate _open_alerts from the real fixture
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

    resolved_metrics = [
        m for m in aggregator.metrics("nutanix.alert.resolved") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(resolved_metrics) == 1

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

    # Pick an alert currently tracked as open (not acknowledged) so we can transition it
    target_ext_id = next(
        ext_id for ext_id, a in check.activity_monitor._open_alerts.items() if not a.get("isAcknowledged")
    )

    aggregator.reset()

    # Same unresolved set, but the target now has isAcknowledged=True
    refreshed = []
    for ext_id, a in check.activity_monitor._open_alerts.items():
        if ext_id == target_ext_id:
            updated = dict(a)
            updated["isAcknowledged"] = True
            updated["acknowledgedByUsername"] = "noueman"
            updated["lastUpdatedTime"] = "2026-04-15T00:00:00.000000Z"
            refreshed.append(updated)
        else:
            refreshed.append(a)

    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=refreshed)

    dd_run_check(check)

    open_zeros = [
        m for m in aggregator.metrics("nutanix.alert.open") if m.value == 0 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(open_zeros) == 1

    ack_ones = [
        m
        for m in aggregator.metrics("nutanix.alert.acknowledged")
        if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(ack_ones) >= 1

    open_ones = [
        m for m in aggregator.metrics("nutanix.alert.open") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(open_ones) == 0

    # Transition emits a dedicated event so the timeline is recorded in Events Explorer
    transition_events = [
        e
        for e in aggregator.events
        if f"ext_id:{target_ext_id}" in e.get("tags", []) and e["msg_title"].startswith("Alert acknowledged:")
    ]
    assert len(transition_events) == 1
    assert "Acknowledged by noueman" in transition_events[0]["msg_text"]
    assert transition_events[0]["alert_type"] == "warning"
    assert "ntnx_alert_status:acknowledged" in transition_events[0]["tags"]


# --- Tier 1 tags + status-tag-free metrics ---


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_event_carries_originating_cluster_and_user_defined_tags(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Alert events carry ntnx_originating_cluster_name and ntnx_alert_user_defined tags."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) > 0

    # At least one alert exposes both cluster perspectives with distinct values
    # (clusterUUID = managed cluster the alert is reported against,
    #  originatingClusterUUID = PC's own cluster federating the alert)
    distinct_pairs = [
        e
        for e in alerts
        if any(t.startswith("ntnx_cluster_name:") for t in e["tags"])
        and any(t.startswith("ntnx_originating_cluster_name:") for t in e["tags"])
    ]
    assert len(distinct_pairs) > 0, "Expected at least one alert with both cluster tags"

    for e in alerts:
        assert any(t.startswith("ntnx_alert_user_defined:") for t in e["tags"])


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_event_carries_service_tag_when_available(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """ntnx_alert_service is emitted only when the alert has a serviceName."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    synthetic = _fixture_alert(
        "NTNX_IAMv2_Authn_Database_Connectivity_Error_Warning",
        isResolved=False,
        isAcknowledged=False,
    )
    mocker.patch(
        'datadog_checks.nutanix.activity_monitor.ActivityMonitor._list_alerts_unresolved',
        return_value=[synthetic],
    )
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) == 1
    assert "ntnx_alert_service:IAMv2" in alerts[0]["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_state_metrics_do_not_carry_status_tag(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """The metric name encodes the state, so ntnx_alert_status is omitted from metric tags."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    for name in ("nutanix.alert.open", "nutanix.alert.acknowledged"):
        for m in aggregator.metrics(name):
            assert not any(t.startswith("ntnx_alert_status:") for t in m.tags), (
                f"{name} should not carry ntnx_alert_status tag (redundant with metric name)"
            )


# --- Edge cases: state transitions, filter changes, deletion, empty list ---


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_open_metric_zero_on_resolution_from_acknowledged_state(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Resolution from the acknowledged state closes nutanix.alert.acknowledged, not .open."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    # Specifically pick an alert tracked in the acknowledged state
    target_ext_id = next(ext_id for ext_id, a in check.activity_monitor._open_alerts.items() if a.get("isAcknowledged"))

    aggregator.reset()

    resolved_alert = {
        "extId": target_ext_id,
        "isResolved": True,
        "resolvedTime": "2026-03-04T01:10:00.000000Z",
        "resolvedByUsername": "admin",
        "isAutoResolved": False,
        "isAcknowledged": True,
        "title": "Resolved Acknowledged Alert",
        "alertType": "A1031",
        "severity": "WARNING",
    }

    remaining = [a for a in check.activity_monitor._open_alerts.values() if a.get("extId") != target_ext_id]
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=remaining)
    mocker.patch.object(check.activity_monitor, '_get_alert', return_value=resolved_alert)

    dd_run_check(check)

    ack_zeros = [
        m
        for m in aggregator.metrics("nutanix.alert.acknowledged")
        if m.value == 0 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(ack_zeros) == 1

    # No :0 on nutanix.alert.open for this ext_id (it never was in that state on this run)
    open_zeros = [
        m for m in aggregator.metrics("nutanix.alert.open") if m.value == 0 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(open_zeros) == 0

    resolved_metrics = [
        m for m in aggregator.metrics("nutanix.alert.resolved") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(resolved_metrics) == 1


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_state_transition_acknowledged_to_open(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Un-acknowledging in Nutanix moves the alert back from .acknowledged to .open."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    target_ext_id = next(ext_id for ext_id, a in check.activity_monitor._open_alerts.items() if a.get("isAcknowledged"))

    aggregator.reset()

    # Same unresolved set, but the target is now un-acknowledged
    refreshed = []
    for ext_id, a in check.activity_monitor._open_alerts.items():
        if ext_id == target_ext_id:
            updated = dict(a)
            updated["isAcknowledged"] = False
            refreshed.append(updated)
        else:
            refreshed.append(a)

    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=refreshed)

    dd_run_check(check)

    ack_zeros = [
        m
        for m in aggregator.metrics("nutanix.alert.acknowledged")
        if m.value == 0 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(ack_zeros) == 1

    open_ones = [
        m for m in aggregator.metrics("nutanix.alert.open") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(open_ones) >= 1

    # Target should not have a :1 on .acknowledged this cycle
    ack_ones_target = [
        m
        for m in aggregator.metrics("nutanix.alert.acknowledged")
        if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(ack_ones_target) == 0

    # Transition emits an "Alert reopened" event
    transition_events = [
        e
        for e in aggregator.events
        if f"ext_id:{target_ext_id}" in e.get("tags", []) and e["msg_title"].startswith("Alert reopened:")
    ]
    assert len(transition_events) == 1
    assert "ntnx_alert_status:open" in transition_events[0]["tags"]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_filter_excludes_tracked_alert_emits_spurious_resolution(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """A tracked alert that becomes filter-excluded mid-life is currently treated as resolved.

    Documents existing behavior: when a resource_filter is added that excludes a
    previously-tracked alert, reconciliation sees it disappear from api_alerts and
    emits a resolution event + nutanix.alert.resolved=1 — even though Prism Central
    still has the alert open. Operators changing filter rules should be aware.
    """
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    target_ext_id = next(iter(check.activity_monitor._open_alerts))

    aggregator.reset()

    # Simulate adding a filter that excludes the target ext_id mid-life
    original = check.activity_monitor._should_collect_activity_item
    mocker.patch.object(
        check.activity_monitor,
        '_should_collect_activity_item',
        side_effect=lambda item, kind: item.get("extId") != target_ext_id and original(item, kind),
    )

    dd_run_check(check)

    resolved_events = [
        e
        for e in aggregator.events
        if "ntnx_alert_status:resolved" in e.get("tags", []) and f"ext_id:{target_ext_id}" in e.get("tags", [])
    ]
    assert len(resolved_events) == 1
    assert target_ext_id not in check.activity_monitor._open_alerts

    resolved_metrics = [
        m for m in aggregator.metrics("nutanix.alert.resolved") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(resolved_metrics) == 1


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alerts_collection_empty_unresolved_list(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Cold start with no open alerts in Prism Central is a clean no-op."""
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    mocker.patch(
        'datadog_checks.nutanix.activity_monitor.ActivityMonitor._list_alerts_unresolved',
        return_value=[],
    )
    dd_run_check(check)

    assert check.activity_monitor.alerts_count == 0
    assert check.activity_monitor._open_alerts == {}
    assert [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])] == []
    for name in ("nutanix.alert.open", "nutanix.alert.acknowledged", "nutanix.alert.resolved"):
        assert list(aggregator.metrics(name)) == []


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_alert_resolution_with_no_metadata_when_alert_deleted(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """An alert deleted (not resolved) in Nutanix: _get_alert returns None; falls back to cached metadata.

    Exercises the bare 'Resolved' msg_text fallback (no resolvedByUsername, not auto-resolved)
    and the cached-tags path when the API can no longer return the alert.
    """
    instance = mock_instance.copy()
    instance["collect_alerts"] = True
    get_current_datetime.return_value = MOCK_ALERT_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    target_ext_id = next(iter(check.activity_monitor._open_alerts))
    cached_state = check.activity_monitor._open_alerts[target_ext_id].copy()
    prior_state = "acknowledged" if cached_state.get("isAcknowledged") else "open"

    aggregator.reset()

    remaining = [a for a in check.activity_monitor._open_alerts.values() if a.get("extId") != target_ext_id]
    mocker.patch.object(check.activity_monitor, '_list_alerts_unresolved', return_value=remaining)
    mocker.patch.object(check.activity_monitor, '_get_alert', return_value=None)

    dd_run_check(check)

    resolution_events = [
        e
        for e in aggregator.events
        if "ntnx_alert_status:resolved" in e.get("tags", []) and f"ext_id:{target_ext_id}" in e.get("tags", [])
    ]
    assert len(resolution_events) == 1
    # No resolvedByUsername and isAutoResolved defaults to False on the cached alert,
    # so the message falls through to the bare "Resolved" branch.
    assert resolution_events[0]["msg_text"] == "Resolved"
    assert "ntnx_alert_auto_resolved:false" in resolution_events[0]["tags"]

    zero_metrics = [
        m
        for m in aggregator.metrics(f"nutanix.alert.{prior_state}")
        if m.value == 0 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(zero_metrics) == 1

    resolved_metrics = [
        m for m in aggregator.metrics("nutanix.alert.resolved") if m.value == 1 and f"ext_id:{target_ext_id}" in m.tags
    ]
    assert len(resolved_metrics) == 1
