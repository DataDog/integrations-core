# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks import config
from datadog_checks.base.checks.openmetrics.v2.base import OpenMetricsBaseCheckV2


def test_alias():
    """
    Ensure we have an alias to import is_affirmative as _is_affirmative for
    backward compatibility with Agent 5.x
    """
    assert getattr(config, "_is_affirmative", None) is not None


def test_is_affirmative():
    assert config.is_affirmative(None) is False
    assert config.is_affirmative(0) is False
    assert config.is_affirmative("whatever, it could be 'off'") is False

    assert config.is_affirmative(1) is True
    assert config.is_affirmative('YES') is True
    assert config.is_affirmative('True') is True
    assert config.is_affirmative('On') is True
    assert config.is_affirmative('1') is True


def test_openmetrics_config():
    instance = {
        'openmetrics_endpoint': 'http://localhost:10249/metrics',
        'metrics': [{'metric1': 'renamed.metric1'}, 'metric2', 'counter1', 'counter2'],
    }
    check = OpenMetricsBaseCheckV2('openmetrics', {}, [instance])
    config = check.get_config_with_defaults(instance)
    assert config == ChainMap(
        {
            'metrics': [
                {
                    'go_gc_duration_seconds': 'go.gc.duration.seconds',
                    'go_goroutines': 'go.goroutines',
                    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash.sys_bytes',
                    'go_memstats_frees': 'go.memstats.frees',
                    'go_memstats_gc_cpu_fraction': 'go.memstats.gc.cpu_fraction',
                    'go_memstats_gc_sys_bytes': 'go.memstats.gc.sys_bytes',
                    'go_memstats_heap_alloc_bytes': 'go.memstats.heap.alloc_bytes',
                    'go_memstats_heap_idle_bytes': 'go.memstats.heap.idle_bytes',
                    'go_memstats_heap_inuse_bytes': 'go.memstats.heap.inuse_bytes',
                    'go_memstats_heap_objects': 'go.memstats.heap.objects',
                    'go_memstats_heap_released_bytes': 'go.memstats.heap.released_bytes',
                    'go_memstats_heap_sys_bytes': 'go.memstats.heap.sys_bytes',
                    'go_memstats_last_gc_time_seconds': 'go.memstats.last_gc_time.seconds',
                    'go_memstats_lookups': 'go.memstats.lookups',
                    'go_memstats_mallocs': 'go.memstats.mallocs',
                    'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache.inuse_bytes',
                    'go_memstats_mcache_sys_bytes': 'go.memstats.mcache.sys_bytes',
                    'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan.inuse_bytes',
                    'go_memstats_mspan_sys_bytes': 'go.memstats.mspan.sys_bytes',
                    'go_memstats_next_gc_bytes': 'go.memstats.next.gc_bytes',
                    'go_memstats_other_sys_bytes': 'go.memstats.other.sys_bytes',
                    'go_memstats_stack_inuse_bytes': 'go.memstats.stack.inuse_bytes',
                    'go_memstats_stack_sys_bytes': 'go.memstats.stack.sys_bytes',
                    'go_memstats_sys_bytes': 'go.memstats.sys_bytes',
                    'go_threads': 'go.threads',
                    'process_cpu_seconds': 'process.cpu.seconds',
                    'process_max_fds': 'process.max_fds',
                    'process_open_fds': 'process.open_fds',
                    'process_resident_memory_bytes': 'process.resident_memory.bytes',
                    'process_start_time_seconds': 'process.start_time.seconds',
                    'process_virtual_memory_bytes': 'process.virtual_memory.bytes',
                    'process_virtual_memory_max_bytes': 'process.virtual_memory.max_bytes',
                },
            ],
            'openmetrics_endpoint': 'http://localhost:10249/metrics',
        },
        {},
    )
