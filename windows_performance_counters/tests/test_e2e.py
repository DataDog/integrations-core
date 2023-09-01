# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import subprocess

import pytest

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.utils import get_active_env

from .common import INSTANCE

pytestmark = pytest.mark.e2e


def test(dd_agent_check):
    aggregator = dd_agent_check(INSTANCE, rate=True)

    container_name = f'dd_windows_performance_counters_{get_active_env()}'
    python_path = r'C:\Program Files\Datadog\Datadog Agent\embedded3\python.exe'
    num_threads = subprocess.check_output(
        ['docker', 'exec', container_name, python_path, '-c', 'import os;print(os.cpu_count())'],
        text=True,
    ).strip()
    num_threads = int(num_threads)

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
