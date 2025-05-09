# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD st/trale license (see LICENSE)

gauges_counters = {
    'api_server_http_requests_inflight': 'api_server.http.requests_inflight',
    'certwatcher_read_certificate_errors_total': 'certwatcher.read_certificate.errors_total',
    'certwatcher_read_certificate_total': 'certwatcher.read_certificate.total',
    'controller_runtime_active_workers': 'controller_runtime.active_workers',
    'controller_runtime_max_concurrent_reconciles': 'controller_runtime.max_concurrent_reconciles',
    'controller_runtime_reconcile_errors_total': 'controller_runtime.reconcile_errors_total',
    'controller_runtime_reconcile_panics_total': 'controller_runtime.reconcile_panics_total',
    'controller_runtime_terminal_reconcile_errors_total': 'controller_runtime.terminal_reconcile_errors_total',
    'go_goroutines': 'go.goroutines',
    'go_threads': 'go.threads',
    'leader': 'leader.status',
    'leader_election_master_status': 'leader_election.master_status',
    'process_cpu_seconds_total': 'process.cpu.seconds_total',
    'process_resident_memory_bytes': 'process.resident_memory.bytes',
    'process_virtual_memory_bytes': 'process.virtual_memory.bytes',
    'process_virtual_memory_max_bytes': 'process.virtual_memory.max_bytes',
}

summaries = {
    'api_server_http_request_duration_seconds': 'api_server.http.request_duration.seconds',
    'api_server_http_response_size_bytes': 'api_server.http.response_size.bytes',
    'component_catalog_writer': 'component.catalog_writer',
    'component_heartbeat': 'component.heartbeat',
    'component_hostname_generator': 'component.hostname_generator',
    'component_ms_status_updater': 'component.ms_status_updater',
    'component_mzms_status_updater': 'component.mzms_status_updater',
    'component_store_counter': 'component.store_counter',
    'component_sub_finalizer': 'component.sub_finalizer',
    'component_vip_allocator': 'component.vip_allocator',
    'component_zone_available_services': 'component.zone_available_services',
    'controller_runtime_reconcile_time_seconds': 'controller_runtime.reconcile_time.seconds',
    'controller_runtime_webhook_latency_seconds': 'controller_runtime.webhook_latency.seconds',
    'controller_runtime_webhook_requests_total': 'controller_runtime.webhook_requests.total',
    'store': 'store.operations',
}

METRIC_MAP = {**gauges_counters, **summaries}
RENAME_LABELS_MAP = {
    'service': 'kubernetes_service'
}
