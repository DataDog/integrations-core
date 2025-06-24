# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

METRIC_MAP = {
    "api_server_http_request_duration_seconds": "api_server.http_request_duration_seconds",  # histogram
    "api_server_http_requests_inflight": "api_server.http_requests_inflight",  # gauge
    "api_server_http_response_size_bytes": "api_server.http_response_size_bytes",  # histogram
    "ca_manager_get_cert": "ca_manager.get_cert",  # summary
    "ca_manager_get_root_cert_chain": "ca_manager.get_root_cert_chain",  # summary
    "cert_generation": "cert_generation",  # counter
    "certwatcher_read_certificate_errors": "certwatcher.read_certificate.errors_total",  # counter
    "certwatcher_read_certificate": "certwatcher.read_certificate.total",  # counter
    "cla_cache": "cla_cache",  # gauge
    "component_catalog_writer": "component.catalog_writer",  # summary
    "component_heartbeat": "component.heartbeat",  # summary
    "component_hostname_generator": "component.hostname_generator",  # summary
    "component_ms_status_updater": "component.ms_status_updater",  # summary
    "component_mzms_status_updater": "component.mzms_status_updater",  # summary
    "component_store_counter": "component.store_counter",  # summary
    "component_sub_finalizer": "component.sub_finalizer",  # summary
    "component_vip_allocator": "component.vip_allocator",  # summary
    "component_zone_available_services": "component.zone_available_services",  # summary
    "controller_runtime_active_workers": "controller_runtime.active_workers",  # gauge
    "controller_runtime_max_concurrent_reconciles": "controller_runtime.max_concurrent_reconciles",  # gauge
    "controller_runtime_reconcile_errors": "controller_runtime.reconcile.errors_total",  # counter
    "controller_runtime_reconcile_panics": "controller_runtime.reconcile.panics_total",  # counter
    "controller_runtime_reconcile_time_seconds": "controller_runtime.reconcile.time_seconds",  # histogram
    "controller_runtime_reconcile": "controller_runtime.reconcile.total",  # counter
    "controller_runtime_terminal_reconcile_errors": "controller_runtime.terminal_reconcile.errors_total",  # counter # noqa: E501
    "controller_runtime_webhook_latency_seconds": "controller_runtime.webhook.latency_seconds",  # histogram
    "controller_runtime_webhook_panics": "controller_runtime.webhook.panics_total",  # counter
    "controller_runtime_webhook_requests_in_flight": "controller_runtime.webhook.requests_in_flight",  # gauge
    "controller_runtime_webhook_requests": "controller_runtime.webhook.requests_total",  # counter
    "cp_info": "cp_info",  # gauge
    "dp_server_http_request_duration_seconds": "dp_server.http_request_duration_seconds",  # histogram
    "dp_server_http_requests_inflight": "dp_server.http_requests_inflight",  # gauge
    "dp_server_http_response_size_bytes": "dp_server.http_response_size_bytes",  # histogram
    "events_dropped": "events.dropped",  # counter
    "go_gc_duration_seconds": "go.gc.duration_seconds",  # summary
    "go_goroutines": "go.goroutines",  # gauge
    "go_memstats_alloc_bytes": "go.memstats.alloc_bytes",  # gauge
    "go_threads": "go.threads",  # gauge
    "grpc_server_handled": "grpc.server.handled_total",  # counter
    "grpc_server_handling_seconds": "grpc.server.handling_seconds",  # histogram
    "grpc_server_msg_received": "grpc.server.msg_received_total",  # counter
    "grpc_server_msg_sent": "grpc.server.msg_sent_total",  # counter
    "grpc_server_started": "grpc.server.started_total",  # counter
    "insights_resyncer_event_time_processing": "insights_resyncer.event_time_processing",  # summary
    "insights_resyncer_event_time_to_process": "insights_resyncer.event_time_to_process",  # summary
    "insights_resyncer_processor_idle_time": "insights_resyncer.processor_idle_time",  # summary
    "leader": "leader",  # gauge
    "leader_election_master_status": "leader_election.master_status",  # gauge
    "mesh_cache": "mesh_cache",  # gauge
    "process_cpu_seconds": "process.cpu_seconds_total",  # counter
    "process_max_fds": "process.max_fds",  # gauge
    "process_network_receive_bytes": "process.network.receive_bytes_total",  # counter
    "process_network_transmit_bytes": "process.network.transmit_bytes_total",  # counter
    "process_open_fds": "process.open_fds",  # gauge
    "process_resident_memory_bytes": "process.resident_memory_bytes",  # gauge
    "process_start_time_seconds": "process.start_time_seconds",  # gauge
    "process_virtual_memory_bytes": "process.virtual_memory_bytes",  # gauge
    "process_virtual_memory_max_bytes": "process.virtual_memory_max_bytes",  # gauge
    "promhttp_metric_handler_requests_in_flight": "promhttp.metric_handler.requests_in_flight",  # gauge
    "promhttp_metric_handler_requests": "promhttp.metric_handler.requests_total",  # counter
    "resources_count": "resources_count",  # gauge
    "rest_client_requests": "rest_client.requests_total",  # counter
    "store": "store",  # histogram
    "store_cache": "store_cache",  # counter
    "store_conflicts": "store_conflicts",  # counter
    "vip_generation": "vip_generation",  # summary
    "vip_generation_errors": "vip_generation_errors",  # counter
    "workqueue_adds": "workqueue.adds_total",  # counter
    "workqueue_depth": "workqueue.depth",  # gauge
    "workqueue_longest_running_processor_seconds": "workqueue.longest_running_processor_seconds",  # gauge
    "workqueue_queue_duration_seconds": "workqueue.queue_duration_seconds",  # histogram
    "workqueue_retries": "workqueue.retries_total",  # counter
    "workqueue_unfinished_work_seconds": "workqueue.unfinished_work_seconds",  # gauge
    "workqueue_work_duration_seconds": "workqueue.work_duration_seconds",  # histogram
    "xds_delivery": "xds.delivery",  # summary
    "xds_generation": "xds.generation",  # summary
    "xds_generation_errors": "xds.generation_errors",  # counter
    "xds_requests_received": "xds.requests_received",  # counter
    "xds_responses_sent": "xds.responses_sent",  # counter
    "xds_streams_active": "xds.streams_active",  # gauge
}

RENAME_LABELS_MAP = {
    "service": "kubernetes_service",
    "cluster_id": "kuma_cluster_id",
    "version": "kuma_version",
    "host": "kuma_host",
}
