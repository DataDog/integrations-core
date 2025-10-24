# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import logging

from . import common

log = logging.getLogger(__file__)


def test_basic_check(mock_proc_sampler, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['tags'] = ["optional:tag1"]

    c = check(instance)
    c.check(instance)

    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['optional:tag1'], count=1)

    aggregator.assert_all_metrics_covered()


def test_tags(mock_proc_sampler, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['tags'] = ["optional:tag1"]
    instance['constant_tags'] = ["instance:tag2"]
    c = check(instance)

    c.check(instance)

    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['optional:tag1', 'instance:tag2'], count=1)

    aggregator.assert_all_metrics_covered()


def test_invalid_class(aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['class'] = 'Unix'
    c = check(instance)

    c.check(instance)

    # No metrics/service check
    aggregator.assert_all_metrics_covered()


def test_invalid_metrics(aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['metrics'].append(['InvalidProperty', 'proc.will.not.be.reported', 'gauge'])
    c = check(instance)

    c.check(instance)
    # No metrics/service check
    aggregator.assert_all_metrics_covered()


def test_check(mock_disk_sampler, aggregator, check):
    c = check(common.WMI_CONFIG)
    c.check(common.WMI_CONFIG)

    for _, mname, _ in common.WMI_CONFIG['metrics']:
        aggregator.assert_metric(mname, tags=["foobar"], count=1)
        aggregator.assert_metric(mname, tags=["foobar"], count=1)

    aggregator.assert_all_metrics_covered()


def test_tag_by_is_correctly_requested(mock_proc_sampler, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    instance['tag_by'] = 'Name'
    c = check(instance)
    c.check(instance)
    get_running_wmi_sampler = c._get_running_wmi_sampler
    assert get_running_wmi_sampler.call_args.kwargs['tag_by'] == 'Name'

def test_tag_queries_with_alias(mock_sampler_with_tag_queries, aggregator, check):
    """Test that tag_queries with an alias use the alias as the tag name instead of the property name"""
    import copy

    instance = copy.deepcopy(common.INSTANCE)
    # Add tag_queries: [source_property, target_class, link_property, target_property, alias]
    instance['tag_queries'] = [
        ['IDProcess', 'Win32_Process', 'Handle', 'Name', 'process_name']
    ]

    c = check(instance)
    c.check(instance)

    # Verify metrics are tagged with the alias 'process_name' instead of 'name'
    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['process_name:chrome.exe'], count=1)

    aggregator.assert_all_metrics_covered()


def test_tag_queries_without_alias(mock_sampler_with_tag_queries, aggregator, check):
    """Test that tag_queries without an alias default to using the target property name"""
    import copy

    instance = copy.deepcopy(common.INSTANCE)
    # Add tag_queries without alias (only 4 elements)
    instance['tag_queries'] = [
        ['IDProcess', 'Win32_Process', 'Handle', 'Name']
    ]

    c = check(instance)
    c.check(instance)

    # Verify metrics are tagged with 'name' (the property name, lowercased)
    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['name:chrome.exe'], count=1)

    aggregator.assert_all_metrics_covered()
