# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.nutanix import NutanixCheck
from tests.metrics import (
    ALL_METRICS,
    CLUSTER_STATS_METRICS_REQUIRED,
    HOST_STATS_METRICS_REQUIRED,
    VM_STATS_METRICS_REQUIRED,
)

pytestmark = [pytest.mark.unit]


def test_health_check_success(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=1, count=1, tags=['prism_central:10.0.0.197'])


def test_health_check_failure(dd_run_check, aggregator, mock_instance, mocker):
    def mock_exception(*args, **kwargs):
        from requests.exceptions import ConnectionError

        raise ConnectionError("Connection failed")

    mocker.patch('requests.Session.get', side_effect=mock_exception)
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.health.up", value=0, count=1, tags=['prism_central:10.0.0.197'])


def test_cluster_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.cluster.count", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.nbr_nodes", value=1, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.count", value=4, tags=expected_tags)
    aggregator.assert_metric("nutanix.cluster.vm.inefficient_count", value=0, tags=expected_tags)


def test_cluster_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'prism_central:10.0.0.197',
    ]

    for metric in CLUSTER_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags)


def test_host_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:host',
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_host_type:HYPER_CONVERGED',
        'ntnx_hypervisor_name:AHV 10.0.1.4',
        'ntnx_hypervisor_type:AHV',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.host.count", value=1, tags=expected_tags, hostname="10-0-0-9-aws-us-east-1a")


def test_host_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:host',
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_host_type:HYPER_CONVERGED',
        'ntnx_hypervisor_name:AHV 10.0.1.4',
        'ntnx_hypervisor_type:AHV',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'prism_central:10.0.0.197',
    ]

    for metric in HOST_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags, hostname="10-0-0-9-aws-us-east-1a")


def test_vm_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
        'ntnx_vm_name:PC-OptionName-1',
        'prism_central:10.0.0.197',
    ]

    aggregator.assert_metric("nutanix.vm.count", value=1, tags=expected_tags, hostname="PC-OptionName-1")


def test_vm_stats_metrics(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    expected_tags = [
        'ntnx_type:vm',
        'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
        'ntnx_cluster_name:datadog-nutanix-dev',
        'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
        'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
        'ntnx_host_name:10-0-0-9-aws-us-east-1a',
        'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
        'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
        'ntnx_vm_name:PC-OptionName-1',
        'prism_central:10.0.0.197',
    ]

    for metric in VM_STATS_METRICS_REQUIRED:
        aggregator.assert_metric(metric, at_least=1, tags=expected_tags, hostname="PC-OptionName-1")


def test_all_metrics_in_metadata_csv(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric in ALL_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_symmetric_inclusion=True)


def test_external_tags_for_host(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Assert external tags for the host
    datadog_agent.assert_external_tags(
        '10-0-0-9-aws-us-east-1a',
        {
            'nutanix': [
                'ntnx_type:host',
                'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
                'ntnx_cluster_name:datadog-nutanix-dev',
                'ntnx_host_name:10-0-0-9-aws-us-east-1a',
                'ntnx_host_type:HYPER_CONVERGED',
                'ntnx_hypervisor_name:AHV 10.0.1.4',
                'ntnx_hypervisor_type:AHV',
                'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
                'prism_central:10.0.0.197',
            ]
        },
    )


def test_external_tags_for_vm(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    # Assert external tags for the VM
    datadog_agent.assert_external_tags(
        'PC-OptionName-1',
        {
            'nutanix': [
                'ntnx_type:vm',
                'ntnx_cluster_id:0006411c-0286-bc71-9f02-191e334d457b',
                'ntnx_cluster_name:datadog-nutanix-dev',
                'ntnx_generation_uuid:75125cab-fd4e-45ed-85c2-f7c4343ceacc',
                'ntnx_host_id:71877eae-8fc1-4aae-8d20-70196dfb2f8d',
                'ntnx_host_name:10-0-0-9-aws-us-east-1a',
                'ntnx_owner_id:00000000-0000-0000-0000-000000000000',
                'ntnx_vm_id:f3272103-ea1e-4a90-8318-899636993ed6',
                'ntnx_vm_name:PC-OptionName-1',
                'prism_central:10.0.0.197',
            ]
        },
    )


# Mock datetime to match events fixture creation times
MOCK_DATETIME = datetime(2025, 10, 14, 11, 15, 00, tzinfo=timezone.utc)
LAST_EVENT_TIMESTAMP = datetime(2025, 12, 4, 15, 53, tzinfo=timezone.utc)


@mock.patch("datadog_checks.nutanix.check.get_current_datetime")
def test_events_collection(get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get):
    """Test that events are collected and have proper structure."""
    get_current_datetime.return_value = MOCK_DATETIME
    instance = mock_instance.copy()
    instance["collect_events"] = True
    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    events = aggregator.events
    assert len(events) > 0, "Expected events to be collected"

    # Verify event structure

    assert events[0]['event_type'] == 'nutanix'
    assert events[0]['source_type_name'] == 'nutanix'
    assert events[0]['alert_type'] in ['error', 'warning', 'info']
    assert events[0]['msg_text'] == "Ultimate license applied to cluster"


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


@mock.patch("datadog_checks.nutanix.check.get_current_datetime")
def test_events_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no events are collected when there are no new events since last collection."""
    instance = mock_instance.copy()
    instance["collect_events"] = True
    check = NutanixCheck('nutanix', {}, [instance])
    get_current_datetime.return_value = MOCK_DATETIME
    dd_run_check(check)
    assert len(aggregator.events) == 10, "Expected events to be collected on first run"
    assert aggregator.events == EXPECTED_EVENTS

    aggregator.reset()

    # Move time forward past all events - the most recent event is at 2025-10-16T14:26:43
    last_event_time = datetime.fromisoformat("2025-10-16T14:26:43.962603Z".replace("Z", "+00:00"))
    get_current_datetime.return_value = last_event_time + timedelta(seconds=check.sampling_interval + 1)
    dd_run_check(check)

    assert len(aggregator.events) == 0, "Expected no events when there are no new events since last collection"


def test_pc_ip_with_port_raises_error(mock_instance):
    """Test that ConfigurationError is raised when pc_ip contains a port."""

    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197:9440'

    with pytest.raises(ConfigurationError) as exc_info:
        NutanixCheck('nutanix', {}, [instance])

    assert "Conflicting configuration" in str(exc_info.value)


def test_pc_ip_without_port(mock_instance):
    """Test that pc_port is used when pc_ip has no port."""
    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197'

    check = NutanixCheck('nutanix', {}, [instance])

    assert check.pc_ip == '10.0.0.197'
    assert check.pc_port == 9440
    assert check.base_url == 'https://10.0.0.197:9440'


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


@mock.patch("datadog_checks.nutanix.check.get_current_datetime")
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

    assert len(aggregator.events) == 3, "Expected 3 tasks to be collected on first run"
    assert aggregator.events == EXPECTED_TASKS, "Expected tasks to be collected"


@mock.patch("datadog_checks.nutanix.check.get_current_datetime")
def test_tasks_no_duplicates_on_subsequent_runs(
    get_current_datetime, dd_run_check, aggregator, mock_instance, mock_http_get, mocker
):
    """Test that no tasks are collected when there are no new tasks since last collection."""
    instance = mock_instance.copy()
    instance["page_limit"] = 50
    instance["collect_events"] = False
    instance["collect_tasks"] = True

    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120)
    )

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    assert len(aggregator.events) == 3, "Expected 3 tasks to be collected on first run"
    assert aggregator.events == EXPECTED_TASKS

    aggregator.reset()

    # Move time forward past all tasks - the most recent task is at 2026-01-09T12:39:54
    get_current_datetime.return_value = MOCK_TASK_DATETIME + timedelta(
        seconds=instance.get("min_collection_interval", 120) + 30
    )

    dd_run_check(check)

    assert len(aggregator.events) == 0, "Expected no tasks when there are no new tasks since last collection"
