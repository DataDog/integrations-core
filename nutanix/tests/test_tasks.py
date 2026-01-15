# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


# Mock datetime to match tasks fixture creation times
MOCK_TASK_DATETIME = datetime.fromisoformat("2026-01-02T15:00:00.000000Z")


# Expected tasks sorted by createdTime ascending:
# 1. LogCollectionFromPC (2026-01-02T15:14:09.478485Z)
# 2. LogCollectionWithDownloadLink (2026-01-02T15:14:09.562678Z)
# 3. update_vm_intentful (2026-01-09T12:39:54.844819Z)
EXPECTED_TASKS = [
    {
        'alert_type': 'success',
        'event_type': 'nutanix',
        'msg_text': 'Collect logs (Progress: 100%)',
        'msg_title': 'Task: LogCollectionFromPC',
        'source_type_name': 'nutanix',
        'tags': [
            'prism_central:10.0.0.197',
            'ntnx_task_id:ZXJnb24=:c26e2479-8a31-4ca8-7390-f7ac065816b3',
            'ntnx_task_status:SUCCEEDED',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_owner_name:dd_agent',
            'ntnx_owner_id:0a0c3867-2fd6-534a-bb3f-01f60431deef',
            'ntnx_entity_type:clustermgmt:config:cluster',
            'ntnx_entity_id:0006411c-0286-bc71-9f02-191e334d457b',
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
            'prism_central:10.0.0.197',
            'ntnx_task_id:ZXJnb24=:a87db417-a83d-4d8d-7a1b-4441099d9850',
            'ntnx_task_status:SUCCEEDED',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_owner_name:System',
            'ntnx_entity_type:clustermgmt:config:cluster',
            'ntnx_entity_id:0006411c-0286-bc71-9f02-191e334d457b',
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
            'prism_central:10.0.0.197',
            'ntnx_task_id:ZXJnb24=:8cd5cb75-37dc-4aa0-9726-3bf31f2239af',
            'ntnx_task_status:SUCCEEDED',
            'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
            'ntnx_cluster_name:datadog-nutanix-dev',
            'ntnx_owner_name:admin',
            'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
            'ntnx_entity_type:vmm:ahv:config:vm',
            'ntnx_entity_id:7b9d5b24-b99a-4c62-516c-0fe0c20411dd',
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
    instance["page_limit"] = 50
    instance["collect_events"] = False
    instance["collect_tasks"] = True

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]

    assert len(tasks) == 3, "Expected 3 tasks to be collected on first run"
    assert tasks == EXPECTED_TASKS, "Expected tasks to be collected"


@mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime")
def test_tasks_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no tasks are collected when there are no new tasks since last collection."""
    instance = mock_instance.copy()
    instance["page_limit"] = 50
    instance["collect_tasks"] = True

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]

    assert len(tasks) == 3, "Expected 3 tasks to be collected on first run"
    assert tasks == EXPECTED_TASKS

    aggregator.reset()

    # Move time forward past all tasks - the most recent task is at 2026-01-09T12:39:54
    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120) + 30
    )

    dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]
    assert len(tasks) == 0, "Expected no tasks when there are no new tasks since last collection"
