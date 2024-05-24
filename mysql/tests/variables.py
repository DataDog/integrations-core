# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
STATUS_VARS = [
    # Command Metrics
    'mysql.performance.prepared_stmt_count',
    'mysql.performance.slow_queries',
    'mysql.performance.questions',
    'mysql.performance.queries',
    'mysql.performance.com_select',
    'mysql.performance.com_insert',
    'mysql.performance.com_update',
    'mysql.performance.com_delete',
    'mysql.performance.com_replace',
    'mysql.performance.com_load',
    'mysql.performance.com_insert_select',
    'mysql.performance.com_update_multi',
    'mysql.performance.com_delete_multi',
    'mysql.performance.com_replace_select',
    # Connection Metrics
    'mysql.net.connections',
    'mysql.net.max_connections',
    'mysql.net.aborted_clients',
    'mysql.net.aborted_connects',
    # Table Cache Metrics
    'mysql.performance.open_files',
    'mysql.performance.open_tables',
    # Network Metrics
    'mysql.performance.bytes_sent',
    'mysql.performance.bytes_received',
    # Table Lock Metrics
    'mysql.performance.table_locks_waited',
    'mysql.performance.table_locks_waited.rate',
    # Temporary Table Metrics
    'mysql.performance.created_tmp_tables',
    'mysql.performance.created_tmp_disk_tables',
    'mysql.performance.created_tmp_files',
    # Thread Metrics
    'mysql.performance.threads_connected',
    'mysql.performance.threads_running',
    # MyISAM Metrics
    'mysql.myisam.key_buffer_bytes_unflushed',
    'mysql.myisam.key_buffer_bytes_used',
    'mysql.myisam.key_read_requests',
    'mysql.myisam.key_reads',
    'mysql.myisam.key_write_requests',
    'mysql.myisam.key_writes',
]

COMPLEX_STATUS_VARS = [
    # Query Cache Metrics
    'mysql.performance.qcache_hits',
    'mysql.performance.qcache_inserts',
    'mysql.performance.qcache_lowmem_prunes',
]

TABLE_VARS = [
    'mysql.info.table.index_size',
    'mysql.info.table.data_size',
]

ROW_TABLE_STATS_VARS = [
    'mysql.info.table.rows.read',
    'mysql.info.table.rows.changed',
]

# Possibly from SHOW GLOBAL VARIABLES
VARIABLES_VARS = [
    'mysql.myisam.key_buffer_size',
    'mysql.performance.key_cache_utilization',
    'mysql.net.max_connections_available',
    'mysql.performance.max_prepared_stmt_count',
    'mysql.performance.table_open_cache',
    'mysql.performance.thread_cache_size',
]

COMPLEX_VARIABLES_VARS = [
    'mysql.performance.qcache_size',
]

INNODB_VARS = [
    # InnoDB metrics
    'mysql.innodb.data_reads',
    'mysql.innodb.data_writes',
    'mysql.innodb.os_log_fsyncs',
    'mysql.innodb.buffer_pool_dirty',
    'mysql.innodb.buffer_pool_free',
    'mysql.innodb.buffer_pool_used',
    'mysql.innodb.buffer_pool_total',
    'mysql.innodb.buffer_pool_read_requests',
    'mysql.innodb.buffer_pool_reads',
    'mysql.innodb.buffer_pool_utilization',
    'mysql.innodb.deadlocks',
]

COMPLEX_INNODB_VARS = [
    'mysql.innodb.mutex_spin_waits',
    'mysql.innodb.mutex_spin_rounds',
    'mysql.innodb.mutex_os_waits',
    'mysql.innodb.row_lock_waits',
    'mysql.innodb.row_lock_time',
    'mysql.innodb.row_lock_current_waits',
    # 'mysql.innodb.current_row_locks', MariaDB status
]

# Calculated from "SHOW MASTER LOGS;"
BINLOG_VARS = [
    'mysql.binlog.disk_use',  # Only collected if log_bin is true
]

SYSTEM_METRICS = ['mysql.performance.user_time', 'mysql.performance.kernel_time', 'mysql.performance.cpu_time']

OPTIONAL_REPLICATION_METRICS = [
    'mysql.replication.slave_running',
    'mysql.replication.seconds_behind_master',
    'mysql.replication.seconds_behind_source',
    'mysql.replication.slaves_connected',
    'mysql.replication.replicas_connected',
]

# Additional Vars found in "SHOW STATUS;"
# Will collect if [FLAG NAME] is True
OPTIONAL_STATUS_VARS = [
    'mysql.binlog.cache_disk_use',
    'mysql.binlog.cache_use',
    'mysql.binlog.disk_use',
    'mysql.performance.handler_commit',
    'mysql.performance.handler_delete',
    'mysql.performance.handler_prepare',
    'mysql.performance.handler_read_first',
    'mysql.performance.handler_read_key',
    'mysql.performance.handler_read_next',
    'mysql.performance.handler_read_prev',
    'mysql.performance.handler_read_rnd',
    'mysql.performance.handler_read_rnd_next',
    'mysql.performance.handler_rollback',
    'mysql.performance.handler_update',
    'mysql.performance.handler_write',
    'mysql.performance.opened_tables',
    'mysql.performance.qcache_total_blocks',
    'mysql.performance.qcache_free_blocks',
    'mysql.performance.qcache_free_memory',
    'mysql.performance.qcache_not_cached',
    'mysql.performance.qcache_queries_in_cache',
    'mysql.performance.select_full_join',
    'mysql.performance.select_full_range_join',
    'mysql.performance.select_range',
    'mysql.performance.select_range_check',
    'mysql.performance.select_scan',
    'mysql.performance.sort_merge_passes',
    'mysql.performance.sort_range',
    'mysql.performance.sort_rows',
    'mysql.performance.sort_scan',
    'mysql.performance.table_locks_immediate',
    'mysql.performance.table_locks_immediate.rate',
    'mysql.performance.threads_cached',
    'mysql.performance.threads_created',
]

OPTIONAL_STATUS_VARS_5_6_6 = ['mysql.performance.table_cache_hits', 'mysql.performance.table_cache_misses']

# Will collect if [FLAG NAME] is True
OPTIONAL_INNODB_VARS = [
    'mysql.innodb.active_transactions',
    'mysql.innodb.buffer_pool_data',
    'mysql.innodb.buffer_pool_pages_data',
    'mysql.innodb.buffer_pool_pages_dirty',
    'mysql.innodb.buffer_pool_pages_flushed',
    'mysql.innodb.buffer_pool_pages_free',
    'mysql.innodb.buffer_pool_pages_total',
    'mysql.innodb.buffer_pool_read_ahead',
    'mysql.innodb.buffer_pool_read_ahead_evicted',
    'mysql.innodb.buffer_pool_read_ahead_rnd',
    'mysql.innodb.buffer_pool_wait_free',
    'mysql.innodb.buffer_pool_write_requests',
    'mysql.innodb.checkpoint_age',
    'mysql.innodb.current_transactions',
    'mysql.innodb.data_fsyncs',
    'mysql.innodb.data_pending_fsyncs',
    'mysql.innodb.data_pending_reads',
    'mysql.innodb.data_pending_writes',
    'mysql.innodb.data_read',
    'mysql.innodb.data_written',
    'mysql.innodb.dblwr_pages_written',
    'mysql.innodb.dblwr_writes',
    'mysql.innodb.hash_index_cells_total',
    'mysql.innodb.hash_index_cells_used',
    'mysql.innodb.history_list_length',
    'mysql.innodb.ibuf_free_list',
    'mysql.innodb.ibuf_merged',
    'mysql.innodb.ibuf_merged_delete_marks',
    'mysql.innodb.ibuf_merged_deletes',
    'mysql.innodb.ibuf_merged_inserts',
    'mysql.innodb.ibuf_merges',
    'mysql.innodb.ibuf_segment_size',
    'mysql.innodb.ibuf_size',
    'mysql.innodb.lock_structs',
    'mysql.innodb.locked_tables',
    'mysql.innodb.locked_transactions',
    'mysql.innodb.log_waits',
    'mysql.innodb.log_write_requests',
    'mysql.innodb.log_writes',
    'mysql.innodb.lsn_current',
    'mysql.innodb.lsn_flushed',
    'mysql.innodb.lsn_last_checkpoint',
    'mysql.innodb.mem_adaptive_hash',
    'mysql.innodb.mem_additional_pool',
    'mysql.innodb.mem_dictionary',
    'mysql.innodb.mem_file_system',
    'mysql.innodb.mem_lock_system',
    'mysql.innodb.mem_page_hash',
    'mysql.innodb.mem_recovery_system',
    'mysql.innodb.mem_thread_hash',
    'mysql.innodb.mem_total',
    'mysql.innodb.os_file_fsyncs',
    'mysql.innodb.os_file_reads',
    'mysql.innodb.os_file_writes',
    'mysql.innodb.os_log_pending_fsyncs',
    'mysql.innodb.os_log_pending_writes',
    'mysql.innodb.os_log_written',
    'mysql.innodb.pages_created',
    'mysql.innodb.pages_read',
    'mysql.innodb.pages_written',
    'mysql.innodb.pending_aio_log_ios',
    'mysql.innodb.pending_aio_sync_ios',
    'mysql.innodb.pending_buffer_pool_flushes',
    'mysql.innodb.pending_checkpoint_writes',
    'mysql.innodb.pending_ibuf_aio_reads',
    'mysql.innodb.pending_log_flushes',
    'mysql.innodb.pending_log_writes',
    'mysql.innodb.pending_normal_aio_reads',
    'mysql.innodb.pending_normal_aio_writes',
    'mysql.innodb.queries_inside',
    'mysql.innodb.queries_queued',
    'mysql.innodb.read_views',
    'mysql.innodb.rows_deleted',
    'mysql.innodb.rows_inserted',
    'mysql.innodb.rows_read',
    'mysql.innodb.rows_updated',
    'mysql.innodb.s_lock_os_waits',
    'mysql.innodb.s_lock_spin_rounds',
    'mysql.innodb.s_lock_spin_waits',
    'mysql.innodb.semaphore_wait_time',
    'mysql.innodb.semaphore_waits',
    'mysql.innodb.tables_in_use',
    'mysql.innodb.x_lock_os_waits',
    'mysql.innodb.x_lock_spin_rounds',
    'mysql.innodb.x_lock_spin_waits',
]

PERFORMANCE_VARS = ['mysql.performance.query_run_time.avg', 'mysql.performance.digest_95th_percentile.avg_us']

COMMON_PERFORMANCE_VARS = ['mysql.performance.user_connections']

# This exists to comply with some of the testing patterns with the old API.
QUERY_EXECUTOR_METRIC_SETS = {
    'user_connections': ('mysql.performance.user_connections', 'guage'),
}

SCHEMA_VARS = ['mysql.info.schema.size']

SYNTHETIC_VARS = ['mysql.performance.qcache.utilization', 'mysql.performance.qcache.utilization.instant']

STATEMENT_VARS = ['dd.mysql.queries.query_rows_raw', 'dd.mysql.queries.query_rows_limited']

GROUP_REPLICATION_VARS = [
    'mysql.replication.group.member_status',
    'mysql.replication.group.conflicts_detected',
    'mysql.replication.group.transactions',
    'mysql.replication.group.transactions_applied',
    'mysql.replication.group.transactions_in_applier_queue',
    'mysql.replication.group.transactions_check',
    'mysql.replication.group.transactions_proposed',
    'mysql.replication.group.transactions_rollback',
    'mysql.replication.group.transactions_validating',
]

SIMPLE_OPERATION_TIME_METRICS = [
    'status_metrics',
    'innodb_metrics',
    'variables_metrics',
    'binary_log_metrics',
]

COMPLEX_OPERATION_TIME_METRICS = [
    'schema_size_metrics',
    'system_table_size_metrics',
    'table_size_metrics',
]

REPLICATION_OPERATION_TIME_METRICS = ['replication_metrics']

GROUP_REPLICATION_OPERATION_TIME_METRICS = ['group_replication_metrics']

PERFORMANCE_OPERATION_TIME_METRICS = ['exec_time_95th_metrics', 'exec_time_per_schema_metrics']

COMMON_PERFORMANCE_OPERATION_TIME_METRICS = ['performance_schema.threads']

OPERATION_TIME_METRIC_NAME = 'dd.mysql.operation.time'

E2E_OPERATION_TIME_METRIC_NAME = [
    'dd.mysql.operation.time.{}'.format(suffix) for suffix in ('avg', 'max', '95percentile', 'count', 'median')
]
