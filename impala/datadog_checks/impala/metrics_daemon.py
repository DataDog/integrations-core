# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# E501: line too long (XXX > 120 characters)
# ruff: noqa: E501
from datadog_checks.impala.common import counter

DAEMON_METRIC_MAP = {
    # jvm
    "impala_jvm_code_cache_committed_usage_bytes": "daemon.jvm.code_cache.committed_usage",
    "impala_jvm_code_cache_current_usage_bytes": "daemon.jvm.code_cache.current_usage",
    "impala_jvm_code_cache_init_usage_bytes": "daemon.jvm.code_cache.init_usage",
    "impala_jvm_code_cache_max_usage_bytes": "daemon.jvm.code_cache.max_usage",
    "impala_jvm_code_cache_peak_committed_usage_bytes": "daemon.jvm.code_cache.peak_committed_usage",
    "impala_jvm_code_cache_peak_current_usage_bytes": "daemon.jvm.code_cache.peak_current_usage",
    "impala_jvm_code_cache_peak_init_usage_bytes": "daemon.jvm.code_cache.peak_init_usage",
    "impala_jvm_code_cache_peak_max_usage_bytes": "daemon.jvm.code_cache.peak_max_usage",
    "impala_jvm_compressed_class_space_committed_usage_bytes": "daemon.jvm.compressed_class_space.committed_usage",
    "impala_jvm_compressed_class_space_current_usage_bytes": "daemon.jvm.compressed_class_space.current_usage",
    "impala_jvm_compressed_class_space_init_usage_bytes": "daemon.jvm.compressed_class_space.init_usage",
    "impala_jvm_compressed_class_space_max_usage_bytes": "daemon.jvm.compressed_class_space.max_usage",
    "impala_jvm_compressed_class_space_peak_committed_usage_bytes": "daemon.jvm.compressed_class_space.peak_committed_usage",
    "impala_jvm_compressed_class_space_peak_current_usage_bytes": "daemon.jvm.compressed_class_space.peak_current_usage",
    "impala_jvm_compressed_class_space_peak_init_usage_bytes": "daemon.jvm.compressed_class_space.peak_init_usage",
    "impala_jvm_compressed_class_space_peak_max_usage_bytes": "daemon.jvm.compressed_class_space.peak_max_usage",
    "impala_jvm_gc_count": "daemon.jvm.gc",
    "impala_jvm_gc_num_info_threshold_exceeded": "daemon.jvm.gc.num_info_threshold_exceeded",
    "impala_jvm_gc_num_warn_threshold_exceeded": "daemon.jvm.gc.num_warn_threshold_exceeded",
    "impala_jvm_gc_time_millis": "daemon.jvm.gc.time_millis",
    "impala_jvm_gc_total_extra_sleep_time_millis": "daemon.jvm.gc.total_extra_sleep_time_millis",
    "impala_jvm_heap_committed_usage_bytes": "daemon.jvm.heap.committed_usage",
    "impala_jvm_heap_current_usage_bytes": "daemon.jvm.heap.current_usage",
    "impala_jvm_heap_init_usage_bytes": "daemon.jvm.heap.init_usage",
    "impala_jvm_heap_max_usage_bytes": "daemon.jvm.heap.max_usage",
    "impala_jvm_heap_peak_committed_usage_bytes": "daemon.jvm.heap.peak_committed_usage",
    "impala_jvm_heap_peak_current_usage_bytes": "daemon.jvm.heap.peak_current_usage",
    "impala_jvm_heap_peak_init_usage_bytes": "daemon.jvm.heap.peak_init_usage",
    "impala_jvm_heap_peak_max_usage_bytes": "daemon.jvm.heap.peak_max_usage",
    "impala_jvm_metaspace_committed_usage_bytes": "daemon.jvm.metaspace.committed_usage",
    "impala_jvm_metaspace_current_usage_bytes": "daemon.jvm.metaspace.current_usage",
    "impala_jvm_metaspace_init_usage_bytes": "daemon.jvm.metaspace.init_usage",
    "impala_jvm_metaspace_max_usage_bytes": "daemon.jvm.metaspace.max_usage",
    "impala_jvm_metaspace_peak_committed_usage_bytes": "daemon.jvm.metaspace.peak_committed_usage",
    "impala_jvm_metaspace_peak_current_usage_bytes": "daemon.jvm.metaspace.peak_current_usage",
    "impala_jvm_metaspace_peak_init_usage_bytes": "daemon.jvm.metaspace.peak_init_usage",
    "impala_jvm_metaspace_peak_max_usage_bytes": "daemon.jvm.metaspace.peak_max_usage",
    "impala_jvm_non_heap_committed_usage_bytes": "daemon.jvm.non_heap.committed_usage",
    "impala_jvm_non_heap_current_usage_bytes": "daemon.jvm.non_heap.current_usage",
    "impala_jvm_non_heap_init_usage_bytes": "daemon.jvm.non_heap.init_usage",
    "impala_jvm_non_heap_max_usage_bytes": "daemon.jvm.non_heap.max_usage",
    "impala_jvm_non_heap_peak_committed_usage_bytes": "daemon.jvm.non_heap.peak_committed_usage",
    "impala_jvm_non_heap_peak_current_usage_bytes": "daemon.jvm.non_heap.peak_current_usage",
    "impala_jvm_non_heap_peak_init_usage_bytes": "daemon.jvm.non_heap.peak_init_usage",
    "impala_jvm_non_heap_peak_max_usage_bytes": "daemon.jvm.non_heap.peak_max_usage",
    "impala_jvm_ps_eden_space_committed_usage_bytes": "daemon.jvm.ps_eden_space.committed_usage",
    "impala_jvm_ps_eden_space_current_usage_bytes": "daemon.jvm.ps_eden_space.current_usage",
    "impala_jvm_ps_eden_space_init_usage_bytes": "daemon.jvm.ps_eden_space.init_usage",
    "impala_jvm_ps_eden_space_max_usage_bytes": "daemon.jvm.ps_eden_space.max_usage",
    "impala_jvm_ps_eden_space_peak_committed_usage_bytes": "daemon.jvm.ps_eden_space.peak_committed_usage",
    "impala_jvm_ps_eden_space_peak_current_usage_bytes": "daemon.jvm.ps_eden_space.peak_current_usage",
    "impala_jvm_ps_eden_space_peak_init_usage_bytes": "daemon.jvm.ps_eden_space.peak_init_usage",
    "impala_jvm_ps_eden_space_peak_max_usage_bytes": "daemon.jvm.ps_eden_space.peak_max_usage",
    "impala_jvm_ps_old_gen_committed_usage_bytes": "daemon.jvm.ps_old_gen.committed_usage",
    "impala_jvm_ps_old_gen_current_usage_bytes": "daemon.jvm.ps_old_gen.current_usage",
    "impala_jvm_ps_old_gen_init_usage_bytes": "daemon.jvm.ps_old_gen.init_usage",
    "impala_jvm_ps_old_gen_max_usage_bytes": "daemon.jvm.ps_old_gen.max_usage",
    "impala_jvm_ps_old_gen_peak_committed_usage_bytes": "daemon.jvm.ps_old_gen.peak_committed_usage",
    "impala_jvm_ps_old_gen_peak_current_usage_bytes": "daemon.jvm.ps_old_gen.peak_current_usage",
    "impala_jvm_ps_old_gen_peak_init_usage_bytes": "daemon.jvm.ps_old_gen.peak_init_usage",
    "impala_jvm_ps_old_gen_peak_max_usage_bytes": "daemon.jvm.ps_old_gen.peak_max_usage",
    "impala_jvm_ps_survivor_space_committed_usage_bytes": "daemon.jvm.ps_survivor_space.committed_usage",
    "impala_jvm_ps_survivor_space_current_usage_bytes": "daemon.jvm.ps_survivor_space.current_usage",
    "impala_jvm_ps_survivor_space_init_usage_bytes": "daemon.jvm.ps_survivor_space.init_usage",
    "impala_jvm_ps_survivor_space_max_usage_bytes": "daemon.jvm.ps_survivor_space.max_usage",
    "impala_jvm_ps_survivor_space_peak_committed_usage_bytes": "daemon.jvm.ps_survivor_space.peak_committed_usage",
    "impala_jvm_ps_survivor_space_peak_current_usage_bytes": "daemon.jvm.ps_survivor_space.peak_current_usage",
    "impala_jvm_ps_survivor_space_peak_init_usage_bytes": "daemon.jvm.ps_survivor_space.peak_init_usage",
    "impala_jvm_ps_survivor_space_peak_max_usage_bytes": "daemon.jvm.ps_survivor_space.peak_max_usage",
    "impala_jvm_total_committed_usage_bytes": "daemon.jvm.total_committed_usage",
    "impala_jvm_total_current_usage_bytes": "daemon.jvm.total_current_usage",
    "impala_jvm_total_init_usage_bytes": "daemon.jvm.total_init_usage",
    "impala_jvm_total_max_usage_bytes": "daemon.jvm.total_max_usage",
    "impala_jvm_total_peak_committed_usage_bytes": "daemon.jvm.total_peak_committed_usage",
    "impala_jvm_total_peak_current_usage_bytes": "daemon.jvm.total_peak_current_usage",
    "impala_jvm_total_peak_init_usage_bytes": "daemon.jvm.total_peak_init_usage",
    "impala_jvm_total_peak_max_usage_bytes": "daemon.jvm.total_peak_max_usage",
    # tcmalloc
    "impala_tcmalloc_physical_bytes_reserved": "daemon.tcmalloc.physical_reserved",
    "impala_tcmalloc_bytes_in_use": "daemon.tcmalloc.in_use",
    "impala_tcmalloc_total_bytes_reserved": "daemon.tcmalloc.total_reserved",
    "impala_tcmalloc_pageheap_free_bytes": "daemon.tcmalloc.pageheap.free",
    "impala_tcmalloc_pageheap_unmapped_bytes": "daemon.tcmalloc.pageheap.unmapped",
    # thrift_server_beeswax_frontend
    "impala_thrift_server_beeswax_frontend_connections_in_use": "daemon.thrift_server.beeswax.frontend.connections_in_use",
    "impala_thrift_server_beeswax_frontend_total_connections": "daemon.thrift_server.beeswax.frontend.total_connections",
    "impala_thrift_server_beeswax_frontend_svc_thread_wait_time": "daemon.thrift_server.beeswax.frontend.svc_thread_wait_time",
    "impala_thrift_server_beeswax_frontend_connection_setup_time": "daemon.thrift_server.beeswax.frontend.connection_setup_time",
    "impala_thrift_server_beeswax_frontend_timedout_cnxn_requests": "daemon.thrift_server.beeswax.frontend.timedout_cnxn_requests",
    "impala_thrift_server_beeswax_frontend_connection_setup_queue_size": "daemon.thrift_server.beeswax.frontend.connection_setup_queue_size",
    # thrift_server_hiveserver2_frontend
    "impala_thrift_server_hiveserver2_frontend_connections_in_use": "daemon.thrift_server.hiveserver2.frontend.connections_in_use",
    "impala_thrift_server_hiveserver2_frontend_connection_setup_time": "daemon.thrift_server.hiveserver2.frontend.connection_setup_time",
    "impala_thrift_server_hiveserver2_frontend_total_connections": "daemon.thrift_server.hiveserver2.frontend.total_connections",
    "impala_thrift_server_hiveserver2_frontend_connection_setup_queue_size": "daemon.thrift_server.hiveserver2.frontend.connection_setup_queue_size",
    "impala_thrift_server_hiveserver2_frontend_timedout_cnxn_requests": "daemon.thrift_server.hiveserver2.frontend.timedout_cnxn_requests",
    "impala_thrift_server_hiveserver2_frontend_svc_thread_wait_time": "daemon.thrift_server.hiveserver2.frontend.svc_thread_wait_time",
    # thrift_server_hiveserver2_http_frontend
    "impala_thrift_server_hiveserver2_http_frontend_total_connections": "daemon.thrift_server.hiveserver2.http_frontend.total_connections",
    "impala_thrift_server_hiveserver2_http_frontend_timedout_cnxn_requests": "daemon.thrift_server.hiveserver2.http_frontend.timedout_cnxn_requests",
    "impala_thrift_server_hiveserver2_http_frontend_svc_thread_wait_time": "daemon.thrift_server.hiveserver2.http_frontend.svc_thread_wait_time",
    "impala_thrift_server_hiveserver2_http_frontend_connection_setup_queue_size": "daemon.thrift_server.hiveserver2.http_frontend.connection_setup_queue_size",
    "impala_thrift_server_hiveserver2_http_frontend_connection_setup_time": "daemon.thrift_server.hiveserver2.http_frontend.connection_setup_time",
    "impala_thrift_server_hiveserver2_http_frontend_connections_in_use": "daemon.thrift_server.hiveserver2.http_frontend.connections_in_use",
    # io_mgr
    "impala_server_io_mgr_bytes_read": "daemon.io_mgr.bytes_read",
    "impala_server_io_mgr_bytes_written": "daemon.io_mgr.bytes_written",
    "impala_server_io_mgr_cached_bytes_read": "daemon.io_mgr.cached_bytes_read",
    "impala_server_io_mgr_cached_file_handles_hit_count": "daemon.io_mgr.cached_file_handles.hit",
    "impala_server_io_mgr_cached_file_handles_hit_ratio_total": counter(
        "daemon.io_mgr.cached_file_handles.hit_ratio_total"
    ),
    "impala_server_io_mgr_cached_file_handles_miss_count": "daemon.io_mgr.cached_file_handles.miss",
    "impala_server_io_mgr_cached_file_handles_reopened": "daemon.io_mgr.cached_file_handles.reopened",
    "impala_server_io_mgr_local_bytes_read": "daemon.io_mgr.local_bytes_read",
    "impala_server_io_mgr_num_cached_file_handles": "daemon.io_mgr.num_cached_file_handles",
    "impala_server_io_mgr_num_file_handles_outstanding": "daemon.io_mgr.num_file_handles_outstanding",
    "impala_server_io_mgr_num_open_files": "daemon.io_mgr.num_open_files",
    "impala_server_io_mgr_remote_data_cache_dropped_bytes": "daemon.io_mgr.remote_data_cache.dropped",
    "impala_server_io_mgr_remote_data_cache_dropped_entries": "daemon.io_mgr.remote_data_cache.dropped_entries",
    "impala_server_io_mgr_remote_data_cache_hit_bytes": "daemon.io_mgr.remote_data_cache.hit_bytes",
    "impala_server_io_mgr_remote_data_cache_hit_count": "daemon.io_mgr.remote_data_cache.hit",
    "impala_server_io_mgr_remote_data_cache_instant_evictions": "daemon.io_mgr.remote_data_cache.instant_evictions",
    "impala_server_io_mgr_remote_data_cache_miss_bytes": "daemon.io_mgr.remote_data_cache.miss_bytes",
    "impala_server_io_mgr_remote_data_cache_miss_count": "daemon.io_mgr.remote_data_cache.miss",
    "impala_server_io_mgr_remote_data_cache_num_entries": "daemon.io_mgr.remote_data_cache.num_entries",
    "impala_server_io_mgr_remote_data_cache_num_writes": "daemon.io_mgr.remote_data_cache.num_writes",
    "impala_server_io_mgr_remote_data_cache_total_bytes": "daemon.io_mgr.remote_data_cache.total",
    "impala_server_io_mgr_short_circuit_bytes_read": "daemon.io_mgr.short_circuit.read",
    # admission_controller
    "impala_admission_controller_executor_group_num_queries_executing_default": "daemon.admission_controller.executor_group_num_queries_executing_default",
    "impala_admission_controller_total_dequeue_failed_coordinator_limited": "daemon.admission_controller.total_dequeue_failed_coordinator_limited",
    # buffer_pool
    "impala_buffer_pool_clean_page_bytes": "daemon.buffer_pool.clean_page_bytes",
    "impala_buffer_pool_clean_pages": "daemon.buffer_pool.clean_pages",
    "impala_buffer_pool_clean_pages_limit": "daemon.buffer_pool.clean_pages_limit",
    "impala_buffer_pool_free_buffer_bytes": "daemon.buffer_pool.free_buffer",
    "impala_buffer_pool_free_buffers": "daemon.buffer_pool.free_buffers",
    "impala_buffer_pool_limit": "daemon.buffer_pool.limit",
    "impala_buffer_pool_reserved": "daemon.buffer_pool.reserved",
    "impala_buffer_pool_system_allocated": "daemon.buffer_pool.system_allocated",
    "impala_buffer_pool_unused_reservation_bytes": "daemon.buffer_pool.unused_reservation",
    # catalog_cache
    "impala_catalog_cache_average_load_time": "daemon.catalog_cache.average_load_time",
    "impala_catalog_cache_eviction_count": "daemon.catalog_cache.eviction",
    "impala_catalog_cache_hit_count": "daemon.catalog_cache.hit",
    "impala_catalog_cache_hit_rate": "daemon.catalog_cache.hit_rate",
    "impala_catalog_cache_load_count": "daemon.catalog_cache.load",
    "impala_catalog_cache_load_exception_count": "daemon.catalog_cache.load_exception",
    "impala_catalog_cache_load_exception_rate": "daemon.catalog_cache.load_exception_rate",
    "impala_catalog_cache_load_success_count": "daemon.catalog_cache.load_success",
    "impala_catalog_cache_miss_count": "daemon.catalog_cache.miss",
    "impala_catalog_cache_miss_rate": "daemon.catalog_cache.miss_rate",
    "impala_catalog_cache_request_count": "daemon.catalog_cache.request",
    "impala_catalog_cache_total_load_time": "daemon.catalog_cache.total_load_time",
    # catalog
    "impala_catalog_catalog_object_version_lower_bound": "daemon.catalog.catalog_object_version_lower_bound",
    "impala_catalog_curr_topic": "daemon.catalog.curr_topic",
    "impala_catalog_curr_version": "daemon.catalog.curr_version",
    "impala_catalog_num_databases": "daemon.catalog.num_databases",
    "impala_catalog_num_tables": "daemon.catalog.num_tables",
    "impala_catalog_server_client_cache_clients_in_use": "daemon.catalog.server_client_cache.clients_in_use",
    "impala_catalog_server_client_cache_total_clients": "daemon.catalog.server_client_cache.total_clients",
    # cluster_membership
    "impala_cluster_membership_backends": "daemon.cluster_membership.backends",
    "impala_cluster_membership_executor_groups": "daemon.cluster_membership.executor_groups",
    "impala_cluster_membership_executor_groups_total_healthy": "daemon.cluster_membership.executor_groups_total_healthy",
    # external_data_source_class_cache
    "impala_external_data_source_class_cache_hits": "daemon.external_data_source_class_cache.hits",
    "impala_external_data_source_class_cache_misses": "daemon.external_data_source_class_cache.misses",
    # mem_tracker
    "impala_mem_tracker_process_bytes_freed_by_last_gc": "daemon.mem_tracker.process.bytes_freed_by_last_gc",
    "impala_mem_tracker_process_bytes_over_limit": "daemon.mem_tracker.process.bytes_over_limit",
    "impala_mem_tracker_process_limit": "daemon.mem_tracker.process.limit",
    "impala_mem_tracker_process_num_gcs": "daemon.mem_tracker.process.num_gcs",
    # memory
    "impala_memory_mapped_bytes": "daemon.memory.mapped",
    "impala_memory_rss": "daemon.memory.rss",
    "impala_memory_total_used": "daemon.memory.total_used",
    # simple_scheduler
    "impala_simple_scheduler_assignments": "daemon.simple_scheduler.assignments",
    "impala_simple_scheduler_local_assignments": "daemon.simple_scheduler.local_assignments",
    # thread_manager
    "impala_thread_manager_running_threads": "daemon.thread_manager.running_threads",
    "impala_thread_manager_total_threads_created": "daemon.thread_manager.total_threads_created",
    # tmp_file_mgr
    "impala_tmp_file_mgr_active_scratch_dirs": "daemon.tmp_file_mgr.active_scratch_dirs",
    "impala_tmp_file_mgr_scratch_space_bytes_used": "daemon.tmp_file_mgr.scratch_space_bytes_used",
    "impala_tmp_file_mgr_scratch_space_bytes_used_dir_0": "daemon.tmp_file_mgr.scratch_space_bytes_used_dir_0",
    "impala_tmp_file_mgr_scratch_space_bytes_used_high_water_mark": "daemon.tmp_file_mgr.scratch_space_bytes_used_high_water_mark",
    # resultset_cache
    "impala_server_resultset_cache_total_bytes": "daemon.resultset_cache.total_bytes",
    "impala_server_resultset_cache_total_num_rows": "daemon.resultset_cache.total_num_rows",
    # daemon
    "impala_server_backend_num_queries_executed": "daemon.num_queries_executed",
    "impala_server_backend_num_queries_executing": "daemon.num_queries_executing",
    "impala_server_num_files_open_for_insert": "daemon.num_files_open_for_insert",
    "impala_server_num_fragments": "daemon.num_fragments",
    "impala_server_num_fragments_in_flight": "daemon.num_fragments_in_flight",
    "impala_server_num_open_beeswax_sessions": "daemon.num_open_beeswax_sessions",
    "impala_server_num_open_hiveserver2_sessions": "daemon.num_open_hiveserver2_sessions",
    "impala_server_num_queries": "daemon.num_queries",
    "impala_server_num_queries_expired": "daemon.num_queries_expired",
    "impala_server_num_queries_registered": "daemon.num_queries_registered",
    "impala_server_num_queries_spilled": "daemon.num_queries_spilled",
    "impala_server_num_sessions_expired": "daemon.num_sessions_expired",
    "impala_server_ddl_durations_ms": "daemon.ddl_durations_ms",
    "impala_server_query_durations_ms": "daemon.query_durations_ms",
    "impala_server_scan_ranges_num_missing_volume_id": "daemon.scan_ranges_num_missing_volume_id",
    "impala_server_scan_ranges": "daemon.scan_ranges",
    "impala_server_hedged_read_ops": "daemon.hedged_read_ops",
    "impala_server_hedged_read_ops_win": "daemon.hedged_read_ops.win",
    "impala_total_senders_blocked_on_recvr_creation": "daemon.total_senders_blocked_on_recvr_creation",
    "impala_total_senders_timedout_waiting_for_recvr_creation": "daemon.total_senders_timedout_waiting_for_recvr_creation",
    "impala_request_pool_service_resolve_pool_duration_ms_total": counter(
        "daemon.request_pool_service_resolve_pool_duration"
    ),
    "impala_senders_blocked_on_recvr_creation": "daemon.senders_blocked_on_recvr_creation",
    # statestore_subscriber
    "impala_statestore_subscriber_heartbeat_interval_time_total": counter(
        "daemon.statestore_subscriber.heartbeat_interval_time"
    ),
    "impala_statestore_subscriber_last_recovery_duration": "daemon.statestore_subscriber.last_recovery_duration",
    "impala_statestore_subscriber_num_connection_failures": "daemon.statestore_subscriber.num_connection_failures",
    "impala_statestore_subscriber_statestore_client_cache_clients_in_use": "daemon.statestore_subscriber.statestore_client_cache.clients_in_use",
    "impala_statestore_subscriber_statestore_client_cache_total_clients": "daemon.statestore_subscriber.statestore_client_cache.total_clients",
    "impala_statestore_subscriber_topic_update_duration_total": counter(
        "daemon.statestore_subscriber.topic.update_duration"
    ),
    "impala_statestore_subscriber_topic_update_interval_time_total": counter(
        "daemon.statestore_subscriber.topic.update_interval_time"
    ),
}

DAEMON_METRICS_WITH_LABEL_IN_NAME = {
    "^impala_server_io_mgr_queue_([0-9]+)_(.+)$": {
        "label_name": "id",
        "sub_metrics": {
            "write_io_error_total": {
                "new_name": "daemon.io_mgr_queue.write_io_error_total.count",
                "type": "monotonic_count",
            },
            "read_latency": {
                "new_name": "daemon.io_mgr_queue.read_latency.quantile",
                "type": "gauge",
            },
            "read_latency_sum": {
                "new_name": "daemon.io_mgr_queue.read_latency.sum",
                "type": "monotonic_count",
            },
            "read_latency_count": {
                "new_name": "daemon.io_mgr_queue.read_latency.count",
                "type": "monotonic_count",
            },
            "write_latency": {
                "new_name": "daemon.io_mgr_queue.write_latency.quantile",
                "type": "gauge",
            },
            "write_latency_sum": {
                "new_name": "daemon.io_mgr_queue.write_latency.sum",
                "type": "monotonic_count",
            },
            "write_latency_count": {
                "new_name": "daemon.io_mgr_queue.write_latency.count",
                "type": "monotonic_count",
            },
            "read_size": {
                "new_name": "daemon.io_mgr_queue.read_size.quantile",
                "type": "gauge",
            },
            "read_size_sum": {
                "new_name": "daemon.io_mgr_queue.read_size.sum",
                "type": "monotonic_count",
            },
            "read_size_count": {
                "new_name": "daemon.io_mgr_queue.read_size.count",
                "type": "monotonic_count",
            },
            "write_size": {
                "new_name": "daemon.io_mgr_queue.write_size.quantile",
                "type": "gauge",
            },
            "write_size_sum": {
                "new_name": "daemon.io_mgr_queue.write_size.sum",
                "type": "monotonic_count",
            },
            "write_size_count": {
                "new_name": "daemon.io_mgr_queue.write_size.count",
                "type": "monotonic_count",
            },
        },
    },
    "^impala_buffer_pool_arena_([0-9]+)_(.+)$": {
        "label_name": "id",
        "sub_metrics": {
            "num_final_scavenges_total": {
                "new_name": "daemon.buffer_pool.arena.num_final_scavenges_total.count",
                "type": "monotonic_count",
            },
            "num_scavenges_total": {
                "new_name": "daemon.buffer_pool.arena.num_scavenges_total.count",
                "type": "monotonic_count",
            },
            "clean_page_hits_total": {
                "new_name": "daemon.buffer_pool.arena.clean_page_hits_total.count",
                "type": "monotonic_count",
            },
            "system_alloc_time_total": {
                "new_name": "daemon.buffer_pool.arena.system_alloc_time_total.count",
                "type": "monotonic_count",
            },
            "local_arena_free_buffer_hits_total": {
                "new_name": "daemon.buffer_pool.arena.local_arena_free_buffer_hits_total.count",
                "type": "monotonic_count",
            },
            "numa_arena_free_buffer_hits_total": {
                "new_name": "daemon.buffer_pool.arena.numa_arena_free_buffer_hits_total.count",
                "type": "monotonic_count",
            },
            "direct_alloc_count_total": {
                "new_name": "daemon.buffer_pool.arena.direct_alloc_count_total.count",
                "type": "monotonic_count",
            },
            "allocated_buffer_sizes": {
                "new_name": "daemon.buffer_pool.arena.allocated_buffer_sizes.quantile",
                "type": "gauge",
            },
            "allocated_buffer_sizes_sum": {
                "new_name": "daemon.buffer_pool.arena.allocated_buffer_sizes.sum",
                "type": "monotonic_count",
            },
            "allocated_buffer_sizes_count": {
                "new_name": "daemon.buffer_pool.arena.allocated_buffer_sizes.count",
                "type": "monotonic_count",
            },
        },
    },
    "^impala_rpc_impala_(.+Service)_(.+)$": {
        "label_name": "daemon_service",
        "sub_metrics": {
            "rpcs_queue_overflow_total": {
                "new_name": "daemon.rpcs_queue_overflow.count",
                "type": "monotonic_count",
            },
        },
    },
    "^impala_mem_tracker_(.+Service)_(.+)$": {
        "label_name": "daemon_service",
        "sub_metrics": {
            "current_usage_bytes": {
                "new_name": "daemon.mem_tracker.process.current_usage",
                "type": "gauge",
            },
            "peak_usage_bytes": {
                "new_name": "daemon.mem_tracker.process.peak_usage",
                "type": "gauge",
            },
        },
    },
    "^impala_statestore_subscriber_topic_(.+)_(processing_time_s_total)$": {
        "label_name": "topic",
        "sub_metrics": {
            "processing_time_s_total": {
                "new_name": "daemon.statestore_subscriber.processing_time.count",
                "type": "monotonic_count",
            },
        },
    },
    "^impala_statestore_subscriber_topic_(.+)_(update_interval_total)$": {
        "label_name": "topic",
        "sub_metrics": {
            "update_interval_total": {
                "new_name": "daemon.statestore_subscriber.update_interval.count",
                "type": "monotonic_count",
            },
        },
    },
}
