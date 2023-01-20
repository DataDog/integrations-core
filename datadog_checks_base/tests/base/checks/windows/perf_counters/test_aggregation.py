# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, get_check

pytestmark = [requires_py3, requires_windows]


def test_single_instance(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': ([None], {'Bar': [9000], 'Baz': [42]})})
    check = get_check(
        {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar'}}, {'Baz': {'name': 'baz'}}]}}}
    )
    dd_run_check(check)

    aggregator.assert_metric('test.foo.bar', 9000, tags=GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.baz', 42, tags=GLOBAL_TAGS)

    aggregator.assert_all_metrics_covered()


def test_default_sum(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects(
        {'Foo': (['instance1', 'instance2', 'instance1', 'instance2'], {'Bar': [6, 7, 8, 9], 'Baz': [6, 7, 8, 9]})}
    )
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'bat',
                    'counters': [{'Bar': {'name': 'bar'}, 'Baz': {'name': 'baz'}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['bat:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)
    aggregator.assert_metric('test.foo.baz', 14, tags=tags)

    tags = ['bat:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 16, tags=tags)
    aggregator.assert_metric('test.foo.baz', 16, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_average(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects(
        {'Foo': (['instance1', 'instance2', 'instance1', 'instance2'], {'Bar': [6, 7, 8, 9], 'Baz': [6, 7, 8, 9]})}
    )
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'bat',
                    'counters': [{'Bar': {'name': 'bar', 'average': True}, 'Baz': {'name': 'baz'}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['bat:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 7, tags=tags)
    aggregator.assert_metric('test.foo.baz', 14, tags=tags)

    tags = ['bat:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 8, tags=tags)
    aggregator.assert_metric('test.foo.baz', 16, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_aggregate(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects(
        {'Foo': (['instance1', 'instance2', 'instance1', 'instance2'], {'Bar': [6, 7, 8, 9], 'Baz': [6, 7, 8, 9]})}
    )
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'bat',
                    'counters': [{'Bar': {'name': 'bar', 'aggregate': True}, 'Baz': {'name': 'baz'}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['bat:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)
    aggregator.assert_metric('test.foo.baz', 14, tags=tags)
    aggregator.assert_metric('test.foo.bar.sum', 30, metric_type=aggregator.GAUGE, tags=GLOBAL_TAGS)

    tags = ['bat:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 16, tags=tags)
    aggregator.assert_metric('test.foo.baz', 16, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_aggregate_average(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects(
        {'Foo': (['instance1', 'instance2', 'instance1', 'instance2'], {'Bar': [6, 7, 8, 9], 'Baz': [6, 7, 8, 9]})}
    )
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'bat',
                    'counters': [{'Bar': {'name': 'bar', 'average': True, 'aggregate': True}, 'Baz': {'name': 'baz'}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['bat:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 7, tags=tags)
    aggregator.assert_metric('test.foo.baz', 14, tags=tags)
    aggregator.assert_metric('test.foo.bar.avg', 7.5, metric_type=aggregator.GAUGE, tags=GLOBAL_TAGS)

    tags = ['bat:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 8, tags=tags)
    aggregator.assert_metric('test.foo.baz', 16, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_aggregate_metric_type(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects(
        {'Foo': (['instance1', 'instance2', 'instance1', 'instance2'], {'Bar': [6, 7, 8, 9], 'Baz': [6, 7, 8, 9]})}
    )
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'bat',
                    'counters': [
                        {
                            'Bar': {'name': 'bar', 'type': 'monotonic_count', 'aggregate': True},
                            'Baz': {'name': 'baz', 'average': True},
                        }
                    ],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['bat:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)
    aggregator.assert_metric('test.foo.baz', 7, tags=tags)
    aggregator.assert_metric('test.foo.bar.sum', 30, metric_type=aggregator.MONOTONIC_COUNT, tags=GLOBAL_TAGS)

    tags = ['bat:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 16, tags=tags)
    aggregator.assert_metric('test.foo.baz', 8, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_aggregate_only(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects(
        {'Foo': (['instance1', 'instance2', 'instance1', 'instance2'], {'Bar': [6, 7, 8, 9], 'Baz': [6, 7, 8, 9]})}
    )
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'bat',
                    'counters': [
                        {'Bar': {'name': 'bar', 'aggregate': 'only'}, 'Baz': {'name': 'baz', 'average': True}}
                    ],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['bat:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.baz', 7, tags=tags)
    aggregator.assert_metric('test.foo.bar.sum', 30, metric_type=aggregator.GAUGE, tags=GLOBAL_TAGS)

    tags = ['bat:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.baz', 8, tags=tags)

    aggregator.assert_all_metrics_covered()
