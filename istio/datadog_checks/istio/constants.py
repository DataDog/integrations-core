# (C) Datadog, Inc. 2020 - Present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# Istio namespaces
MIXER_NAMESPACE = 'istio.mixer'
MESH_NAMESPACE = 'istio.mesh'
PILOT_NAMESPACE = 'istio.pilot'
GALLEY_NAMESPACE = 'istio.galley'
CITADEL_NAMESPACE = 'istio.citadel'

DEFAULT_METRIC_LIMIT = 0


@staticmethod
def _get_generic_metrics():
    return {
        'go_gc_duration_seconds': 'go.gc_duration_seconds',
        'go_goroutines': 'go.goroutines',
        'go_info': 'go.info',
        'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
        'go_memstats_alloc_bytes_total': 'go.memstats.alloc_bytes_total',
        'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash_sys_bytes',
        'go_memstats_frees_total': 'go.memstats.frees_total',
        'go_memstats_gc_cpu_fraction': 'go.memstats.gc_cpu_fraction',
        'go_memstats_gc_sys_bytes': 'go.memstats.gc_sys_bytes',
        'go_memstats_heap_alloc_bytes': 'go.memstats.heap_alloc_bytes',
        'go_memstats_heap_idle_bytes': 'go.memstats.heap_idle_bytes',
        'go_memstats_heap_inuse_bytes': 'go.memstats.heap_inuse_bytes',
        'go_memstats_heap_objects': 'go.memstats.heap_objects',
        'go_memstats_heap_released_bytes': 'go.memstats.heap_released_bytes',
        'go_memstats_heap_sys_bytes': 'go.memstats.heap_sys_bytes',
        'go_memstats_last_gc_time_seconds': 'go.memstats.last_gc_time_seconds',
        'go_memstats_lookups_total': 'go.memstats.lookups_total',
        'go_memstats_mallocs_total': 'go.memstats.mallocs_total',
        'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache_inuse_bytes',
        'go_memstats_mcache_sys_bytes': 'go.memstats.mcache_sys_bytes',
        'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan_inuse_bytes',
        'go_memstats_mspan_sys_bytes': 'go.memstats.mspan_sys_bytes',
        'go_memstats_next_gc_bytes': 'go.memstats.next_gc_bytes',
        'go_memstats_other_sys_bytes': 'go.memstats.other_sys_bytes',
        'go_memstats_stack_inuse_bytes': 'go.memstats.stack_inuse_bytes',
        'go_memstats_stack_sys_bytes': 'go.memstats.stack_sys_bytes',
        'go_memstats_sys_bytes': 'go.memstats.sys_bytes',
        'go_threads': 'go.threads',
        'process_cpu_seconds_total': 'process.cpu_seconds_total',
        'process_max_fds': 'process.max_fds',
        'process_open_fds': 'process.open_fds',
        'process_resident_memory_bytes': 'process.resident_memory_bytes',
        'process_start_time_seconds': 'process.start_time_seconds',
        'process_virtual_memory_bytes': 'process.virtual_memory_bytes',
    }
