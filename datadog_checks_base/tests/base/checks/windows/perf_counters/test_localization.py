# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, SERVER, get_check

pytestmark = [requires_py3, requires_windows]


def test_default(aggregator, dd_run_check, mock_performance_objects):
    import win32pdh

    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=['server:{}'.format(SERVER)])

    win32pdh.AddEnglishCounter.assert_called_once_with(
        mock.ANY, win32pdh.MakeCounterPath((SERVER, 'Foo', '*', None, 0, 'Bar'))
    )


def test_localized_object(aggregator, dd_run_check, mock_performance_objects):
    import win32pdh

    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    check = get_check(
        {'metrics': {'Foo': {'use_localized_counters': True, 'name': 'foo', 'counters': [{'Bar': 'bar'}]}}}
    )
    dd_run_check(check)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=['server:{}'.format(SERVER)])

    win32pdh.AddCounter.assert_called_once_with(
        mock.ANY, win32pdh.MakeCounterPath((SERVER, 'Foo', '*', None, 0, 'Bar'))
    )


def test_localized_global(aggregator, dd_run_check, mock_performance_objects):
    import win32pdh

    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    check = get_check(
        {'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}}, {'use_localized_counters': True}
    )
    dd_run_check(check)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=['server:{}'.format(SERVER)])

    win32pdh.AddCounter.assert_called_once_with(
        mock.ANY, win32pdh.MakeCounterPath((SERVER, 'Foo', '*', None, 0, 'Bar'))
    )


def test_localized_object_overrides_global(aggregator, dd_run_check, mock_performance_objects):
    import win32pdh

    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})
    check = get_check(
        {'metrics': {'Foo': {'use_localized_counters': False, 'name': 'foo', 'counters': [{'Bar': 'bar'}]}}},
        {'use_localized_counters': True},
    )
    dd_run_check(check)

    tags = ['instance:baz']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=['server:{}'.format(SERVER)])

    win32pdh.AddEnglishCounter.assert_called_once_with(
        mock.ANY, win32pdh.MakeCounterPath((SERVER, 'Foo', '*', None, 0, 'Bar'))
    )
