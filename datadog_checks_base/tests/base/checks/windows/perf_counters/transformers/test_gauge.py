# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3, requires_windows

from ..utils import GLOBAL_TAGS, get_check

pytestmark = [requires_py3, requires_windows]


def test_explicit(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [9000]})})
    check = get_check(
        {
            'metrics': {
                'Foo': {'name': 'foo', 'tag_name': 'baz', 'counters': [{'Bar': {'name': 'bar', 'type': 'gauge'}}]}
            }
        }
    )
    dd_run_check(check)

    tags = ['baz:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_default(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [9000]})})
    check = get_check({'metrics': {'Foo': {'name': 'foo', 'tag_name': 'baz', 'counters': [{'Bar': 'bar'}]}}})
    dd_run_check(check)

    tags = ['baz:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.foo.bar', 9000, metric_type=aggregator.GAUGE, tags=tags)

    aggregator.assert_all_metrics_covered()
