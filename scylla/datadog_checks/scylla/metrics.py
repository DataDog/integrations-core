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
    'scylla_cache_dummy_row_hits': 'cache.dummy_row_hits',
    'scylla_cache_mispopulations': 'cache.mispopulations',
    'scylla_cache_partition_evictions': 'cache.partition_evictions',
    'scylla_cache_partition_hits': 'cache.partition_hits',
    'scylla_cache_partition_insertions': 'cache.partition_insertions',
    'scylla_cache_partition_merges': 'cache.partition_merges',
    'scylla_cache_partition_misses': 'cache.partition_misses',
    'scylla_cache_partition_removals': 'cache.partition_removals',
    'scylla_cache_partitions': 'cache.partitions',
    'scylla_cache_pinned_dirty_memory_overload': 'cache.pinned_dirty_memory_overload',
    'scylla_cache_range_tombstone_reads': 'cache.range_tombstone_reads',
    'scylla_cache_reads': 'cache.reads',
    'scylla_cache_reads_with_misses': 'cache.reads_with_misses',
    'scylla_cache_row_evictions': 'cache.row_evictions',
    'scylla_cache_row_hits': 'cache.row_hits',
    'scylla_cache_row_insertions': 'cache.row_insertions',
    'scylla_cache_row_misses': 'cache.row_misses',
    'scylla_cache_row_removals': 'cache.row_removals',
    'scylla_cache_row_tombstone_reads': 'cache.row_tombstone_reads',
    'scylla_cache_rows': 'cache.rows',
    'scylla_cache_rows_compacted_with_tombstones': 'cache.rows_compacted_with_tombstones',
    'scylla_cache_rows_dropped_by_tombstones': 'cache.rows_dropped_by_tombstones',
    'scylla_cache_rows_dropped_from_memtable': 'cache.rows_dropped_from_memtable',
    'scylla_cache_rows_merged_from_memtable': 'cache.rows_merged_from_memtable',
    'scylla_cache_rows_processed_from_memtable': 'cache.rows_processed_from_memtable',
    'scylla_cache_sstable_partition_skips': 'cache.sstable_partition_skips',
    'scylla_cache_sstable_reader_recreations': 'cache.sstable_reader_recreations',
    'scylla_cache_sstable_row_skips': 'cache.sstable_row_skips',
    'scylla_cache_static_row_insertions': 'cache.static_row_insertions',
}

SCYLLA_CDC = {
    'scylla_cdc_operations_failed': 'cdc.operations_failed',
    'scylla_cdc_operations_on_clustering_row_performed_failed': 'cdc.operations_on_clustering_row_performed_failed',
    'scylla_cdc_operations_on_clustering_row_performed_total': 'cdc.operations_on_clustering_row_performed_total',
    'scylla_cdc_operations_on_list_performed_failed': 'cdc.operations_on_list_performed_failed',
    'scylla_cdc_operations_on_list_performed_total': 'cdc.operations_on_list_performed_total',
    'scylla_cdc_operations_on_map_performed_failed': 'cdc.operations_on_map_performed_failed',
    'scylla_cdc_operations_on_map_performed_total': 'cdc.operations_on_map_performed_total',
    'scylla_cdc_operations_on_partition_delete_performed_failed': 'cdc.operations_on_partition_delete_performed_failed',
    'scylla_cdc_operations_on_partition_delete_performed_total': 'cdc.operations_on_partition_delete_performed_total',
    'scylla_cdc_operations_on_range_tombstone_performed_failed': 'cdc.operations_on_range_tombstone_performed_failed',
    'scylla_cdc_operations_on_range_tombstone_performed_total': 'cdc.operations_on_range_tombstone_performed_total',
    'scylla_cdc_operations_on_row_delete_performed_failed': 'cdc.operations_on_row_delete_performed_failed',
    'scylla_cdc_operations_on_row_delete_performed_total': 'cdc.operations_on_row_delete_performed_total',
    'scylla_cdc_operations_on_set_performed_failed': 'cdc.operations_on_set_performed_failed',
    'scylla_cdc_operations_on_set_performed_total': 'cdc.operations_on_set_performed_total',
    'scylla_cdc_operations_on_static_row_performed_failed': 'cdc.operations_on_static_row_performed_failed',
    'scylla_cdc_operations_on_static_row_performed_total': 'cdc.operations_on_static_row_performed_total',
    'scylla_cdc_operations_on_udt_performed_failed': 'cdc.operations_on_udt_performed_failed',
    'scylla_cdc_operations_on_udt_performed_total': 'cdc.operations_on_udt_performed_total',
    'scylla_cdc_operations_total': 'cdc.operations_total',
    'scylla_cdc_operations_with_postimage_failed': 'cdc.operations_with_postimage_failed',
    'scylla_cdc_operations_with_postimage_total': 'cdc.operations_with_postimage_total',
    'scylla_cdc_operations_with_preimage_failed': 'cdc.operations_with_preimage_failed',
    'scylla_cdc_operations_with_preimage_total': 'cdc.operations_with_preimage_total',
    'scylla_cdc_preimage_selects_failed': 'cdc.preimage_selects_failed',
    'scylla_cdc_preimage_selects_total': 'cdc.preimage_selects_total',
}

SCYLLA_COMMITLOG = {
    'scylla_commitlog_active_allocations': 'commitlog.active_allocations',
    'scylla_commitlog_alloc': 'commitlog.alloc',
    'scylla_commitlog_allocating_segments': 'commitlog.allocating_segments',
    'scylla_commitlog_blocked_on_new_segment': 'commitlog.blocked_on_new_segment',
    'scylla_commitlog_bytes_flush_requested': 'commitlog.bytes_flush_requested',
    'scylla_commitlog_bytes_released': 'commitlog.bytes_released',
    'scylla_commitlog_bytes_written': 'commitlog.bytes_written',
    'scylla_commitlog_cycle': 'commitlog.cycle',
    'scylla_commitlog_disk_active_bytes': 'commitlog.disk_active_bytes',
    'scylla_commitlog_disk_slack_end_bytes': 'commitlog.disk_slack_end_bytes',
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
    'scylla_compaction_manager_backlog': 'compaction_manager.backlog',
    'scylla_compaction_manager_compactions': 'compaction_manager.compactions',
    'scylla_compaction_manager_completed_compactions': 'compaction_manager.completed_compactions',
    'scylla_compaction_manager_failed_compactions': 'compaction_manager.failed_compactions',
    'scylla_compaction_manager_normalized_backlog': 'compaction_manager.normalized_backlog',
    'scylla_compaction_manager_pending_compactions': 'compaction_manager.pending_compactions',
    'scylla_compaction_manager_postponed_compactions': 'compaction_manager.postponed_compactions',
    'scylla_compaction_manager_validation_errors': 'compaction_manager.validation_errors',
}

SCYLLA_CQL = {
    'scylla_cql_authorized_prepared_statements_cache_evictions': 'cql.authorized_prepared_statements_cache_evictions',
    'scylla_cql_authorized_prepared_statements_cache_size': 'cql.authorized_prepared_statements_cache_size',
    'scylla_cql_batches': 'cql.batches',
    'scylla_cql_batches_pure_logged': 'cql.batches_pure_logged',
    'scylla_cql_batches_pure_unlogged': 'cql.batches_pure_unlogged',
    'scylla_cql_batches_unlogged_from_logged': 'cql.batches_unlogged_from_logged',
    'scylla_cql_deletes': 'cql.deletes',
    'scylla_cql_deletes_per_ks': 'cql.deletes_per_ks',
    'scylla_cql_filtered_read_requests': 'cql.filtered_read_requests',
    'scylla_cql_filtered_rows_dropped_total': 'cql.filtered_rows_dropped_total',
    'scylla_cql_filtered_rows_matched_total': 'cql.filtered_rows_matched_total',
    'scylla_cql_filtered_rows_read_total': 'cql.filtered_rows_read_total',
    'scylla_cql_inserts': 'cql.inserts',
    'scylla_cql_inserts_per_ks': 'cql.inserts_per_ks',
    'scylla_cql_prepared_cache_evictions': 'cql.prepared_cache_evictions',
    'scylla_cql_prepared_cache_memory_footprint': 'cql.prepared_cache_memory_footprint',
    'scylla_cql_prepared_cache_size': 'cql.prepared_cache_size',
    'scylla_cql_reads': 'cql.reads',
    'scylla_cql_reads_per_ks': 'cql.reads_per_ks',
    'scylla_cql_reverse_queries': 'cql.reverse_queries',
    'scylla_cql_rows_read': 'cql.rows_read',
    'scylla_cql_secondary_index_creates': 'cql.secondary_index_creates',
    'scylla_cql_secondary_index_drops': 'cql.secondary_index_drops',
    'scylla_cql_secondary_index_reads': 'cql.secondary_index_reads',
    'scylla_cql_secondary_index_rows_read': 'cql.secondary_index_rows_read',
    'scylla_cql_select_allow_filtering': 'cql.select_allow_filtering',
    'scylla_cql_select_bypass_caches': 'cql.select_bypass_caches',
    'scylla_cql_select_parallelized': 'cql.select_parallelized',
    'scylla_cql_select_partition_range_scan': 'cql.select_partition_range_scan',
    'scylla_cql_select_partition_range_scan_no_bypass_cache': 'cql.select_partition_range_scan_no_bypass_cache',
    'scylla_cql_statements_in_batches': 'cql.statements_in_batches',
    'scylla_cql_unpaged_select_queries': 'cql.unpaged_select_queries',
    'scylla_cql_unpaged_select_queries_per_ks': 'cql.unpaged_select_queries_per_ks',
    'scylla_cql_unprivileged_entries_evictions_on_size': 'cql.unprivileged_entries_evictions_on_size',
    'scylla_cql_updates': 'cql.updates',
    'scylla_cql_updates_per_ks': 'cql.updates_per_ks',
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
    'scylla_database_disk_reads': 'database.disk_reads',
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
    'scylla_database_reads_shed_due_to_overload': 'database.reads_shed_due_to_overload',
    'scylla_database_requests_blocked_memory': 'database.requests_blocked_memory',
    'scylla_database_requests_blocked_memory_current': 'database.requests_blocked_memory_current',
    'scylla_database_schema_changed': 'database.schema_changed',
    'scylla_database_short_data_queries': 'database.short_data_queries',
    'scylla_database_short_mutation_queries': 'database.short_mutation_queries',
    'scylla_database_sstables_read': 'database.sstable_read',
    'scylla_database_sstable_read_queue_overloads': 'database.sstable_read_queue_overloads',
    'scylla_database_total_reads': 'database.total_reads',
    'scylla_database_total_reads_failed': 'database.total_reads_failed',
    'scylla_database_total_reads_rate_limited': 'database.reads_rate_limited',
    'scylla_database_total_result_bytes': 'database.total_result_bytes',
    'scylla_database_total_view_updates_failed_local': 'database.total_view_updates_failed_local',
    'scylla_database_total_view_updates_failed_remote': 'database.total_view_updates_failed_remote',
    'scylla_database_total_view_updates_pushed_local': 'database.total_view_updates_pushed_local',
    'scylla_database_total_view_updates_pushed_remote': 'database.total_view_updates_pushed_remote',
    'scylla_database_total_writes': 'database.total_writes',
    'scylla_database_total_writes_failed': 'database.total_writes_failed',
    'scylla_database_total_writes_rate_limited': 'database.writes_rate_limited',
    'scylla_database_total_writes_timedout': 'database.total_writes_timedout',
    'scylla_database_view_building_paused': 'database.view_building_paused',
    'scylla_database_view_update_backlog': 'database.view_update_backlog',
    # Scylla 5.2 - renamed
    'scylla_database_reads_memory_consumption': 'database.active_reads_memory_consumption',
}

SCYLLA_EXECUTION_STAGES = {
    'scylla_execution_stages_function_calls_enqueued': 'execution_stages.function_calls_enqueued',
    'scylla_execution_stages_function_calls_executed': 'execution_stages.function_calls_executed',
    'scylla_execution_stages_tasks_preempted': 'execution_stages.tasks_preempted',
    'scylla_execution_stages_tasks_scheduled': 'execution_stages.tasks_scheduled',
}

SCYLLA_FORWARD_SERVICE = {
    'scylla_forward_service_requests_dispatched_to_other_nodes': 'forward_service.requests_dispatched_to_other_nodes',
    'scylla_forward_service_requests_dispatched_to_own_shards': 'forward_service.requests_dispatched_to_own_shards',
    'scylla_forward_service_requests_executed': 'forward_service.requests_executed',
}

SCYLLA_GOSSIP = {
    'scylla_gossip_heart_beat': 'gossip.heart_beat',
    'scylla_gossip_live': 'gossip.live',
    'scylla_gossip_unreachable': 'gossip.unreachable',
}

SCYLLA_HINTS = {
    'scylla_hints_for_views_manager_corrupted_files': 'hints.for_views_manager_corrupted_files',
    'scylla_hints_for_views_manager_discarded': 'hints.for_views_manager_discarded',
    'scylla_hints_for_views_manager_dropped': 'hints.for_views_manager_dropped',
    'scylla_hints_for_views_manager_errors': 'hints.for_views_manager_errors',
    'scylla_hints_for_views_manager_sent': 'hints.for_views_manager_sent',
    'scylla_hints_for_views_manager_size_of_hints_in_progress': 'hints.for_views_manager_size_of_hints_in_progress',
    'scylla_hints_for_views_manager_written': 'hints.for_views_manager_written',
    'scylla_hints_for_views_manager_pending_drains': 'hints.for_views_manager_pending_drains',
    'scylla_hints_for_views_manager_pending_sends': 'hints.for_views_manager_pending_sends',
    'scylla_hints_manager_pending_drains': 'hints.manager_pending_drains',
    'scylla_hints_manager_pending_sends': 'hints.manager_pending_sends',
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
    'scylla_io_queue_adjusted_consumption': 'io_queue.adjusted_consumption',
    'scylla_io_queue_consumption': 'io_queue.consumption',
    'scylla_io_queue_delay': 'io_queue.delay',
    'scylla_io_queue_disk_queue_length': 'io_queue.disk_queue_length',
    'scylla_io_queue_queue_length': 'io_queue.queue_length',
    'scylla_io_queue_shares': 'io_queue.shares',
    'scylla_io_queue_starvation_time_sec': 'io_queue.starvation_time_sec',
    'scylla_io_queue_total_bytes': 'io_queue.total_bytes',
    'scylla_io_queue_total_delay_sec': 'io_queue.total_delay_sec',
    'scylla_io_queue_total_exec_sec': 'io_queue.total_exec_sec',
    'scylla_io_queue_total_operations': 'io_queue.total_operations',
    'scylla_io_queue_total_read_bytes': 'io_queue.total_read_bytes',
    'scylla_io_queue_total_read_ops': 'io_queue.read_ops',
    'scylla_io_queue_total_split_bytes': 'io_queue.total_split_bytes',
    'scylla_io_queue_total_split_ops': 'io_queue.total_split_ops',
    'scylla_io_queue_total_write_bytes': 'io_queue.write_bytes',
    'scylla_io_queue_total_write_ops': 'io_queue.write_ops',
}

SCYLLA_LSA = {
    'scylla_lsa_free_space': 'lsa.free_space',
    'scylla_lsa_large_objects_total_space_bytes': 'lsa.large_objects_total_space_bytes',
    'scylla_lsa_memory_allocated': 'lsa.memory_allocated',
    'scylla_lsa_memory_compacted': 'lsa.memory_compacted',
    'scylla_lsa_memory_evicted': 'lsa.memory_evicted',
    'scylla_lsa_memory_freed': 'lsa.memory_freed',
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
    'scylla_memory_malloc_failed': 'memory.malloc_failed',
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
    # Scylla 5.2 - renamed
    'scylla_memory_regular_unspooled_dirty_bytes': 'memory.regular_virtual_dirty_bytes',
    'scylla_memory_system_unspooled_dirty_bytes': 'memory.system_virtual_dirty_bytes',
    'scylla_memory_unspooled_dirty_bytes': 'memory.virtual_dirty_bytes',
}

SCYLLA_MEMTABLES = {
    'scylla_memtables_failed_flushes': 'memtables.failed_flushes',
    'scylla_memtables_pending_flushes': 'memtables.pending_flushes',
    'scylla_memtables_pending_flushes_bytes': 'memtables.pending_flushes_bytes',
}

SCYLLA_NODE = {
    'scylla_node_operation_mode': 'node.operation_mode',
    'scylla_node_ops_finished_percentage': 'node.ops_finished_percentage',
}

SCYLLA_PER_PARTITION = {
    'scylla_per_partition_rate_limiter_allocations': 'per_partition.rate_limiter_allocations',
    'scylla_per_partition_rate_limiter_failed_allocations': 'per_partition.rate_limiter_failed_allocations',
    'scylla_per_partition_rate_limiter_load_factor': 'per_partition.rate_limiter_load_factor',
    'scylla_per_partition_rate_limiter_probe_count': 'per_partition.rate_limiter_probe_count',
    'scylla_per_partition_rate_limiter_successful_lookups': 'per_partition.rate_limiter_successful_lookups',
}

SCYLLA_QUERY_PROCESSOR = {
    'scylla_query_processor_queries': 'query_processor.queries',
    'scylla_query_processor_statements_prepared': 'query_processor.statements_prepared',
}

SCYLLA_RAFT = {
    'scylla_raft_add_entries': 'raft.add_entries',
    'scylla_raft_applied_entries': 'raft.applied_entries',
    'scylla_raft_group0_status': 'raft.group0_status',
    'scylla_raft_in_memory_log_size': 'raft.in_memory_log_size',
    'scylla_raft_messages_received': 'raft.messages_received',
    'scylla_raft_messages_sent': 'raft.messages_sent',
    'scylla_raft_persisted_log_entriespersisted_log_entries': 'raft.persisted_log_entriespersisted_log_entries',
    'scylla_raft_polls': 'raft.polls',
    'scylla_raft_queue_entries_for_apply': 'raft.queue_entries_for_apply',
    'scylla_raft_sm_load_snapshot': 'raft.sm_load_snapshot',
    'scylla_raft_snapshots_taken': 'raft.snapshots_taken',
    'scylla_raft_store_snapshot': 'raft.store_snapshot',
    'scylla_raft_store_term_and_vote': 'raft.store_term_and_vote',
    'scylla_raft_truncate_persisted_log': 'raft.truncate_persisted_log',
    'scylla_raft_waiter_awaiken': 'raft.waiter_awaiken',
    'scylla_raft_waiter_dropped': 'raft.waiter_dropped',
}

SCYLLA_REACTOR = {
    'scylla_reactor_abandoned_failed_futures': 'reactor.abandoned_failed_futures',
    'scylla_reactor_aio_bytes_read': 'reactor.aio_bytes_read',
    'scylla_reactor_aio_bytes_write': 'reactor.aio_bytes_write',
    'scylla_reactor_aio_errors': 'reactor.aio_errors',
    'scylla_reactor_aio_outsizes': 'reactor.aio_outsizes',
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

SCYLLA_REPAIR = {
    'scylla_repair_row_from_disk_bytes': 'repair.row_from_disk_bytes',
    'scylla_repair_row_from_disk_nr': 'repair.row_from_disk_nr',
    'scylla_repair_rx_hashes_nr': 'repair.rx_hashes_nr',
    'scylla_repair_rx_row_bytes': 'repair.rx_row_bytes',
    'scylla_repair_rx_row_nr': 'repair.rx_row_nr',
    'scylla_repair_tx_hashes_nr': 'repair.tx_hashes_nr',
    'scylla_repair_tx_row_bytes': 'repair.tx_row_bytes',
    'scylla_repair_tx_row_nr': 'repair.tx_row_nr',
}

SCYLLA_SCHEMA_COMMITLOG = {
    'scylla_schema_commitlog_active_allocations': 'schema_commitlog.active_allocations',
    'scylla_schema_commitlog_alloc': 'schema_commitlog.alloc',
    'scylla_schema_commitlog_allocating_segments': 'schema_commitlog.allocating_segments',
    'scylla_schema_commitlog_blocked_on_new_segment': 'schema_commitlog.blocked_on_new_segment',
    'scylla_schema_commitlog_bytes_flush_requested': 'schema_commitlog.bytes_flush_requested',
    'scylla_schema_commitlog_bytes_released': 'schema_commitlog.bytes_released',
    'scylla_schema_commitlog_bytes_written': 'schema_commitlog.bytes_written',
    'scylla_schema_commitlog_cycle': 'schema_commitlog.cycle',
    'scylla_schema_commitlog_disk_active_bytes': 'schema_commitlog.disk_active_bytes',
    'scylla_schema_commitlog_disk_slack_end_bytes': 'schema_commitlog.disk_slack_end_bytes',
    'scylla_schema_commitlog_disk_total_bytes': 'schema_commitlog.disk_total_bytes',
    'scylla_schema_commitlog_flush': 'schema_commitlog.flush',
    'scylla_schema_commitlog_flush_limit_exceeded': 'schema_commitlog.flush_limit_exceeded',
    'scylla_schema_commitlog_memory_buffer_bytes': 'schema_commitlog.memory_buffer_bytes',
    'scylla_schema_commitlog_pending_allocations': 'schema_commitlog.pending_allocations',
    'scylla_schema_commitlog_pending_flushes': 'schema_commitlog.pending_flushes',
    'scylla_schema_commitlog_requests_blocked_memory': 'schema_commitlog.requests_blocked_memory',
    'scylla_schema_commitlog_segments': 'schema_commitlog.segments',
    'scylla_schema_commitlog_slack': 'schema_commitlog.slack',
    'scylla_schema_commitlog_unused_segments': 'schema_commitlog.unused_segments',
}

SCYLLA_SCHEDULER = {
    'scylla_scheduler_queue_length': 'scheduler.queue_length',
    'scylla_scheduler_runtime_ms': 'scheduler.runtime_ms',
    'scylla_scheduler_shares': 'scheduler.shares',
    'scylla_scheduler_starvetime_ms': 'scheduler.starvetime_ms',
    'scylla_scheduler_tasks_processed': 'scheduler.tasks_processed',
    'scylla_scheduler_time_spent_on_task_quota_violations_ms': 'scheduler.time_spent_on_task_quota_violations_ms',
    'scylla_scheduler_waittime_ms': 'scheduler.waittime_ms',
}

SCYLLA_SSTABLES = {
    'scylla_sstables_bloom_filter_memory_size': 'sstables.bloom_filter_memory_size',
    'scylla_sstables_capped_local_deletion_time': 'sstables.capped_local_deletion_time',
    'scylla_sstables_capped_tombstone_deletion_time': 'sstables.capped_tombstone_deletion_time',
    'scylla_sstables_cell_tombstone_writes': 'sstables.cell_tombstone_writes',
    'scylla_sstables_cell_writes': 'sstables.cell_writes',
    'scylla_sstables_currently_open_for_reading': 'sstables.currently_open_for_reading',
    'scylla_sstables_currently_open_for_writing': 'sstables.currently_open_for_writing',
    'scylla_sstables_index_page_blocks': 'sstables.index_page_blocks',
    'scylla_sstables_index_page_cache_bytes': 'sstables.index_page_cache_bytes',
    'scylla_sstables_index_page_cache_bytes_in_std': 'sstables.index_page_cache_bytes_in_std',
    'scylla_sstables_index_page_cache_evictions': 'sstables.index_page_cache_evictions',
    'scylla_sstables_index_page_cache_hits': 'sstables.index_page_cache_hits',
    'scylla_sstables_index_page_cache_misses': 'sstables.index_page_cache_misses',
    'scylla_sstables_index_page_cache_populations': 'sstables.index_page_cache_populations',
    'scylla_sstables_index_page_evictions': 'sstables.index_page_evictions',
    'scylla_sstables_index_page_hits': 'sstables.index_page_hits',
    'scylla_sstables_index_page_misses': 'sstables.index_page_misses',
    'scylla_sstables_index_page_populations': 'sstables.index_page_populations',
    'scylla_sstables_index_page_used_bytes': 'sstables.index_page_used_bytes',
    'scylla_sstables_partition_reads': 'sstables.partition_reads',
    'scylla_sstables_partition_seeks': 'sstables.partition_seeks',
    'scylla_sstables_partition_writes': 'sstables.partition_writes',
    'scylla_sstables_pi_auto_scale_events': 'sstables.pi_auto_scale_events',
    'scylla_sstables_pi_cache_block_count': 'sstables.pi_cache_block_count',
    'scylla_sstables_pi_cache_bytes': 'sstables.pi_cache_bytes',
    'scylla_sstables_pi_cache_evictions': 'sstables.pi_cache_evictions',
    'scylla_sstables_pi_cache_hits_l0': 'sstables.pi_cache_hits_l0',
    'scylla_sstables_pi_cache_hits_l1': 'sstables.pi_cache_hits_l1',
    'scylla_sstables_pi_cache_hits_l2': 'sstables.pi_cache_hits_l2',
    'scylla_sstables_pi_cache_misses_l0': 'sstables.pi_cache_misses_l0',
    'scylla_sstables_pi_cache_misses_l1': 'sstables.pi_cache_misses_l1',
    'scylla_sstables_pi_cache_misses_l2': 'sstables.pi_cache_misses_l2',
    'scylla_sstables_pi_cache_populations': 'sstables.pi_cache_populations',
    'scylla_sstables_range_partition_reads': 'sstables.range_partition_reads',
    'scylla_sstables_range_tombstone_reads': 'sstables.range_tombstone_reads',
    'scylla_sstables_range_tombstone_writes': 'sstables.range_tombstone_writes',
    'scylla_sstables_row_reads': 'sstables.row_reads',
    'scylla_sstables_row_writes': 'sstables.row_writes',
    'scylla_sstables_row_tombstone_reads': 'sstables.row_tombstone_reads',
    'scylla_sstables_single_partition_reads': 'sstables.single_partition_reads',
    'scylla_sstables_sstable_partition_reads': 'sstables.sstable_partition_reads',
    'scylla_sstables_static_row_writes': 'sstables.static_row_writes',
    'scylla_sstables_tombstone_writes': 'sstables.tombstone_writes',
    'scylla_sstables_total_deleted': 'sstables.total_deleted',
    'scylla_sstables_total_open_for_reading': 'sstables.total_open_for_reading',
    'scylla_sstables_total_open_for_writing': 'sstables.total_open_for_writing',
}

SCYLLA_STALL = {
    'scylla_stall_detector_reported': 'stall.detector_reported',
}

SCYLLA_STORAGE = {
    'scylla_storage_proxy_coordinator_background_read_repairs': 'storage.proxy.coordinator_background_read_repairs',
    'scylla_storage_proxy_coordinator_background_reads': 'storage.proxy.coordinator_background_reads',
    'scylla_storage_proxy_coordinator_background_replica_writes_failed_local_node': 'storage.proxy.coordinator_background_replica_writes_failed_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_background_write_bytes': 'storage.proxy.coordinator_background_write_bytes',
    'scylla_storage_proxy_coordinator_background_writes': 'storage.proxy.coordinator_background_writes',
    'scylla_storage_proxy_coordinator_background_writes_failed': 'storage.proxy.coordinator_background_writes_failed',
    'scylla_storage_proxy_coordinator_canceled_read_repairs': 'storage.proxy.coordinator_canceled_read_repairs',
    'scylla_storage_proxy_coordinator_cas_background': 'storage.proxy.coordinator_cas_background',
    'scylla_storage_proxy_coordinator_cas_dropped_prune': 'storage.proxy.coordinator_cas_dropped_prune',
    'scylla_storage_proxy_coordinator_cas_failed_read_round_optimization': 'storage.proxy.coordinator_cas_failed_read_round_optimization',  # noqa E501
    'scylla_storage_proxy_coordinator_cas_foreground': 'storage.proxy.coordinator_cas_foreground',
    'scylla_storage_proxy_coordinator_cas_prune': 'storage.proxy.coordinator_cas_prune',
    'scylla_storage_proxy_coordinator_cas_read_contention': 'storage.proxy.coordinator_cas_read_contention',
    'scylla_storage_proxy_coordinator_cas_read_latency': 'storage.proxy.coordinator_cas_read_latency',
    'scylla_storage_proxy_coordinator_cas_read_latency_summary': 'storage.proxy.coordinator_cas_read_latency_summary',
    'scylla_storage_proxy_coordinator_cas_read_timeouts': 'storage.proxy.coordinator_cas_read_timouts',
    'scylla_storage_proxy_coordinator_cas_read_unavailable': 'storage.proxy.coordinator_cas_read_unavailable',
    'scylla_storage_proxy_coordinator_cas_read_unfinished_commit': 'storage.proxy.coordinator_cas_read_unfinished_commit',  # noqa E501
    'scylla_storage_proxy_coordinator_cas_write_condition_not_met': 'storage.proxy.coordinator_cas_write_condition_not_met',  # noqa E501
    'scylla_storage_proxy_coordinator_cas_write_contention': 'storage.proxy.coordinator_cas_write_contention',
    'scylla_storage_proxy_coordinator_cas_write_latency': 'storage.proxy.coordinator_cas_write_latency',
    'scylla_storage_proxy_coordinator_cas_write_latency_summary': 'storage.proxy.coordinator_cas_write_latency_summary',
    'scylla_storage_proxy_coordinator_cas_write_timeout_due_to_uncertainty': 'storage.proxy.coordinator_cas_write_timeout_due_to_uncertainty',  # noqa E501
    'scylla_storage_proxy_coordinator_cas_write_timeouts': 'storage.proxy.coordinator_cas_write_timeouts',
    'scylla_storage_proxy_coordinator_cas_write_unavailable': 'storage.proxy.coordinator_cas_write_unavailable',
    'scylla_storage_proxy_coordinator_cas_write_unfinished_commit': 'storage.proxy.coordinator_cas_write_unfinished_commit',  # noqa E501
    'scylla_storage_proxy_coordinator_cas_total_operations': 'storage.proxy.coordinator_cas_total_operations',
    'scylla_storage_proxy_coordinator_completed_reads_local_node': 'storage.proxy.coordinator_completed_reads_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_completed_reads_remote_node': 'storage.proxy_coordinator_completed_reads_remote_node',  # noqa E501
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
    'scylla_storage_proxy_coordinator_read_latency_summary': 'storage.proxy.coordinator_read_latency_summary',
    'scylla_storage_proxy_coordinator_read_repair_write_attempts_local_node': 'storage.proxy.coordinator_read_repair_write_attempts_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_read_repair_write_attempts_remote_node': 'storage.proxy.coordinator_read_repair_write_attempts_remote_node',  # noqa E501
    'scylla_storage_proxy_coordinator_read_rate_limited': 'storage.proxy.coordinator_read_rate_limited',
    'scylla_storage_proxy_coordinator_read_retries': 'storage.proxy.coordinator_read_retries',
    'scylla_storage_proxy_coordinator_read_timeouts': 'storage.proxy.coordinator_read_timeouts',
    'scylla_storage_proxy_coordinator_read_unavailable': 'storage.proxy.coordinator_read_unavailable',
    'scylla_storage_proxy_coordinator_reads_coordinator_outside_replica_set': 'storage.proxy.coordinator_reads_coordinator_outside_replica_set',  # noqa E501
    'scylla_storage_proxy_coordinator_reads_local_node': 'storage.proxy.coordinator_reads_local_node',
    'scylla_storage_proxy_coordinator_reads_remote_node': 'storage.proxy.coordinator_reads_remote_node',
    'scylla_storage_proxy_coordinator_speculative_data_reads': 'storage.proxy.coordinator_speculative_data_reads',
    'scylla_storage_proxy_coordinator_speculative_digest_reads': 'storage.proxy.coordinator_speculative_digest_reads',
    'scylla_storage_proxy_coordinator_throttled_writes': 'storage.proxy.coordinator_throttled_writes',
    'scylla_storage_proxy_coordinator_total_write_attempts_local_node': 'storage.proxy.coordinator_total_write_attempts_local_node',  # noqa E501
    'scylla_storage_proxy_coordinator_total_write_attempts_remote_node': 'storage.proxy.coordinator_total_write_attempts_remote_node',  # noqa E501
    'scylla_storage_proxy_coordinator_write_errors_local_node': 'storage.proxy.coordinator_write_errors_local_node',
    'scylla_storage_proxy_coordinator_write_latency': 'storage.proxy.coordinator_write_latency',
    'scylla_storage_proxy_coordinator_write_latency_summary': 'storage.proxy.coordinator_write_latency_summary',
    'scylla_storage_proxy_coordinator_write_rate_limited': 'storage.proxy.coordinator_write_rate_limited',
    'scylla_storage_proxy_coordinator_write_timeouts': 'storage.proxy.coordinator_write_timeouts',
    'scylla_storage_proxy_coordinator_write_unavailable': 'storage.proxy.coordinator_write_unavailable',
    'scylla_storage_proxy_coordinator_writes_coordinator_outside_replica_set': 'storage.proxy.coordinator_writes_coordinator_outside_replica_set',  # noqa E501
    'scylla_storage_proxy_coordinator_writes_failed_due_to_too_many_in_flight_hints': 'storage.proxy.coordinator_writes_failed_due_to_too_many_in_flight_hints',  # noqa E501
    'scylla_storage_proxy_replica_cas_dropped_prune': 'storage.proxy.replica_cas_dropped_prune',
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
    'scylla_streaming_finished_percentage': 'streaming.finished_percentage',
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
    'scylla_transport_auth_responses': 'transport.auth_responses',
    'scylla_transport_batch_requests': 'transport.cql_connections',
    'scylla_transport_cql_connections': 'transport.cql_connections',
    'scylla_transport_cql_errors_total': 'transport.cql_errors_total',
    'scylla_transport_current_connections': 'transport.current_connections',
    'scylla_transport_execute_requests': 'transport.execute_requests',
    'scylla_transport_options_requests': 'transport.options_requests',
    'scylla_transport_prepare_requests': 'transport.prepare_requests',
    'scylla_transport_query_requests': 'transport.query_requests',
    'scylla_transport_register_requests': 'transport.register_requests',
    'scylla_transport_requests_blocked_memory': 'transport.requests_blocked_memory',
    'scylla_transport_requests_blocked_memory_current': 'transport.requests_blocked_memory_current',
    'scylla_transport_requests_memory_available': 'transport.requests_memory_available',
    'scylla_transport_requests_served': 'transport.requests_served',
    'scylla_transport_requests_serving': 'transport.requests_serving',
    'scylla_transport_requests_shed': 'transport.requests_shed',
    'scylla_transport_startups': 'transport.startups',
}

SCYLLA_VIEW = {
    'scylla_view_builder_builds_in_progress': 'view.builder_builds_in_progress',
    'scylla_view_builder_pending_bookkeeping_ops': 'view.builder_builds_in_progress',
    'scylla_view_builder_steps_failed': 'view.builder_steps_failed',
    'scylla_view_builder_steps_performed': 'view.builder_steps_performed',
    'scylla_view_update_generator_pending_registrations': 'view.update_generator_pending_registrations',
    'scylla_view_update_generator_queued_batches_count': 'view.update_generator_queued_batches_count',
    'scylla_view_update_generator_sstables_pending_work': 'view.update_generator_sstables_pending_work',
    'scylla_view_update_generator_sstables_to_move_count': 'view.update_generator_sstables_to_move_count',
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
    'scylla.cdc': SCYLLA_CDC,
    'scylla.commitlog': SCYLLA_COMMITLOG,
    'scylla.cql': SCYLLA_CQL,
    'scylla.database': SCYLLA_DATABASE,
    'scylla.execution_stages': SCYLLA_EXECUTION_STAGES,
    'scylla.forward_service': SCYLLA_FORWARD_SERVICE,
    'scylla.hints': SCYLLA_HINTS,
    'scylla.httpd': SCYLLA_HTTPD,
    'scylla.io_queue': SCYLLA_IO_QUEUE,
    'scylla.lsa': SCYLLA_LSA,
    'scylla.memory': SCYLLA_MEMORY,
    'scylla.memtables': SCYLLA_MEMTABLES,
    'scylla.per_partition': SCYLLA_PER_PARTITION,
    'scylla.query_processor': SCYLLA_QUERY_PROCESSOR,
    'scylla.raft': SCYLLA_RAFT,
    'scylla.repair': SCYLLA_REPAIR,
    'scylla.scheduler': SCYLLA_SCHEDULER,
    'scylla.schema_commitlog': SCYLLA_SCHEMA_COMMITLOG,
    'scylla.sstables': SCYLLA_SSTABLES,
    'scylla.stall': SCYLLA_STALL,
    'scylla.thrift': SCYLLA_THRIFT,
    'scylla.tracing': SCYLLA_TRACING,
    'scylla.view': SCYLLA_VIEW,
}

NON_CONFORMING_LIST = [
    'cache.bytes_total',
]


def construct_metrics_config(metrics):
    # turns the metrics from a list of dicts to a flat dict
    metric_map = {}
    for metric_group in metrics:
        metric_map.update(metric_group)  # we're turning a list of dicts into a flat dict then back into a list of dicts

    # interate over the flat dict and create the metric config
    metrics = []
    for raw_metric_name, metric_name in metric_map.items():
        if raw_metric_name.endswith('_total') and metric_name not in NON_CONFORMING_LIST:
            if metric_name.endswith('.count'):
                metric_name = metric_name[:-6]
            raw_metric_name = raw_metric_name[:-6]

        config = {raw_metric_name: {'name': metric_name}}
        metrics.append(config)
    return metrics
