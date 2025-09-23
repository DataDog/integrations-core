# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# E501: line too long (XXX > 120 characters)
# ruff: noqa: E501
from datadog_checks.impala.common import counter

CATALOG_METRIC_MAP = {
    # subscriber
    "impala_catalog_partial_fetch_rpc_queue_len": "catalog.partial_fetch_rpc_queue_len",
    "impala_catalog_server_topic_processing_time_s_total": counter("catalog.server_topic_processing_time_s_total"),
    "impala_rpc_method_catalog_server_CatalogService_GetPartialCatalogObject_call_duration": "catalog.rpc_method_catalog_server.get_partial_catalog_object_call_duration",
    "impala_rpc_method_statestore_subscriber_StatestoreSubscriber_Heartbeat_call_duration": "catalog.rpc_method_statestore_subscriber.heartbeat_call_duration",
    "impala_rpc_method_statestore_subscriber_StatestoreSubscriber_UpdateState_call_duration": "catalog.rpc_method_statestore_subscriber.update_state_call_duration",
    "impala_statestore_subscriber_heartbeat_interval_time_total": counter(
        "catalog.statestore_subscriber.heartbeat_interval_time_total"
    ),
    "impala_statestore_subscriber_last_recovery_duration": "catalog.statestore_subscriber.last_recovery_duration",
    "impala_statestore_subscriber_num_connection_failures": counter(
        "catalog.statestore_subscriber.num_connection_failures"
    ),
    "impala_statestore_subscriber_statestore_client_cache_clients_in_use": "catalog.statestore_subscriber.statestore_client_cache.clients_in_use",
    "impala_statestore_subscriber_statestore_client_cache_total_clients": "catalog.statestore_subscriber.statestore_client_cache.total_clients",
    "impala_statestore_subscriber_topic_update_duration_total": counter(
        "catalog.statestore_subscriber.topic_update_duration_total"
    ),
    "impala_statestore_subscriber_topic_update_interval_time_total": counter(
        "catalog.statestore_subscriber.topic_update_interval_time_total"
    ),
    # thread
    "impala_thread_manager_running_threads": "catalog.thread_manager.running_threads",
    "impala_thread_manager_total_threads_created": "catalog.thread_manager.total_threads_created",
    # # thrift_server
    "impala_thrift_server_CatalogService_connection_setup_queue_size": "catalog.thrift_server.connection.setup_queue_size",
    "impala_thrift_server_CatalogService_connection_setup_time": "catalog.thrift_server.connection.setup_time",
    "impala_thrift_server_CatalogService_connections_in_use": "catalog.thrift_server.connections.in_use",
    "impala_thrift_server_CatalogService_svc_thread_wait_time": "catalog.thrift_server.svc_thread_wait_time",
    "impala_thrift_server_CatalogService_timedout_cnxn_requests": "catalog.thrift_server.timedout_cnxn_requests",
    "impala_thrift_server_CatalogService_total_connections": "catalog.thrift_server.total_connections",
    # memory
    "impala_memory_rss": "catalog.memory.rss",
    "impala_memory_total_used": "catalog.memory.total_used",
    "impala_memory_mapped_bytes": "catalog.memory.mapped",
    # event processor
    "impala_events_processor_events_received_15min_rate": "catalog.events_processor.events_received_15min_rate",
    "impala_events_processor_events_received": "catalog.events_processor.events_received",
    "impala_events_processor_events_received_5min_rate": "catalog.events_processor.events_received_5min_rate",
    "impala_events_processor_events_received_1min_rate": "catalog.events_processor.events_received_1min_rate",
    "impala_events_processor_events_skipped": "catalog.events_processor.events_skipped",
    "impala_events_processor_last_synced_event_id": "catalog.events_processor.last_synced_event_id",
    "impala_events_processor_avg_events_fetch_duration": "catalog.events_processor.avg_events_fetch_duration",
    "impala_events_processor_avg_events_process_duration": "catalog.events_processor.avg_events_process_duration",
    # jvm
    "impala_jvm_code_cache_committed_usage_bytes": "catalog.jvm.code_cache.committed_usage",
    "impala_jvm_code_cache_current_usage_bytes": "catalog.jvm.code_cache.current_usage",
    "impala_jvm_code_cache_init_usage_bytes": "catalog.jvm.code_cache.init_usage",
    "impala_jvm_code_cache_max_usage_bytes": "catalog.jvm.code_cache.max_usage",
    "impala_jvm_code_cache_peak_committed_usage_bytes": "catalog.jvm.code_cache.peak_committed_usage",
    "impala_jvm_code_cache_peak_current_usage_bytes": "catalog.jvm.code_cache.peak_current_usage",
    "impala_jvm_code_cache_peak_init_usage_bytes": "catalog.jvm.code_cache.peak_init_usage",
    "impala_jvm_code_cache_peak_max_usage_bytes": "catalog.jvm.code_cache.peak_max_usage",
    "impala_jvm_compressed_class_space_committed_usage_bytes": "catalog.jvm.compressed_class_space.committed_usage",
    "impala_jvm_compressed_class_space_current_usage_bytes": "catalog.jvm.compressed_class_space.current_usage",
    "impala_jvm_compressed_class_space_init_usage_bytes": "catalog.jvm.compressed_class_space.init_usage",
    "impala_jvm_compressed_class_space_max_usage_bytes": "catalog.jvm.compressed_class_space.max_usage",
    "impala_jvm_compressed_class_space_peak_committed_usage_bytes": "catalog.jvm.compressed_class_space.peak_committed_usage",
    "impala_jvm_compressed_class_space_peak_current_usage_bytes": "catalog.jvm.compressed_class_space.peak_current_usage",
    "impala_jvm_compressed_class_space_peak_init_usage_bytes": "catalog.jvm.compressed_class_space.peak_init_usage",
    "impala_jvm_compressed_class_space_peak_max_usage_bytes": "catalog.jvm.compressed_class_space.peak_max_usage",
    "impala_jvm_gc_count": "catalog.jvm.gc",
    "impala_jvm_gc_num_info_threshold_exceeded": "catalog.jvm.gc.num_info_threshold_exceeded",
    "impala_jvm_gc_num_warn_threshold_exceeded": "catalog.jvm.gc.num_warn_threshold_exceeded",
    "impala_jvm_gc_time_millis": "catalog.jvm.gc.time_millis",
    "impala_jvm_gc_total_extra_sleep_time_millis": "catalog.jvm.gc.total_extra_sleep_time_millis",
    "impala_jvm_heap_committed_usage_bytes": "catalog.jvm.heap.committed_usage",
    "impala_jvm_heap_current_usage_bytes": "catalog.jvm.heap.current_usage",
    "impala_jvm_heap_init_usage_bytes": "catalog.jvm.heap.init_usage",
    "impala_jvm_heap_max_usage_bytes": "catalog.jvm.heap.max_usage",
    "impala_jvm_heap_peak_committed_usage_bytes": "catalog.jvm.heap.peak_committed_usage",
    "impala_jvm_heap_peak_current_usage_bytes": "catalog.jvm.heap.peak_current_usage",
    "impala_jvm_heap_peak_init_usage_bytes": "catalog.jvm.heap.peak_init_usage",
    "impala_jvm_heap_peak_max_usage_bytes": "catalog.jvm.heap.peak_max_usage",
    "impala_jvm_metaspace_committed_usage_bytes": "catalog.jvm.metaspace.committed_usage",
    "impala_jvm_metaspace_current_usage_bytes": "catalog.jvm.metaspace.current_usage",
    "impala_jvm_metaspace_init_usage_bytes": "catalog.jvm.metaspace.init_usage",
    "impala_jvm_metaspace_max_usage_bytes": "catalog.jvm.metaspace.max_usage",
    "impala_jvm_metaspace_peak_committed_usage_bytes": "catalog.jvm.metaspace.peak_committed_usage",
    "impala_jvm_metaspace_peak_current_usage_bytes": "catalog.jvm.metaspace.peak_current_usage",
    "impala_jvm_metaspace_peak_init_usage_bytes": "catalog.jvm.metaspace.peak_init_usage",
    "impala_jvm_metaspace_peak_max_usage_bytes": "catalog.jvm.metaspace.peak_max_usage",
    "impala_jvm_non_heap_committed_usage_bytes": "catalog.jvm.non_heap.committed_usage",
    "impala_jvm_non_heap_current_usage_bytes": "catalog.jvm.non_heap.current_usage",
    "impala_jvm_non_heap_init_usage_bytes": "catalog.jvm.non_heap.init_usage",
    "impala_jvm_non_heap_max_usage_bytes": "catalog.jvm.non_heap.max_usage",
    "impala_jvm_non_heap_peak_committed_usage_bytes": "catalog.jvm.non_heap.peak_committed_usage",
    "impala_jvm_non_heap_peak_current_usage_bytes": "catalog.jvm.non_heap.peak_current_usage",
    "impala_jvm_non_heap_peak_init_usage_bytes": "catalog.jvm.non_heap.peak_init_usage",
    "impala_jvm_non_heap_peak_max_usage_bytes": "catalog.jvm.non_heap.peak_max_usage",
    "impala_jvm_ps_eden_space_committed_usage_bytes": "catalog.jvm.ps_eden_space.committed_usage",
    "impala_jvm_ps_eden_space_current_usage_bytes": "catalog.jvm.ps_eden_space.current_usage",
    "impala_jvm_ps_eden_space_init_usage_bytes": "catalog.jvm.ps_eden_space.init_usage",
    "impala_jvm_ps_eden_space_max_usage_bytes": "catalog.jvm.ps_eden_space.max_usage",
    "impala_jvm_ps_eden_space_peak_committed_usage_bytes": "catalog.jvm.ps_eden_space.peak_committed_usage",
    "impala_jvm_ps_eden_space_peak_current_usage_bytes": "catalog.jvm.ps_eden_space.peak_current_usage",
    "impala_jvm_ps_eden_space_peak_init_usage_bytes": "catalog.jvm.ps_eden_space.peak_init_usage",
    "impala_jvm_ps_eden_space_peak_max_usage_bytes": "catalog.jvm.ps_eden_space.peak_max_usage",
    "impala_jvm_ps_old_gen_committed_usage_bytes": "catalog.jvm.ps_old_gen.committed_usage",
    "impala_jvm_ps_old_gen_current_usage_bytes": "catalog.jvm.ps_old_gen.current_usage",
    "impala_jvm_ps_old_gen_init_usage_bytes": "catalog.jvm.ps_old_gen.init_usage",
    "impala_jvm_ps_old_gen_max_usage_bytes": "catalog.jvm.ps_old_gen.max_usage",
    "impala_jvm_ps_old_gen_peak_committed_usage_bytes": "catalog.jvm.ps_old_gen.peak_committed_usage",
    "impala_jvm_ps_old_gen_peak_current_usage_bytes": "catalog.jvm.ps_old_gen.peak_current_usage",
    "impala_jvm_ps_old_gen_peak_init_usage_bytes": "catalog.jvm.ps_old_gen.peak_init_usage",
    "impala_jvm_ps_old_gen_peak_max_usage_bytes": "catalog.jvm.ps_old_gen.peak_max_usage",
    "impala_jvm_ps_survivor_space_committed_usage_bytes": "catalog.jvm.ps_survivor_space.committed_usage",
    "impala_jvm_ps_survivor_space_current_usage_bytes": "catalog.jvm.ps_survivor_space.current_usage",
    "impala_jvm_ps_survivor_space_init_usage_bytes": "catalog.jvm.ps_survivor_space.init_usage",
    "impala_jvm_ps_survivor_space_max_usage_bytes": "catalog.jvm.ps_survivor_space.max_usage",
    "impala_jvm_ps_survivor_space_peak_committed_usage_bytes": "catalog.jvm.ps_survivor_space.peak_committed_usage",
    "impala_jvm_ps_survivor_space_peak_current_usage_bytes": "catalog.jvm.ps_survivor_space.peak_current_usage",
    "impala_jvm_ps_survivor_space_peak_init_usage_bytes": "catalog.jvm.ps_survivor_space.peak_init_usage",
    "impala_jvm_ps_survivor_space_peak_max_usage_bytes": "catalog.jvm.ps_survivor_space.peak_max_usage",
    "impala_jvm_total_committed_usage_bytes": "catalog.jvm.total_committed_usage",
    "impala_jvm_total_current_usage_bytes": "catalog.jvm.total_current_usage",
    "impala_jvm_total_init_usage_bytes": "catalog.jvm.total_init_usage",
    "impala_jvm_total_max_usage_bytes": "catalog.jvm.total_max_usage",
    "impala_jvm_total_peak_committed_usage_bytes": "catalog.jvm.total_peak_committed_usage",
    "impala_jvm_total_peak_current_usage_bytes": "catalog.jvm.total_peak_current_usage",
    "impala_jvm_total_peak_init_usage_bytes": "catalog.jvm.total_peak_init_usage",
    "impala_jvm_total_peak_max_usage_bytes": "catalog.jvm.total_peak_max_usage",
    # tcmalloc
    "impala_tcmalloc_physical_bytes_reserved": "catalog.tcmalloc.physical_reserved",
    "impala_tcmalloc_bytes_in_use": "catalog.tcmalloc.in_use",
    "impala_tcmalloc_total_bytes_reserved": "catalog.tcmalloc.total_reserved",
    "impala_tcmalloc_pageheap_free_bytes": "catalog.tcmalloc.pageheap.free",
    "impala_tcmalloc_pageheap_unmapped_bytes": "catalog.tcmalloc.pageheap.unmapped",
}

CATALOG_METRICS_WITH_LABEL_IN_NAME = {
    "^impala_statestore_subscriber_topic_(.+)_(processing_time_s_total)$": {
        "label_name": "topic",
        "sub_metrics": {
            "processing_time_s_total": {
                "new_name": "catalog.statestore_subscriber.processing_time.count",
                "type": "monotonic_count",
            },
        },
    },
    "^impala_statestore_subscriber_topic_(.+)_(update_interval_total)$": {
        "label_name": "topic",
        "sub_metrics": {
            "update_interval_total": {
                "new_name": "catalog.statestore_subscriber.update_interval.count",
                "type": "monotonic_count",
            },
        },
    },
}
