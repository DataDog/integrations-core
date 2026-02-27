# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta
from unittest import mock

import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


def test_vm_metrics_include_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)
    aggregator.assert_metric_has_tag("nutanix.vm.count", tag="Environment:Testing")
    aggregator.assert_metric_has_tag("nutanix.vm.count", tag="Team:agent-integrations")


def test_vm_metrics_with_prefix_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["prefix_category_tags"] = True
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)
    aggregator.assert_metric_has_tag("nutanix.vm.count", tag="ntnx_Environment:Testing")
    aggregator.assert_metric_has_tag("nutanix.vm.count", tag="ntnx_Team:agent-integrations")


def test_external_tags_include_category_tags(dd_run_check, mock_instance, mock_http_get, datadog_agent):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    external_tags_calls = datadog_agent._external_tags
    for _hostname, source_tags in external_tags_calls:
        if 'nutanix' in source_tags:
            tags = source_tags['nutanix']
            if "Environment:Testing" in tags and "Team:agent-integrations" in tags:
                return

    pytest.fail("Expected category tags in external tags")


def test_events_include_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["collect_events"] = True
    mock_datetime = datetime.fromisoformat("2025-10-14T11:15:00.000000Z")

    with mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime") as get_current_datetime:
        get_current_datetime.return_value = mock_datetime
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

    events = [e for e in aggregator.events if "ntnx_type:event" in e.get('tags', [])]
    assert len(events) > 0


def test_tasks_include_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["collect_tasks"] = True
    mock_datetime = datetime.fromisoformat("2026-01-02T15:00:00.000000Z")

    with mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime") as get_current_datetime:
        get_current_datetime.return_value = mock_datetime + timedelta(seconds=120)
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

    tasks = [t for t in aggregator.events if "ntnx_type:task" in t.get('tags', [])]
    assert len(tasks) > 0


def test_alerts_include_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["collect_alerts"] = True
    mock_datetime = datetime.fromisoformat("2026-01-13T11:00:00.000000Z")

    with mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime") as get_current_datetime:
        get_current_datetime.return_value = mock_datetime + timedelta(seconds=120)
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

    alerts = [a for a in aggregator.events if "ntnx_type:alert" in a.get('tags', [])]
    assert len(alerts) > 0


def test_audits_include_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["collect_audits"] = True
    mock_datetime = datetime.fromisoformat("2026-01-13T11:00:00.000000Z")

    with mock.patch("datadog_checks.nutanix.activity_monitor.get_current_datetime") as get_current_datetime:
        get_current_datetime.return_value = mock_datetime + timedelta(seconds=120)
        check = NutanixCheck('nutanix', {}, [mock_instance])
        dd_run_check(check)

    audits = [a for a in aggregator.events if "ntnx_type:audit" in a.get('tags', [])]
    assert len(audits) > 0
