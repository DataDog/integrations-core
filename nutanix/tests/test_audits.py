# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]

MOCK_AUDIT_DATETIME = datetime.fromisoformat("2026-01-15T10:45:00.000000Z")

EXPECTED_AUDITS = [
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'User {audit_user} has logged in from {ip_address}',
        'msg_title': 'Audit: LoginInfoAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_audit_id:529bb5f3-fb9f-412c-9452-1dbff8a5b1fc',
            'ntnx_audit_type:LoginInfoAudit',
            'ntnx_operation_type:$UNKNOWN',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_IAM_id:admin',
            'ntnx_IAM_name:admin',
            'ntnx_user_name:admin',
            'ntnx_affected_entity_type:IAM',
            'ntnx_affected_entity_id:admin',
            'ntnx_affected_entity_name:admin',
            'ntnx_type:audit',
        ],
        'timestamp': 1768473947,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'User {audit_user} has logged in from {ip_address}',
        'msg_title': 'Audit: LoginInfoAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_audit_id:cee0bd9d-ec29-4f47-a7f8-3a341a7e56c4',
            'ntnx_audit_type:LoginInfoAudit',
            'ntnx_operation_type:$UNKNOWN',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_IAM_id:admin',
            'ntnx_IAM_name:admin',
            'ntnx_user_name:admin',
            'ntnx_affected_entity_type:IAM',
            'ntnx_affected_entity_id:admin',
            'ntnx_affected_entity_name:admin',
            'ntnx_type:audit',
        ],
        'timestamp': 1768473947,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'User {audit_user} has logged in from {ip_address}',
        'msg_title': 'Audit: LoginInfoAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_audit_id:c583fa23-d8fd-42af-a0f3-3425bd2e4300',
            'ntnx_audit_type:LoginInfoAudit',
            'ntnx_operation_type:$UNKNOWN',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_IAM_id:admin',
            'ntnx_IAM_name:admin',
            'ntnx_user_name:admin',
            'ntnx_affected_entity_type:IAM',
            'ntnx_affected_entity_id:admin',
            'ntnx_affected_entity_name:admin',
            'ntnx_type:audit',
        ],
        'timestamp': 1768474009,
    },
    {
        'alert_type': 'info',
        'event_type': 'nutanix',
        'msg_text': 'User {audit_user} has logged in from {ip_address}',
        'msg_title': 'Audit: LoginInfoAudit',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_audit_id:f13a286e-6a73-492d-bc91-c9e6041cf4a2',
            'ntnx_audit_type:LoginInfoAudit',
            'ntnx_operation_type:$UNKNOWN',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_IAM_id:admin',
            'ntnx_IAM_name:admin',
            'ntnx_user_name:admin',
            'ntnx_affected_entity_type:IAM',
            'ntnx_affected_entity_id:admin',
            'ntnx_affected_entity_name:admin',
            'ntnx_type:audit',
        ],
        'timestamp': 1768474010,
    },
]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_audits_collection(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance["collect_audits"] = True
    get_current_datetime.return_value = MOCK_AUDIT_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    audits = [e for e in aggregator.events if "ntnx_type:audit" in e.get("tags", [])]
    assert len(audits) == 4

    assert audits == EXPECTED_AUDITS


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_audits_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no audits are collected when there are no new audits since last collection."""

    instance = mock_instance.copy()
    instance["collect_audits"] = True
    get_current_datetime.return_value = MOCK_AUDIT_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    audits = [e for e in aggregator.events if "ntnx_type:audit" in e.get("tags", [])]
    assert len(audits) == 4, "Expected audits to be collected on first run"
    assert audits == EXPECTED_AUDITS

    aggregator.reset()

    # second check run, no new audits to be collected
    dd_run_check(check)

    audits = [e for e in aggregator.events if "ntnx_type:audit" in e.get("tags", [])]
    assert len(audits) == 0, "Expected no audits when there are no new audits since last collection"
