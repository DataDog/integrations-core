# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import GLOBAL_TAGS, SERVER

try:
    from datadog_checks.base.checks.windows.perf_counters.base import PerfCountersBaseCheckWithLegacySupport
# non-Windows systems
except Exception:
    PerfCountersBaseCheckWithLegacySupport = object

pytestmark = [requires_py3, requires_windows]


class CustomCheck(PerfCountersBaseCheckWithLegacySupport):
    __NAMESPACE__ = 'test'

    def get_default_config(self):
        return {'metrics': {'Baz': {'name': 'baz', 'counters': [{'Bar': {'name': 'bar', 'type': 'count'}}]}}}


def test(aggregator, dd_run_check, mock_performance_objects, caplog):
    mock_performance_objects(
        {
            'Foo': (['instance1', 'instance2'], {'Bar': [9000, 42]}),
            'Bar': (['instance1', 'instance2'], {'Baz': [9000, 42], 'Foo': [9000, 1984]}),
            'Baz': (['instance1'], {'Bar': [3.14]}),
        }
    )
    instance = {
        'host': SERVER,
        'additional_metrics': [
            ['Foo', None, 'Bar', 'foo.bar', 'gauge'],
            ['Bar', 'instance1', 'Baz', 'bar.baz', 'monotonic_count'],
            ['Bar', 'instance2', 'Foo', 'bar.foo', 'rate'],
        ],
    }
    check = CustomCheck('test', {}, [instance])
    check.hostname = instance['host']
    dd_run_check(check)
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=GLOBAL_TAGS)

    tags = ['instance:instance1']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('test.baz.bar', 3.14, metric_type=aggregator.COUNT, tags=tags)
    aggregator.assert_metric('foo.bar', 9000, metric_type=aggregator.GAUGE, tags=tags)
    aggregator.assert_metric('bar.baz', 9000, metric_type=aggregator.MONOTONIC_COUNT, tags=tags)

    tags = ['instance:instance2']
    tags.extend(GLOBAL_TAGS)
    aggregator.assert_metric('foo.bar', 42, metric_type=aggregator.GAUGE, tags=tags)
    aggregator.assert_metric('bar.foo', 1984, metric_type=aggregator.RATE, tags=tags)

    aggregator.assert_all_metrics_covered()

    for i in (2, 3):
        expected_message = 'Ignoring instance for entry #{} of option `additional_metrics`'.format(i)
        for _, level, message in caplog.record_tuples:
            if level == logging.WARNING and message == expected_message:
                break
        else:
            raise AssertionError('Expected WARNING log with message `{}`'.format(expected_message))
