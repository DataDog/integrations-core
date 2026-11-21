# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from datadog_checks.dev.testing import requires_windows

from .utils import GLOBAL_TAGS, get_check

pytestmark = [requires_windows]


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


def test_exclude_case_insensitive(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['0,_total', 'baz'], {'Bar': [1, 2]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'exclude': ['Baz'], 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()


def test_include_case_insensitive(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['Foobar', 'Bar', 'Barbat'], {'Bar': [1, 2, 3]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'include': ['bar$'], 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:Foobar']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 1, tags=tags)

    tags = ['instance:Bar']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 2, tags=tags)

    aggregator.assert_metric_has_tag('test.foo.bar', 'instance:Barbat', count=0)

    aggregator.assert_all_metrics_covered()


def test_include_total(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['_Total', 'baz'], {'Bar': [1, 2]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'include_total': True, 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:_Total']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 1, tags=tags)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 2, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_include_total_with_lowercase_instance(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['_total', 'baz'], {'Bar': [1, 2]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'include_total': True, 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:_total']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 1, tags=tags)

    aggregator.assert_metric_has_tag('test.foo.bar', 'instance:baz', count=1)

    aggregator.assert_all_metrics_covered()


def test_include_total_respects_user_exclude(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['_Total', 'baz'], {'Bar': [1, 2]})})
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'include_total': True,
                    'exclude': ['baz'],
                    'counters': [{'Bar': 'bar'}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['instance:_Total']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 1, tags=tags)

    aggregator.assert_metric_has_tag('test.foo.bar', 'instance:baz', count=0)

    aggregator.assert_all_metrics_covered()


def test_include_fast_error_does_not_skip_subsequent_handles(
    aggregator, dd_run_check, mock_performance_objects, mocker, caplog
):
    import pywintypes

    from datadog_checks.base.checks.windows.perf_counters.constants import PDH_NO_DATA

    mock_performance_objects({'Foo': (['inst_a', 'inst_b', 'inst_c'], {'Bar': [10, 20, 30]})})

    error = pywintypes.error(PDH_NO_DATA, 'PdhGetFormattedCounterArray', 'Failed to retrieve counters values.')

    def mock_get_counter_values(handle, duplicate_instances_exist):
        if '(inst_b)' in handle:
            raise error
        if '(inst_a)' in handle:
            return {'inst_a': 10}
        if '(inst_c)' in handle:
            return {'inst_c': 30}
        return {}

    mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.counter.get_counter_values',
        side_effect=mock_get_counter_values,
    )

    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'include_fast': ['inst_a', 'inst_b', 'inst_c'],
                    'counters': [{'Bar': {'name': 'bar', 'aggregate': True}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags_a = ['instance:inst_a']
    tags_a.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 10, tags=tags_a)

    tags_c = ['instance:inst_c']
    tags_c.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 30, tags=tags_c)

    aggregator.assert_metric_has_tag('test.foo.bar', 'instance:inst_b', count=0)
    aggregator.assert_metric('test.foo.bar.sum', count=0)
    aggregator.assert_all_metrics_covered()

    expected_message = f'Error collecting counter `Bar` (instance `inst_b`) for object `Foo`: `{error}`'
    assert any(level == logging.ERROR and message == expected_message for _, level, message in caplog.record_tuples)
