# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Monitor procedures and functions:
# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/c0053963.html
#
# Monitor views:
# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/c0061229.html
#
# Monitor element reference:
# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001140.html


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0060770.html
INSTANCE_TABLE_COLUMNS = (
    'agents_created_empty_pool',
    'agents_from_pool',
    'agents_registered',
    'agents_registered_top',
    'con_local_dbases',
    'coord_agents_top',
    'current timestamp AS current_time',
    'db2start_time',
    'idle_agents',
    'num_coord_agents',
    'total_connections',
)
INSTANCE_TABLE = 'SELECT {} FROM TABLE(MON_GET_INSTANCE(-1))'.format(', '.join(INSTANCE_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0060769.html
DATABASE_TABLE_COLUMNS = (
    'act_aborted_total',
    'act_completed_total',
    'act_rejected_total',
    'appls_cur_cons',
    'appls_in_db2',
    'connections_top',
    'current timestamp AS current_time',
    'db_status',
    'deadlocks',
    'direct_read_reqs',
    'direct_read_time',
    'direct_reads',
    'direct_write_reqs',
    'direct_write_time',
    'direct_writes',
    'hash_grpby_overflows',
    'hash_join_overflows',
    'hash_join_small_overflows',
    'int_commits',
    'int_rollbacks',
    'last_backup',
    'lock_escals',
    'lock_escals_locklist',
    'lock_escals_maxlocks',
    'lock_list_in_use',
    'lock_timeouts',
    'lock_wait_time',
    'lock_waits',
    'num_locks_held',
    'num_locks_waiting',
    'post_shrthreshold_hash_joins',
    'post_shrthreshold_sorts',
    'post_threshold_hash_joins',
    'post_threshold_sorts',
    'rqsts_completed_total',
    'rows_deleted',
    'rows_inserted',
    'rows_modified',
    'rows_read',
    'rows_returned',
    'rows_updated',
    'sort_overflows',
    'total_app_commits',
    'total_app_rollbacks',
    'total_app_section_executions',
    'total_hash_grpbys',
    'total_hash_joins',
    'total_hash_loops',
    'total_section_sort_proc_time',
    'total_section_sort_time',
    'total_section_sorts',
    'total_cons',
    'total_sorts',
)
DATABASE_TABLE = 'SELECT {} FROM TABLE(MON_GET_DATABASE(-1))'.format(', '.join(DATABASE_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0053942.html
BUFFER_POOL_TABLE_COLUMNS = (
    'block_ios',
    'bp_cur_buffsz',
    'bp_pages_left_to_remove',
    'bp_tbsp_use_count',
    'bp_name',
    'files_closed',
    'pages_from_block_ios',
    'pages_from_vectored_ios',
    'pool_async_col_reads',
    'pool_async_col_writes',
    'pool_async_col_lbp_pages_found',
    'pool_async_data_reads',
    'pool_async_data_writes',
    'pool_async_data_lbp_pages_found',
    'pool_async_index_reads',
    'pool_async_index_writes',
    'pool_async_index_lbp_pages_found',
    'pool_async_xda_reads',
    'pool_async_xda_writes',
    'pool_async_xda_lbp_pages_found',
    'pool_col_gbp_l_reads',
    'pool_col_gbp_p_reads',
    'pool_col_l_reads',
    'pool_col_lbp_pages_found',
    'pool_col_p_reads',
    'pool_col_writes',
    'pool_data_gbp_l_reads',
    'pool_data_gbp_p_reads',
    'pool_data_l_reads',
    'pool_data_lbp_pages_found',
    'pool_data_p_reads',
    'pool_data_writes',
    'pool_index_gbp_l_reads',
    'pool_index_gbp_p_reads',
    'pool_index_l_reads',
    'pool_index_lbp_pages_found',
    'pool_index_p_reads',
    'pool_index_writes',
    'pool_no_victim_buffer',
    'pool_read_time',
    'pool_temp_col_l_reads',
    'pool_temp_col_p_reads',
    'pool_temp_data_l_reads',
    'pool_temp_data_p_reads',
    'pool_temp_index_l_reads',
    'pool_temp_index_p_reads',
    'pool_temp_xda_l_reads',
    'pool_temp_xda_p_reads',
    'pool_xda_gbp_l_reads',
    'pool_xda_gbp_p_reads',
    'pool_xda_l_reads',
    'pool_xda_lbp_pages_found',
    'pool_xda_p_reads',
    'pool_xda_writes',
    'pool_write_time',
    'prefetch_wait_time',
    'prefetch_waits',
    'unread_prefetch_pages',
    'vectored_ios',
)
BUFFER_POOL_TABLE = 'SELECT {} FROM TABLE(MON_GET_BUFFERPOOL(NULL, -1))'.format(', '.join(BUFFER_POOL_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0053943.html
TABLE_SPACE_TABLE_COLUMNS = (
    'storage_group_name',
    'tbsp_auto_resize_enabled',
    'tbsp_content_type',
    'tbsp_free_pages',
    'tbsp_increase_size',
    'tbsp_initial_size',
    'tbsp_last_resize_failed',
    'tbsp_max_size',
    'tbsp_name',
    'tbsp_num_containers',
    'tbsp_page_size',
    'tbsp_page_top',
    'tbsp_pending_free_pages',
    'tbsp_state',
    'tbsp_total_pages',
    'tbsp_type',
    'tbsp_usable_pages',
    'tbsp_using_auto_storage',
    'tbsp_used_pages',
)
TABLE_SPACE_TABLE = 'SELECT {} FROM TABLE(MON_GET_TABLESPACE(NULL, -1))'.format(', '.join(TABLE_SPACE_TABLE_COLUMNS))


# https://www.ibm.com/docs/en/db2/12.1?topic=functions-mon-get-container-table-function
CONTAINER_TABLE_COLUMNS = (
    'C.tbsp_name AS tbsp_name',
    'C.container_name AS container_name',
    'C.container_id AS container_id',
    'C.member AS member',
    'C.container_type AS container_type',
    'C.total_pages AS total_pages',
    'C.usable_pages AS usable_pages',
    'C.accessible AS accessible',
    'C.fs_total_size AS fs_total_size',
    'C.fs_used_size AS fs_used_size',
    'T.tbsp_page_size AS tbsp_page_size',
)
CONTAINER_TABLE = """\
SELECT {}
FROM TABLE(MON_GET_CONTAINER(NULL, -1)) C
LEFT JOIN TABLE(MON_GET_TABLESPACE(NULL, -1)) T
  ON C.TBSP_ID = T.TBSP_ID
 AND C.MEMBER = T.MEMBER
""".format(', '.join(CONTAINER_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0059253.html
TRANSACTION_LOG_TABLE_COLUMNS = (
    'cur_commit_disk_log_reads',
    'cur_commit_log_buff_log_reads',
    'cur_commit_total_log_reads',
    'log_hadr_wait_time',
    'log_hadr_waits_total',
    'log_held_by_dirty_pages',
    'log_read_time',
    'log_reads',
    'log_to_redo_for_recovery',
    'log_write_time',
    'log_writes',
    'num_indoubt_trans',
    'num_log_buffer_full',
    'num_log_data_found_in_buffer',
    'num_log_part_page_io',
    'num_log_read_io',
    'num_log_write_io',
    'num_logs_avail_for_rename',
    'sec_log_used_top',
    'sec_logs_allocated',
    'total_log_available',
    'total_log_used',
    'tot_log_used_top',
)
TRANSACTION_LOG_TABLE = 'SELECT {} FROM TABLE(MON_GET_TRANSACTION_LOG(-1))'.format(
    ', '.join(TRANSACTION_LOG_TABLE_COLUMNS)
)


# https://www.ibm.com/docs/en/db2/12.1?topic=functions-mon-get-hadr-returns-high-availability-disaster
HADR_TABLE_COLUMNS = (
    'current timestamp AS current_time',
    'hadr_connect_status',
    'hadr_flags',
    'hadr_log_gap',
    'hadr_role',
    'hadr_state',
    'hadr_syncmode',
    'hadr_timeout',
    'heartbeat_expected',
    'heartbeat_interval',
    'heartbeat_missed',
    'log_hadr_wait_cur',
    'log_stream_id',
    'peer_window',
    'peer_window_end',
    'primary_log_pos',
    'primary_log_time',
    'sock_recv_buf_actual',
    'sock_send_buf_actual',
    'standby_id',
    'standby_log_pos',
    'standby_member_host',
    'standby_recv_buf_percent',
    'standby_recv_buf_size',
    'standby_recv_replay_gap',
    'standby_replay_log_pos',
    'standby_replay_log_time',
    'standby_replay_only_window_tran_count',
    'standby_spool_limit',
    'standby_spool_percent',
    'takeover_app_remaining_primary',
    'takeover_app_remaining_standby',
    'time_since_last_recv',
)
HADR_TABLE = 'SELECT {} FROM TABLE(MON_GET_HADR(-1))'.format(', '.join(HADR_TABLE_COLUMNS))
