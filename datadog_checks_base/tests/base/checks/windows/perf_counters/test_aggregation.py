# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.testing import requires_windows

from .utils import GLOBAL_TAGS, get_check

pytestmark = [requires_windows]


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


@pytest.mark.parametrize(
    'options, invalid_instances, expected_sum',
    [
        pytest.param({}, ['_Total'], 60, id='only excluded _Total invalid'),
        pytest.param({}, ['inst_b', '_Total'], None, id='monitored instance invalid'),
        pytest.param({'include_total': True}, ['_Total'], None, id='included _Total invalid'),
        pytest.param({'exclude': ['inst_b']}, ['inst_b', '_Total'], 40, id='user-excluded instance invalid'),
    ],
)
def test_aggregate_after_negative_value(
    aggregator, dd_run_check, mock_performance_objects, mocker, options, invalid_instances, expected_sum
):
    from datadog_checks.base.checks.windows.perf_counters.utils_win32pdh_fix import PartialCounterValues

    all_values = {'inst_a': 10, 'inst_b': 20, 'inst_c': 30, '_Total': 60}
    mock_performance_objects({'Foo': (list(all_values), {'Bar': list(all_values.values())})})
    valid_values = {name: value for name, value in all_values.items() if name not in invalid_instances}
    mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.counter.get_counter_values',
        return_value=PartialCounterValues(valid_values, invalid_instances),
    )

    check = get_check(
        {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': {'name': 'bar', 'aggregate': True}}], **options}}}
    )
    dd_run_check(check)

    for name, value in valid_values.items():
        aggregator.assert_metric('test.foo.bar', value, tags=[f'instance:{name}', *GLOBAL_TAGS])
    if expected_sum is None:
        aggregator.assert_metric('test.foo.bar.sum', count=0)
    else:
        aggregator.assert_metric('test.foo.bar.sum', expected_sum, tags=GLOBAL_TAGS)
    aggregator.assert_all_metrics_covered()
