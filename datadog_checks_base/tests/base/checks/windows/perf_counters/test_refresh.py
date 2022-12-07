# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, get_check

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
