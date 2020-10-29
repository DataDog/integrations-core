# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from itertools import chain
from time import time as timestamp

import ibm_db

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.utils.containers import iter_unique

from . import queries
from .utils import get_version, scrub_connection_string, status_to_service_check


class IbmDb2Check(AgentCheck):
    METRIC_PREFIX = 'ibm_db2'
    SERVICE_CHECK_CONNECT = '{}.can_connect'.format(METRIC_PREFIX)
    SERVICE_CHECK_STATUS = '{}.status'.format(METRIC_PREFIX)
    EVENT_TABLE_SPACE_STATE = '{}.tablespace_state_change'.format(METRIC_PREFIX)

    def __init__(self, name, init_config, instances):
        super(IbmDb2Check, self).__init__(name, init_config, instances)
        self._db = self.instance.get('db', '')
        self._username = self.instance.get('username', '')
        self._password = self.instance.get('password', '')
        self._host = self.instance.get('host', '')
        self._port = self.instance.get('port', 50000)
        self._tags = self.instance.get('tags', [])
        self._tls_cert = self.instance.get('tls_cert')

        # Add global database tag
        self._tags.append('db:{}'.format(self._db))

        # Track table space state changes
        self._table_space_states = {}

        # We'll connect on the first check run
        self._conn = None

        custom_queries = self.instance.get('custom_queries', [])
        use_global_custom_queries = self.instance.get('use_global_custom_queries', True)

        # Handle overrides
        if use_global_custom_queries == 'extend':
            custom_queries.extend(self.init_config.get('global_custom_queries', []))
        elif 'global_custom_queries' in self.init_config and is_affirmative(use_global_custom_queries):
            custom_queries = self.init_config.get('global_custom_queries', [])

        # Deduplicate
        self._custom_queries = list(iter_unique(custom_queries))

    def check(self, _):
        if self._conn is None:
            connection = self.get_connection()
            if connection is None:
                return

            self._conn = connection

        self.query_instance()
        self.query_database()
        self.query_buffer_pool()
        self.query_table_space()
        self.query_transaction_log()
        self.query_custom()
        self.collect_metadata()

    def collect_metadata(self):
        try:
            raw_version = get_version(self._conn)
        except Exception as e:
            self.log.error("Error getting version: %s", e)
            return

        if raw_version:
            version_parts = self.parse_version(raw_version)
            self.set_metadata('version', raw_version, scheme='parts', part_map=version_parts)

            self.log.debug('Found ibm_db2 version: %s', raw_version)
        else:
            self.log.warning('Could not retrieve ibm_db2 version info: %s', raw_version)

    def parse_version(self, version):
        """
        Raw version string is in format MM.mm.uuuu.
        Parse version to MM.mm.xx.yy
        where xx is the modification number and yy is the fix pack number
        https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.wn.doc/doc/c0070229.html#c0070229
        """
        major, minor, update = version.split('.')
        modification, fix = update[:2], update[2:]

        # remove leading zeros from raw version parts
        return {
            'major': str(int(major)),
            'minor': str(int(minor)),
            'mod': str(int(modification)),
            'fix': str(int(fix)),
        }

    def query_instance(self):
        # Only 1 instance
        for inst in self.iter_rows(queries.INSTANCE_TABLE, ibm_db.fetch_assoc):

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060773.html
            self.gauge(self.m('connection.active'), inst['total_connections'], tags=self._tags)

    def query_database(self):
        # Only 1 database
        for db in self.iter_rows(queries.DATABASE_TABLE, ibm_db.fetch_assoc):

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001156.html
            self.service_check(self.SERVICE_CHECK_STATUS, status_to_service_check(db['db_status']), tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001201.html
            self.gauge(self.m('application.active'), db['appls_cur_cons'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001202.html
            self.gauge(self.m('application.executing'), db['appls_in_db2'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002225.html
            self.gauge(self.m('connection.max'), db['connections_top'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001200.html
            self.monotonic_count(self.m('connection.total'), db['total_cons'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001283.html
            self.monotonic_count(self.m('lock.dead'), db['deadlocks'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001290.html
            self.monotonic_count(self.m('lock.timeouts'), db['lock_timeouts'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001281.html
            self.gauge(self.m('lock.active'), db['num_locks_held'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001296.html
            self.gauge(self.m('lock.waiting'), db['num_locks_waiting'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001294.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001293.html
            if db['lock_waits']:
                average_lock_wait = db['lock_wait_time'] / db['lock_waits']
            else:
                average_lock_wait = 0
            self.gauge(self.m('lock.wait'), average_lock_wait, tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001282.html
            # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.config.doc/doc/r0000267.html
            self.gauge(self.m('lock.pages'), db['lock_list_in_use'] / 4096, tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001160.html
            last_backup = db['last_backup']
            if last_backup:
                seconds_since_last_backup = (db['current_time'] - last_backup).total_seconds()
            else:
                seconds_since_last_backup = -1
            self.gauge(self.m('backup.latest'), seconds_since_last_backup, tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0051568.html
            self.monotonic_count(self.m('row.modified.total'), db['rows_modified'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001317.html
            self.monotonic_count(self.m('row.reads.total'), db['rows_read'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0051569.html
            self.monotonic_count(self.m('row.returned.total'), db['rows_returned'], tags=self._tags)

    def query_buffer_pool(self):
        # Hit ratio formulas:
        # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056871.html
        for bp in self.iter_rows(queries.BUFFER_POOL_TABLE, ibm_db.fetch_assoc):

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002256.html
            bp_tags = ['bufferpool:{}'.format(bp['bp_name'])]
            bp_tags.extend(self._tags)

            # Column-organized pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060858.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060874.html
            column_reads_physical = bp['pool_col_p_reads'] + bp['pool_temp_col_p_reads']
            self.monotonic_count(self.m('bufferpool.column.reads.physical'), column_reads_physical, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060763.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060873.html
            column_reads_logical = bp['pool_col_l_reads'] + bp['pool_temp_col_l_reads']
            self.monotonic_count(self.m('bufferpool.column.reads.logical'), column_reads_logical, tags=bp_tags)

            # Submit total
            self.monotonic_count(
                self.m('bufferpool.column.reads.total'), column_reads_physical + column_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060857.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060850.html
            column_pages_found = bp['pool_col_lbp_pages_found'] - bp['pool_async_col_lbp_pages_found']

            if column_reads_logical:
                column_hit_percent = column_pages_found / column_reads_logical * 100
            else:
                column_hit_percent = 0
            self.gauge(self.m('bufferpool.column.hit_percent'), column_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060855.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060856.html
            group_column_reads_logical = bp['pool_col_gbp_l_reads'] or 0
            group_column_pages_found = group_column_reads_logical - (bp['pool_col_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_column_reads_logical:  # no cov
                group_column_hit_percent = group_column_pages_found / group_column_reads_logical * 100
                self.gauge(self.m('bufferpool.group.column.hit_percent'), group_column_hit_percent, tags=bp_tags)

            # Data pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001236.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011300.html
            data_reads_physical = bp['pool_data_p_reads'] + bp['pool_temp_data_p_reads']
            self.monotonic_count(self.m('bufferpool.data.reads.physical'), data_reads_physical, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001235.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011302.html
            data_reads_logical = bp['pool_data_l_reads'] + bp['pool_temp_data_l_reads']
            self.monotonic_count(self.m('bufferpool.data.reads.logical'), data_reads_logical, tags=bp_tags)

            # Submit total
            self.monotonic_count(
                self.m('bufferpool.data.reads.total'), data_reads_physical + data_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056487.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056493.html
            data_pages_found = bp['pool_data_lbp_pages_found'] - bp['pool_async_data_lbp_pages_found']

            if data_reads_logical:
                data_hit_percent = data_pages_found / data_reads_logical * 100
            else:
                data_hit_percent = 0
            self.gauge(self.m('bufferpool.data.hit_percent'), data_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056485.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056486.html
            group_data_reads_logical = bp['pool_data_gbp_l_reads'] or 0
            group_data_pages_found = group_data_reads_logical - (bp['pool_data_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_data_reads_logical:  # no cov
                group_data_hit_percent = group_data_pages_found / group_data_reads_logical * 100
                self.gauge(self.m('bufferpool.group.data.hit_percent'), group_data_hit_percent, tags=bp_tags)

            # Index pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001239.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011301.html
            index_reads_physical = bp['pool_index_p_reads'] + bp['pool_temp_index_p_reads']
            self.monotonic_count(self.m('bufferpool.index.reads.physical'), index_reads_physical, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001238.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0011303.html
            index_reads_logical = bp['pool_index_l_reads'] + bp['pool_temp_index_l_reads']
            self.monotonic_count(self.m('bufferpool.index.reads.logical'), index_reads_logical, tags=bp_tags)

            # Submit total
            self.monotonic_count(
                self.m('bufferpool.index.reads.total'), index_reads_physical + index_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056243.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056496.html
            index_pages_found = bp['pool_index_lbp_pages_found'] - bp['pool_async_index_lbp_pages_found']

            if index_reads_logical:
                index_hit_percent = index_pages_found / index_reads_logical * 100
            else:
                index_hit_percent = 0
            self.gauge(self.m('bufferpool.index.hit_percent'), index_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056488.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056489.html
            group_index_reads_logical = bp['pool_index_gbp_l_reads'] or 0
            group_index_pages_found = group_index_reads_logical - (bp['pool_index_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_index_reads_logical:  # no cov
                group_index_hit_percent = group_index_pages_found / group_index_reads_logical * 100
                self.gauge(self.m('bufferpool.group.index.hit_percent'), group_index_hit_percent, tags=bp_tags)

            # XML storage object (XDA) pages

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022730.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022739.html
            xda_reads_physical = bp['pool_xda_p_reads'] + bp['pool_temp_xda_p_reads']
            self.monotonic_count(self.m('bufferpool.xda.reads.physical'), xda_reads_physical, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022731.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0022738.html
            xda_reads_logical = bp['pool_xda_l_reads'] + bp['pool_temp_xda_l_reads']
            self.monotonic_count(self.m('bufferpool.xda.reads.logical'), xda_reads_logical, tags=bp_tags)

            # Submit total
            self.monotonic_count(
                self.m('bufferpool.xda.reads.total'), xda_reads_physical + xda_reads_logical, tags=bp_tags
            )

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058666.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058670.html
            xda_pages_found = bp['pool_xda_lbp_pages_found'] - bp['pool_async_xda_lbp_pages_found']

            if xda_reads_logical:
                xda_hit_percent = xda_pages_found / xda_reads_logical * 100
            else:
                xda_hit_percent = 0
            self.gauge(self.m('bufferpool.xda.hit_percent'), xda_hit_percent, tags=bp_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058664.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0058665.html
            group_xda_reads_logical = bp['pool_xda_gbp_l_reads'] or 0
            group_xda_pages_found = group_xda_reads_logical - (bp['pool_xda_gbp_p_reads'] or 0)

            # Submit group ratio if in a pureScale environment
            if group_xda_reads_logical:  # no cov
                group_xda_hit_percent = group_xda_pages_found / group_xda_reads_logical * 100
                self.gauge(self.m('bufferpool.group.xda.hit_percent'), group_xda_hit_percent, tags=bp_tags)

            # Compute overall stats
            reads_physical = column_reads_physical + data_reads_physical + index_reads_physical + xda_reads_physical
            self.monotonic_count(self.m('bufferpool.reads.physical'), reads_physical, tags=bp_tags)

            reads_logical = column_reads_logical + data_reads_logical + index_reads_logical + xda_reads_logical
            self.monotonic_count(self.m('bufferpool.reads.logical'), reads_logical, tags=bp_tags)

            reads_total = reads_physical + reads_logical
            self.monotonic_count(self.m('bufferpool.reads.total'), reads_total, tags=bp_tags)

            if reads_logical:
                pages_found = column_pages_found + data_pages_found + index_pages_found + xda_pages_found
                hit_percent = pages_found / reads_logical * 100
            else:
                hit_percent = 0
            self.gauge(self.m('bufferpool.hit_percent'), hit_percent, tags=bp_tags)

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
                self.gauge(self.m('bufferpool.group.hit_percent'), group_hit_percent, tags=bp_tags)

    def query_table_space(self):
        # Utilization formulas:
        # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0056516.html
        for ts in self.iter_rows(queries.TABLE_SPACE_TABLE, ibm_db.fetch_assoc):

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001295.html
            table_space_name = ts['tbsp_name']
            ts_tags = ['tablespace:{}'.format(table_space_name)]
            ts_tags.extend(self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007534.html
            page_size = ts['tbsp_page_size']

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007539.html
            total_pages = ts['tbsp_total_pages']
            self.gauge(self.m('tablespace.size'), total_pages * page_size, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007540.html
            usable_pages = ts['tbsp_usable_pages']
            self.gauge(self.m('tablespace.usable'), usable_pages * page_size, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007541.html
            used_pages = ts['tbsp_used_pages']
            self.gauge(self.m('tablespace.used'), used_pages * page_size, tags=ts_tags)

            # Percent utilized
            if usable_pages:
                utilized = used_pages / usable_pages * 100
            else:
                utilized = 0
            self.gauge(self.m('tablespace.utilized'), utilized, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007533.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.dbobj.doc/doc/c0060111.html
            self.track_table_space_state_changes(table_space_name, ts['tbsp_state'], ts_tags)

    def query_transaction_log(self):
        # Only 1 transaction log
        for tlog in self.iter_rows(queries.TRANSACTION_LOG_TABLE, ibm_db.fetch_assoc):

            # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.config.doc/doc/r0000239.html
            block_size = 4096

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002530.html
            used = tlog['total_log_used']
            self.gauge(self.m('log.used'), used / block_size, tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002531.html
            available = tlog['total_log_available']

            # Handle infinite log space
            if available == -1:
                utilized = 0
            else:
                utilized = used / available * 100
                available /= block_size

            self.gauge(self.m('log.available'), available, tags=self._tags)
            self.gauge(self.m('log.utilized'), utilized, tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001278.html
            self.monotonic_count(self.m('log.reads'), tlog['log_reads'], tags=self._tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001279.html
            self.monotonic_count(self.m('log.writes'), tlog['log_writes'], tags=self._tags)

    def query_custom(self):
        for custom_query in self._custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:  # no cov
                self.log.error('Custom query field `metric_prefix` is required')
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:  # no cov
                self.log.error('Custom query field `query` is required for metric_prefix `%s`', metric_prefix)
                continue

            columns = custom_query.get('columns')
            if not columns:  # no cov
                self.log.error('Custom query field `columns` is required for metric_prefix `%s`', metric_prefix)
                continue

            rows = self.iter_rows(query, ibm_db.fetch_tuple)
            self.log.debug('Running query for metric_prefix `%s`: `%s`', metric_prefix, query)

            # Trigger query execution
            try:
                first_row = next(rows)
            except Exception as e:  # no cov
                self.log.error('Error executing query for metric_prefix `%s`: `%s`', metric_prefix, e)
                continue

            for row in chain((first_row,), rows):
                if not row:  # no cov
                    self.log.debug('Query result for metric_prefix `%s`: returned an empty result', metric_prefix)
                    continue

                if len(columns) != len(row):  # no cov
                    self.log.error(
                        'Query result for metric_prefix `%s`: expected %s columns, got %s',
                        metric_prefix,
                        len(columns),
                        len(row),
                    )
                    continue

                metric_info = []
                query_tags = list(self._tags)
                query_tags.extend(custom_query.get('tags', []))

                for column, value in zip(columns, row):
                    # Columns can be ignored via configuration.
                    if not column:  # no cov
                        continue

                    name = column.get('name')
                    if not name:  # no cov
                        self.log.error('Column field `name` is required for metric_prefix `%s`', metric_prefix)
                        break

                    column_type = column.get('type')
                    if not column_type:  # no cov
                        self.log.error(
                            'Column field `type` is required for column `%s` of metric_prefix `%s`',
                            name,
                            metric_prefix,
                        )
                        break

                    if column_type == 'tag':
                        query_tags.append('{}:{}'.format(name, value))
                    else:
                        if not hasattr(self, column_type):
                            self.log.error(
                                'Invalid submission method `%s` for metric column `%s` of metric_prefix `%s`',
                                column_type,
                                name,
                                metric_prefix,
                            )
                            break
                        try:
                            metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                        except (ValueError, TypeError):  # no cov
                            self.log.error(
                                'Non-numeric value `%s` for metric column `%s` of metric_prefix `%s`',
                                value,
                                name,
                                metric_prefix,
                            )
                            break

                # Only submit metrics if there were absolutely no errors - all or nothing.
                else:
                    for info in metric_info:
                        metric, value, method = info
                        getattr(self, method)(metric, value, tags=query_tags)

    def track_table_space_state_changes(self, name, state, tags):
        previous_state = self._table_space_states.get(name)
        if state:
            if previous_state is not None and state != previous_state:
                self.event(
                    {
                        'timestamp': timestamp(),
                        'event_type': self.EVENT_TABLE_SPACE_STATE,
                        'msg_title': 'Table space state change',
                        'msg_text': 'State of `{}` changed from `{}` to `{}`.'.format(name, previous_state, state),
                        'alert_type': 'info',
                        'source_type_name': self.METRIC_PREFIX,
                        'host': self.hostname,
                        'tags': tags,
                    }
                )
            self._table_space_states[name] = state

    def get_connection(self):
        target, username, password = self.get_connection_data(
            self._db, self._username, self._password, self._host, self._port, self._tls_cert
        )

        # Get column names in lower case
        connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}

        try:
            connection = ibm_db.connect(target, username, password, connection_options)
        except Exception as e:
            if self._host:
                self.log.error('Unable to connect with `%s`: %s', scrub_connection_string(target), e)
            else:  # no cov
                self.log.error('Unable to connect to database `%s` as user `%s`: %s', target, username, e)
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, tags=self._tags)
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)
            return connection

    @classmethod
    def get_connection_data(cls, db, username, password, host, port, tls_cert):
        if host:
            target = 'database={};hostname={};port={};protocol=tcpip;uid={};pwd={}'.format(
                db, host, port, username, password
            )
            username = ''
            password = ''
            if tls_cert:
                target = '{};security=ssl;sslservercertificate={}'.format(target, tls_cert)
        else:  # no cov
            target = db

        return target, username, password

    def iter_rows(self, query, method):
        # https://github.com/ibmdb/python-ibmdb/wiki/APIs
        try:
            cursor = ibm_db.exec_immediate(self._conn, query)
        except Exception as e:
            error = str(e)
            self.log.error("Error executing query, attempting to a new connection: %s", error)
            connection = self.get_connection()

            if connection is None:
                raise ConnectionError("Unable to create new connection")

            self._conn = connection
            cursor = ibm_db.exec_immediate(self._conn, query)

        row = method(cursor)
        while row is not False:
            yield row

            # Get next row, if any
            row = method(cursor)

    @classmethod
    def m(cls, metric):
        return '{}.{}'.format(cls.METRIC_PREFIX, metric)
