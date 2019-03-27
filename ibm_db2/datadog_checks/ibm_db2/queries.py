# (C) Datadog, Inc. 2019
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
INSTANCE_TABLE_COLUMNS = ('total_connections',)
INSTANCE_TABLE = 'SELECT {} FROM TABLE(MON_GET_INSTANCE(-1))'.format(', '.join(INSTANCE_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0060769.html
DATABASE_TABLE_COLUMNS = (
    'appls_cur_cons',
    'appls_in_db2',
    'connections_top',
    'current timestamp AS current_time',
    'db_status',
    'deadlocks',
    'last_backup',
    'lock_list_in_use',
    'lock_timeouts',
    'lock_wait_time',
    'lock_waits',
    'num_locks_held',
    'num_locks_waiting',
    'rows_modified',
    'rows_read',
    'rows_returned',
    'total_cons',
)
DATABASE_TABLE = 'SELECT {} FROM TABLE(MON_GET_DATABASE(-1))'.format(', '.join(DATABASE_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0053942.html
BUFFER_POOL_TABLE_COLUMNS = (
    'bp_name',
    'pool_async_col_lbp_pages_found',
    'pool_async_data_lbp_pages_found',
    'pool_async_index_lbp_pages_found',
    'pool_async_xda_lbp_pages_found',
    'pool_col_gbp_l_reads',
    'pool_col_gbp_p_reads',
    'pool_col_l_reads',
    'pool_col_lbp_pages_found',
    'pool_col_p_reads',
    'pool_data_gbp_l_reads',
    'pool_data_gbp_p_reads',
    'pool_data_l_reads',
    'pool_data_lbp_pages_found',
    'pool_data_p_reads',
    'pool_index_gbp_l_reads',
    'pool_index_gbp_p_reads',
    'pool_index_l_reads',
    'pool_index_lbp_pages_found',
    'pool_index_p_reads',
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
)
BUFFER_POOL_TABLE = 'SELECT {} FROM TABLE(MON_GET_BUFFERPOOL(NULL, -1))'.format(', '.join(BUFFER_POOL_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0053943.html
TABLE_SPACE_TABLE_COLUMNS = (
    'tbsp_name',
    'tbsp_page_size',
    'tbsp_state',
    'tbsp_total_pages',
    'tbsp_usable_pages',
    'tbsp_used_pages',
)
TABLE_SPACE_TABLE = 'SELECT {} FROM TABLE(MON_GET_TABLESPACE(NULL, -1))'.format(', '.join(TABLE_SPACE_TABLE_COLUMNS))


# https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0059253.html
TRANSACTION_LOG_TABLE_COLUMNS = (
    'log_reads',
    'log_writes',
    'total_log_available',
    'total_log_used',
)
TRANSACTION_LOG_TABLE = 'SELECT {} FROM TABLE(MON_GET_TRANSACTION_LOG(-1))'.format(
    ', '.join(TRANSACTION_LOG_TABLE_COLUMNS)
)
