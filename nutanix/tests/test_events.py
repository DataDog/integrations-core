# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]

# Mock datetime to match events fixture creation times
MOCK_DATETIME = datetime(2025, 10, 14, 11, 15, 00, tzinfo=timezone.utc)

EXPECTED_EVENTS = [
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Ultimate license applied to cluster',
        'msg_title': 'LicenseAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:9dba574f-90c0-473f-b91b-9be33f1d4732',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760440548,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Password changed for user {username}',
        'msg_title': 'PasswordAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:1f4d5f21-8bdd-4b15-8886-d232b5d030d8',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760442479,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Pulse configuration updated',
        'msg_title': 'PulseAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:4b7625c6-8a8d-4816-8ef1-019e8636f498',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760442526,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Password reset for user admin',
        'msg_title': 'PasswordAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:14f94d80-4404-4f1e-869d-fe22cbb4d00a',
            'ntnx_cluster_id:b6d83094-9404-48de-9c74-ca6bddc3a01d',
            'ntnx_cluster_name:Unnamed',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760605372,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Password reset for user admin',
        'msg_title': 'PasswordAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:0e7621b9-db61-4344-8978-3001cf386c3d',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760607684,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Password reset for user admin',
        'msg_title': 'PasswordAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:3c3da430-7670-406e-8f03-d29bdbc173f5',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760622603,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'User admin enabled',
        'msg_title': 'EnableDisableUserAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:348a9873-f3c4-47f7-95bb-5ff52ad069cc',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760622668,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Pulse configuration updated',
        'msg_title': 'PulseAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:57d23178-e257-497d-9db4-9aa2ccbcd89e',
            'ntnx_cluster_id:b6d83094-9404-48de-9c74-ca6bddc3a01d',
            'ntnx_cluster_name:Unnamed',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760624754,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'Pulse configuration updated',
        'msg_title': 'PulseAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:48c8d441-040e-480c-a36f-a05c5f276d35',
            'ntnx_cluster_id:b6d83094-9404-48de-9c74-ca6bddc3a01d',
            'ntnx_cluster_name:Unnamed',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760624754,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'External state added for cluster datadog-nutanix-dev',
        'msg_title': 'MulticlusterAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_event_id:f1e41e4e-3a4b-4e22-970d-6df49f008e4c',
            'ntnx_cluster_id:b6d83094-9404-48de-9c74-ca6bddc3a01d',
            'ntnx_cluster_name:Unnamed',
            'ntnx_event_classification:UserAction',
            'ntnx_type:event',
        ],
        'timestamp': 1760624803,
    },
]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_events_collection(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that events are collected and have proper structure."""

    instance = mock_instance.copy()
    instance["collect_events"] = True
    get_current_datetime.return_value = MOCK_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    events = [e for e in aggregator.events if "ntnx_type:event" in e.get('tags', [])]
    assert len(events) > 0, "Expected events to be collected"

    assert events[0]['event_type'] == 'nutanix'
    assert events[0]['source_type_name'] == 'nutanix'
    assert events[0]['alert_type'] in ['error', 'warning', 'info']
    assert events[0]['msg_text'] == "Ultimate license applied to cluster"


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_events_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no events are collected when there are no new events since last collection."""

    instance = mock_instance.copy()
    instance["collect_events"] = True
    get_current_datetime.return_value = MOCK_DATETIME

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    events = [e for e in aggregator.events if "ntnx_type:event" in e.get('tags', [])]

    assert len(events) == 10, "Expected events to be collected on first run"
    assert events == EXPECTED_EVENTS

    aggregator.reset()

    # Move time forward past all events - the most recent event is at 2025-10-16T14:26:43
    last_event_time = datetime.fromisoformat("2025-10-16T14:26:43.962603Z".replace("Z", "+00:00"))
    get_current_datetime.return_value = last_event_time + timedelta(seconds=check.sampling_interval + 1)
    dd_run_check(check)

    events = [e for e in aggregator.events if "ntnx_type:event" in e.get('tags', [])]

    assert len(events) == 0, "Expected no events when there are no new events since last collection"
