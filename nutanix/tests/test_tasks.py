# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datetime import datetime, timedelta
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


# Mock datetime to match tasks fixture creation times
MOCK_TASK_DATETIME = datetime.fromisoformat("2026-01-02T15:00:00.000000Z")


EXPECTED_TASKS = [
    {
        'alert_type': 'success',
        'event_type': 'nutanix',
        'msg_text': 'Collect logs (Progress: 100%)',
        'msg_title': 'Task: LogCollectionFromPC',
        'source_type_name': 'nutanix',
        'tags': [
            'nutanix',
            'prism_central:10.0.0.197',
            'ntnx_task_status:SUCCEEDED',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_owner_name:dd_agent',
            'ntnx_entity_type:clustermgmt:config:cluster',
            'ntnx_entity_name:datadog-nutanix-dev',
            'ntnx_type:task',
        ],
        'timestamp': 1767366849,
    },
    {
        'alert_type': 'success',
        'event_type': 'nutanix',
        'msg_text': 'Collect logs (Progress: 100%)',
        'msg_title': 'Task: LogCollectionWithDownloadLink',
        'source_type_name': 'nutanix',
        'tags': [
            'nutanix',
            'prism_central:10.0.0.197',
            'ntnx_task_status:SUCCEEDED',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_owner_name:System',
            'ntnx_entity_type:clustermgmt:config:cluster',
            'ntnx_entity_name:datadog-nutanix-dev',
            'ntnx_type:task',
        ],
        'timestamp': 1767366849,
    },
    {
        'alert_type': 'success',
        'event_type': 'nutanix',
        'msg_text': 'Update the VM (Progress: 100%)',
        'msg_title': 'Task: update_vm_intentful',
        'source_type_name': 'nutanix',
        'tags': [
            'nutanix',
            'prism_central:10.0.0.197',
            'ntnx_task_status:SUCCEEDED',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_owner_name:admin',
            'ntnx_entity_type:vmm:ahv:config:vm',
            'ntnx_entity_name:ubuntu-vm',
            'ntnx_type:task',
        ],
        'timestamp': 1767962394,
    },
]


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_collection(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that tasks are collected and have proper structure."""

    instance = mock_instance.copy()
    instance["collect_tasks"] = True

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]

    assert len(tasks) > 0, "Expected tasks to be collected"
    # Verify task structure
    for task in tasks:
        assert task['event_type'] == 'nutanix'
        assert 'ntnx_type:task' in task['tags']


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no tasks are collected when there are no new tasks since last collection."""
    instance = mock_instance.copy()
    instance["collect_tasks"] = True

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]

    first_run_count = len(tasks)
    assert first_run_count > 0, "Expected tasks to be collected on first run"

    aggregator.reset()

    # second check run, no new tasks to be collected
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]

    assert len(tasks) == 0, "Expected no tasks when there are no new tasks since last collection"


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_filtered_by_resource_filters_exclude_cluster(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that tasks for excluded clusters are not collected."""
    instance = mock_instance.copy()
    instance["collect_tasks"] = True
    instance["resource_filters"] = [
        {
            "resource": "cluster",
            "property": "extId",
            "type": "exclude",
            "patterns": ["^00064715-c043-5d8f-ee4b-176ec875554d$"],
        },
    ]

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]
    # Verify that no tasks from the excluded cluster are collected
    # Note: all() returns True for empty list, which is correct for exclude filters
    assert all("ntnx_cluster_name:datadog-nutanix-dev" not in t["tags"] for t in tasks)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_filtered_by_resource_filters_include_cluster(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that only tasks for included clusters are collected."""
    instance = mock_instance.copy()
    instance["collect_tasks"] = True
    instance["resource_filters"] = [
        {"resource": "cluster", "property": "extId", "patterns": ["^00064715-c043-5d8f-ee4b-176ec875554d$"]},
    ]

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]
    assert len(tasks) > 0
    # Verify that all collected tasks are from the included cluster
    assert all("ntnx_cluster_name:datadog-nutanix-dev" in t["tags"] for t in tasks)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_filtered_by_activity_filter_status_exclude(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that tasks with excluded status are not collected."""
    instance = mock_instance.copy()
    instance["collect_tasks"] = True
    instance["resource_filters"] = [
        {"resource": "task", "property": "status", "type": "exclude", "patterns": ["^SUCCEEDED$"]},
    ]

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]
    # Verify that no tasks with excluded status are collected
    # Note: all() returns True for empty list, which is correct for exclude filters
    assert all("ntnx_task_status:SUCCEEDED" not in t["tags"] for t in tasks)


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_filtered_by_activity_filter_status_include(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get
):
    """Test that only tasks matching the status filter are collected."""
    instance = mock_instance.copy()
    instance["collect_tasks"] = True
    instance["resource_filters"] = [
        {"resource": "task", "property": "status", "patterns": ["^SUCCEEDED$"]},
    ]

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]
    assert len(tasks) > 0
    # Verify that all collected tasks have the included status
    assert all("ntnx_task_status:SUCCEEDED" in t["tags"] for t in tasks)
