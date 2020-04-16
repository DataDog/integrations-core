# (C) Datadog, Inc. 2020 - Present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


GENERIC_METRICS = {
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


CITADEL_METRICS = {
    'citadel_secret_controller_csr_err_count': 'secret_controller.csr_err_count',
    'citadel_secret_controller_secret_deleted_cert_count': ('secret_controller.secret_deleted_cert_count'),
    'citadel_secret_controller_svc_acc_created_cert_count': ('secret_controller.svc_acc_created_cert_count'),
    'citadel_secret_controller_svc_acc_deleted_cert_count': ('secret_controller.svc_acc_deleted_cert_count'),
    'citadel_server_authentication_failure_count': 'server.authentication_failure_count',
    'citadel_server_citadel_root_cert_expiry_timestamp': ('server.citadel_root_cert_expiry_timestamp'),
    'citadel_server_csr_count': 'server.csr_count',
    'citadel_server_csr_parsing_err_count': 'server.csr_parsing_err_count',
    'citadel_server_id_extraction_err_count': 'server.id_extraction_err_count',
    'citadel_server_success_cert_issuance_count': 'server.success_cert_issuance_count',
    'citadel_server_root_cert_expiry_timestamp': 'server.root_cert_expiry_timestamp',
}


GALLEY_METRICS = {
    'endpoint_no_pod': 'endpoint_no_pod',
    'galley_mcp_source_clients_total': 'mcp_source.clients_total',
    'galley_runtime_processor_event_span_duration_milliseconds': ('runtime_processor.event_span_duration_milliseconds'),
    'galley_runtime_processor_events_processed_total': 'runtime_processor.events_processed_total',
    'galley_runtime_processor_snapshot_events_total': 'runtime_processor.snapshot_events_total',
    'galley_runtime_processor_snapshot_lifetime_duration_milliseconds': (
        'runtime_processor.snapshot_lifetime_duration_milliseconds'
    ),
    'galley_runtime_processor_snapshots_published_total': ('runtime_processor.snapshots_published_total'),
    'galley_runtime_state_type_instances_total': 'runtime_state_type_instances_total',
    'galley_runtime_strategy_on_change_total': 'runtime_strategy.on_change_total',
    'galley_runtime_strategy_timer_max_time_reached_total': ('runtime_strategy.timer_max_time_reached_total'),
    'galley_runtime_strategy_timer_quiesce_reached_total': 'runtime_strategy.quiesce_reached_total',
    'galley_runtime_strategy_timer_resets_total': 'runtime_strategy.timer_resets_total',
    'galley_source_kube_dynamic_converter_success_total': ('source_kube.dynamic_converter_success_total'),
    'galley_source_kube_event_success_total': 'source_kube.event_success_total',
    'galley_validation_cert_key_updates': 'validation.cert_key_updates',
    'galley_validation_config_load': 'validation.config_load',
    'galley_validation_config_updates': 'validation.config_update',
    'galley_validation_passed': 'validation.passed',
}


MESH_METRICS = {
    # These metrics support Istio 1.0
    'istio_requests_total': 'request.count',
    'istio_request_duration_seconds': 'request.duration',
    'istio_request_bytes': 'request.size',
    'istio_response_bytes': 'response.size',
    # These metrics support Istio 0.8
    'istio_request_count': 'request.count',
    'istio_request_duration': 'request.duration',
    'istio_request_size': 'request.size',
    'istio_response_size': 'response.size',
}


MIXER_METRICS = {
    # Pre 1.1 metrics
    'grpc_server_handled_total': 'grpc.server.handled_total',
    'grpc_server_handling_seconds': 'grpc.server.handling_seconds',
    'grpc_server_msg_received_total': 'grpc.server.msg_received_total',
    'grpc_server_msg_sent_total': 'grpc.server.msg_sent_total',
    'grpc_server_started_total': 'grpc.server.started_total',
    'mixer_adapter_dispatch_count': 'adapter.dispatch_count',
    'mixer_adapter_dispatch_duration': 'adapter.dispatch_duration',
    'mixer_adapter_old_dispatch_count': 'adapter.old_dispatch_count',
    'mixer_adapter_old_dispatch_duration': 'adapter.old_dispatch_duration',
    'mixer_config_resolve_actions': 'config.resolve_actions',
    'mixer_config_resolve_count': 'config.resolve_count',
    'mixer_config_resolve_duration': 'config.resolve_duration',
    'mixer_config_resolve_rules': 'config.resolve_rules',
    # 1.1 metrics
    'grpc_io_server_completed_rpcs': 'grpc_io_server.completed_rpcs',
    'grpc_io_server_received_bytes_per_rpc': 'grpc_io_server.received_bytes_per_rpc',
    'grpc_io_server_sent_bytes_per_rpc': 'grpc_io_server.sent_bytes_per_rpc',
    'grpc_io_server_server_latency': 'grpc_io_server.server_latency',
    'mixer_config_attributes_total': 'config.attributes_total',
    'mixer_config_handler_configs_total': 'config.handler_configs_total',
    'mixer_config_instance_configs_total': 'config.instance_configs_total',
    'mixer_config_rule_configs_total': 'config.rule_configs_total',
    'mixer_dispatcher_destinations_per_request': 'dispatcher.destinations_per_request',
    'mixer_dispatcher_instances_per_request': 'dispatcher.instances_per_request',
    'mixer_handler_daemons_total': 'handler.daemons_total',
    'mixer_handler_new_handlers_total': 'handler.new_handlers_total',
    'mixer_mcp_sink_reconnections': 'mcp_sink.reconnections',
    'mixer_mcp_sink_request_acks_total': 'mcp_sink.request_acks_total',
    'mixer_runtime_dispatches_total': 'runtime.dispatches_total',
    'mixer_runtime_dispatch_duration_seconds': 'runtime.dispatch_duration_seconds',
}

PILOT_METRICS = {
    'pilot_conflict_inbound_listener': 'conflict.inbound_listener',
    'pilot_conflict_outbound_listener_http_over_current_tcp': ('conflict.outbound_listener.http_over_current_tcp'),
    'pilot_conflict_outbound_listener_tcp_over_current_http': ('conflict.outbound_listener.tcp_over_current_http'),
    'pilot_conflict_outbound_listener_tcp_over_current_tcp': ('conflict.outbound_listener.tcp_over_current_tcp'),
    'pilot_destrule_subsets': 'destrule_subsets',
    'pilot_duplicate_envoy_clusters': 'duplicate_envoy_clusters',
    'pilot_eds_no_instances': 'eds_no_instances',
    'pilot_endpoint_not_ready': 'endpoint_not_ready',
    'pilot_invalid_out_listeners': 'invalid_out_listeners',
    'pilot_mcp_sink_reconnections': 'mcp_sink.reconnections',
    'pilot_mcp_sink_recv_failures_total': 'mcp_sink.recv_failures_total',
    'pilot_mcp_sink_request_acks_total': 'mcp_sink.request_acks_total',
    'pilot_no_ip': 'no_ip',
    'pilot_proxy_convergence_time': 'proxy_convergence_time',
    'pilot_rds_expired_nonce': 'rds_expired_nonce',
    'pilot_services': 'services',
    'pilot_total_xds_internal_errors': 'total_xds_internal_errors',
    'pilot_total_xds_rejects': 'total_xds_rejects',
    'pilot_virt_services': 'virt_services',
    'pilot_vservice_dup_domain': 'vservice_dup_domain',
    'pilot_xds': 'xds',
    'pilot_xds_eds_instances': 'xds.eds_instances',
    'pilot_xds_push_context_errors': 'xds.push.context_errors',
    'pilot_xds_push_timeout': 'xds.push.timeout',
    'pilot_xds_push_timeout_failures': 'xds.push.timeout_failures',
    'pilot_xds_pushes': 'xds.pushes',
    'pilot_xds_write_timeout': 'xds.write_timeout',
}
