# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import copy
import logging
from unittest.mock import patch

import pytest

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


@pytest.mark.parametrize(
    "tag_query,result_tags",
    [
        ([['IDProcess', 'Win32_Process', 'Handle', 'Name AS process_name']], ['process_name:chrome.exe']),
        ([['IDProcess', 'Win32_Process', 'Handle', 'Name AS ProcessName']], ['processname:chrome.exe']),
        ([['IDProcess', 'Win32_Process', 'Handle', 'Name']], ['name:chrome.exe']),
        ([['IDProcess', 'Win32_Process', 'Handle', 'Name', '']], ['name:chrome.exe']),
        ([['IDProcess', 'Win32_Process', 'Handle', 'Name as process_name', 'foo']], ['process_name:chrome.exe']),
    ],
)
def test_tag_queries_with_alias(mock_sampler_with_tag_queries, aggregator, check, tag_query, result_tags):
    instance = copy.deepcopy(common.INSTANCE)
    # Add tag_queries: [source_property, target_class, link_property, target_property, alias]
    instance['tag_queries'] = tag_query

    c = check(instance)
    c.check(instance)

    # Verify metrics are tagged with the alias 'process_name' instead of 'name'
    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=result_tags, count=1)

    aggregator.assert_all_metrics_covered()


def test_tag_queries_without_alias(mock_sampler_with_tag_queries, aggregator, check):
    instance = copy.deepcopy(common.INSTANCE)
    # Add tag_queries without alias (only 4 elements)
    instance['tag_queries'] = [['IDProcess', 'Win32_Process', 'Handle', 'Name']]

    c = check(instance)
    c.check(instance)

    # Verify metrics are tagged with 'name' (the property name, lowercased)
    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=['name:chrome.exe'], count=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    "tag_by,result_tags",
    [
        ('Name AS wmi_name', ['wmi_name:foo']),
        ('Name,Label AS wmi_label', ['name:foo', 'wmi_label:bar']),
        ('name as wmi_name,label as wmi_label', ['wmi_name:foo', 'wmi_label:bar']),
        ('nameaswmi_name', []),
        ('Name AS , Label AS wmi_label', ['name:foo', 'wmi_label:bar']),
    ],
)
def test_tag_by_is_correctly_prefixed(mock_sampler_with_tag_by_prefix, aggregator, check, tag_by, result_tags):
    instance = copy.deepcopy(common.INSTANCE)
    instance['tag_by'] = tag_by

    c = check(instance)

    with patch.object(c, '_extract_metrics', wraps=c._extract_metrics) as mock_extract:
        c.check(instance)
        assert mock_extract.called
        # Check the arguments it was called with
        # _extract_metrics(self, wmi_sampler, tag_by, tag_queries, constant_tags)
        call_args = mock_extract.call_args
        assert call_args[0][1] == tag_by

    # Verify metrics are tagged with the alias
    for metric in common.INSTANCE_METRICS:
        aggregator.assert_metric(metric, tags=result_tags, count=1)

    aggregator.assert_all_metrics_covered()
