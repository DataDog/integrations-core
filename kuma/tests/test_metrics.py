# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


HISTOGRAM_METRICS = [
    'api_server.http_request_duration_seconds',
    'api_server.http_response_size_bytes',
    'controller_runtime.reconcile.time_seconds',
    'controller_runtime.webhook.latency_seconds',
    'dp_server.http_request_duration_seconds',
    'dp_server.http_response_size_bytes',
    'grpc.server.handling_seconds',
    'store',
    'workqueue.queue_duration_seconds',
    'workqueue.work_duration_seconds',
]

SUMMARY_METRICS = [
    'ca_manager.get_cert',
    'ca_manager.get_root_cert_chain',
    'component.catalog_writer',
    'component.heartbeat',
    'component.hostname_generator',
    'component.ms_status_updater',
    'component.mzms_status_updater',
    'component.store_counter',
    'component.sub_finalizer',
    'component.vip_allocator',
    'component.zone_available_services',
    'go.gc.duration_seconds',
    'insights_resyncer.event_time_processing',
    'insights_resyncer.event_time_to_process',
    'insights_resyncer.processor_idle_time',
    'vip_generation',
    'xds.delivery',
    'xds.generation',
]

GAUGE_METRICS = [
    'api_server.http_requests_inflight',
    'cla_cache',
    'controller_runtime.active_workers',
    'controller_runtime.max_concurrent_reconciles',
    'controller_runtime.webhook.requests_in_flight',
    'cp_info',
    'dp_server.http_requests_inflight',
    'go.goroutines',
    'go.memstats.alloc_bytes',
    'go.threads',
    'leader',
    'leader_election.master_status',
    'mesh_cache',
    'process.max_fds',
    'process.open_fds',
    'process.resident_memory_bytes',
    'process.start_time_seconds',
    'process.virtual_memory_bytes',
    'process.virtual_memory_max_bytes',
    'promhttp.metric_handler.requests_in_flight',
    'resources_count',
    'workqueue.depth',
    'workqueue.longest_running_processor_seconds',
    'workqueue.unfinished_work_seconds',
    'xds.streams_active',
]

# We know that these metrics are present in the control plane regardless of timing or activity.
GAUGE_METRICS_E2E = [
    'cp_info',
    'leader',
]

COUNTER_METRICS = [
    'cert_generation',
    'certwatcher.read_certificate.errors_total',
    'certwatcher.read_certificate.total',
    'controller_runtime.reconcile.errors_total',
    'controller_runtime.reconcile.panics_total',
    'controller_runtime.reconcile.total',
    'controller_runtime.terminal_reconcile.errors_total',
    'controller_runtime.webhook.panics_total',
    'controller_runtime.webhook.requests_total',
    'events.dropped',
    'grpc.server.handled_total',
    'grpc.server.msg_received_total',
    'grpc.server.msg_sent_total',
    'grpc.server.started_total',
    'process.cpu_seconds_total',
    'process.network.receive_bytes_total',
    'process.network.transmit_bytes_total',
    'promhttp.metric_handler.requests_total',
    'rest_client.requests_total',
    'store_cache',
    'store_conflicts',
    'vip_generation_errors',
    'workqueue.adds_total',
    'workqueue.retries_total',
    'xds.generation_errors',
    'xds.requests_received',
    'xds.responses_sent',
]
