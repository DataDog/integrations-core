# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import PerfCountersBaseCheck
from datadog_checks.base.constants import ServiceCheck
from datadog_checks.windows_performance_counters import WindowsPerformanceCountersCheck

pytestmark = pytest.mark.unit


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
