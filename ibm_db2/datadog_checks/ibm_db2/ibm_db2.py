# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from itertools import chain
from string import Template
from time import time as timestamp

from requests import ConnectionError

from datadog_checks.base import AgentCheck, is_affirmative
from datadog_checks.base.checks.db import DatabaseCheck
from datadog_checks.base.utils.containers import iter_unique
from datadog_checks.base.utils.db.utils import TagManager, default_json_event_encoding, resolve_db_host
from datadog_checks.base.utils.platform import Platform
from datadog_checks.base.utils.serialization import json

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

if Platform.is_windows():
    # After installing ibm_db, dll path of dependent library of clidriver must be set before importing the module
    # Ref: https://github.com/ibmdb/python-ibmdb/#installation
    import os

    embedded_lib = os.path.dirname(os.path.abspath(os.__file__))
    os.add_dll_directory(os.path.join(embedded_lib, 'site-packages', 'clidriver', 'bin'))

import ibm_db

from . import queries
from .__about__ import __version__
from .config import IbmDb2Config
from .connection import Db2Connection
from .metadata import Db2Metadata
from .statement_samples import Db2StatementSamples
from .statements import Db2StatementMetrics
from .utils import (
    get_version,
    hadr_status_to_service_check,
    is_connection_error,
    scrub_connection_string,
    status_to_service_check,
)

DATABASE_MONOTONIC_METRICS = (
    ('transaction.commits', 'total_app_commits'),
    ('transaction.commits.internal', 'int_commits'),
    ('transaction.rollbacks', 'total_app_rollbacks'),
    ('transaction.rollbacks.internal', 'int_rollbacks'),
    ('row.inserted.total', 'rows_inserted'),
    ('row.updated.total', 'rows_updated'),
    ('row.deleted.total', 'rows_deleted'),
    ('activity.completed', 'act_completed_total'),
    ('activity.aborted', 'act_aborted_total'),
    ('activity.rejected', 'act_rejected_total'),
    ('request.completed', 'rqsts_completed_total'),
    ('section.executions', 'total_app_section_executions'),
    ('lock.waits', 'lock_waits'),
    ('lock.wait_time', 'lock_wait_time'),
    ('lock.escalations', 'lock_escals'),
    ('lock.escalations.locklist', 'lock_escals_locklist'),
    ('lock.escalations.maxlocks', 'lock_escals_maxlocks'),
    ('direct.reads', 'direct_reads'),
    ('direct.read_reqs', 'direct_read_reqs'),
    ('direct.read_time', 'direct_read_time'),
    ('direct.writes', 'direct_writes'),
    ('direct.write_reqs', 'direct_write_reqs'),
    ('direct.write_time', 'direct_write_time'),
    ('sort.total', 'total_sorts'),
    ('sort.overflows', 'sort_overflows'),
    ('sort.post_threshold', 'post_threshold_sorts'),
    ('sort.post_shrthreshold', 'post_shrthreshold_sorts'),
    ('sort.section.total', 'total_section_sorts'),
    ('sort.section.time', 'total_section_sort_time'),
    ('sort.section.proc_time', 'total_section_sort_proc_time'),
    ('hash.joins.total', 'total_hash_joins'),
    ('hash.joins.loops', 'total_hash_loops'),
    ('hash.joins.overflows', 'hash_join_overflows'),
    ('hash.joins.small_overflows', 'hash_join_small_overflows'),
    ('hash.joins.post_threshold', 'post_threshold_hash_joins'),
    ('hash.joins.post_shrthreshold', 'post_shrthreshold_hash_joins'),
    ('hash.grpbys.total', 'total_hash_grpbys'),
    ('hash.grpbys.overflows', 'hash_grpby_overflows'),
)

INSTANCE_GAUGE_METRICS = (
    ('databases.active', 'con_local_dbases'),
    ('agent.registered', 'agents_registered'),
    ('agent.registered.max', 'agents_registered_top'),
    ('agent.idle', 'idle_agents'),
    ('agent.coord', 'num_coord_agents'),
    ('agent.coord.max', 'coord_agents_top'),
)

INSTANCE_MONOTONIC_METRICS = (
    ('agent.from_pool', 'agents_from_pool'),
    ('agent.created_empty_pool', 'agents_created_empty_pool'),
)

BUFFER_POOL_PAGE_CLASSES = (
    ('column', 'col'),
    ('data', 'data'),
    ('index', 'index'),
    ('xda', 'xda'),
)

BUFFER_POOL_MONOTONIC_METRICS = (
    ('bufferpool.read_time', 'pool_read_time'),
    ('bufferpool.write_time', 'pool_write_time'),
    ('bufferpool.unread_prefetch_pages', 'unread_prefetch_pages'),
    ('bufferpool.prefetch_wait_time', 'prefetch_wait_time'),
    ('bufferpool.prefetch_waits', 'prefetch_waits'),
    ('bufferpool.no_victim_buffer', 'pool_no_victim_buffer'),
    ('bufferpool.vectored_ios', 'vectored_ios'),
    ('bufferpool.pages_from_vectored_ios', 'pages_from_vectored_ios'),
    ('bufferpool.block_ios', 'block_ios'),
    ('bufferpool.pages_from_block_ios', 'pages_from_block_ios'),
    ('bufferpool.files_closed', 'files_closed'),
)

BUFFER_POOL_GAUGE_METRICS = (
    ('bufferpool.pages.configured', 'bp_cur_buffsz'),
    ('bufferpool.pages.left_to_remove', 'bp_pages_left_to_remove'),
    ('bufferpool.tablespaces', 'bp_tbsp_use_count'),
)

TRANSACTION_LOG_MONOTONIC_METRICS = (
    ('log.read_time', 'log_read_time'),
    ('log.write_time', 'log_write_time'),
    ('log.read_io', 'num_log_read_io'),
    ('log.write_io', 'num_log_write_io'),
    ('log.partial_page_io', 'num_log_part_page_io'),
    ('log.buffer_full', 'num_log_buffer_full'),
    ('log.data_found_in_buffer', 'num_log_data_found_in_buffer'),
    ('log.cur_commit.reads.total', 'cur_commit_total_log_reads'),
    ('log.cur_commit.reads.disk', 'cur_commit_disk_log_reads'),
    ('log.cur_commit.reads.buffer', 'cur_commit_log_buff_log_reads'),
    ('hadr.log_wait.time', 'log_hadr_wait_time'),
    ('hadr.log_wait.count', 'log_hadr_waits_total'),
)

TRANSACTION_LOG_GAUGE_METRICS = (
    ('log.space.used.max', 'tot_log_used_top'),
    ('log.secondary.used.max', 'sec_log_used_top'),
    ('log.secondary.allocated', 'sec_logs_allocated'),
    ('log.files.reusable', 'num_logs_avail_for_rename'),
    ('log.to_redo_for_recovery', 'log_to_redo_for_recovery'),
    ('log.held_by_dirty_pages', 'log_held_by_dirty_pages'),
    ('log.indoubt_transactions', 'num_indoubt_trans'),
)

MEMORY_POOL_GAUGE_METRICS = (
    ('memory.pool.used', 'memory_pool_used'),
    ('memory.pool.used_hwm', 'memory_pool_used_hwm'),
)

MEMORY_SET_GAUGE_METRICS = (
    ('memory.set.committed', 'memory_set_committed'),
    ('memory.set.used', 'memory_set_used'),
    ('memory.set.used_hwm', 'memory_set_used_hwm'),
    ('memory.set.additional_committed', 'additional_committed'),
    ('memory.set.size', 'memory_set_size'),
)

WLM_MONOTONIC_METRICS = (
    ('wlm.total_cpu_time', 'total_cpu_time'),
    ('wlm.activities.completed', 'act_completed_total'),
    ('wlm.activities.aborted', 'act_aborted_total'),
    ('wlm.activities.rejected', 'act_rejected_total'),
    ('wlm.app_activities.completed', 'app_act_completed_total'),
    ('wlm.app_activities.aborted', 'app_act_aborted_total'),
    ('wlm.app_activities.rejected', 'app_act_rejected_total'),
    ('wlm.activity_requests', 'act_rqsts_total'),
    ('wlm.requests.completed', 'rqsts_completed_total'),
    ('wlm.app_requests.completed', 'app_rqsts_completed_total'),
    ('wlm.total_wait_time', 'total_wait_time'),
    ('wlm.total_request_time', 'total_rqst_time'),
    ('wlm.total_app_request_time', 'total_app_rqst_time'),
    ('wlm.queue_time', 'wlm_queue_time_total'),
    ('wlm.queue_assignments', 'wlm_queue_assignments_total'),
    ('wlm.total_activity_time', 'total_act_time'),
    ('wlm.total_activity_wait_time', 'total_act_wait_time'),
    ('wlm.total_section_time', 'total_section_time'),
    ('wlm.total_section_proc_time', 'total_section_proc_time'),
    ('wlm.commits', 'total_app_commits'),
    ('wlm.rollbacks', 'total_app_rollbacks'),
    ('wlm.internal_commits', 'int_commits'),
    ('wlm.internal_rollbacks', 'int_rollbacks'),
    ('wlm.lock_wait_time', 'lock_wait_time'),
    ('wlm.lock_waits', 'lock_waits'),
    ('wlm.pool_read_time', 'pool_read_time'),
    ('wlm.pool_write_time', 'pool_write_time'),
    ('wlm.direct_read_time', 'direct_read_time'),
    ('wlm.direct_write_time', 'direct_write_time'),
    ('wlm.log_disk_wait_time', 'log_disk_wait_time'),
    ('wlm.log_buffer_wait_time', 'log_buffer_wait_time'),
    ('wlm.agent_wait_time', 'agent_wait_time'),
    ('wlm.agent_waits', 'agent_waits_total'),
    ('wlm.client_idle_wait_time', 'client_idle_wait_time'),
    ('wlm.prefetch_wait_time', 'prefetch_wait_time'),
    ('wlm.extended_latch_wait_time', 'total_extended_latch_wait_time'),
    ('wlm.extended_latch_waits', 'total_extended_latch_waits'),
    ('wlm.fcm_recv_wait_time', 'fcm_recv_wait_time'),
    ('wlm.fcm_send_wait_time', 'fcm_send_wait_time'),
    ('wlm.tcpip_recv_wait_time', 'tcpip_recv_wait_time'),
    ('wlm.tcpip_send_wait_time', 'tcpip_send_wait_time'),
    ('wlm.ipc_recv_wait_time', 'ipc_recv_wait_time'),
    ('wlm.ipc_send_wait_time', 'ipc_send_wait_time'),
    ('wlm.cf_wait_time', 'cf_wait_time'),
    ('wlm.cf_waits', 'cf_waits'),
    ('wlm.reclaim_wait_time', 'reclaim_wait_time'),
)

HADR_GAUGE_METRICS = (
    ('hadr.log_gap', 'hadr_log_gap'),
    ('hadr.log_wait.current', 'log_hadr_wait_cur'),
    ('hadr.time_since_last_recv', 'time_since_last_recv'),
    ('hadr.primary_log_pos', 'primary_log_pos'),
    ('hadr.standby_log_pos', 'standby_log_pos'),
    ('hadr.standby_replay_log_pos', 'standby_replay_log_pos'),
    ('hadr.recv_replay_gap', 'standby_recv_replay_gap'),
    ('hadr.standby_recv_buf_size', 'standby_recv_buf_size'),
    ('hadr.standby_recv_buf_percent', 'standby_recv_buf_percent'),
    ('hadr.standby_spool_limit', 'standby_spool_limit'),
    ('hadr.standby_spool_percent', 'standby_spool_percent'),
    ('hadr.sock_send_buf', 'sock_send_buf_actual'),
    ('hadr.sock_recv_buf', 'sock_recv_buf_actual'),
    ('hadr.heartbeat.interval', 'heartbeat_interval'),
    ('hadr.timeout', 'hadr_timeout'),
    ('hadr.heartbeat.missed', 'heartbeat_missed'),
    ('hadr.heartbeat.expected', 'heartbeat_expected'),
    ('hadr.peer_window', 'peer_window'),
    ('hadr.takeover_app_remaining.primary', 'takeover_app_remaining_primary'),
    ('hadr.takeover_app_remaining.standby', 'takeover_app_remaining_standby'),
    ('hadr.replay_only_window.tran_count', 'standby_replay_only_window_tran_count'),
)


class IbmDb2Check(DatabaseCheck):
    METRIC_PREFIX = 'ibm_db2'
    SERVICE_CHECK_CONNECT = '{}.can_connect'.format(METRIC_PREFIX)
    SERVICE_CHECK_STATUS = '{}.status'.format(METRIC_PREFIX)
    SERVICE_CHECK_HADR_STATUS = '{}.hadr.status'.format(METRIC_PREFIX)
    EVENT_TABLE_SPACE_STATE = '{}.tablespace_state_change'.format(METRIC_PREFIX)

    def __init__(self, name, init_config, instances):
        super(IbmDb2Check, self).__init__(name, init_config, instances)
        self._config = IbmDb2Config(self.init_config, self.instance, self.log)
        self._db = self._config.db
        self._username = self._config.username
        self._password = self._config.password
        self._host = self._config.host
        self._port = self._config.port
        self._tags = list(self._config.tags)
        self._security = self._config.security
        self._tls_cert = self._config.tls_cert
        self._connection_timeout = self._config.connection_timeout
        self._dbms_version = None
        self._resolved_hostname = None
        self._agent_hostname = None
        self._database_identifier = None
        self._database_instance_emitted = {}

        # Add global database tag
        self._tags.append('db:{}'.format(self._db))
        self.tag_manager = TagManager(normalizer=lambda tag: self.normalize_tag(tag).lower())
        self.tag_manager.set_tags_from_list(self._tags, replace=True)
        self.add_core_tags()
        self.set_resource_tags()
        self.connection = Db2Connection(self, self._config)
        self.statement_metrics = Db2StatementMetrics(self, self._config)
        self.statement_samples = Db2StatementSamples(self, self._config)
        self.dbm_metadata = Db2Metadata(self, self._config)

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
        self._query_methods = (
            self.query_instance,
            self.query_database,
            self.query_memory_pool,
            self.query_memory_set,
            self.query_wlm_workload,
            self.query_wlm_service_class,
            self.query_buffer_pool,
            self.query_table_space,
            self.query_container,
            self.query_transaction_log,
            self.query_hadr,
            self.query_custom,
        )

    def check(self, instance):
        if self._conn is None:
            self._conn = self.get_connection()
        self.emit_connection_service_checks()
        if self._conn is None:
            return

        self.collect_metadata()
        self._send_database_instance_metadata()
        for query_method in self._query_methods:
            try:
                query_method()
            except ConnectionError:
                raise
            except Exception as e:
                self.log.warning('Encountered error running `%s`: %s', query_method.__name__, str(e))
                continue

        if self._config.dbm_enabled:
            self.statement_metrics.run_job_loop(self.tag_manager.get_tags())
            self.statement_samples.run_job_loop(self.tag_manager.get_tags())
            self.dbm_metadata.run_job_loop(self.tag_manager.get_tags())

    def cancel(self):
        self.statement_metrics.cancel()
        self.statement_samples.cancel()
        self.dbm_metadata.cancel()
        self.connection.close()

    @AgentCheck.metadata_entrypoint
    def collect_metadata(self):
        try:
            raw_version = get_version(self._conn)
        except Exception as e:
            self.log.error("Error getting version: %s", e)
            return

        if raw_version:
            self._dbms_version = raw_version
            version_parts = self.parse_version(raw_version)
            self.set_metadata('version', raw_version, scheme='parts', part_map=version_parts)

            self.log.debug('Found ibm_db2 version: %s', raw_version)
        else:
            self.log.warning('Could not retrieve ibm_db2 version info: %s', raw_version)

    @property
    def agent_hostname(self):
        if self._agent_hostname is None:
            self._agent_hostname = datadog_agent.get_hostname()
        return self._agent_hostname

    @property
    def dbms(self):
        return 'db2'

    @property
    def dbms_version(self):
        return self._dbms_version or ''

    @property
    def reported_hostname(self):
        if self._config.exclude_hostname:
            return None
        return self.resolved_hostname

    @property
    def resolved_hostname(self):
        if self._resolved_hostname is None:
            if self._config.reported_hostname:
                self._resolved_hostname = self._config.reported_hostname
            else:
                self._resolved_hostname = resolve_db_host(self._host)
        return self._resolved_hostname

    @property
    def database_hostname(self):
        return self.resolved_hostname

    @property
    def database_identifier(self):
        if self._database_identifier is None:
            template = self._config.database_identifier.get('template') or '$resolved_hostname'
            self._database_identifier = Template(template).safe_substitute(
                {
                    'resolved_hostname': self.resolved_hostname,
                    'host': self._host,
                    'port': self._port,
                    'db': self._db,
                }
            )
        return self._database_identifier

    @property
    def tags(self):
        return self.tag_manager.get_tags()

    @property
    def cloud_metadata(self):
        return self._config.cloud_metadata

    def add_core_tags(self):
        self.tag_manager.set_tag('database_hostname', self.database_hostname, replace=True)
        self.tag_manager.set_tag('database_instance', self.database_identifier, replace=True)

    def set_resource_tags(self):
        self.tag_manager.set_tag('dd.internal.resource:database_instance', self.database_identifier, replace=True)

    def _send_database_instance_metadata(self):
        now = timestamp()
        last_emit_time = self._database_instance_emitted.get(self.database_identifier)
        if last_emit_time is None or now - last_emit_time >= self._config.database_instance_collection_interval:
            event = {
                'host': self.reported_hostname,
                'port': self._port,
                'database_instance': self.database_identifier,
                'database_hostname': self.database_hostname,
                'agent_version': datadog_agent.get_version(),
                'ddagenthostname': self.agent_hostname,
                'dbms': self.dbms,
                'kind': 'database_instance',
                'collection_interval': self._config.database_instance_collection_interval,
                'dbms_version': self.dbms_version,
                'integration_version': __version__,
                'tags': self.tag_manager.get_tags(),
                'timestamp': now * 1000,
                'cloud_metadata': self.cloud_metadata,
                'metadata': {
                    'dbm': self._config.dbm_enabled,
                    'connection_host': self._host,
                },
            }
            self._database_instance_emitted[self.database_identifier] = now
            self.database_monitoring_metadata(json.dumps(event, default=default_json_event_encoding))

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
            instance_tags = self._member_tags(inst)
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0060773.html
            self.gauge(self.m('connection.active'), inst['total_connections'], tags=instance_tags)
            self.gauge(self.m('running'), 1, tags=instance_tags)

            db2_start_time = inst['db2start_time']
            if db2_start_time:
                self.gauge(
                    self.m('uptime'), (inst['current_time'] - db2_start_time).total_seconds(), tags=instance_tags
                )

            for metric, column in INSTANCE_GAUGE_METRICS:
                self._gauge(metric, inst[column], tags=instance_tags)

            for metric, column in INSTANCE_MONOTONIC_METRICS:
                self._monotonic_count(metric, inst[column], tags=instance_tags)

    def query_database(self):
        # Only 1 database
        for db in self.iter_rows(queries.DATABASE_TABLE, ibm_db.fetch_assoc):
            database_tags = self._member_tags(db)
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001156.html
            self.service_check(self.SERVICE_CHECK_STATUS, status_to_service_check(db['db_status']), tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001201.html
            self.gauge(self.m('application.active'), db['appls_cur_cons'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001202.html
            self.gauge(self.m('application.executing'), db['appls_in_db2'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002225.html
            self.gauge(self.m('connection.max'), db['connections_top'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001200.html
            self.monotonic_count(self.m('connection.total'), db['total_cons'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001283.html
            self.monotonic_count(self.m('lock.dead'), db['deadlocks'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001290.html
            self.monotonic_count(self.m('lock.timeouts'), db['lock_timeouts'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001281.html
            self.gauge(self.m('lock.active'), db['num_locks_held'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001296.html
            self.gauge(self.m('lock.waiting'), db['num_locks_waiting'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001294.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001293.html
            if db['lock_waits']:
                average_lock_wait = db['lock_wait_time'] / db['lock_waits']
            else:
                average_lock_wait = 0
            self.gauge(self.m('lock.wait'), average_lock_wait, tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001282.html
            # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.config.doc/doc/r0000267.html
            self.gauge(self.m('lock.pages'), db['lock_list_in_use'] / 4096, tags=database_tags)

            for metric, column in DATABASE_MONOTONIC_METRICS:
                self._monotonic_count(metric, db[column], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001160.html
            last_backup = db['last_backup']
            if last_backup:
                seconds_since_last_backup = (db['current_time'] - last_backup).total_seconds()
            else:
                seconds_since_last_backup = -1
            self.gauge(self.m('backup.latest'), seconds_since_last_backup, tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0051568.html
            self.monotonic_count(self.m('row.modified.total'), db['rows_modified'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001317.html
            self.monotonic_count(self.m('row.reads.total'), db['rows_read'], tags=database_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0051569.html
            self.monotonic_count(self.m('row.returned.total'), db['rows_returned'], tags=database_tags)

    def query_memory_pool(self) -> None:
        for memory_pool in self.iter_rows(queries.MEMORY_POOL_TABLE, ibm_db.fetch_assoc):
            if memory_pool.get('application_handle') is not None or memory_pool.get('edu_id') is not None:
                continue

            tags = self._memory_tags(memory_pool)
            self._add_tag(tags, 'memory_pool', memory_pool.get('memory_pool_type'))
            for metric, column in MEMORY_POOL_GAUGE_METRICS:
                self._gauge(metric, memory_pool.get(column), tags=tags)

    def query_memory_set(self) -> None:
        for memory_set in self.iter_rows(queries.MEMORY_SET_TABLE, ibm_db.fetch_assoc):
            tags = self._memory_tags(memory_set)
            for metric, column in MEMORY_SET_GAUGE_METRICS:
                self._gauge(metric, memory_set.get(column), tags=tags)

    def query_wlm_workload(self) -> None:
        for workload in self.iter_rows(queries.WLM_WORKLOAD_TABLE, ibm_db.fetch_assoc):
            self._submit_wlm_metrics(workload, self._wlm_workload_tags(workload))

    def query_wlm_service_class(self) -> None:
        if not self._config.collect_wlm_service_class_metrics:
            return

        for service_class in self.iter_rows(queries.WLM_SERVICE_SUBCLASS_TABLE, ibm_db.fetch_assoc):
            self._submit_wlm_metrics(service_class, self._wlm_service_class_tags(service_class))

    def query_buffer_pool(self):
        # Hit ratio formulas:
        # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0056871.html
        for bp in self.iter_rows(queries.BUFFER_POOL_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002256.html
            bp_tags = ['bufferpool:{}'.format(bp['bp_name'])]
            self._add_tag(bp_tags, 'member', bp.get('member'))
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

            writes_total = 0
            for metric_page_class, column_page_class in BUFFER_POOL_PAGE_CLASSES:
                writes = bp['pool_{}_writes'.format(column_page_class)]
                writes_total += writes
                self._monotonic_count('bufferpool.{}.writes'.format(metric_page_class), writes, tags=bp_tags)
                self._monotonic_count(
                    'bufferpool.{}.reads.async'.format(metric_page_class),
                    bp['pool_async_{}_reads'.format(column_page_class)],
                    tags=bp_tags,
                )
                self._monotonic_count(
                    'bufferpool.{}.writes.async'.format(metric_page_class),
                    bp['pool_async_{}_writes'.format(column_page_class)],
                    tags=bp_tags,
                )

            self._monotonic_count('bufferpool.writes.total', writes_total, tags=bp_tags)

            for metric, column in BUFFER_POOL_MONOTONIC_METRICS:
                self._monotonic_count(metric, bp[column], tags=bp_tags)

            for metric, column in BUFFER_POOL_GAUGE_METRICS:
                self._gauge(metric, bp[column], tags=bp_tags)

    def query_table_space(self):
        # Utilization formulas:
        # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.sql.rtn.doc/doc/r0056516.html
        for ts in self.iter_rows(queries.TABLE_SPACE_TABLE, ibm_db.fetch_assoc):
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001295.html
            table_space_name = ts['tbsp_name']
            ts_tags = ['tablespace:{}'.format(table_space_name)]
            if ts.get('tbsp_type'):
                ts_tags.append('tablespace_type:{}'.format(ts['tbsp_type'].lower()))
            if ts.get('tbsp_content_type'):
                ts_tags.append('tablespace_content_type:{}'.format(ts['tbsp_content_type'].lower()))
            if ts.get('storage_group_name'):
                ts_tags.append('storage_group:{}'.format(ts['storage_group_name']))
            self._add_tag(ts_tags, 'member', ts.get('member'))
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
            used_bytes = used_pages * page_size
            self.gauge(self.m('tablespace.used'), used_bytes, tags=ts_tags)

            # Percent utilized
            if usable_pages:
                utilized = used_pages / usable_pages * 100
            else:
                utilized = 0
            self.gauge(self.m('tablespace.utilized'), utilized, tags=ts_tags)

            free_pages = ts['tbsp_free_pages']
            if free_pages is not None and free_pages >= 0:
                self.gauge(self.m('tablespace.free'), free_pages * page_size, tags=ts_tags)

            self.gauge(self.m('tablespace.high_water_mark'), ts['tbsp_page_top'] * page_size, tags=ts_tags)

            pending_free_pages = ts['tbsp_pending_free_pages']
            if pending_free_pages is not None and pending_free_pages >= 0:
                self.gauge(self.m('tablespace.pending_free'), pending_free_pages * page_size, tags=ts_tags)

            max_size = ts['tbsp_max_size']
            if max_size is not None and max_size > 0:
                self.gauge(self.m('tablespace.max_size'), max_size, tags=ts_tags)
                self.gauge(self.m('tablespace.max_utilized'), used_bytes / max_size * 100, tags=ts_tags)

            initial_size = ts['tbsp_initial_size']
            if initial_size is not None and initial_size > 0:
                self.gauge(self.m('tablespace.initial_size'), initial_size, tags=ts_tags)

            increase_size = ts['tbsp_increase_size']
            if increase_size is not None and increase_size > 0:
                self.gauge(self.m('tablespace.increase_size'), increase_size, tags=ts_tags)

            self.gauge(self.m('tablespace.containers'), ts['tbsp_num_containers'], tags=ts_tags)
            self.gauge(self.m('tablespace.last_resize_failed'), ts['tbsp_last_resize_failed'], tags=ts_tags)
            self.gauge(self.m('tablespace.online'), 1 if ts['tbsp_state'] == 'NORMAL' else 0, tags=ts_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0007533.html
            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.dbobj.doc/doc/c0060111.html
            self.track_table_space_state_changes(
                table_space_name,
                ts['tbsp_state'],
                ts_tags,
                state_key='{}:{}'.format(table_space_name, ts.get('member')),
            )

    def query_container(self) -> None:
        if not self._config.collect_container_metrics:
            return

        for container in self.iter_rows(queries.CONTAINER_TABLE, ibm_db.fetch_assoc):
            container_tags = self._container_tags(container)
            page_size = container.get('tbsp_page_size')

            self._gauge_nonnegative('container.fs_total', container.get('fs_total_size'), tags=container_tags)
            self._gauge_nonnegative('container.fs_used', container.get('fs_used_size'), tags=container_tags)
            self._gauge_nonnegative('container.accessible', container.get('accessible'), tags=container_tags)

            if page_size is not None:
                total_pages = container.get('total_pages')
                if total_pages is not None and total_pages >= 0:
                    self.gauge(self.m('container.total'), total_pages * page_size, tags=container_tags)

                usable_pages = container.get('usable_pages')
                if usable_pages is not None and usable_pages >= 0:
                    self.gauge(self.m('container.usable'), usable_pages * page_size, tags=container_tags)

    def query_transaction_log(self):
        # Only 1 transaction log
        for tlog in self.iter_rows(queries.TRANSACTION_LOG_TABLE, ibm_db.fetch_assoc):
            transaction_log_tags = self._member_tags(tlog)
            # https://www.ibm.com/support/knowledgecenter/en/SSEPGG_11.1.0/com.ibm.db2.luw.admin.config.doc/doc/r0000239.html
            block_size = 4096

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002530.html
            used = tlog['total_log_used']
            self.gauge(self.m('log.used'), used / block_size, tags=transaction_log_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0002531.html
            available = tlog['total_log_available']

            # Handle infinite log space
            if available == -1:
                utilized = 0
            else:
                utilized = used / available * 100
                available /= block_size

            self.gauge(self.m('log.available'), available, tags=transaction_log_tags)
            self.gauge(self.m('log.utilized'), utilized, tags=transaction_log_tags)
            self.gauge(self.m('log.space.used'), used, tags=transaction_log_tags)
            if tlog['total_log_available'] != -1:
                self.gauge(self.m('log.space.available'), tlog['total_log_available'], tags=transaction_log_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001278.html
            self.monotonic_count(self.m('log.reads'), tlog['log_reads'], tags=transaction_log_tags)

            # https://www.ibm.com/support/knowledgecenter/SSEPGG_11.1.0/com.ibm.db2.luw.admin.mon.doc/doc/r0001279.html
            self.monotonic_count(self.m('log.writes'), tlog['log_writes'], tags=transaction_log_tags)

            for metric, column in TRANSACTION_LOG_MONOTONIC_METRICS:
                self._monotonic_count(metric, tlog[column], tags=transaction_log_tags)

            for metric, column in TRANSACTION_LOG_GAUGE_METRICS:
                self._gauge(metric, tlog[column], tags=transaction_log_tags)

    def query_hadr(self) -> None:
        hadr_rows = 0
        primary_standby_count = 0
        for hadr in self.iter_rows(queries.HADR_TABLE, ibm_db.fetch_assoc):
            hadr_rows += 1
            hadr_tags = self._hadr_tags(hadr)
            hadr_role = hadr.get('hadr_role')
            if hadr_role == 'PRIMARY':
                primary_standby_count += 1

            self.gauge(self.m('hadr.role'), 1, tags=hadr_tags)
            self._hadr_state_metric('hadr.state', 'hadr_state', hadr.get('hadr_state'), hadr_tags)
            self._hadr_state_metric('hadr.connected', 'connect_status', hadr.get('hadr_connect_status'), hadr_tags)
            self._hadr_state_metric('hadr.syncmode', 'syncmode', hadr.get('hadr_syncmode'), hadr_tags)

            for metric, column in HADR_GAUGE_METRICS:
                self._gauge(metric, hadr[column], tags=hadr_tags)

            self._emit_hadr_derived_metrics(hadr, hadr_tags)
            hadr_status = hadr_status_to_service_check(hadr.get('hadr_state'), hadr.get('hadr_connect_status'))
            hadr_status_message = None
            if hadr_status != self.OK:
                hadr_status_message = 'HADR state: {}, connect status: {}'.format(
                    hadr.get('hadr_state'), hadr.get('hadr_connect_status')
                )
            self.service_check(
                self.SERVICE_CHECK_HADR_STATUS,
                hadr_status,
                tags=hadr_tags,
                message=hadr_status_message,
            )

        if hadr_rows == 0:
            self.gauge(self.m('hadr.role'), 1, tags=['hadr_role:standard'] + self._tags)

        self.gauge(self.m('hadr.standby.count'), primary_standby_count, tags=self._tags)

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

    def track_table_space_state_changes(self, name, state, tags, state_key=None):
        state_key = state_key or name
        previous_state = self._table_space_states.get(state_key)
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
            self._table_space_states[state_key] = state

    def get_connection(self):
        target, username, password = self.get_connection_data(
            self._db,
            self._username,
            self._password,
            self._host,
            self._port,
            self._security,
            self._tls_cert,
            self._connection_timeout,
        )

        # Get column names in lower case
        connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}

        try:
            self.log.debug("Attempting to connect to Db2 with `%s`...", scrub_connection_string(target))
            connection = ibm_db.connect(target, username, password, connection_options)
        except Exception as e:
            if self._host:
                self.log.error('Unable to connect with `%s`: %s', scrub_connection_string(target), e)
            else:  # no cov
                self.log.error('Unable to connect to database `%s` as user `%s`: %s', target, username, e)
            connection = None
        return connection

    def emit_connection_service_checks(self):
        if self._conn is None:
            self.service_check(
                self.SERVICE_CHECK_CONNECT,
                self.CRITICAL,
                tags=self._tags,
                message="Unable to create new connection to database: {}".format(self._db),
            )
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._tags)

    @classmethod
    def get_connection_data(cls, db, username, password, host, port, security, tls_cert, connection_timeout):
        if host:
            target = 'database={};hostname={};port={};protocol=tcpip;uid={};pwd={}'.format(
                db, host, port, username, password
            )
            username = ''
            password = ''
            if security == 'ssl':
                target = '{};security=ssl;'.format(target)
            if tls_cert:
                target = '{};security=ssl;sslservercertificate={}'.format(target, tls_cert)
            if connection_timeout:
                target = '{};connecttimeout={}'.format(target, connection_timeout)
        else:  # no cov
            target = db

        return target, username, password

    def iter_rows(self, query, method):
        # https://github.com/ibmdb/python-ibmdb/wiki/APIs
        try:
            cursor = ibm_db.exec_immediate(self._conn, query)
        except Exception as e:
            if not is_connection_error(e):
                raise
            error = str(e)
            self.log.error("Error executing query: %s.\nAttempting to reconnect", error)
            self._conn = self.get_connection()
            self.emit_connection_service_checks()
            if self._conn is None:
                raise ConnectionError("Unable to create new connection")

            cursor = ibm_db.exec_immediate(self._conn, query)

        row = method(cursor)
        while row is not False:
            yield row

            # Get next row, if any
            row = method(cursor)

    @classmethod
    def m(cls, metric):
        return '{}.{}'.format(cls.METRIC_PREFIX, metric)

    def _hadr_tags(self, hadr: dict) -> list[str]:
        hadr_tags = []
        self._add_tag(hadr_tags, 'hadr_role', hadr.get('hadr_role'))
        self._add_tag(hadr_tags, 'standby_id', hadr.get('standby_id'))
        self._add_tag(hadr_tags, 'log_stream', hadr.get('log_stream_id'))
        self._add_tag(hadr_tags, 'standby_host', hadr.get('standby_member_host'))
        hadr_tags.extend(self._tags)
        return hadr_tags

    def _container_tags(self, container: dict[str, object]) -> list[str]:
        container_tags = []
        self._add_tag(container_tags, 'tablespace', container.get('tbsp_name'))
        self._add_tag(container_tags, 'container', container.get('container_name'))
        self._add_tag(container_tags, 'container_id', container.get('container_id'))
        self._add_tag(container_tags, 'container_type', container.get('container_type'))
        self._add_tag(container_tags, 'member', container.get('member'))
        container_tags.extend(self._tags)
        return container_tags

    def _memory_tags(self, memory: dict[str, object]) -> list[str]:
        tags = []
        self._add_tag(tags, 'memory_set', memory.get('memory_set_type'))
        self._add_tag(tags, 'member', memory.get('member'))
        tags.extend(self._tags)
        return tags

    def _member_tags(self, row: dict[str, object]) -> list[str]:
        tags = []
        self._add_tag(tags, 'member', row.get('member'))
        tags.extend(self._tags)
        return tags

    def _wlm_workload_tags(self, workload: dict[str, object]) -> list[str]:
        tags = []
        self._add_tag(tags, 'workload_name', workload.get('workload_name'))
        self._add_tag(tags, 'workload_id', workload.get('workload_id'))
        self._add_tag(tags, 'member', workload.get('member'))
        tags.extend(self._tags)
        return tags

    def _wlm_service_class_tags(self, service_class: dict[str, object]) -> list[str]:
        tags = []
        self._add_tag(tags, 'service_superclass', service_class.get('service_superclass_name'))
        self._add_tag(tags, 'service_subclass', service_class.get('service_subclass_name'))
        self._add_tag(tags, 'service_class_id', service_class.get('service_class_id'))
        self._add_tag(tags, 'member', service_class.get('member'))
        tags.extend(self._tags)
        return tags

    def _submit_wlm_metrics(self, row: dict[str, object], tags: list[str]) -> None:
        for metric, column in WLM_MONOTONIC_METRICS:
            self._monotonic_count(metric, row.get(column), tags=tags)

    def _hadr_state_metric(self, metric: str, tag_name: str, value: object | None, tags: list[str]) -> None:
        if value:
            self.gauge(self.m(metric), 1, tags=tags + ['{}:{}'.format(tag_name, str(value).strip().lower())])

    def _emit_hadr_derived_metrics(self, hadr: dict, tags: list[str]) -> None:
        primary_log_pos = hadr.get('primary_log_pos')
        standby_log_pos = hadr.get('standby_log_pos')
        if primary_log_pos is not None and standby_log_pos is not None:
            self.gauge(self.m('hadr.send_recv_gap'), max(primary_log_pos - standby_log_pos, 0), tags=tags)

        primary_log_time = hadr.get('primary_log_time')
        standby_replay_log_time = hadr.get('standby_replay_log_time')
        if primary_log_time and standby_replay_log_time:
            replay_lag = (primary_log_time - standby_replay_log_time).total_seconds()
            self.gauge(self.m('hadr.replay_lag'), max(replay_lag, 0), tags=tags)

        current_time = hadr.get('current_time')
        peer_window_end = hadr.get('peer_window_end')
        if current_time and peer_window_end:
            peer_window_remaining = (peer_window_end - current_time).total_seconds()
            self.gauge(self.m('hadr.peer_window_remaining'), max(peer_window_remaining, 0), tags=tags)

        hadr_flags = hadr.get('hadr_flags') or ''
        self.gauge(self.m('hadr.recv_blocked'), 1 if 'STANDBY_RECV_BLOCKED' in hadr_flags else 0, tags=tags)

    def _add_tag(self, tags: list[str], tag_name: str, value: object | None) -> None:
        if value is not None and value != '':
            tags.append('{}:{}'.format(tag_name, str(value).strip().lower()))

    def _gauge(self, metric, value, tags):
        if value is not None:
            self.gauge(self.m(metric), value, tags=tags)

    def _gauge_nonnegative(self, metric: str, value: int | float | None, tags: list[str]) -> None:
        if value is not None and value >= 0:
            self.gauge(self.m(metric), value, tags=tags)

    def _monotonic_count(self, metric, value, tags):
        if value is not None:
            self.monotonic_count(self.m(metric), value, tags=tags)
