# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# metrics namespaced under 'scylla'
SCYLLA_ALIEN = {
    'scylla_alien_receive_batch_queue_length': 'alien.receive_batch_queue_length',
    'scylla_alien_total_received_messages': 'alien.total_received_messages',
    'scylla_alien_total_sent_messages': 'alien.total_sent_messages',
}

SCYLLA_BATCHLOG_MANAGER = {
    'scylla_batchlog_manager_total_write_replay_attempts': 'batchlog_manager.total_write_replay_attempts',
}

SCYLLA_CACHE = {
    'scylla_cache_active_reads': 'cache.active_reads',
    'scylla_cache_bytes_total': 'cache.bytes_total',
    'scylla_cache_bytes_used': 'cache.bytes_used',
    'scylla_cache_concurrent_misses_same_key': 'cache.concurrent_misses_same_key',
    'scylla_cache_mispopulations': 'cache.mispopulations',
    'scylla_cache_partition_evictions': 'cache.partition_evictions',
    'scylla_cache_partition_hits': 'cache.partition_hits',
    'scylla_cache_partition_insertions': 'cache.partition_insertions',
    'scylla_cache_partition_merges': 'cache.partition_merges',
    'scylla_cache_partition_misses': 'cache.partition_misses',
    'scylla_cache_partition_removals': 'cache.partition_removals',
    'scylla_cache_partitions': 'cache.partitions',
    'scylla_cache_pinned_dirty_memory_overload': 'cache.pinned_dirty_memory_overload',
    'scylla_cache_reads': 'cache.reads',
    'scylla_cache_reads_with_misses': 'cache.reads_with_misses',
    'scylla_cache_row_evictions': 'cache.row_evictions',
    'scylla_cache_row_hits': 'cache.row_hits',
    'scylla_cache_row_insertions': 'cache.row_insertions',
    'scylla_cache_row_misses': 'cache.row_misses',
    'scylla_cache_row_removals': 'cache.row_removals',
    'scylla_cache_rows': 'cache.rows',
    'scylla_cache_rows_dropped_from_memtable': 'cache.rows_dropped_from_memtable',
    'scylla_cache_rows_merged_from_memtable': 'cache.rows_merged_from_memtable',
    'scylla_cache_rows_processed_from_memtable': 'cache.rows_processed_from_memtable',
    'scylla_cache_sstable_partition_skips': 'cache.sstable_partition_skips',
    'scylla_cache_sstable_reader_recreations': 'cache.sstable_reader_recreations',
    'scylla_cache_sstable_row_skips': 'cache.sstable_row_skips',
    'scylla_cache_static_row_insertions': 'cache.static_row_insertions',
}

SCYLLA_COMMITLOG = {
    'scylla_commitlog_alloc': 'commitlog.alloc',
    'scylla_commitlog_allocating_segments': 'commitlog.allocating_segments',
    'scylla_commitlog_bytes_written': 'commitlog.bytes_written',
    'scylla_commitlog_cycle': 'commitlog.cycle',
    'scylla_commitlog_disk_total_bytes': 'commitlog.disk_total_bytes',
    'scylla_commitlog_flush': 'commitlog.flush',
    'scylla_commitlog_flush_limit_exceeded': 'commitlog.flush_limit_exceeded',
    'scylla_commitlog_memory_buffer_bytes': 'commitlog.memory_buffer_bytes',
    'scylla_commitlog_pending_allocations': 'commitlog.pending_allocations',
    'scylla_commitlog_pending_flushes': 'commitlog.pending_flushes',
    'scylla_commitlog_requests_blocked_memory': 'commitlog.requests_blocked_memory',
    'scylla_commitlog_segments': 'commitlog.segments',
    'scylla_commitlog_slack': 'commitlog.slack',
    'scylla_commitlog_unused_segments': 'commitlog.unused_segments',
}

SCYLLA_COMPACTION = {
    'scylla_compaction_manager_compactions': 'compaction_manager.compactions',
}

SCYLLA_CQL = {
    'scylla_cql_authorized_prepared_statements_cache_evictions': 'cql.authorized_prepared_statements_cache_evictions',
    'scylla_cql_authorized_prepared_statements_cache_size': 'cql.authorized_prepared_statements_cache_size',
    'scylla_cql_batches': 'cql.batches',
    'scylla_cql_batches_pure_logged': 'cql.batches_pure_logged',
    'scylla_cql_batches_pure_unlogged': 'cql.batches_pure_unlogged',
    'scylla_cql_batches_unlogged_from_logged': 'cql.batches_unlogged_from_logged',
    'scylla_cql_deletes': 'cql.deletes',
    'scylla_cql_filtered_read_requests': 'cql.filtered_read_requests',
    'scylla_cql_filtered_rows_dropped_total': 'cql.filtered_rows_dropped_total',
    'scylla_cql_filtered_rows_matched_total': 'cql.filtered_rows_matched_total',
    'scylla_cql_filtered_rows_read_total': 'cql.filtered_rows_read_total',
    'scylla_cql_inserts': 'cql.inserts',
    'scylla_cql_prepared_cache_evictions': 'cql.prepared_cache_evictions',
    'scylla_cql_prepared_cache_memory_footprint': 'cql.prepared_cache_memory_footprint',
    'scylla_cql_prepared_cache_size': 'cql.prepared_cache_size',
    'scylla_cql_reads': 'cql.reads',
    'scylla_cql_reverse_queries': 'cql.reverse_queries',
    'scylla_cql_rows_read': 'cql.rows_read',
    'scylla_cql_secondary_index_creates': 'cql.secondary_index_creates',
    'scylla_cql_secondary_index_drops': 'cql.secondary_index_drops',
    'scylla_cql_secondary_index_reads': 'cql.secondary_index_reads',
    'scylla_cql_secondary_index_rows_read': 'cql.secondary_index_rows_read',
    'scylla_cql_statements_in_batches': 'cql.statements_in_batches',
    'scylla_cql_unpaged_select_queries': 'cql.unpaged_select_queries',
    'scylla_cql_updates': 'cql.updates',
    'scylla_cql_user_prepared_auth_cache_footprint': 'cql.user_prepared_auth_cache_footprint',
}

SCYLLA_DATABASE = {
    'scylla_database_active_reads': 'database.active_reads',
    'scylla_database_active_reads_memory_consumption': 'database.active_reads_memory_consumption',
    'scylla_database_clustering_filter_count': 'database.clustering_filter_count',
    'scylla_database_clustering_filter_fast_path_count': 'database.clustering_filter_fast_path_count',
    'scylla_database_clustering_filter_sstables_checked': 'database.clustering_filter_sstables_checked',
    'scylla_database_clustering_filter_surviving_sstables': 'database.clustering_filter_surviving_sstables',
    'scylla_database_counter_cell_lock_acquisition': 'database.counter_cell_lock_acquisition',
    'scylla_database_counter_cell_lock_pending': 'database.counter_cell_lock_pending',
    'scylla_database_dropped_view_updates': 'database.dropped_view_updates',
    'scylla_database_large_partition_exceeding_threshold': 'database.large_partition_exceeding_threshold',
    'scylla_database_multishard_query_failed_reader_saves': 'database.multishard_query_failed_reader_saves',
    'scylla_database_multishard_query_failed_reader_stops': 'database.multishard_query_failed_reader_stops',
    'scylla_database_multishard_query_unpopped_bytes': 'database.multishard_query_unpopped_bytes',
    'scylla_database_multishard_query_unpopped_fragments': 'database.multishard_query_unpopped_fragments',
    'scylla_database_paused_reads': 'database.paused_reads',
    'scylla_database_paused_reads_permit_based_evictions': 'database.paused_reads_permit_based_evictions',
    'scylla_database_querier_cache_drops': 'database.querier_cache_drops',
    'scylla_database_querier_cache_lookups': 'database.querier_cache_lookups',
    'scylla_database_querier_cache_memory_based_evictions': 'database.querier_cache_memory_based_evictions',
    'scylla_database_querier_cache_misses': 'database.querier_cache_misses',
    'scylla_database_querier_cache_population': 'database.querier_cache_population',
    'scylla_database_querier_cache_resource_based_evictions': 'database.querier_cache_resource_based_evictions',
    'scylla_database_querier_cache_time_based_evictions': 'database.querier_cache_time_based_evictions',
    'scylla_database_queued_reads': 'database.queued_reads',
    'scylla_database_requests_blocked_memory': 'database.requests_blocked_memory',
    'scylla_database_requests_blocked_memory_current': 'database.requests_blocked_memory_current',
    'scylla_database_short_data_queries': 'database.short_data_queries',
    'scylla_database_short_mutation_queries': 'database.short_mutation_queries',
    'scylla_database_sstable_read_queue_overloads': 'database.sstable_read_queue_overloads',
    'scylla_database_total_reads': 'database.total_reads',
    'scylla_database_total_reads_failed': 'database.total_reads_failed',
    'scylla_database_total_result_bytes': 'database.total_result_bytes',
    'scylla_database_total_view_updates_failed_local': 'database.total_view_updates_failed_local',
    'scylla_database_total_view_updates_failed_remote': 'database.total_view_updates_failed_remote',
    'scylla_database_total_view_updates_pushed_local': 'database.total_view_updates_pushed_local',
    'scylla_database_total_view_updates_pushed_remote': 'database.total_view_updates_pushed_remote',
    'scylla_database_total_writes': 'database.total_writes',
    'scylla_database_total_writes_failed': 'database.total_writes_failed',
    'scylla_database_total_writes_timedout': 'database.total_writes_timedout',
    'scylla_database_view_building_paused': 'database.view_building_paused',
    'scylla_database_view_update_backlog': 'database.view_update_backlog',
}

SCYLLA_EXECUTION_STAGES = {
    'scylla_execution_stages_function_calls_enqueued': 'execution_stages.function_calls_enqueued',
    'scylla_execution_stages_function_calls_executed': 'execution_stages.function_calls_executed',
    'scylla_execution_stages_tasks_preempted': 'execution_stages.tasks_preempted',
    'scylla_execution_stages_tasks_scheduled': 'execution_stages.tasks_scheduled',
}

SCYLLA_GOSSIP = {
    'scylla_gossip_heart_beat': 'gossip.heart_beat',
}

SCYLLA_HINTS = {
    'scylla_hints_for_views_manager_corrupted_files': 'hints.for_views_manager_corrupted_files',
    'scylla_hints_for_views_manager_discarded': 'hints.for_views_manager_discarded',
    'scylla_hints_for_views_manager_dropped': 'hints.for_views_manager_dropped',
    'scylla_hints_for_views_manager_errors': 'hints.for_views_manager_errors',
    'scylla_hints_for_views_manager_sent': 'hints.for_views_manager_sent',
    'scylla_hints_for_views_manager_size_of_hints_in_progress': 'hints.for_views_manager_size_of_hints_in_progress',
    'scylla_hints_for_views_manager_written': 'hints.for_views_manager_written',
    'scylla_hints_manager_corrupted_files': 'hints.manager_corrupted_files',
    'scylla_hints_manager_discarded': 'hints.manager_discarded',
    'scylla_hints_manager_dropped': 'hints.manager_dropped',
    'scylla_hints_manager_errors': 'hints.manager_errors',
    'scylla_hints_manager_sent': 'hints.manager_sent',
    'scylla_hints_manager_size_of_hints_in_progress': 'hints.manager_size_of_hints_in_progress',
    'scylla_hints_manager_written': 'hints.manager_written',
}

SCYLLA_HTTPD = {
    'scylla_httpd_connections_current': 'httpd.connections_current',
    'scylla_httpd_connections_total': 'httpd.connections_total',
    'scylla_httpd_read_errors': 'httpd.read_errors',
    'scylla_httpd_reply_errors': 'httpd.reply_errors',
    'scylla_httpd_requests_served': 'httpd.requests_served',
}

SCYLLA_IO_QUEUE = {
    'scylla_io_queue_delay': 'io_queue.delay',
    'scylla_io_queue_queue_length': 'io_queue.queue_length',
    'scylla_io_queue_shares': 'io_queue.shares',
    'scylla_io_queue_total_bytes': 'io_queue.total_bytes',
    'scylla_io_queue_total_operations': 'io_queue.total_operations',
}

SCYLLA_LSA = {
    'scylla_lsa_free_space': 'lsa.free_space',
    'scylla_lsa_large_objects_total_space_bytes': 'lsa.large_objects_total_space_bytes',
    'scylla_lsa_memory_allocated': 'lsa.memory_allocated',
    'scylla_lsa_memory_compacted': 'lsa.memory_compacted',
    'scylla_lsa_non_lsa_used_space_bytes': 'lsa.non_lsa_used_space_bytes',
    'scylla_lsa_occupancy': 'lsa.occupancy',
    'scylla_lsa_segments_compacted': 'lsa.segments_compacted',
    'scylla_lsa_segments_migrated': 'lsa.segments_migrated',
    'scylla_lsa_small_objects_total_space_bytes': 'lsa.small_objects_total_space_bytes',
    'scylla_lsa_small_objects_used_space_bytes': 'lsa.small_objects_used_space_bytes',
    'scylla_lsa_total_space_bytes': 'lsa.total_space_bytes',
    'scylla_lsa_used_space_bytes': 'lsa.used_space_bytes',
}

SCYLLA_MEMORY = {
    'scylla_memory_allocated_memory': 'memory.allocated_memory',
    'scylla_memory_cross_cpu_free_operations': 'memory.cross_cpu_free_operations',
    'scylla_memory_dirty_bytes': 'memory.dirty_bytes',
    'scylla_memory_free_memory': 'memory.free_memory',
    'scylla_memory_free_operations': 'memory.free_operations',
    'scylla_memory_malloc_live_objects': 'memory.malloc_live_objects',
    'scylla_memory_malloc_operations': 'memory.malloc_operations',
    'scylla_memory_reclaims_operations': 'memory.reclaims_operations',
    'scylla_memory_regular_dirty_bytes': 'memory.regular_dirty_bytes',
    'scylla_memory_regular_virtual_dirty_bytes': 'memory.regular_virtual_dirty_bytes',
    'scylla_memory_streaming_dirty_bytes': 'memory.streaming_dirty_bytes',
    'scylla_memory_streaming_virtual_dirty_bytes': 'memory.streaming_virtual_dirty_bytes',
    'scylla_memory_system_dirty_bytes': 'memory.system_dirty_bytes',
    'scylla_memory_system_virtual_dirty_bytes': 'memory.system_virtual_dirty_bytes',
    'scylla_memory_total_memory': 'memory.total_memory',
    'scylla_memory_virtual_dirty_bytes': 'memory.virtual_dirty_bytes',
}

SCYLLA_MEMTABLES = {
    'scylla_memtables_pending_flushes': 'memtables.pending_flushes',
    'scylla_memtables_pending_flushes_bytes': 'memtables.pending_flushes_bytes',
}

SCYLLA_NODE = {
    'scylla_node_operation_mode': 'node.operation_mode',
}

SCYLLA_QUERY_PROCESSOR = {
    'scylla_query_processor_queries': 'query_processor.queries',
    'scylla_query_processor_statements_prepared': 'query_processor.statements_prepared',
}

SCYLLA_REACTOR = {
    'scylla_reactor_aio_bytes_read': 'reactor.aio_bytes_read',
    'scylla_reactor_aio_bytes_write': 'reactor.aio_bytes_write',
    'scylla_reactor_aio_errors': 'reactor.aio_errors',
    'scylla_reactor_aio_reads': 'reactor.aio_reads',
    'scylla_reactor_aio_writes': 'reactor.aio_writes',
    'scylla_reactor_cpp_exceptions': 'reactor.cpp_exceptions',
    'scylla_reactor_cpu_busy_ms': 'reactor.cpu_busy_ms',
    'scylla_reactor_cpu_steal_time_ms': 'reactor.cpu_steal_time_ms',
    'scylla_reactor_fstream_read_bytes': 'reactor.fstream_read_bytes',
    'scylla_reactor_fstream_read_bytes_blocked': 'reactor.fstream_read_bytes_blocked',
    'scylla_reactor_fstream_reads': 'reactor.fstream_reads',
    'scylla_reactor_fstream_reads_ahead_bytes_discarded': 'reactor.fstream_reads_ahead_bytes_discarded',
    'scylla_reactor_fstream_reads_aheads_discarded': 'reactor.fstream_reads_aheads_discarded',
    'scylla_reactor_fstream_reads_blocked': 'reactor.fstream_reads_blocked',
    'scylla_reactor_fsyncs': 'reactor.fsyncs',
    'scylla_reactor_io_queue_requests': 'reactor.io_queue_requests',
    'scylla_reactor_io_threaded_fallbacks': 'reactor.io_threaded_fallbacks',
    'scylla_reactor_logging_failures': 'reactor.logging_failures',
    'scylla_reactor_polls': 'reactor.polls',
    'scylla_reactor_tasks_pending': 'reactor.tasks_pending',
    'scylla_reactor_tasks_processed': 'reactor.tasks_processed',
    'scylla_reactor_timers_pending': 'reactor.timers_pending',
    'scylla_reactor_utilization': 'reactor.utilization',
}

SCYLLA_SCHEDULER = {
    'scylla_scheduler_queue_length': 'scheduler.queue_length',
    'scylla_scheduler_runtime_ms': 'scheduler.runtime_ms',
    'scylla_scheduler_shares': 'scheduler.shares',
    'scylla_scheduler_tasks_processed': 'scheduler.tasks_processed',
    'scylla_scheduler_time_spent_on_task_quota_violations_ms': 'scheduler.time_spent_on_task_quota_violations_ms',
}

SCYLLA_SSTABLES = {
    'scylla_sstables_capped_local_deletion_time': 'sstables.capped_local_deletion_time',
    'scylla_sstables_capped_tombstone_deletion_time': 'sstables.capped_tombstone_deletion_time',
    'scylla_sstables_cell_tombstone_writes': 'sstables.cell_tombstone_writes',
    'scylla_sstables_cell_writes': 'sstables.cell_writes',
    'scylla_sstables_index_page_blocks': 'sstables.index_page_blocks',
    'scylla_sstables_index_page_hits': 'sstables.index_page_hits',
    'scylla_sstables_index_page_misses': 'sstables.index_page_misses',
    'scylla_sstables_partition_reads': 'sstables.partition_reads',
    'scylla_sstables_partition_seeks': 'sstables.partition_seeks',
    'scylla_sstables_partition_writes': 'sstables.partition_writes',
    'scylla_sstables_range_partition_reads': 'sstables.range_partition_reads',
    'scylla_sstables_range_tombstone_writes': 'sstables.range_tombstone_writes',
    'scylla_sstables_row_reads': 'sstables.row_reads',
    'scylla_sstables_row_writes': 'sstables.row_writes',
    'scylla_sstables_single_partition_reads': 'sstables.single_partition_reads',
    'scylla_sstables_sstable_partition_reads': 'sstables.sstable_partition_reads',
    'scylla_sstables_static_row_writes': 'sstables.static_row_writes',
    'scylla_sstables_tombstone_writes': 'sstables.tombstone_writes',
}

SCYLLA_STORAGE = {
    # Scylla 3.1
    'scylla_storage_proxy_coordinator_background_read_repairs': 'storage.proxy.coordinator_background_read_repairs',
    'scylla_storage_proxy_coordinator_background_reads': 'storage.proxy.coordinator_background_reads',
    'scylla_storage_proxy_coordinator_background_replica_writes_failed_local_node': 'storage.proxy.coordinator_background_replica_writes_failed_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_background_write_bytes': 'storage.proxy.coordinator_background_write_bytes',
    'scylla_storage_proxy_coordinator_background_writes': 'storage.proxy.coordinator_background_writes',
    'scylla_storage_proxy_coordinator_background_writes_failed': 'storage.proxy.coordinator_background_writes_failed',
    'scylla_storage_proxy_coordinator_canceled_read_repairs': 'storage.proxy.coordinator_canceled_read_repairs',
    'scylla_storage_proxy_coordinator_completed_reads_local_node': 'storage.proxy.coordinator_completed_reads_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_current_throttled_base_writes': 'storage.proxy.coordinator_current_throttled_base_writes',  # noqa E501
    'scylla_storage_proxy_coordinator_current_throttled_writes': 'storage.proxy.coordinator_current_throttled_writes',
    'scylla_storage_proxy_coordinator_foreground_read_repair': 'storage.proxy.coordinator_foreground_read_repair',
    'scylla_storage_proxy_coordinator_foreground_reads': 'storage.proxy.coordinator_foreground_reads',
    'scylla_storage_proxy_coordinator_foreground_writes': 'storage.proxy.coordinator_foreground_writes',
    'scylla_storage_proxy_coordinator_last_mv_flow_control_delay': 'storage.proxy.coordinator_last_mv_flow_control_delay',  # noqa E501
    'scylla_storage_proxy_coordinator_queued_write_bytes': 'storage.proxy.coordinator_queued_write_bytes',
    'scylla_storage_proxy_coordinator_range_timeouts': 'storage.proxy.coordinator_range_timeouts',
    'scylla_storage_proxy_coordinator_range_unavailable': 'storage.proxy.coordinator_range_unavailable',
    'scylla_storage_proxy_coordinator_read_errors_local_node': 'storage.proxy.coordinator_read_errors_local_node',
    'scylla_storage_proxy_coordinator_read_latency': 'storage.proxy.coordinator_read_latency',
    'scylla_storage_proxy_coordinator_read_repair_write_attempts_local_node': 'storage.proxy.coordinator_read_repair_write_attempts_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_read_retries': 'storage.proxy.coordinator_read_retries',
    'scylla_storage_proxy_coordinator_read_timeouts': 'storage.proxy.coordinator_read_timeouts',
    'scylla_storage_proxy_coordinator_read_unavailable': 'storage.proxy.coordinator_read_unavailable',
    'scylla_storage_proxy_coordinator_reads_local_node': 'storage.proxy.coordinator_reads_local_node',
    'scylla_storage_proxy_coordinator_speculative_data_reads': 'storage.proxy.coordinator_speculative_data_reads',
    'scylla_storage_proxy_coordinator_speculative_digest_reads': 'storage.proxy.coordinator_speculative_digest_reads',
    'scylla_storage_proxy_coordinator_throttled_writes': 'storage.proxy.coordinator_throttled_writes',
    'scylla_storage_proxy_coordinator_total_write_attempts_local_node': 'storage.proxy.coordinator_total_write_attempts_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_write_errors_local_node': 'storage.proxy.coordinator_write_errors_local_node',
    'scylla_storage_proxy_coordinator_write_latency': 'storage.proxy.coordinator_write_latency',
    'scylla_storage_proxy_coordinator_write_timeouts': 'storage.proxy.coordinator_write_timeouts',
    'scylla_storage_proxy_coordinator_write_unavailable': 'storage.proxy.coordinator_write_unavailable',
    'scylla_storage_proxy_replica_cross_shard_ops': 'storage.proxy.replica_cross_shard_ops',
    'scylla_storage_proxy_replica_forwarded_mutations': 'storage.proxy.replica_forwarded_mutations',
    'scylla_storage_proxy_replica_forwarding_errors': 'storage.proxy.replica_forwarding_errors',
    'scylla_storage_proxy_replica_reads': 'storage.proxy.replica_reads',
    'scylla_storage_proxy_replica_received_counter_updates': 'storage.proxy.replica_received_counter_updates',
    'scylla_storage_proxy_replica_received_mutations': 'storage.proxy.replica_received_mutations',
    # Scylla 3.2 - renamed
    'scylla_storage_proxy_coordinator_foreground_read_repairs': 'storage.proxy.coordinator_foreground_read_repair',
}

SCYLLA_STREAMING = {
    'scylla_streaming_total_incoming_bytes': 'streaming.total_incoming_bytes',
    'scylla_streaming_total_outgoing_bytes': 'streaming.total_outgoing_bytes',
}

SCYLLA_THRIFT = {
    'scylla_thrift_current_connections': 'thrift.current_connections',
    'scylla_thrift_served': 'thrift.served',
    'scylla_thrift_thrift_connections': 'thrift.thrift_connections',
}

SCYLLA_TRACING = {
    'scylla_tracing_active_sessions': 'tracing.active_sessions',
    'scylla_tracing_cached_records': 'tracing.cached_records',
    'scylla_tracing_dropped_records': 'tracing.dropped_records',
    'scylla_tracing_dropped_sessions': 'tracing.dropped_sessions',
    'scylla_tracing_flushing_records': 'tracing.flushing_records',
    'scylla_tracing_keyspace_helper_bad_column_family_errors': 'tracing.keyspace_helper_bad_column_family_errors',
    'scylla_tracing_keyspace_helper_tracing_errors': 'tracing.keyspace_helper_tracing_errors',
    'scylla_tracing_pending_for_write_records': 'tracing.pending_for_write_records',
    'scylla_tracing_trace_errors': 'tracing.trace_errors',
    'scylla_tracing_trace_records_count': 'tracing.trace_records_count',
}

SCYLLA_TRANSPORT = {
    'scylla_transport_cql_connections': 'transport.cql_connections',
    'scylla_transport_current_connections': 'transport.current_connections',
    'scylla_transport_requests_blocked_memory': 'transport.requests_blocked_memory',
    'scylla_transport_requests_blocked_memory_current': 'transport.requests_blocked_memory_current',
    'scylla_transport_requests_served': 'transport.requests_served',
    'scylla_transport_requests_serving': 'transport.requests_serving',
}

INSTANCE_DEFAULT_METRICS = [
    SCYLLA_CACHE,
    SCYLLA_COMPACTION,
    SCYLLA_GOSSIP,
    SCYLLA_NODE,
    SCYLLA_REACTOR,
    SCYLLA_STORAGE,
    SCYLLA_STREAMING,
    SCYLLA_TRANSPORT,
]


ADDITIONAL_METRICS_MAP = {
    'scylla.alien': SCYLLA_ALIEN,
    'scylla.batchlog_manager': SCYLLA_BATCHLOG_MANAGER,
    'scylla.commitlog': SCYLLA_COMMITLOG,
    'scylla.cql': SCYLLA_CQL,
    'scylla.database': SCYLLA_DATABASE,
    'scylla.execution_stages': SCYLLA_EXECUTION_STAGES,
    'scylla.hints': SCYLLA_HINTS,
    'scylla.httpd': SCYLLA_HTTPD,
    'scylla.io_queue': SCYLLA_IO_QUEUE,
    'scylla.lsa': SCYLLA_LSA,
    'scylla.memory': SCYLLA_MEMORY,
    'scylla.memtables': SCYLLA_MEMTABLES,
    'scylla.query_processor': SCYLLA_QUERY_PROCESSOR,
    'scylla.scheduler': SCYLLA_SCHEDULER,
    'scylla.sstables': SCYLLA_SSTABLES,
    'scylla.thrift': SCYLLA_THRIFT,
    'scylla.tracing': SCYLLA_TRACING,
}
