# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import pytest

from datadog_checks.nutanix import NutanixCheck

pytestmark = [pytest.mark.unit]


def test_default_includes_only_user_category_tags(dd_run_check, aggregator, mock_instance, mock_http_get):
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)
    aggregator.assert_metric_has_tag("nutanix.vm.count", tag="Team:agent-integrations")
    vm_metrics = aggregator.metrics("nutanix.vm.count")
    for metric in vm_metrics:
        assert "Environment:Testing" not in metric.tags


def test_filtering_by_system_category_type(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "patterns": ["^SYSTEM$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)
    vm_metrics = aggregator.metrics("nutanix.vm.count")

    for metric in vm_metrics:
        has_system_tag = any(tag.startswith("Environment:") for tag in metric.tags)
        has_user_tag = any(tag.startswith("Team:") for tag in metric.tags)
        if has_system_tag or has_user_tag:
            assert has_system_tag
            assert not has_user_tag


def test_excluding_user_category_type(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance["resource_filters"] = [
        {"resource": "category", "property": "type", "type": "exclude", "patterns": ["^USER$"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)
    vm_metrics = aggregator.metrics("nutanix.vm.count")

    for metric in vm_metrics:
        has_user_tag = any(tag.startswith("Team:") for tag in metric.tags)
        assert not has_user_tag


def test_default_category_filter_applies_with_other_resource_filters(
    dd_run_check, aggregator, mock_instance, mock_http_get
):
    mock_instance["resource_filters"] = [
        {"resource": "cluster", "property": "name", "patterns": ["^datadog-"]},
    ]
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric("nutanix.vm.count", at_least=1)
    vm_metrics = aggregator.metrics("nutanix.vm.count")

    for metric in vm_metrics:
        has_user_tag = any(tag.startswith("Team:") for tag in metric.tags)
        has_system_tag = any(tag.startswith("Environment:") for tag in metric.tags)
        if has_user_tag or has_system_tag:
            assert has_user_tag
            assert not has_system_tag


def test_prefix_category_tags_disabled(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance['prefix_category_tags'] = False
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric_has_tag("nutanix.vm.count", "Team:agent-integrations")


def test_prefix_category_tags_enabled(dd_run_check, aggregator, mock_instance, mock_http_get):
    mock_instance['prefix_category_tags'] = True
    check = NutanixCheck('nutanix', {}, [mock_instance])
    dd_run_check(check)

    aggregator.assert_metric_has_tag("nutanix.vm.count", "ntnx_Team:agent-integrations")
