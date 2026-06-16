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
    'member',
    'num_coord_agents',
    'total_connections',
)
INSTANCE_TABLE = 'SELECT {} FROM TABLE(MON_GET_INSTANCE(-2))'.format(', '.join(INSTANCE_TABLE_COLUMNS))


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
    'member',
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
DATABASE_TABLE = 'SELECT {} FROM TABLE(MON_GET_DATABASE(-2))'.format(', '.join(DATABASE_TABLE_COLUMNS))


MEMORY_POOL_TABLE_COLUMNS = (
    'member',
    'db_name',
    'memory_set_type',
    'memory_pool_type',
    'application_handle',
    'edu_id',
    'memory_pool_used',
    'memory_pool_used_hwm',
)
MEMORY_POOL_TABLE = 'SELECT {} FROM TABLE(MON_GET_MEMORY_POOL(NULL, NULL, -2))'.format(
    ', '.join(MEMORY_POOL_TABLE_COLUMNS)
)


# The set-level function has changed more across Db2 releases than MON_GET_MEMORY_POOL.
MEMORY_SET_TABLE = 'SELECT * FROM TABLE(MON_GET_MEMORY_SET(NULL, NULL, -2))'


WLM_METRIC_COLUMNS = (
    'total_cpu_time',
    'act_completed_total',
    'act_aborted_total',
    'act_rejected_total',
    'app_act_completed_total',
    'app_act_aborted_total',
    'app_act_rejected_total',
    'act_rqsts_total',
    'rqsts_completed_total',
    'app_rqsts_completed_total',
    'total_wait_time',
    'total_rqst_time',
    'total_app_rqst_time',
    'wlm_queue_time_total',
    'wlm_queue_assignments_total',
    'total_act_time',
    'total_act_wait_time',
    'total_section_time',
    'total_section_proc_time',
    'total_app_commits',
    'total_app_rollbacks',
    'int_commits',
    'int_rollbacks',
    'lock_wait_time',
    'lock_waits',
    'pool_read_time',
    'pool_write_time',
    'direct_read_time',
    'direct_write_time',
    'log_disk_wait_time',
    'log_buffer_wait_time',
    'agent_wait_time',
    'agent_waits_total',
    'client_idle_wait_time',
    'prefetch_wait_time',
    'total_extended_latch_wait_time',
    'total_extended_latch_waits',
    'fcm_recv_wait_time',
    'fcm_send_wait_time',
    'tcpip_recv_wait_time',
    'tcpip_send_wait_time',
    'ipc_recv_wait_time',
    'ipc_send_wait_time',
    'cf_wait_time',
    'cf_waits',
    'reclaim_wait_time',
)
WLM_WORKLOAD_TABLE_COLUMNS = ('workload_name', 'workload_id', 'member') + WLM_METRIC_COLUMNS
WLM_WORKLOAD_TABLE = 'SELECT {} FROM TABLE(MON_GET_WORKLOAD(NULL, -2))'.format(', '.join(WLM_WORKLOAD_TABLE_COLUMNS))
WLM_SERVICE_SUBCLASS_TABLE_COLUMNS = (
    'service_superclass_name',
    'service_subclass_name',
    'service_class_id',
    'member',
) + WLM_METRIC_COLUMNS
WLM_SERVICE_SUBCLASS_TABLE = 'SELECT {} FROM TABLE(MON_GET_SERVICE_SUBCLASS(NULL, NULL, -2))'.format(
    ', '.join(WLM_SERVICE_SUBCLASS_TABLE_COLUMNS)
)


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0053942.html
BUFFER_POOL_TABLE_COLUMNS = (
    'block_ios',
    'bp_cur_buffsz',
    'bp_pages_left_to_remove',
    'bp_tbsp_use_count',
    'bp_name',
    'files_closed',
    'member',
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
BUFFER_POOL_TABLE = 'SELECT {} FROM TABLE(MON_GET_BUFFERPOOL(NULL, -2))'.format(', '.join(BUFFER_POOL_TABLE_COLUMNS))


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
    'member',
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
TABLE_SPACE_TABLE = 'SELECT {} FROM TABLE(MON_GET_TABLESPACE(NULL, -2))'.format(', '.join(TABLE_SPACE_TABLE_COLUMNS))


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
FROM TABLE(MON_GET_CONTAINER(NULL, -2)) C
LEFT JOIN TABLE(MON_GET_TABLESPACE(NULL, -2)) T
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
    'member',
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
TRANSACTION_LOG_TABLE = 'SELECT {} FROM TABLE(MON_GET_TRANSACTION_LOG(-2))'.format(
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
HADR_TABLE = 'SELECT {} FROM TABLE(MON_GET_HADR(-2))'.format(', '.join(HADR_TABLE_COLUMNS))


TABLE_METRICS_TABLE_COLUMNS = (
    'tabschema',
    'tabname',
    'member',
    'table_scans',
    'rows_read',
    'rows_inserted',
    'rows_updated',
    'rows_deleted',
    'object_data_l_reads',
    'object_data_p_reads',
    'direct_reads',
    'direct_writes',
    'lock_wait_time',
    'lock_waits',
    'lock_escals',
)
TABLE_METRICS_TABLE = """\
SELECT {}
FROM TABLE(MON_GET_TABLE(NULL, NULL, -2))
WHERE TABSCHEMA NOT LIKE 'SYS%'
  AND TABSCHEMA NOT IN ('NULLID', 'SQLJ')
ORDER BY ROWS_READ DESC
FETCH FIRST {{limit}} ROWS ONLY
""".format(', '.join(TABLE_METRICS_TABLE_COLUMNS))


INDEX_METRICS_TABLE_COLUMNS = (
    'M.tabschema AS tabschema',
    'M.tabname AS tabname',
    'M.iid AS iid',
    'M.member AS member',
    'C.indschema AS indschema',
    'C.indname AS indname',
    'M.index_scans AS index_scans',
    'M.index_only_scans AS index_only_scans',
    'M.index_jump_scans AS index_jump_scans',
    'M.key_updates AS key_updates',
    'M.pseudo_deletes AS pseudo_deletes',
    'M.del_keys_cleaned AS del_keys_cleaned',
    'M.nleaf AS nleaf',
    'M.nlevels AS nlevels',
    'M.object_index_l_reads AS object_index_l_reads',
    'M.object_index_p_reads AS object_index_p_reads',
)
INDEX_METRICS_TABLE = """\
SELECT {}
FROM TABLE(MON_GET_INDEX(NULL, NULL, -2)) M
LEFT JOIN SYSCAT.INDEXES C
  ON C.TABSCHEMA = M.TABSCHEMA
 AND C.TABNAME = M.TABNAME
 AND C.IID = M.IID
WHERE M.TABSCHEMA NOT LIKE 'SYS%'
  AND M.TABSCHEMA NOT IN ('NULLID', 'SQLJ')
ORDER BY M.INDEX_SCANS DESC
FETCH FIRST {{limit}} ROWS ONLY
""".format(', '.join(INDEX_METRICS_TABLE_COLUMNS))


CONNECTION_METRICS_TABLE_COLUMNS = (
    'application_handle',
    'application_name',
    'session_auth_id',
    'client_hostname',
    'client_applname',
    'workload_occurrence_state',
    'member',
    'total_app_commits',
    'total_app_rollbacks',
    'deadlocks',
    'lock_escals',
    'lock_timeouts',
    'lock_wait_time',
    'lock_waits',
    'num_locks_held',
    'num_locks_waiting',
    'rows_deleted',
    'rows_inserted',
    'rows_modified',
    'rows_read',
    'rows_returned',
    'rows_updated',
)
CONNECTION_METRICS_TABLE = """\
SELECT {}
FROM TABLE(MON_GET_CONNECTION(NULL, -2))
WHERE IS_SYSTEM_APPL = 0
ORDER BY ROWS_READ DESC
FETCH FIRST {{limit}} ROWS ONLY
""".format(', '.join(CONNECTION_METRICS_TABLE_COLUMNS))


FCM_TABLE_COLUMNS = (
    'member',
    'buff_free',
    'buff_free_bottom',
    'ch_free',
    'ch_free_bottom',
    'fcm_recv_volume',
    'fcm_recv_wait_time',
    'fcm_recv_waits_total',
    'fcm_recvs_total',
    'fcm_send_volume',
    'fcm_send_wait_time',
    'fcm_send_waits_total',
    'fcm_sends_total',
    'fcm_tq_recv_volume',
    'fcm_tq_recv_wait_time',
    'fcm_tq_send_volume',
    'fcm_tq_send_wait_time',
)
FCM_TABLE = 'SELECT {} FROM TABLE(MON_GET_FCM(-2))'.format(', '.join(FCM_TABLE_COLUMNS))


FCM_CONNECTION_TABLE_COLUMNS = (
    'member',
    'remote_member',
    'total_bytes_sent',
    'total_bytes_received',
)
FCM_CONNECTION_TABLE = 'SELECT {} FROM TABLE(MON_GET_FCM_CONNECTION_LIST(-2))'.format(
    ', '.join(FCM_CONNECTION_TABLE_COLUMNS)
)


CF_DATABASE_TABLE_COLUMNS = (
    'member',
    'cf_wait_time',
    'cf_waits',
)
CF_DATABASE_TABLE = 'SELECT {} FROM TABLE(MON_GET_DATABASE(-2))'.format(', '.join(CF_DATABASE_TABLE_COLUMNS))


CF_TABLE_COLUMNS = (
    'cf_id',
    'host_name',
    'state',
    'current_cf_gbp_size',
    'current_cf_lock_size',
    'current_cf_mem_size',
    'target_cf_mem_size',
)
CF_TABLE = 'SELECT {} FROM TABLE(MON_GET_CF(-2))'.format(', '.join(CF_TABLE_COLUMNS))


CF_CMD_TABLE_COLUMNS = (
    'cf_id',
    'cf_cmd_name',
    'total_cf_requests',
    'total_cf_cmd_time_micro',
)
CF_CMD_TABLE = 'SELECT {} FROM TABLE(MON_GET_CF_CMD(-2))'.format(', '.join(CF_CMD_TABLE_COLUMNS))


CF_WAIT_TABLE_COLUMNS = (
    'member',
    'cf_id',
    'cf_cmd_name',
    'total_cf_wait_time_micro',
)
CF_WAIT_TABLE = 'SELECT {} FROM TABLE(MON_GET_CF_WAIT_TIME(-2))'.format(', '.join(CF_WAIT_TABLE_COLUMNS))


GROUP_BUFFERPOOL_TABLE_COLUMNS = (
    'member',
    'num_gbp_full',
    'castout_pages',
    'cross_invalidations',
    'gbp_l_reads',
    'gbp_p_reads',
)
GROUP_BUFFERPOOL_TABLE = 'SELECT {} FROM TABLE(MON_GET_GROUP_BUFFERPOOL(-2))'.format(
    ', '.join(GROUP_BUFFERPOOL_TABLE_COLUMNS)
)
