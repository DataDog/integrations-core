# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


def test_conflicting_port_configuration_raises_error(mock_instance):
    instance = mock_instance.copy()
    instance['pc_ip'] = '10.0.0.197:9441'
    instance['pc_port'] = 9440

    with pytest.raises(ConfigurationError):
        NutanixCheck('nutanix', {}, [instance])


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
