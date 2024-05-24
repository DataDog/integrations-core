# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

GAUGE = "gauge"
RATE = "rate"
COUNT = "count"
MONOTONIC = "monotonic_count"
PROC_NAME = 'mysqld'
AWS_RDS_HOSTNAME_SUFFIX = ".rds.amazonaws.com"
AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE = {
    "flexible_server": "azure_mysql_flexible_server",
    "single_server": "azure_mysql_server",
    "virtual_machine": "azure_virtual_machine_instance",
}

# Vars found in "SHOW STATUS;"
STATUS_VARS = {
    # Command Metrics
    'Prepared_stmt_count': ('mysql.performance.prepared_stmt_count', GAUGE),
    'Slow_queries': ('mysql.performance.slow_queries', RATE),
    'Questions': ('mysql.performance.questions', RATE),
    'Queries': ('mysql.performance.queries', RATE),
    'Com_select': ('mysql.performance.com_select', RATE),
    'Com_insert': ('mysql.performance.com_insert', RATE),
    'Com_update': ('mysql.performance.com_update', RATE),
    'Com_delete': ('mysql.performance.com_delete', RATE),
    'Com_replace': ('mysql.performance.com_replace', RATE),
    'Com_load': ('mysql.performance.com_load', RATE),
    'Com_insert_select': ('mysql.performance.com_insert_select', RATE),
    'Com_update_multi': ('mysql.performance.com_update_multi', RATE),
    'Com_delete_multi': ('mysql.performance.com_delete_multi', RATE),
    'Com_replace_select': ('mysql.performance.com_replace_select', RATE),
    # Connection Metrics
    'Connections': ('mysql.net.connections', RATE),
    'Max_used_connections': ('mysql.net.max_connections', GAUGE),
    'Aborted_clients': ('mysql.net.aborted_clients', RATE),
    'Aborted_connects': ('mysql.net.aborted_connects', RATE),
    # Table Cache Metrics
    'Open_files': ('mysql.performance.open_files', GAUGE),
    'Open_tables': ('mysql.performance.open_tables', GAUGE),
    # Network Metrics
    'Bytes_sent': ('mysql.performance.bytes_sent', RATE),
    'Bytes_received': ('mysql.performance.bytes_received', RATE),
    # Query Cache Metrics
    'Qcache_hits': ('mysql.performance.qcache_hits', RATE),
    'Qcache_inserts': ('mysql.performance.qcache_inserts', RATE),
    'Qcache_lowmem_prunes': ('mysql.performance.qcache_lowmem_prunes', RATE),
    # Table Lock Metrics
    'Table_locks_waited': ('mysql.performance.table_locks_waited', GAUGE),
    'Table_locks_waited_rate': ('mysql.performance.table_locks_waited.rate', RATE),
    # Temporary Table Metrics
    'Created_tmp_tables': ('mysql.performance.created_tmp_tables', RATE),
    'Created_tmp_disk_tables': ('mysql.performance.created_tmp_disk_tables', RATE),
    'Created_tmp_files': ('mysql.performance.created_tmp_files', RATE),
    # Thread Metrics
    'Threads_connected': ('mysql.performance.threads_connected', GAUGE),
    'Threads_running': ('mysql.performance.threads_running', GAUGE),
    # MyISAM Metrics
    'Key_buffer_bytes_unflushed': ('mysql.myisam.key_buffer_bytes_unflushed', GAUGE),
    'Key_buffer_bytes_used': ('mysql.myisam.key_buffer_bytes_used', GAUGE),
    'Key_read_requests': ('mysql.myisam.key_read_requests', RATE),
    'Key_reads': ('mysql.myisam.key_reads', RATE),
    'Key_write_requests': ('mysql.myisam.key_write_requests', RATE),
    'Key_writes': ('mysql.myisam.key_writes', RATE),
}

# Possibly from SHOW GLOBAL VARIABLES
VARIABLES_VARS = {
    'Key_buffer_size': ('mysql.myisam.key_buffer_size', GAUGE),
    'Key_cache_utilization': ('mysql.performance.key_cache_utilization', GAUGE),
    'max_connections': ('mysql.net.max_connections_available', GAUGE),
    'max_prepared_stmt_count': ('mysql.performance.max_prepared_stmt_count', GAUGE),
    'query_cache_size': ('mysql.performance.qcache_size', GAUGE),
    'table_open_cache': ('mysql.performance.table_open_cache', GAUGE),
    'thread_cache_size': ('mysql.performance.thread_cache_size', GAUGE),
}

INNODB_VARS = {
    # InnoDB metrics
    'Innodb_data_reads': ('mysql.innodb.data_reads', RATE),
    'Innodb_data_writes': ('mysql.innodb.data_writes', RATE),
    'Innodb_os_log_fsyncs': ('mysql.innodb.os_log_fsyncs', RATE),
    'Innodb_mutex_spin_waits': ('mysql.innodb.mutex_spin_waits', RATE),
    'Innodb_mutex_spin_rounds': ('mysql.innodb.mutex_spin_rounds', RATE),
    'Innodb_mutex_os_waits': ('mysql.innodb.mutex_os_waits', RATE),
    'Innodb_row_lock_waits': ('mysql.innodb.row_lock_waits', RATE),
    'Innodb_row_lock_time': ('mysql.innodb.row_lock_time', RATE),
    'Innodb_row_lock_current_waits': ('mysql.innodb.row_lock_current_waits', GAUGE),
    'Innodb_current_row_locks': ('mysql.innodb.current_row_locks', GAUGE),
    'Innodb_buffer_pool_bytes_dirty': ('mysql.innodb.buffer_pool_dirty', GAUGE),
    'Innodb_buffer_pool_bytes_free': ('mysql.innodb.buffer_pool_free', GAUGE),
    'Innodb_buffer_pool_bytes_used': ('mysql.innodb.buffer_pool_used', GAUGE),
    'Innodb_buffer_pool_bytes_total': ('mysql.innodb.buffer_pool_total', GAUGE),
    'Innodb_buffer_pool_read_requests': ('mysql.innodb.buffer_pool_read_requests', RATE),
    'Innodb_buffer_pool_reads': ('mysql.innodb.buffer_pool_reads', RATE),
    'Innodb_buffer_pool_pages_utilization': ('mysql.innodb.buffer_pool_utilization', GAUGE),
}


# Calculated from "SHOW MASTER LOGS;"
BINLOG_VARS = {'Binlog_space_usage_bytes': ('mysql.binlog.disk_use', GAUGE)}

# Additional Vars found in "SHOW STATUS;"
# Will collect if [extra_status_metrics] is True
OPTIONAL_STATUS_VARS = {
    'Binlog_cache_disk_use': ('mysql.binlog.cache_disk_use', GAUGE),
    'Binlog_cache_use': ('mysql.binlog.cache_use', GAUGE),
    'Handler_commit': ('mysql.performance.handler_commit', RATE),
    'Handler_delete': ('mysql.performance.handler_delete', RATE),
    'Handler_prepare': ('mysql.performance.handler_prepare', RATE),
    'Handler_read_first': ('mysql.performance.handler_read_first', RATE),
    'Handler_read_key': ('mysql.performance.handler_read_key', RATE),
    'Handler_read_next': ('mysql.performance.handler_read_next', RATE),
    'Handler_read_prev': ('mysql.performance.handler_read_prev', RATE),
    'Handler_read_rnd': ('mysql.performance.handler_read_rnd', RATE),
    'Handler_read_rnd_next': ('mysql.performance.handler_read_rnd_next', RATE),
    'Handler_rollback': ('mysql.performance.handler_rollback', RATE),
    'Handler_update': ('mysql.performance.handler_update', RATE),
    'Handler_write': ('mysql.performance.handler_write', RATE),
    'Opened_tables': ('mysql.performance.opened_tables', RATE),
    'Qcache_total_blocks': ('mysql.performance.qcache_total_blocks', GAUGE),
    'Qcache_free_blocks': ('mysql.performance.qcache_free_blocks', GAUGE),
    'Qcache_free_memory': ('mysql.performance.qcache_free_memory', GAUGE),
    'Qcache_not_cached': ('mysql.performance.qcache_not_cached', RATE),
    'Qcache_queries_in_cache': ('mysql.performance.qcache_queries_in_cache', GAUGE),
    'Select_full_join': ('mysql.performance.select_full_join', RATE),
    'Select_full_range_join': ('mysql.performance.select_full_range_join', RATE),
    'Select_range': ('mysql.performance.select_range', RATE),
    'Select_range_check': ('mysql.performance.select_range_check', RATE),
    'Select_scan': ('mysql.performance.select_scan', RATE),
    'Sort_merge_passes': ('mysql.performance.sort_merge_passes', RATE),
    'Sort_range': ('mysql.performance.sort_range', RATE),
    'Sort_rows': ('mysql.performance.sort_rows', RATE),
    'Sort_scan': ('mysql.performance.sort_scan', RATE),
    'Table_locks_immediate': ('mysql.performance.table_locks_immediate', GAUGE),
    'Table_locks_immediate_rate': ('mysql.performance.table_locks_immediate.rate', RATE),
    'Threads_cached': ('mysql.performance.threads_cached', GAUGE),
    'Threads_created': ('mysql.performance.threads_created', MONOTONIC),
}

# Status Vars added in Mysql 5.6.6
OPTIONAL_STATUS_VARS_5_6_6 = {
    'Table_open_cache_hits': ('mysql.performance.table_cache_hits', RATE),
    'Table_open_cache_misses': ('mysql.performance.table_cache_misses', RATE),
}

# Will collect if [extra_innodb_metrics] is True
OPTIONAL_INNODB_VARS = {
    'Innodb_active_transactions': ('mysql.innodb.active_transactions', GAUGE),
    'Innodb_buffer_pool_bytes_data': ('mysql.innodb.buffer_pool_data', GAUGE),
    'Innodb_buffer_pool_pages_data': ('mysql.innodb.buffer_pool_pages_data', GAUGE),
    'Innodb_buffer_pool_pages_dirty': ('mysql.innodb.buffer_pool_pages_dirty', GAUGE),
    'Innodb_buffer_pool_pages_flushed': ('mysql.innodb.buffer_pool_pages_flushed', RATE),
    'Innodb_buffer_pool_pages_free': ('mysql.innodb.buffer_pool_pages_free', GAUGE),
    'Innodb_buffer_pool_pages_total': ('mysql.innodb.buffer_pool_pages_total', GAUGE),
    'Innodb_buffer_pool_read_ahead': ('mysql.innodb.buffer_pool_read_ahead', RATE),
    'Innodb_buffer_pool_read_ahead_evicted': ('mysql.innodb.buffer_pool_read_ahead_evicted', RATE),
    'Innodb_buffer_pool_read_ahead_rnd': ('mysql.innodb.buffer_pool_read_ahead_rnd', GAUGE),
    'Innodb_buffer_pool_wait_free': ('mysql.innodb.buffer_pool_wait_free', MONOTONIC),
    'Innodb_buffer_pool_write_requests': ('mysql.innodb.buffer_pool_write_requests', RATE),
    'Innodb_checkpoint_age': ('mysql.innodb.checkpoint_age', GAUGE),
    'Innodb_current_transactions': ('mysql.innodb.current_transactions', GAUGE),
    'Innodb_data_fsyncs': ('mysql.innodb.data_fsyncs', RATE),
    'Innodb_data_pending_fsyncs': ('mysql.innodb.data_pending_fsyncs', GAUGE),
    'Innodb_data_pending_reads': ('mysql.innodb.data_pending_reads', GAUGE),
    'Innodb_data_pending_writes': ('mysql.innodb.data_pending_writes', GAUGE),
    'Innodb_data_read': ('mysql.innodb.data_read', RATE),
    'Innodb_data_written': ('mysql.innodb.data_written', RATE),
    'Innodb_dblwr_pages_written': ('mysql.innodb.dblwr_pages_written', RATE),
    'Innodb_dblwr_writes': ('mysql.innodb.dblwr_writes', RATE),
    'Innodb_hash_index_cells_total': ('mysql.innodb.hash_index_cells_total', GAUGE),
    'Innodb_hash_index_cells_used': ('mysql.innodb.hash_index_cells_used', GAUGE),
    'Innodb_history_list_length': ('mysql.innodb.history_list_length', GAUGE),
    'Innodb_ibuf_free_list': ('mysql.innodb.ibuf_free_list', GAUGE),
    'Innodb_ibuf_merged': ('mysql.innodb.ibuf_merged', RATE),
    'Innodb_ibuf_merged_delete_marks': ('mysql.innodb.ibuf_merged_delete_marks', RATE),
    'Innodb_ibuf_merged_deletes': ('mysql.innodb.ibuf_merged_deletes', RATE),
    'Innodb_ibuf_merged_inserts': ('mysql.innodb.ibuf_merged_inserts', RATE),
    'Innodb_ibuf_merges': ('mysql.innodb.ibuf_merges', RATE),
    'Innodb_ibuf_segment_size': ('mysql.innodb.ibuf_segment_size', GAUGE),
    'Innodb_ibuf_size': ('mysql.innodb.ibuf_size', GAUGE),
    'Innodb_lock_structs': ('mysql.innodb.lock_structs', GAUGE),
    'Innodb_locked_tables': ('mysql.innodb.locked_tables', GAUGE),
    'Innodb_locked_transactions': ('mysql.innodb.locked_transactions', GAUGE),
    'Innodb_log_waits': ('mysql.innodb.log_waits', RATE),
    'Innodb_log_write_requests': ('mysql.innodb.log_write_requests', RATE),
    'Innodb_log_writes': ('mysql.innodb.log_writes', RATE),
    'Innodb_lsn_current': ('mysql.innodb.lsn_current', RATE),
    'Innodb_lsn_flushed': ('mysql.innodb.lsn_flushed', RATE),
    'Innodb_lsn_last_checkpoint': ('mysql.innodb.lsn_last_checkpoint', RATE),
    'Innodb_mem_adaptive_hash': ('mysql.innodb.mem_adaptive_hash', GAUGE),
    'Innodb_mem_additional_pool': ('mysql.innodb.mem_additional_pool', GAUGE),
    'Innodb_mem_dictionary': ('mysql.innodb.mem_dictionary', GAUGE),
    'Innodb_mem_file_system': ('mysql.innodb.mem_file_system', GAUGE),
    'Innodb_mem_lock_system': ('mysql.innodb.mem_lock_system', GAUGE),
    'Innodb_mem_page_hash': ('mysql.innodb.mem_page_hash', GAUGE),
    'Innodb_mem_recovery_system': ('mysql.innodb.mem_recovery_system', GAUGE),
    'Innodb_mem_thread_hash': ('mysql.innodb.mem_thread_hash', GAUGE),
    'Innodb_mem_total': ('mysql.innodb.mem_total', GAUGE),
    'Innodb_os_file_fsyncs': ('mysql.innodb.os_file_fsyncs', RATE),
    'Innodb_os_file_reads': ('mysql.innodb.os_file_reads', RATE),
    'Innodb_os_file_writes': ('mysql.innodb.os_file_writes', RATE),
    'Innodb_os_log_pending_fsyncs': ('mysql.innodb.os_log_pending_fsyncs', GAUGE),
    'Innodb_os_log_pending_writes': ('mysql.innodb.os_log_pending_writes', GAUGE),
    'Innodb_os_log_written': ('mysql.innodb.os_log_written', RATE),
    'Innodb_pages_created': ('mysql.innodb.pages_created', RATE),
    'Innodb_pages_read': ('mysql.innodb.pages_read', RATE),
    'Innodb_pages_written': ('mysql.innodb.pages_written', RATE),
    'Innodb_pending_aio_log_ios': ('mysql.innodb.pending_aio_log_ios', GAUGE),
    'Innodb_pending_aio_sync_ios': ('mysql.innodb.pending_aio_sync_ios', GAUGE),
    'Innodb_pending_buffer_pool_flushes': ('mysql.innodb.pending_buffer_pool_flushes', GAUGE),
    'Innodb_pending_checkpoint_writes': ('mysql.innodb.pending_checkpoint_writes', GAUGE),
    'Innodb_pending_ibuf_aio_reads': ('mysql.innodb.pending_ibuf_aio_reads', GAUGE),
    'Innodb_pending_log_flushes': ('mysql.innodb.pending_log_flushes', GAUGE),
    'Innodb_pending_log_writes': ('mysql.innodb.pending_log_writes', GAUGE),
    'Innodb_pending_normal_aio_reads': ('mysql.innodb.pending_normal_aio_reads', GAUGE),
    'Innodb_pending_normal_aio_writes': ('mysql.innodb.pending_normal_aio_writes', GAUGE),
    'Innodb_queries_inside': ('mysql.innodb.queries_inside', GAUGE),
    'Innodb_queries_queued': ('mysql.innodb.queries_queued', GAUGE),
    'Innodb_read_views': ('mysql.innodb.read_views', GAUGE),
    'Innodb_rows_deleted': ('mysql.innodb.rows_deleted', RATE),
    'Innodb_rows_inserted': ('mysql.innodb.rows_inserted', RATE),
    'Innodb_rows_read': ('mysql.innodb.rows_read', RATE),
    'Innodb_rows_updated': ('mysql.innodb.rows_updated', RATE),
    'Innodb_s_lock_os_waits': ('mysql.innodb.s_lock_os_waits', RATE),
    'Innodb_s_lock_spin_rounds': ('mysql.innodb.s_lock_spin_rounds', RATE),
    'Innodb_s_lock_spin_waits': ('mysql.innodb.s_lock_spin_waits', RATE),
    'Innodb_semaphore_wait_time': ('mysql.innodb.semaphore_wait_time', GAUGE),
    'Innodb_semaphore_waits': ('mysql.innodb.semaphore_waits', GAUGE),
    'Innodb_tables_in_use': ('mysql.innodb.tables_in_use', GAUGE),
    'Innodb_x_lock_os_waits': ('mysql.innodb.x_lock_os_waits', RATE),
    'Innodb_x_lock_spin_rounds': ('mysql.innodb.x_lock_spin_rounds', RATE),
    'Innodb_x_lock_spin_waits': ('mysql.innodb.x_lock_spin_waits', RATE),
}

GALERA_VARS = {
    'wsrep_cluster_size': ('mysql.galera.wsrep_cluster_size', GAUGE),
    'wsrep_local_recv_queue_avg': ('mysql.galera.wsrep_local_recv_queue_avg', GAUGE),
    'wsrep_local_recv_queue': ('mysql.galera.wsrep_local_recv_queue', GAUGE),
    'wsrep_flow_control_paused': ('mysql.galera.wsrep_flow_control_paused', GAUGE),
    'wsrep_flow_control_paused_ns': ('mysql.galera.wsrep_flow_control_paused_ns', MONOTONIC),
    'wsrep_flow_control_recv': ('mysql.galera.wsrep_flow_control_recv', MONOTONIC),
    'wsrep_flow_control_sent': ('mysql.galera.wsrep_flow_control_sent', MONOTONIC),
    'wsrep_cert_deps_distance': ('mysql.galera.wsrep_cert_deps_distance', GAUGE),
    'wsrep_local_send_queue_avg': ('mysql.galera.wsrep_local_send_queue_avg', GAUGE),
    'wsrep_local_send_queue': ('mysql.galera.wsrep_local_send_queue', GAUGE),
    'wsrep_replicated_bytes': ('mysql.galera.wsrep_replicated_bytes', GAUGE),
    'wsrep_received_bytes': ('mysql.galera.wsrep_received_bytes', GAUGE),
    'wsrep_received': ('mysql.galera.wsrep_received', GAUGE),
    'wsrep_local_state': ('mysql.galera.wsrep_local_state', GAUGE),
    'wsrep_local_cert_failures': ('mysql.galera.wsrep_local_cert_failures', MONOTONIC),
}

PERFORMANCE_VARS = {
    'query_run_time_avg': ('mysql.performance.query_run_time.avg', GAUGE),
    'perf_digest_95th_percentile_avg_us': ('mysql.performance.digest_95th_percentile.avg_us', GAUGE),
}

SCHEMA_VARS = {'information_schema_size': ('mysql.info.schema.size', GAUGE)}

TABLE_VARS = {
    'information_table_index_size': ('mysql.info.table.index_size', GAUGE),
    'information_table_data_size': ('mysql.info.table.data_size', GAUGE),
}

TABLE_ROWS_STATS_VARS = {
    'information_table_rows_read_total': ('mysql.info.table.rows.read', MONOTONIC),
    'information_table_rows_changed_total': ('mysql.info.table.rows.changed', MONOTONIC),
}

# Vars found in "show slave status" or "show replication status" (depending on mysql version)
REPLICA_VARS = {
    'Seconds_Behind_Source': [  # for 8 onwards
        ('mysql.replication.seconds_behind_source', GAUGE),
        ('mysql.replication.seconds_behind_master', GAUGE),  # for retrocompatibility
    ],
    'Seconds_Behind_Master': [  # before 8
        ('mysql.replication.seconds_behind_source', GAUGE),
        ('mysql.replication.seconds_behind_master', GAUGE),
    ],
    'Replicas_connected': [
        ('mysql.replication.slaves_connected', GAUGE),
        ('mysql.replication.replicas_connected', GAUGE),
    ],
}

GROUP_REPLICATION_VARS = {
    'Transactions_count': ('mysql.replication.group.transactions', GAUGE),
    'Transactions_check': ('mysql.replication.group.transactions_check', GAUGE),
    'Conflict_detected': ('mysql.replication.group.conflicts_detected', GAUGE),
    'Transactions_row_validating': ('mysql.replication.group.transactions_validating', GAUGE),
    'Transactions_remote_applier_queue': ('mysql.replication.group.transactions_in_applier_queue', GAUGE),
    'Transactions_remote_applied': ('mysql.replication.group.transactions_applied', GAUGE),
    'Transactions_local_proposed': ('mysql.replication.group.transactions_proposed', GAUGE),
    'Transactions_local_rollback': ('mysql.replication.group.transactions_rollback', GAUGE),
}

SYNTHETIC_VARS = {
    'Qcache_utilization': ('mysql.performance.qcache.utilization', GAUGE),
    'Qcache_instant_utilization': ('mysql.performance.qcache.utilization.instant', GAUGE),
}

BUILDS = ('log', 'standard', 'debug', 'valgrind', 'embedded')
