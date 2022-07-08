# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3, requires_windows

from ..utils import GLOBAL_TAGS, get_check

pytestmark = [requires_py3, requires_windows]


def test_known(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [3.0]})})
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'baz',
                    'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': {'3': 'ok'}}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['baz:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_service_check('test.foo.bar', ServiceCheck.OK, tags=tags)

    aggregator.assert_all_metrics_covered()


def test_unknown(aggregator, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['instance1'], {'Bar': [3.0]})})
    check = get_check(
        {
            'metrics': {
                'Foo': {
                    'name': 'foo',
                    'tag_name': 'baz',
                    'counters': [{'Bar': {'name': 'bar', 'type': 'service_check', 'status_map': {'7': 'ok'}}}],
                }
            }
        }
    )
    dd_run_check(check)

    tags = ['baz:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_service_check('test.foo.bar', ServiceCheck.UNKNOWN, tags=tags)

    aggregator.assert_all_metrics_covered()
