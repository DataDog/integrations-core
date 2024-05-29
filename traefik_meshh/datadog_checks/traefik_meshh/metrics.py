# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


METRIC_MAP = {
    # General Metrics
    'go_info': 'go.info',
    'go_gc_duration_seconds': 'go.gc.duration.seconds',
    'go_goroutines': 'go.goroutines',
    'go_memstats_alloc_bytes': {'name': 'go.memstats.alloc_bytes', 'type': 'native_dynamic'},
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
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#global-metrics
    'traefik_config_last_reload_failure': 'config.last_reload.failure',
    'traefik_config_last_reload_success': 'config.last_reload.success',
    'traefik_config_reloads': 'config.reloads',
    'traefik_config_reloads_failure': 'config.reloads.failure',
    'traefik_tls_certs_not_after': 'tls.certs.not_after',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#entrypoint-metrics
    'traefik_entrypoint_open_connections': 'entrypoint.open_connections',
    'traefik_entrypoint_request_duration_seconds': 'entrypoint.request.duration.seconds',
    'traefik_entrypoint_requests': 'entrypoint.requests',
    'traefik_entrypoint_requests_bytes': 'entrypoint.requests.bytes',
    'traefik_entrypoint_requests_tls': 'entrypoint.requests.tls',
    'traefik_entrypoint_responses_bytes': 'entrypoint.responses.bytes',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#router-metrics
    'traefik_router_open_connections': 'router.open_connections',
    'traefik_router_request_duration_seconds': 'router.request.duration.seconds',
    'traefik_router_requests_bytes': 'router.requests.bytes',
    'traefik_router_requests': 'router.requests',
    'traefik_router_requests_tls': 'router.requests.tls',
    'traefik_router_responses_bytes': 'router.responses.bytes',
    # https://doc.traefik.io/traefik/v2.11/observability/metrics/overview/#service-metrics
    'traefik_service_open_connections': 'service.open_connections',
    'traefik_service_request_duration_seconds': 'service.request.duration.seconds',
    'traefik_service_requests': 'service.requests',
    'traefik_service_requests_tls': 'service.requests.tls',
    'traefik_service_requests_bytes': 'service.requests.bytes',
    'traefik_service_responses_bytes': 'service.responses.bytes',
    'traefik_service_retries': 'service.retries',
    'traefik_service_server_up': 'service.server.up',
}

RENAME_LABELS = {
    'version': 'go_version',
    'service': 'traefik_service',
}
