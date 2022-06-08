# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, SERVER, get_check

pytestmark = [requires_py3, requires_windows]


def test_detection(aggregator, dd_run_check, mock_performance_objects):
    instances = ['instance1']
    values = [6]
    mock_performance_objects({'Foo': (instances, {'Bar': values})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 6, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.reset()

    instances.extend(('instance2', 'instance1'))
    values.extend((9, 10))

    mock_performance_objects({'Foo': (instances, {'Bar': values})})
    dd_run_check(check)

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 16, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_removal(aggregator, dd_run_check, mock_performance_objects):
    import win32pdh

    instances = ['instance1', 'instance2', 'instance1', 'instance2', 'instance2']
    values = [6, 7, 8, 9, 11]
    mock_performance_objects({'Foo': (instances, {'Bar': values})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)
    win32pdh.RemoveCounter.assert_not_called()

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 27, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.reset()

    for _ in range(2):
        instances.pop()
        values.pop()

    mock_performance_objects({'Foo': (instances, {'Bar': values})})
    dd_run_check(check)

    win32pdh.RemoveCounter.assert_any_call(win32pdh.MakeCounterPath((SERVER, 'Foo', 'instance2', None, 2, 'Bar')))
    win32pdh.RemoveCounter.assert_any_call(win32pdh.MakeCounterPath((SERVER, 'Foo', 'instance2', None, 1, 'Bar')))

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 7, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.reset()

    for _ in range(2):
        instances.pop()
        values.pop()

    mock_performance_objects({'Foo': (instances, {'Bar': values})})
    dd_run_check(check)

    win32pdh.RemoveCounter.assert_any_call(win32pdh.MakeCounterPath((SERVER, 'Foo', 'instance1', None, 1, 'Bar')))
    win32pdh.RemoveCounter.assert_any_call(win32pdh.MakeCounterPath((SERVER, 'Foo', 'instance2', None, 0, 'Bar')))

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 6, tags=tags)

    aggregator.assert_all_metrics_covered()
