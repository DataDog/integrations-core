# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import PerfCountersBaseCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.windows_performance_counters import WindowsPerformanceCountersCheck

from .common import INSTANCE


def test_subclass():
    assert issubclass(WindowsPerformanceCountersCheck, PerfCountersBaseCheck)


def test_basic(aggregator, dd_default_hostname, dd_run_check, mock_performance_objects):
    mock_performance_objects({'Foo': (['baz'], {'Bar': [9000]})})

    instance = {'namespace': 'test', 'metrics': {'Foo': {'name': 'foo', 'counters': [{'Bar': 'bar'}]}}}
    check = WindowsPerformanceCountersCheck('windows_performance_counters', {}, [instance])
    check.hostname = dd_default_hostname
    dd_run_check(check)

    static_tags = [f'server:{dd_default_hostname}']
    tags = ['instance:baz']
    tags.extend(static_tags)
    aggregator.assert_metric('test.foo.bar', 9000, tags=tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, tags=static_tags)


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)

    num_threads = 1

    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK)
    aggregator.assert_metric('test.num_cpu_threads.total', num_threads + 1)
    aggregator.assert_metric('test.num_cpu_threads.monitored', num_threads)
    aggregator.assert_metric('test.num_cpu_threads.unique', num_threads)

    for i in range(num_threads):
        for metric in ('test.cpu.interrupts.ps', 'test.core.user_time'):
            aggregator.assert_metric_has_tag(metric, f'thread:{i}')
            aggregator.assert_metric_has_tag(metric, 'foo:bar')
            aggregator.assert_metric_has_tag(metric, 'bar:baz')

    aggregator.assert_all_metrics_covered()
