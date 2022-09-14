# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, get_check

pytestmark = [requires_py3, requires_windows]


def test_include(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['foobar', 'bar', 'barbat'], {'Bar': [1, 2, 3]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'include': ['bar$'], 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:foobar']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 1, tags=tags)

    tags = ['instance:bar']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 2, tags=tags)

    aggregator.assert_metric_has_tag('test.foo.bar', 'instance:bat', count=0)

    aggregator.assert_all_metrics_covered()


def test_exclude(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['foobar', 'bar'], {'Bar': [1, 2]})})
    check = get_check(
        {'metrics': {'Foo': {'name': 'foo', 'include': ['bar$'], 'exclude': ['^bar'], 'counters': [{'Bar': 'bar'}]}}}
    )
    dd_run_check(check)

    tags = ['instance:foobar']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 1, tags=tags)

    aggregator.assert_metric_has_tag('test.foo.bar', 'instance:bar', count=0)

    aggregator.assert_all_metrics_covered()


def test_exclude_default(aggregator, dd_run_check, mock_performance_objects):
    # Account for instances that don't exactly match ^_Total$ like for the `Processor Information` object
    mock_performance_objects({'Foo': (['0,_Total', 'baz'], {'Bar': [1, 2]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'exclude': ['baz'], 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
