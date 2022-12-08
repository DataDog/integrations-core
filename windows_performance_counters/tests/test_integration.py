# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.windows_performance_counters import WindowsPerformanceCountersCheck

from .common import INSTANCE

pytestmark = pytest.mark.integration


def test(aggregator, dd_default_hostname, dd_run_check):
    check = WindowsPerformanceCountersCheck('windows_performance_counters', {}, [INSTANCE])
    check.hostname = dd_default_hostname
    static_tags = [f'machine:{dd_default_hostname}', 'foo:bar', 'bar:baz']

    num_threads = os.cpu_count()

    dd_run_check(check)
    dd_run_check(check)
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, count=2, tags=static_tags)
    aggregator.assert_metric(
        'test.num_cpu_threads.total', num_threads + 1, metric_type=aggregator.GAUGE, count=1, tags=static_tags
    )
    aggregator.assert_metric(
        'test.num_cpu_threads.monitored', num_threads, metric_type=aggregator.GAUGE, count=1, tags=static_tags
    )
    aggregator.assert_metric(
        'test.num_cpu_threads.unique', num_threads, metric_type=aggregator.GAUGE, count=1, tags=static_tags
    )

    dd_run_check(check)
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, count=3, tags=static_tags)
    aggregator.assert_metric(
        'test.num_cpu_threads.total', num_threads + 1, metric_type=aggregator.GAUGE, count=2, tags=static_tags
    )
    aggregator.assert_metric(
        'test.num_cpu_threads.monitored', num_threads, metric_type=aggregator.GAUGE, count=2, tags=static_tags
    )
    aggregator.assert_metric(
        'test.num_cpu_threads.unique', num_threads, metric_type=aggregator.GAUGE, count=2, tags=static_tags
    )

    for i in range(num_threads):
        tags = [f'thread:{i}']
        tags.extend(static_tags)
        aggregator.assert_metric('test.cpu.interrupts.ps', tags=tags)
        aggregator.assert_metric('test.core.user_time', tags=tags)

    aggregator.assert_all_metrics_covered()
