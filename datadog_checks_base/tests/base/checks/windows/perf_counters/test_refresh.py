# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3, requires_windows

import mock

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

    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}, {'Bar2': 'bar2'}]}}})

    # Check attribute overwrite seems to be simpler than mock.path.object mocking
    # Set activated refresher mock (by default refreshes is not active)
    check.interval = 1
    refresher_mock = mock.Mock()
    check.OBJECT_REFRESHER = refresher_mock

    instances = ['instance1', 'instance2', 'instance1', 'instance2', 'instance2']
    values1 = [6, 7, 8, 9, 11]
    values2 = [7, 8, 9, 10, 11]

    # Set two counters
    mock_performance_objects({'Foo': (instances, {'Bar': values1, 'Bar2': values2})})
    refresher_mock.get_last_refresh.return_value = 0
    dd_run_check(check)

    # ... check outcome
    win32pdh.RemoveCounter.assert_not_called()

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)
    aggregator.assert_metric('test.foo.bar2', 16, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 27, tags=tags)
    aggregator.assert_metric('test.foo.bar2', 29, tags=tags)

    # Set one counters and enable refresh
    aggregator.reset()

    mock_performance_objects({'Foo': (instances, {'Bar': values1})})
    refresher_mock.get_last_refresh.return_value = 100
    dd_run_check(check)

    # ... check outcome (counter is removed and corresponding metric does not exist)
    win32pdh.RemoveCounter.assert_any_call(win32pdh.MakeCounterPath((SERVER, 'Foo', '*', None, 0, 'Bar2')))

    assert 'test.foo.bar2' not in aggregator.metric_names
    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 27, tags=tags)


def test_addition(aggregator, dd_run_check, mock_performance_objects):
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}, {'Bar2': 'bar2'}]}}})

    # Check attribute overwrite seems to be simpler than mock.path.object mocking
    # Set activated refresher mock (by default refreshes is not active)
    check.interval = 1
    refresher_mock = mock.Mock()
    check.OBJECT_REFRESHER = refresher_mock

    instances = ['instance1', 'instance2', 'instance1', 'instance2', 'instance2']
    values1 = [6, 7, 8, 9, 11]
    values2 = [7, 8, 9, 10, 11]

    # Set one counters
    mock_performance_objects({'Foo': (instances, {'Bar': values1})})
    refresher_mock.get_last_refresh.return_value = 0
    dd_run_check(check)

    # ... check outcome
    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 27, tags=tags)

    assert 'test.foo.bar2' not in aggregator.metric_names

    # Set two counters and enable refresh
    aggregator.reset()

    mock_performance_objects({'Foo': (instances, {'Bar': values1, 'Bar2': values2})})
    refresher_mock.get_last_refresh.return_value = 100
    dd_run_check(check)

    # ... check outcome (counter is added)
    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 14, tags=tags)
    aggregator.assert_metric('test.foo.bar2', 16, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 27, tags=tags)
    aggregator.assert_metric('test.foo.bar2', 29, tags=tags)
