# (C) Datadog, Inc. 2025-present
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
            'prism_central:10.0.0.197',
            'ntnx_alert_id:5bfd312f-dff9-4c08-a0fe-e059d2167606',
            'ntnx_alert_type:A1031',
            'ntnx_alert_severity:WARNING',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_alert_classification:Storage',
            'ntnx_alert_impact:SYSTEM_INDICATOR',
            'ntnx_node_id:d8787814-4fe8-4ba5-931f-e1ee31c294a6',
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
            'prism_central:10.0.0.197',
            'ntnx_alert_id:ebf72745-2c84-4e5a-a94e-7bec727a206c',
            'ntnx_alert_type:A1031',
            'ntnx_alert_severity:WARNING',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_alert_classification:Storage',
            'ntnx_alert_impact:SYSTEM_INDICATOR',
            'ntnx_node_id:d8787814-4fe8-4ba5-931f-e1ee31c294a6',
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
            'prism_central:10.0.0.197',
            'ntnx_alert_id:c17420bd-d048-4a3a-ba02-fb485cae2aaf',
            'ntnx_alert_type:A130172',
            'ntnx_alert_severity:INFO',
            'ntnx_cluster_id:00064715-c043-5d8f-ee4b-176ec875554d',
            'ntnx_alert_classification:DR',
            'ntnx_alert_impact:SYSTEM_INDICATOR',
            'ntnx_vm_id:7b9d5b24-b99a-4c62-516c-0fe0c20411dd',
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

    assert len(alerts) == 3, "Expected alerts to be collected"
    assert alerts == EXPECTED_ALERTS


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
    assert len(alerts) == 3, "Expected alerts to be collected on first run"
    assert alerts == EXPECTED_ALERTS

    aggregator.reset()

    # second check run, no new alerts to be collected
    dd_run_check(check)

    alerts = [e for e in aggregator.events if "ntnx_type:alert" in e.get("tags", [])]
    assert len(alerts) == 0, "Expected no alerts when there are no new alerts since last collection"
