# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD st/trale license (see LICENSE)

METRIC_MAP = {
    'api_server_http_request_duration_seconds': 'api_server.http_request_duration_seconds', # Must enable percentiles
    'api_server_http_requests_inflight': 'api_server.http_requests_inflight',
    'api_server_http_response_size_bytes': 'api_server.http_response_size_bytes',
    'ca_manager_get_cert': 'ca_manager.get_cert',
    'ca_manager_get_root_cert_chain': 'ca_manager.get_root_cert_chain',
    'cert_generation': 'cert_generation',
    'certwatcher_read_certificate_errors_total': 'certwatcher.read_certificate.errors_total',
    'certwatcher_read_certificate_total': 'certwatcher.read_certificate.total',
    'cla_cache': 'cla_cache',
    'component_catalog_writer': 'component.catalog_writer',
    'component_heartbeat': 'component.heartbeat',
    'component_hostname_generator': 'component.hostname_generator',
    'component_ms_status_updater': 'component.ms_status_updater',
    'component_mzms_status_updater': 'component.mzms_status_updater',
    'component_store_counter': 'component.store_counter',
    'component_sub_finalizer': 'component.sub_finalizer',
    'component_vip_allocator': 'component.vip_allocator',
    'component_zone_available_services': 'component.zone_available_services',
    'controller_runtime_active_workers': 'controller_runtime.active_workers',
    'controller_runtime_max_concurrent_reconciles': 'controller_runtime.max_concurrent_reconciles',
    'controller_runtime_reconcile_errors_total': 'controller_runtime.reconcile.errors_total',
    'controller_runtime_reconcile_panics_total': 'controller_runtime.reconcile.panics_total',
    'controller_runtime_reconcile_time_seconds': 'controller_runtime.reconcile.time_seconds',
    'controller_runtime_reconcile_total': 'controller_runtime.reconcile.total',
    'controller_runtime_terminal_reconcile_errors_total': 'controller_runtime.terminal_reconcile.errors_total',
    'controller_runtime_webhook_latency_seconds': 'controller_runtime.webhook.latency_seconds',
    'controller_runtime_webhook_panics_total': 'controller_runtime.webhook.panics_total',
    'controller_runtime_webhook_requests_in_flight': 'controller_runtime.webhook.requests_in_flight',
    'controller_runtime_webhook_requests_total': 'controller_runtime.webhook.requests_total',
    'cp_info': 'cp_info',  # instance_id from this metric is propagated to all metrics as a tag
    'dp_server_http_request_duration_seconds': 'dp.server.http_request_duration_seconds',
    'dp_server_http_requests_inflight': 'dp.server.http_requests_inflight',
    'dp_server_http_response_size_bytes': 'dp.server.http_response_size_bytes',
    'events_dropped': 'events.dropped',
    'go_cgo_go_to_c_calls_calls_total': 'go.cgo.go_to_c_calls.calls_total',
    'go_cpu_classes_gc_mark_assist_cpu_seconds_total': 'go.cpu_classes.gc_mark_assist.cpu_seconds_total',
    'go_cpu_classes_gc_mark_dedicated_cpu_seconds_total': 'go.cpu_classes.gc_mark_dedicated.cpu_seconds_total',
    'go_cpu_classes_gc_mark_idle_cpu_seconds_total': 'go.cpu_classes.gc_mark_idle.cpu_seconds_total',
    'go_cpu_classes_gc_pause_cpu_seconds_total': 'go.cpu_classes.gc_pause.cpu_seconds_total',
    'go_cpu_classes_gc_total_cpu_seconds_total': 'go.cpu_classes.gc.total.cpu_seconds_total',
    'go_cpu_classes_idle_cpu_seconds_total': 'go.cpu_classes.idle.cpu_seconds_total',
    'go_cpu_classes_scavenge_assist_cpu_seconds_total': 'go.cpu_classes.scavenge_assist.cpu_seconds_total',
    'go_cpu_classes_scavenge_background_cpu_seconds_total': 'go.cpu_classes.scavenge_background.cpu_seconds_total',
    'go_cpu_classes_scavenge_total_cpu_seconds_total': 'go.cpu_classes.scavenge.total.cpu_seconds_total',
    'go_cpu_classes_total_cpu_seconds_total': 'go.cpu_classes.total.cpu_seconds_total',
    'go_cpu_classes_user_cpu_seconds_total': 'go.cpu_classes.user.cpu_seconds_total',
    'go_gc_cycles_automatic_gc_cycles_total': 'go.gc_cycles.automatic.gc_cycles_total',
    'go_gc_cycles_forced_gc_cycles_total': 'go.gc_cycles.forced.gc_cycles_total',
    'go_gc_cycles_total_gc_cycles_total': 'go.gc_cycles.total.gc_cycles_total',
    'go_gc_duration_seconds': 'go.gc.duration_seconds',
    'go_gc_gogc_percent': 'go.gc.gogc_percent',
    'go_gc_gomemlimit_bytes': 'go.gc.gomemlimit_bytes',
    'go_gc_heap_allocs_by_size_bytes': 'go.gc.heap.allocs_by_size_bytes',
    'go_gc_heap_allocs_bytes_total': 'go.gc.heap.allocs_bytes_total',
    'go_gc_heap_allocs_objects_total': 'go.gc.heap.allocs_objects_total',
    'go_gc_heap_frees_by_size_bytes': 'go.gc.heap.frees_by_size_bytes',
    'go_gc_heap_frees_bytes_total': 'go.gc.heap.frees_bytes_total',
    'go_gc_heap_frees_objects_total': 'go.gc.heap.frees_objects_total',
    'go_gc_heap_goal_bytes': 'go.gc.heap.goal_bytes',
    'go_gc_heap_live_bytes': 'go.gc.heap.live_bytes',
    'go_gc_heap_objects_objects': 'go.gc.heap.objects_objects',
    'go_gc_heap_tiny_allocs_objects_total': 'go.gc.heap.tiny_allocs_objects_total',
    'go_gc_limiter_last_enabled_gc_cycle': 'go.gc.limiter.last_enabled_gc_cycle',
    'go_gc_pauses_seconds': 'go.gc.pauses_seconds',
    'go_gc_scan_globals_bytes': 'go.gc.scan.globals_bytes',
    'go_gc_scan_heap_bytes': 'go.gc.scan.heap_bytes',
    'go_gc_scan_stack_bytes': 'go.gc.scan.stack_bytes',
    'go_gc_scan_total_bytes': 'go.gc.scan.total_bytes',
    'go_gc_stack_starting_size_bytes': 'go.gc.stack.starting_size_bytes',
    # 'go_godebug_non_default_behavior_asynctimerchan_events_total': 'go.godebug.non_default_behavior.asynctimerchan_events_total',
    # 'go_godebug_non_default_behavior_execerrdot_events_total': 'go.godebug.non_default_behavior.execerrdot_events_total',
    # 'go_godebug_non_default_behavior_gocachehash_events_total': 'go_godebug_non_default_behavior_gocachehash_events_total',
    # 'go_godebug_non_default_behavior_gocachetest_events_total': 'go_godebug_non_default_behavior_gocachetest_events_total',
    # 'go_godebug_non_default_behavior_gocacheverify_events_total': 'go_godebug_non_default_behavior_gocacheverify_events_total',
    # 'go_godebug_non_default_behavior_gotypesalias_events_total': 'go_godebug_non_default_behavior_gotypesalias_events_total',
    # 'go_godebug_non_default_behavior_http2client_events_total': 'go_godebug_non_default_behavior_http2client_events_total',
    # 'go_godebug_non_default_behavior_http2server_events_total': 'go_godebug_non_default_behavior_http2server_events_total',
    # 'go_godebug_non_default_behavior_httplaxcontentlength_events_total': 'go_godebug_non_default_behavior_httplaxcontentlength_events_total',
    # 'go_godebug_non_default_behavior_httpmuxgo121_events_total': 'go_godebug_non_default_behavior_httpmuxgo121_events_total',
    # 'go_godebug_non_default_behavior_httpservecontentkeepheaders_events_total': 'go_godebug_non_default_behavior_httpservecontentkeepheaders_events_total',
    # 'go_godebug_non_default_behavior_installgoroot_events_total': 'go_godebug_non_default_behavior_installgoroot_events_total',
    # 'go_godebug_non_default_behavior_multipartmaxheaders_events_total': 'go_godebug_non_default_behavior_multipartmaxheaders_events_total',
    # 'go_godebug_non_default_behavior_multipartmaxparts_events_total': 'go_godebug_non_default_behavior_multipartmaxparts_events_total',
    # 'go_godebug_non_default_behavior_multipathtcp_events_total': 'go_godebug_non_default_behavior_multipathtcp_events_total',
    # 'go_godebug_non_default_behavior_netedns0_events_total': 'go_godebug_non_default_behavior_netedns0_events_total',
    # 'go_godebug_non_default_behavior_panicnil_events_total': 'go_godebug_non_default_behavior_panicnil_events_total',
    # 'go_godebug_non_default_behavior_randautoseed_events_total': 'go_godebug_non_default_behavior_randautoseed_events_total',
    # 'go_godebug_non_default_behavior_tarinsecurepath_events_total': 'go_godebug_non_default_behavior_tarinsecurepath_events_total',
    # 'go_godebug_non_default_behavior_tls10server_events_total': 'go_godebug_non_default_behavior_tls10server_events_total',
    # 'go_godebug_non_default_behavior_tls3des_events_total': 'go_godebug_non_default_behavior_tls3des_events_total',
    # 'go_godebug_non_default_behavior_tlsmaxrsasize_events_total': 'go_godebug_non_default_behavior_tlsmaxrsasize_events_total',
    # 'go_godebug_non_default_behavior_tlsrsakex_events_total': 'go_godebug_non_default_behavior_tlsrsakex_events_total',
    # 'go_godebug_non_default_behavior_tlsunsafeekm_events_total': 'go_godebug_non_default_behavior_tlsunsafeekm_events_total',
    # 'go_godebug_non_default_behavior_winreadlinkvolume_events_total': 'go_godebug_non_default_behavior_winreadlinkvolume_events_total',
    # 'go_godebug_non_default_behavior_winsymlink_events_total': 'go_godebug_non_default_behavior_winsymlink_events_total',
    # 'go_godebug_non_default_behavior_x509keypairleaf_events_total': 'go_godebug_non_default_behavior_x509keypairleaf_events_total',
    # 'go_godebug_non_default_behavior_x509negativeserial_events_total': 'go_godebug_non_default_behavior_x509negativeserial_events_total',
    # 'go_godebug_non_default_behavior_x509sha1_events_total': 'go_godebug_non_default_behavior_x509sha1_events_total',
    # 'go_godebug_non_default_behavior_x509usefallbackroots_events_total': 'go_godebug_non_default_behavior_x509usefallbackroots_events_total',
    # 'go_godebug_non_default_behavior_x509usepolicies_events_total': 'go_godebug_non_default_behavior_x509usepolicies_events_total',
    # 'go_godebug_non_default_behavior_zipinsecurepath_events_total': 'go_godebug_non_default_behavior_zipinsecurepath_events_total',
    'go_goroutines': 'go.goroutines',
    'go_info': 'go.info',
    'go_memory_classes_heap_free_bytes': 'go.memory_classes.heap.free_bytes',
    'go_memory_classes_heap_objects_bytes': 'go.memory_classes.heap.objects_bytes',
    'go_memory_classes_heap_released_bytes': 'go.memory_classes.heap.released_bytes',
    'go_memory_classes_heap_stacks_bytes': 'go.memory_classes.heap.stacks_bytes',
    'go_memory_classes_heap_unused_bytes': 'go.memory_classes.heap.unused_bytes',
    'go_memory_classes_metadata_mcache_free_bytes': 'go.memory_classes.metadata.mcache.free_bytes',
    'go_memory_classes_metadata_mcache_inuse_bytes': 'go.memory_classes.metadata.mcache.inuse_bytes',
    'go_memory_classes_metadata_mspan_free_bytes': 'go.memory_classes.metadata.mspan.free_bytes',
    'go_memory_classes_metadata_mspan_inuse_bytes': 'go.memory_classes.metadata.mspan.inuse_bytes',
    'go_memory_classes_metadata_other_bytes': 'go.memory_classes.metadata.other_bytes',
    'go_memory_classes_os_stacks_bytes': 'go.memory_classes.os.stacks_bytes',
    'go_memory_classes_other_bytes': 'go.memory_classes.other_bytes',
    'go_memory_classes_profiling_buckets_bytes': 'go.memory_classes.profiling.buckets_bytes',
    'go_memory_classes_total_bytes': 'go.memory_classes.total_bytes',
    'go_memstats_alloc_bytes': 'go.memstats.alloc_bytes',
    'go_memstats_alloc_bytes_total': 'go.memstats.alloc_bytes_total',
    'go_memstats_buck_hash_sys_bytes': 'go.memstats.buck_hash_sys_bytes',
    'go_memstats_frees_total': 'go.memstats.frees_total',
    'go_memstats_gc_sys_bytes': 'go.memstats.gc_sys_bytes',
    'go_memstats_heap_alloc_bytes': 'go.memstats.heap.alloc_bytes',
    'go_memstats_heap_idle_bytes': 'go.memstats.heap.idle_bytes',
    'go_memstats_heap_inuse_bytes': 'go.memstats.heap.inuse_bytes',
    'go_memstats_heap_objects': 'go.memstats.heap.objects',
    'go_memstats_heap_released_bytes': 'go.memstats.heap.released_bytes',
    'go_memstats_heap_sys_bytes': 'go.memstats.heap.sys_bytes',
    'go_memstats_last_gc_time_seconds': 'go.memstats.last_gc_time_seconds',
    'go_memstats_mallocs_total': 'go.memstats.mallocs_total',
    'go_memstats_mcache_inuse_bytes': 'go.memstats.mcache.inuse_bytes',
    'go_memstats_mcache_sys_bytes': 'go.memstats.mcache.sys_bytes',
    'go_memstats_mspan_inuse_bytes': 'go.memstats.mspan.inuse_bytes',
    'go_memstats_mspan_sys_bytes': 'go.memstats.mspan.sys_bytes',
    'go_memstats_next_gc_bytes': 'go.memstats.next_gc_bytes',
    'go_memstats_other_sys_bytes': 'go.memstats.other_sys_bytes',
    'go_memstats_stack_inuse_bytes': 'go.memstats.stack.inuse_bytes',
    'go_memstats_stack_sys_bytes': 'go.memstats.stack.sys_bytes',
    'go_memstats_sys_bytes': 'go.memstats.sys_bytes',
    'go_sched_gomaxprocs_threads': 'go.sched.gomaxprocs_threads',
    'go_sched_goroutines_goroutines': 'go.sched.goroutines.goroutines',
    'go_sched_latencies_seconds': 'go.sched.latencies_seconds',
    'go_sched_pauses_stopping_gc_seconds': 'go.sched.pauses_stopping_gc_seconds',
    'go_sched_pauses_stopping_other_seconds': 'go.sched.pauses_stopping_other_seconds',
    'go_sched_pauses_total_gc_seconds': 'go.sched.pauses_total_gc_seconds',
    'go_sched_pauses_total_other_seconds': 'go.sched.pauses_total_other_seconds',
    'go_sync_mutex_wait_total_seconds_total': 'go.sync.mutex_wait_total_seconds_total',
    'go_threads': 'go.threads',
    'grpc_server_msg_received_total': 'grpc.server.msg_received_total', # Counter
    'grpc_server_msg_sent_total': 'grpc.server.msg_sent_total', # Counter
    'grpc_server_started_total': 'grpc.server.started_total', # Counter
    'grpc_server_handled_total': 'grpc.server.handled_total', # Counter
    'insights_resyncer_event_time_processing': 'insights.resyncer.event_time_processing', # Histogram
    'insights_resyncer_event_time_to_process': 'insights.resyncer.event_time_to_process', # Histogram
    'insights_resyncer_processor_idle_time': 'insights.resyncer.processor_idle_time', # Histogram
    'leader': 'leader',
    'leader_election_master_status': 'leader_election.master_status',
    'mesh_cache': 'mesh_cache',
    'process_cpu_seconds_total': 'process.cpu_seconds_total', # Counter
    'process_max_fds': 'process.max_fds', # Gauge
    'process_network_receive_bytes_total': 'process.network.receive_bytes_total', # Counter
    'process_network_transmit_bytes_total': 'process.network.transmit_bytes_total', # Counter
    'process_open_fds': 'process.open_fds', # Gauge
    'process_resident_memory_bytes': 'process.resident_memory_bytes', # Gauge
    'process_start_time_seconds': 'process.start_time_seconds', # Gauge
    'process_virtual_memory_bytes': 'process.virtual_memory_bytes', # Gauge
    'resources_count': 'resources_count',
    'rest_client_requests_total': 'rest_client.requests_total', # Counter
    'store': 'store', # Histogram
    'store_cache': 'store_cache',
    'vip_generation': 'vip_generation',
    'vip_generation_errors': 'vip_generation_errors', # Counter
    'workqueue_adds_total': 'workqueue.adds_total', # Counter
    'workqueue_depth': 'workqueue.depth', # Gauge
    'workqueue_longest_running_processor_seconds': 'workqueue.longest_running_processor_seconds', # Gauge
    'workqueue_queue_duration_seconds': 'workqueue.queue_duration_seconds', # Histogram
    'workqueue_retries_total': 'workqueue.retries_total', # Counter
    'workqueue_unfinished_work_seconds': 'workqueue.unfinished_work_seconds', # Counter
    'workqueue_work_duration_seconds': 'workqueue.work_duration_seconds', # Histogram
    'xds_delivery': 'xds.delivery', # Summary
    'xds_generation': 'xds.generation', # Summary
    'xds_generation_errors': 'xds.generation_errors',
    'xds_requests_received': 'xds.requests_received',
    'xds_responses_sent': 'xds.responses_sent',
    'xds_streams_active': 'xds.streams_active',
}


RENAME_LABELS_MAP = {
    'service': 'kubernetes_service',
    'cluster_id': 'kuma_cluster_id',
    'version': 'kuma_version',
}
