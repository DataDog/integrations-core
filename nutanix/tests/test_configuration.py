# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck
from tests.constants import HOST_NAME, HOST_TAGS, UBUNTU_VM_NAME, UBUNTU_VM_TAGS

pytestmark = [pytest.mark.unit]


def test_conflicting_port_configuration_raises_error(dd_run_check, mock_instance):
    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197:9441'
    instance['pc_port'] = 9440

    with pytest.raises(Exception, match="Conflicting port configuration"):
        check = NutanixCheck('nutanix', {}, [instance])
        dd_run_check(check)


def test_events_disabled_no_events_collected(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['collect_events'] = False

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    for event in aggregator.events:
        tags = event.get('tags', [])
        event_type_tags = [tag for tag in tags if tag.startswith('ntnx_type:event')]
        assert not event_type_tags, f"Should not have event type, found: {event_type_tags}"


def test_tasks_disabled_no_task_events_collected(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['collect_tasks'] = False

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    for event in aggregator.events:
        tags = event.get('tags', [])
        task_type_tags = [tag for tag in tags if tag.startswith('ntnx_type:task')]
        assert not task_type_tags, f"Should not have task type, found: {task_type_tags}"


def test_audits_disabled_no_audit_events_collected(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['collect_audits'] = False

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    for event in aggregator.events:
        tags = event.get('tags', [])
        audit_type_tags = [tag for tag in tags if tag.startswith('ntnx_type:audit')]
        assert not audit_type_tags, f"Should not have audit type, found: {audit_type_tags}"


def test_alerts_disabled_no_alert_events_collected(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['collect_alerts'] = False

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    for event in aggregator.events:
        tags = event.get('tags', [])
        alert_type_tags = [tag for tag in tags if tag.startswith('ntnx_type:alert')]
        assert not alert_type_tags, f"Should not have alert type, found: {alert_type_tags}"


def test_category_tags_without_prefix_for_system_and_user_types(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['prefix_category_tags'] = False
    # Include both SYSTEM and USER types to test prefix behavior
    instance['resource_filters'] = [
        {"resource": "category", "property": "type", "patterns": ["^(SYSTEM|USER)$"]},
    ]

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric_has_tag("nutanix.vm.count", "Environment:Testing")
    aggregator.assert_metric_has_tag("nutanix.vm.count", "Team:agent-integrations")

    for metric in aggregator.metrics("nutanix.vm.count"):
        category_tags = [t for t in metric.tags if t.startswith(("Environment:", "Team:"))]
        prefixed_tags = [t for t in category_tags if t.startswith("ntnx_")]
        assert not prefixed_tags, f"Category tags should not have ntnx_ prefix, found: {prefixed_tags}"


def test_category_tags_with_prefix_for_system_and_user_types(dd_run_check, aggregator, mock_instance, mock_http_get):
    instance = mock_instance.copy()
    instance['prefix_category_tags'] = True
    # Include both SYSTEM and USER types to test prefix behavior
    instance['resource_filters'] = [
        {"resource": "category", "property": "type", "patterns": ["^(SYSTEM|USER)$"]},
    ]

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric_has_tag("nutanix.vm.count", "ntnx_Environment:Testing")
    aggregator.assert_metric_has_tag("nutanix.vm.count", "ntnx_Team:agent-integrations")

    for metric in aggregator.metrics("nutanix.vm.count"):
        category_tags = [t for t in metric.tags if "Environment:" in t or "Team:" in t]
        unprefixed_tags = [t for t in category_tags if not t.startswith("ntnx_")]
        assert not unprefixed_tags, f"Category tags must have ntnx_ prefix, found without: {unprefixed_tags}"


RESOURCE_ID_METRICS = ("nutanix.cluster.count", "nutanix.host.count", "nutanix.vm.count")

# extId values of the cluster, host, and ubuntu-vm served by mock_http_get (see conftest.py).
CLUSTER_ID = "00064715-c043-5d8f-ee4b-176ec875554d"
HOST_ID = "d8787814-4fe8-4ba5-931f-e1ee31c294a6"
UBUNTU_VM_ID = "7b9d5b24-b99a-4c62-516c-0fe0c20411dd"


def test_resource_ids_not_collected_by_default(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    for metric_name in RESOURCE_ID_METRICS:
        assert aggregator.metrics(metric_name), f"{metric_name} was not emitted"
        for metric in aggregator.metrics(metric_name):
            id_tags = [t for t in metric.tags if t.startswith(("ntnx_cluster_id:", "ntnx_host_id:", "ntnx_vm_id:"))]
            assert not id_tags, f"{metric_name} should not have resource id tags by default, found: {id_tags}"

    # Id tags must not leak into the separate external-tags submission path either.
    datadog_agent.assert_external_tags(HOST_NAME, {'nutanix': HOST_TAGS})
    datadog_agent.assert_external_tags(UBUNTU_VM_NAME, {'nutanix': UBUNTU_VM_TAGS})


def test_resource_ids_collected_when_enabled(dd_run_check, aggregator, mock_instance, mock_http_get, datadog_agent):
    instance = mock_instance.copy()
    instance['collect_resource_ids_as_tags'] = True

    check = NutanixCheck('nutanix', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric_has_tag("nutanix.cluster.count", f"ntnx_cluster_id:{CLUSTER_ID}")

    aggregator.assert_metric_has_tag("nutanix.host.count", f"ntnx_host_id:{HOST_ID}")
    aggregator.assert_metric_has_tag("nutanix.host.count", f"ntnx_cluster_id:{CLUSTER_ID}")

    aggregator.assert_metric_has_tag("nutanix.vm.count", f"ntnx_vm_id:{UBUNTU_VM_ID}")
    aggregator.assert_metric_has_tag("nutanix.vm.count", f"ntnx_host_id:{HOST_ID}")
    aggregator.assert_metric_has_tag("nutanix.vm.count", f"ntnx_cluster_id:{CLUSTER_ID}")

    # Id tags ride the shared tag list onto non-count metrics, not just the *.count gauges.
    aggregator.assert_metric_has_tag("nutanix.host.status", f"ntnx_host_id:{HOST_ID}")
    aggregator.assert_metric_has_tag("nutanix.vm.status", f"ntnx_vm_id:{UBUNTU_VM_ID}")

    # Id tags also propagate to host-level external tags (separate submission path).
    datadog_agent.assert_external_tags(
        HOST_NAME,
        {'nutanix': HOST_TAGS + [f"ntnx_cluster_id:{CLUSTER_ID}", f"ntnx_host_id:{HOST_ID}"]},
    )
    datadog_agent.assert_external_tags(
        UBUNTU_VM_NAME,
        {
            'nutanix': UBUNTU_VM_TAGS
            + [f"ntnx_vm_id:{UBUNTU_VM_ID}", f"ntnx_host_id:{HOST_ID}", f"ntnx_cluster_id:{CLUSTER_ID}"]
        },
    )


def test_invalid_hostname_transform_raises_error(dd_run_check, mock_instance):
    instance = mock_instance.copy()
    instance['hostname_transform'] = 'INVALID'
    check = NutanixCheck('nutanix', {}, [instance])

    with pytest.raises(Exception, match="hostname_transform"):
        dd_run_check(check)
