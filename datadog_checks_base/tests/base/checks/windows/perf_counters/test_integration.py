# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

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


def test_multi_instance_counter_type(aggregator, dd_run_check):
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
                    'counters': [{'Interrupts/sec': 'interrupts.ps'}],
                }
            },
            'server_tag': 'machine',
        }
    )

    dd_run_check(check)
    dd_run_check(check)

    # Counter type detection provides an additional mechanism validating performance
    # counters based checks. Unfortunately Performance Counters/PDH code/classes do
    # not expose ways to check if the specified counters are actually single-instance
    # or multi-instance counters. But it can be determined indirectly by checking
    # generated metric tags. Metrics for multi-instance counters are additionally
    # tagged by tag_name:instance_name tags which are easy to test. Single-instance
    # counters do not have these instance-based tags.
    static_tags = ['machine:{}'.format(SERVER)]
    tags = ['thread:0']
    tags.extend(static_tags)
    aggregator.assert_metric('test.cpu.interrupts.ps', tags=tags)


def test_single_instance_counter_type(aggregator, dd_run_check):
    check = get_check(
        {
            'metrics': {
                'Memory': {
                    'name': 'mem',
                    'tag_name': 'memory',
                    'instance_counts': {
                        'total': 'memory.total',
                        'monitored': 'memory.monitored',
                        'unique': 'memory.unique',
                    },
                    'counters': [{'Page Reads/sec': 'page_reads_per_second'}],
                }
            },
            'server_tag': 'machine',
        }
    )
    dd_run_check(check)
    dd_run_check(check)

    # Counter type detection provides an additional mechanism validating performance
    # counters based checks. Unfortunately Performance Counters/PDH code/classes do
    # not expose ways to check if the specified counters are actually single-instance
    # or multi-instance counters. But it can be determined indirectly by checking
    # generated metric tags. Metrics for multi-instance counters are additionally
    # tagged by tag_name:instance_name tags which are easy to test. Single-instance
    # counters do not have these instance-based tags.
    static_tags = ['machine:{}'.format(SERVER)]
    aggregator.assert_metric('test.mem.page_reads_per_second', tags=static_tags)


def test_multi_instance_counter_invalid_data_error_handling(aggregator, dd_run_check):
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
                    'counters': [{'Interrupts/sec': 'interrupts.ps'}],
                }
            },
            'server_tag': 'machine',
        }
    )

    log_debug_call = mock.call(
        'Waiting on another data point for counter `%s` of performance object `%s`', 'Interrupts/sec', 'Processor'
    )

    check.log = mock.MagicMock()

    # First time the check is called it should call log.debug "Waiting on another data point for counter xxx"
    check.log.reset_mock()
    dd_run_check(check)
    check.log.debug.assert_has_calls([log_debug_call])

    # ... second time it is called no log.debug "Waiting on another data point for counter xxx" should be invoked
    check.log.reset_mock()
    dd_run_check(check)
    for mock_call in check.log.debug.mock_calls:
        assert not mock_call == log_debug_call

    # ... and thrid or more time it is called no log.debug "Waiting on another data point for counter xxx" should
    # be invoked
    check.log.reset_mock()
    dd_run_check(check)
    for mock_call in check.log.debug.mock_calls:
        assert not mock_call == log_debug_call


def test_single_instance_counter_invalid_data_error_handling(aggregator, dd_run_check):
    check = get_check(
        {
            'metrics': {
                'Memory': {
                    'name': 'mem',
                    'tag_name': 'memory',
                    'instance_counts': {
                        'total': 'memory.total',
                        'monitored': 'memory.monitored',
                        'unique': 'memory.unique',
                    },
                    'counters': [{'Page Reads/sec': 'page_reads_per_second'}],
                }
            },
            'server_tag': 'machine',
        }
    )

    log_debug_call = mock.call(
        'Waiting on another data point for counter `%s` of performance object `%s`', 'Page Reads/sec', 'Memory'
    )

    check.log = mock.MagicMock()

    # First time the check is called it should call log.debug "Waiting on another data point for counter xxx"
    check.log.reset_mock()
    dd_run_check(check)
    check.log.debug.assert_has_calls([log_debug_call])

    # ... second time it is called no log.debug "Waiting on another data point for counter xxx" should be invoked
    check.log.reset_mock()
    dd_run_check(check)
    for mock_call in check.log.debug.mock_calls:
        assert not mock_call == log_debug_call

    # ... and thrid or more time it is called no log.debug "Waiting on another data point for counter xxx" should
    # be invoked
    check.log.reset_mock()
    dd_run_check(check)
    for mock_call in check.log.debug.mock_calls:
        assert not mock_call == log_debug_call


def test_skip_typo_counter(aggregator, dd_run_check):
    # Run correctly configured check
    check = get_check(
        {
            'metrics': {
                'Memory': {
                    'name': 'mem',
                    'tag_name': 'memory',
                    'instance_counts': {
                        'total': 'memory.total',
                        'monitored': 'memory.monitored',
                        'unique': 'memory.unique',
                    },
                    'counters': [
                        {'Available Bytes': 'available_bytes'},
                        {'Committed Bytes': 'committed_bytes'},
                        {'Commit Limit': 'commit_limit'},
                    ],
                }
            },
            'server_tag': 'machine',
        }
    )

    dd_run_check(check)
    aggregator.assert_metric('test.mem.available_bytes')
    aggregator.assert_metric('test.mem.committed_bytes')
    aggregator.assert_metric('test.mem.commit_limit')

    # Run check with typo. Typo has to be first, before the fix
    # the following after typo counters metrics had not been collected
    aggregator.reset()
    check = get_check(
        {
            'metrics': {
                'Memory': {
                    'name': 'mem',
                    'tag_name': 'memory',
                    'instance_counts': {
                        'total': 'memory.total',
                        'monitored': 'memory.monitored',
                        'unique': 'memory.unique',
                    },
                    'counters': [
                        {'Foo': 'foo'},
                        {'Available Bytes': 'available_bytes'},
                        {'Committed Bytes': 'committed_bytes'},
                        {'Commit Limit': 'commit_limit'},
                    ],
                }
            },
            'server_tag': 'machine',
        }
    )

    dd_run_check(check)
    aggregator.assert_metric('test.mem.available_bytes')
    aggregator.assert_metric('test.mem.committed_bytes')
    aggregator.assert_metric('test.mem.commit_limit')


def test_validate_counter_names_sensitivity(aggregator, dd_run_check):
    # Run check with different counter names of different casing to make sure
    # the check is not affected since Windows Performance counters API
    # are case insensitive.
    aggregator.reset()
    check = get_check(
        {
            'metrics': {
                'mEmOrY': {
                    'name': 'mem',
                    'tag_name': 'memory',
                    'instance_counts': {
                        'total': 'memory.total',
                        'monitored': 'memory.monitored',
                        'unique': 'memory.unique',
                    },
                    'counters': [
                        {'available bytes': 'available_bytes'},
                        {'committeD byteS': 'committed_bytes'},
                        {'cOmMiT lImIt': 'commit_limit'},
                    ],
                }
            },
            'server_tag': 'machine',
        }
    )

    dd_run_check(check)
    aggregator.assert_metric('test.mem.available_bytes')
    aggregator.assert_metric('test.mem.committed_bytes')
    aggregator.assert_metric('test.mem.commit_limit')
