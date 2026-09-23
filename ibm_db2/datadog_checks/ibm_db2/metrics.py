# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from time import time as timestamp
from typing import TYPE_CHECKING

import ibm_db

from . import queries
from .utils import status_to_service_check

if TYPE_CHECKING:
    from .ibm_db2 import IbmDb2Check


class MetricsCollector:
    def __init__(self, check: IbmDb2Check):
        self._check = check
        self._table_space_states = {}

    def query_instance(self):
        # Only 1 instance
        for inst in self._check.iter_rows(queries.INSTANCE_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060773.html
            self._check.gauge(self._check.m('connection.active'), inst['total_connections'], tags=self._check.tags)

    def query_database(self):
        # Only 1 database
        for db in self._check.iter_rows(queries.DATABASE_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001156.html
            self._check.service_check(
                self._check.SERVICE_CHECK_STATUS, status_to_service_check(db['db_status']), tags=self._check.tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001201.html
            self._check.gauge(self._check.m('application.active'), db['appls_cur_cons'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001202.html
            self._check.gauge(self._check.m('application.executing'), db['appls_in_db2'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002225.html
            self._check.gauge(self._check.m('connection.max'), db['connections_top'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001200.html
            self._check.monotonic_count(self._check.m('connection.total'), db['total_cons'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001283.html
            self._check.monotonic_count(self._check.m('lock.dead'), db['deadlocks'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001290.html
            self._check.monotonic_count(self._check.m('lock.timeouts'), db['lock_timeouts'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001281.html
            self._check.gauge(self._check.m('lock.active'), db['num_locks_held'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001296.html
            self._check.gauge(self._check.m('lock.waiting'), db['num_locks_waiting'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001294.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001293.html
            if db['lock_waits']:
                average_lock_wait = db['lock_wait_time'] / db['lock_waits']
            else:
                average_lock_wait = 0
            self._check.gauge(self._check.m('lock.wait'), average_lock_wait, tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001282.html
            # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.config.doc/doc/r0000267.html
            self._check.gauge(self._check.m('lock.pages'), db['lock_list_in_use'] / 4096, tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001160.html
            last_backup = db['last_backup']
            if last_backup:
                seconds_since_last_backup = (db['current_time'] - last_backup).total_seconds()
            else:
                seconds_since_last_backup = -1
            self._check.gauge(self._check.m('backup.latest'), seconds_since_last_backup, tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0051568.html
            self._check.monotonic_count(self._check.m('row.modified.total'), db['rows_modified'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001317.html
            self._check.monotonic_count(self._check.m('row.reads.total'), db['rows_read'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0051569.html
            self._check.monotonic_count(self._check.m('row.returned.total'), db['rows_returned'], tags=self._check.tags)

    def query_buffer_pool(self):
        # Hit ratio formulas:
        # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056871.html
        for bp in self._check.iter_rows(queries.BUFFER_POOL_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002256.html
            bp_tags = ['bufferpool:{}'.format(bp['bp_name'])]
            bp_tags.extend(self._check.tags)

            # Column-organized pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060858.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060874.html
            column_reads_physical = bp['pool_col_p_reads'] + bp['pool_temp_col_p_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.column.reads.physical'), column_reads_physical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060763.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060873.html
            column_reads_logical = bp['pool_col_l_reads'] + bp['pool_temp_col_l_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.column.reads.logical'), column_reads_logical, tags=bp_tags
            )

            # Submit total
            self._check.monotonic_count(
                self._check.m('bufferpool.column.reads.total'),
                column_reads_physical + column_reads_logical,
                tags=bp_tags,
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060857.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060850.html
            column_pages_found = bp['pool_col_lbp_pages_found'] - bp['pool_async_col_lbp_pages_found']

            if column_reads_logical:
                column_hit_percent = column_pages_found / column_reads_logical * 100
            else:
                column_hit_percent = 0
            self._check.gauge(self._check.m('bufferpool.column.hit_percent'), column_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060855.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060856.html
            group_column_reads_logical = bp['pool_col_gbp_l_reads'] or 0
            group_column_pages_found = group_column_reads_logical - (bp['pool_col_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_column_reads_logical:  # no cov
                group_column_hit_percent = group_column_pages_found / group_column_reads_logical * 100
                self._check.gauge(
                    self._check.m('bufferpool.group.column.hit_percent'), group_column_hit_percent, tags=bp_tags
                )

            # Data pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001236.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011300.html
            data_reads_physical = bp['pool_data_p_reads'] + bp['pool_temp_data_p_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.data.reads.physical'), data_reads_physical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001235.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011302.html
            data_reads_logical = bp['pool_data_l_reads'] + bp['pool_temp_data_l_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.data.reads.logical'), data_reads_logical, tags=bp_tags
            )

            # Submit total
            self._check.monotonic_count(
                self._check.m('bufferpool.data.reads.total'), data_reads_physical + data_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056487.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056493.html
            data_pages_found = bp['pool_data_lbp_pages_found'] - bp['pool_async_data_lbp_pages_found']

            if data_reads_logical:
                data_hit_percent = data_pages_found / data_reads_logical * 100
            else:
                data_hit_percent = 0
            self._check.gauge(self._check.m('bufferpool.data.hit_percent'), data_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056485.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056486.html
            group_data_reads_logical = bp['pool_data_gbp_l_reads'] or 0
            group_data_pages_found = group_data_reads_logical - (bp['pool_data_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_data_reads_logical:  # no cov
                group_data_hit_percent = group_data_pages_found / group_data_reads_logical * 100
                self._check.gauge(
                    self._check.m('bufferpool.group.data.hit_percent'), group_data_hit_percent, tags=bp_tags
                )

            # Index pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001239.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011301.html
            index_reads_physical = bp['pool_index_p_reads'] + bp['pool_temp_index_p_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.index.reads.physical'), index_reads_physical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001238.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011303.html
            index_reads_logical = bp['pool_index_l_reads'] + bp['pool_temp_index_l_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.index.reads.logical'), index_reads_logical, tags=bp_tags
            )

            # Submit total
            self._check.monotonic_count(
                self._check.m('bufferpool.index.reads.total'), index_reads_physical + index_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056243.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056496.html
            index_pages_found = bp['pool_index_lbp_pages_found'] - bp['pool_async_index_lbp_pages_found']

            if index_reads_logical:
                index_hit_percent = index_pages_found / index_reads_logical * 100
            else:
                index_hit_percent = 0
            self._check.gauge(self._check.m('bufferpool.index.hit_percent'), index_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056488.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056489.html
            group_index_reads_logical = bp['pool_index_gbp_l_reads'] or 0
            group_index_pages_found = group_index_reads_logical - (bp['pool_index_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_index_reads_logical:  # no cov
                group_index_hit_percent = group_index_pages_found / group_index_reads_logical * 100
                self._check.gauge(
                    self._check.m('bufferpool.group.index.hit_percent'), group_index_hit_percent, tags=bp_tags
                )

            # XML storage object (XDA) pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022730.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022739.html
            xda_reads_physical = bp['pool_xda_p_reads'] + bp['pool_temp_xda_p_reads']
            self._check.monotonic_count(
                self._check.m('bufferpool.xda.reads.physical'), xda_reads_physical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022731.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022738.html
            xda_reads_logical = bp['pool_xda_l_reads'] + bp['pool_temp_xda_l_reads']
            self._check.monotonic_count(self._check.m('bufferpool.xda.reads.logical'), xda_reads_logical, tags=bp_tags)

            # Submit total
            self._check.monotonic_count(
                self._check.m('bufferpool.xda.reads.total'), xda_reads_physical + xda_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058666.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058670.html
            xda_pages_found = bp['pool_xda_lbp_pages_found'] - bp['pool_async_xda_lbp_pages_found']

            if xda_reads_logical:
                xda_hit_percent = xda_pages_found / xda_reads_logical * 100
            else:
                xda_hit_percent = 0
            self._check.gauge(self._check.m('bufferpool.xda.hit_percent'), xda_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058664.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058665.html
            group_xda_reads_logical = bp['pool_xda_gbp_l_reads'] or 0
            group_xda_pages_found = group_xda_reads_logical - (bp['pool_xda_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_xda_reads_logical:  # no cov
                group_xda_hit_percent = group_xda_pages_found / group_xda_reads_logical * 100
                self._check.gauge(
                    self._check.m('bufferpool.group.xda.hit_percent'), group_xda_hit_percent, tags=bp_tags
                )

            # Compute overall stats
            reads_physical = column_reads_physical + data_reads_physical + index_reads_physical + xda_reads_physical
            self._check.monotonic_count(self._check.m('bufferpool.reads.physical'), reads_physical, tags=bp_tags)

            reads_logical = column_reads_logical + data_reads_logical + index_reads_logical + xda_reads_logical
            self._check.monotonic_count(self._check.m('bufferpool.reads.logical'), reads_logical, tags=bp_tags)

            reads_total = reads_physical + reads_logical
            self._check.monotonic_count(self._check.m('bufferpool.reads.total'), reads_total, tags=bp_tags)

            if reads_logical:
                pages_found = column_pages_found + data_pages_found + index_pages_found + xda_pages_found
                hit_percent = pages_found / reads_logical * 100
            else:
                hit_percent = 0
            self._check.gauge(self._check.m('bufferpool.hit_percent'), hit_percent, tags=bp_tags)

            # Submit group ratio if in a pureScale environment
            group_reads_logical = (
                group_column_reads_logical
                + group_data_reads_logical
                + group_index_reads_logical
                + group_xda_reads_logical
            )
            if group_reads_logical:  # no cov
                group_pages_found = (
                    group_column_pages_found + group_data_pages_found + group_index_pages_found + group_xda_pages_found
                )
                group_hit_percent = group_pages_found / group_reads_logical * 100
                self._check.gauge(self._check.m('bufferpool.group.hit_percent'), group_hit_percent, tags=bp_tags)

    def query_table_space(self):
        # Utilization formulas:
        # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0056516.html
        for ts in self._check.iter_rows(queries.TABLE_SPACE_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001295.html
            table_space_name = ts['tbsp_name']
            ts_tags = ['tablespace:{}'.format(table_space_name)]
            ts_tags.extend(self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007534.html
            page_size = ts['tbsp_page_size']

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007539.html
            total_pages = ts['tbsp_total_pages']
            self._check.gauge(self._check.m('tablespace.size'), total_pages * page_size, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007540.html
            usable_pages = ts['tbsp_usable_pages']
            self._check.gauge(self._check.m('tablespace.usable'), usable_pages * page_size, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007541.html
            used_pages = ts['tbsp_used_pages']
            self._check.gauge(self._check.m('tablespace.used'), used_pages * page_size, tags=ts_tags)

            # Percent utilized
            if usable_pages:
                utilized = used_pages / usable_pages * 100
            else:
                utilized = 0
            self._check.gauge(self._check.m('tablespace.utilized'), utilized, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007533.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.dbobj.doc/doc/c0060111.html
            self.track_table_space_state_changes(table_space_name, ts['tbsp_state'], ts_tags)

    def query_transaction_log(self):
        # Only 1 transaction log
        for tlog in self._check.iter_rows(queries.TRANSACTION_LOG_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.config.doc/doc/r0000239.html
            block_size = 4096

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002530.html
            used = tlog['total_log_used']
            self._check.gauge(self._check.m('log.used'), used / block_size, tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002531.html
            available = tlog['total_log_available']

            # Handle infinite log space
            if available == -1:
                utilized = 0
            else:
                utilized = used / available * 100
                available /= block_size

            self._check.gauge(self._check.m('log.available'), available, tags=self._check.tags)
            self._check.gauge(self._check.m('log.utilized'), utilized, tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001278.html
            self._check.monotonic_count(self._check.m('log.reads'), tlog['log_reads'], tags=self._check.tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001279.html
            self._check.monotonic_count(self._check.m('log.writes'), tlog['log_writes'], tags=self._check.tags)

    def track_table_space_state_changes(self, name, state, tags):
        previous_state = self._table_space_states.get(name)
        if state:
            if previous_state is not None and state != previous_state:
                self._check.event(
                    {
                        'timestamp': timestamp(),
                        'event_type': self._check.EVENT_TABLE_SPACE_STATE,
                        'msg_title': 'Table space state change',
                        'msg_text': 'State of `{}` changed from `{}` to `{}`.'.format(name, previous_state, state),
                        'alert_type': 'info',
                        'source_type_name': self._check.METRIC_PREFIX,
                        'host': self._check.hostname,
                        'tags': tags,
                    }
                )
            self._table_space_states[name] = state
