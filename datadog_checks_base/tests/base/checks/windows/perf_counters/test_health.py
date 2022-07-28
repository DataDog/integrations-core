# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, get_check

pytestmark = [requires_py3, requires_windows]


def test_disable(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    check = get_check(
        {'enable_health_service_check': False, 'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}}
    )
    dd_run_check(check)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, count=0)


def test_ok(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=GLOBAL_TAGS)


def test_critical_query(aggregator, dd_run_check, mock_performance_objects, mocker, caplog):
    import pywintypes

    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    mocker.patch('win32pdh.CollectQueryData', side_effect=pywintypes.error(None, None, 'foo failed'))
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()

    expected_message = 'Error querying performance counters: foo failed'
    aggregator.assert_service_check(
        'test.windows.perf.health', ServiceCheck.CRITICAL, message=expected_message, tags=GLOBAL_TAGS
    )

    for _, level, message in caplog.record_tuples:
        if level == logging.ERROR and message == expected_message:
            break
    else:
        raise AssertionError('Expected ERROR log with message `{}`'.format(expected_message))


def test_counters_refresh(aggregator, dd_run_check, mock_performance_objects, mocker, caplog):
    import pywintypes

    error_data = (None, None, 'foo failed')
    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.counter.PerfObject.refresh',
        side_effect=pywintypes.error(*error_data),
    )
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=GLOBAL_TAGS)

    expected_message = 'Error refreshing counters for performance object `Foo`: {}'.format(error_data)
    for _, level, message in caplog.record_tuples:
        if level == logging.ERROR and message == expected_message:
            break
    else:
        raise AssertionError('Expected ERROR log with message `{}`'.format(expected_message))


def test_counters_collect(aggregator, dd_run_check, mock_performance_objects, mocker, caplog):
    import pywintypes

    error_data = (None, None, 'foo failed')
    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    mocker.patch(
        'datadog_checks.base.checks.windows.perf_counters.counter.PerfObject.collect',
        side_effect=pywintypes.error(*error_data),
    )
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=GLOBAL_TAGS)

    expected_message = 'Error collecting query data for performance object `Foo`: {}'.format(error_data)
    for _, level, message in caplog.record_tuples:
        if level == logging.ERROR and message == expected_message:
            break
    else:
        raise AssertionError('Expected ERROR log with message `{}`'.format(expected_message))
