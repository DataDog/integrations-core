# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base.constants import ServiceCheck
from datadog_checks.dev.testing import requires_py3, requires_windows

from .utils import SERVER, get_check

pytestmark = [requires_py3, requires_windows]


def test(aggregator, dd_run_check):
    check = get_check(
        {
            'metrics': {
                'Processor': {
                    'name': 'cpu',
                    'tag_name': 'thread',
                    'instance_counts': {
                        'total': 'num_cpu_threads.total',
                        'monitored': 'num_cpu_threads.monitored',
                        'unique': 'num_cpu_threads.unique',
                    },
                    'counters': [{'Interrupts/sec': 'interrupts.ps', '% User Time': {'metric_name': 'core.user_time'}}],
                }
            },
            'server_tag': 'machine',
            'tags': ['foo:bar', 'bar:baz'],
        }
    )
    static_tags = ['machine:{}'.format(SERVER), 'foo:bar', 'bar:baz']

    num_threads = os.cpu_count()

    dd_run_check(check)
    aggregator.assert_service_check('test.windows.perf.health', ServiceCheck.OK, count=1, tags=static_tags)

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
        tags = ['thread:{}'.format(i)]
        tags.extend(static_tags)
        aggregator.assert_metric('test.cpu.interrupts.ps', tags=tags)
        aggregator.assert_metric('test.core.user_time', tags=tags)

    aggregator.assert_metric_has_tag('test.cpu.interrupts.ps', 'thread:_Total', count=0)
    aggregator.assert_metric_has_tag('test.core.user_time', 'thread:_Total', count=0)

    aggregator.assert_all_metrics_covered()
