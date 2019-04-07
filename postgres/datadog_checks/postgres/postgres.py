# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import re
import socket
import threading
from contextlib import closing

import pg8000
from six import iteritems
from six.moves import zip_longest

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative

try:
    import psycopg2
except ImportError:
    psycopg2 = None


MAX_CUSTOM_RESULTS = 100
TABLE_COUNT_LIMIT = 200


def psycopg2_connect(*args, **kwargs):
    if 'ssl' in kwargs:
        del kwargs['ssl']
    if 'unix_sock' in kwargs:
        kwargs['host'] = kwargs['unix_sock']
        del kwargs['unix_sock']
    return psycopg2.connect(*args, **kwargs)


class ShouldRestartException(Exception):
    pass


class PostgreSql(AgentCheck):
    """Collects per-database, and optionally per-relation metrics, custom metrics
    """

    SOURCE_TYPE_NAME = 'postgresql'
    RATE = AgentCheck.rate
    GAUGE = AgentCheck.gauge
    MONOTONIC = AgentCheck.monotonic_count
    SERVICE_CHECK_NAME = 'postgres.can_connect'

    # turning columns into tags

    COMMON_METRICS = {
        'numbackends': ('postgresql.connections', GAUGE),
        'xact_commit': ('postgresql.commits', RATE),
        'xact_rollback': ('postgresql.rollbacks', RATE),
        'blks_read': ('postgresql.disk_read', RATE),
        'blks_hit': ('postgresql.buffer_hit', RATE),
        'tup_returned': ('postgresql.rows_returned', RATE),
        'tup_fetched': ('postgresql.rows_fetched', RATE),
        'tup_inserted': ('postgresql.rows_inserted', RATE),
        'tup_updated': ('postgresql.rows_updated', RATE),
        'tup_deleted': ('postgresql.rows_deleted', RATE),
        '2^31 - age(datfrozenxid) as wraparound': ('postgresql.before_xid_wraparound', GAUGE),
    }

    DATABASE_SIZE_METRICS = {'pg_database_size(psd.datname) as pg_database_size': ('postgresql.database_size', GAUGE)}

    NEWER_92_METRICS = {
        'deadlocks': ('postgresql.deadlocks', RATE),
        'temp_bytes': ('postgresql.temp_bytes', RATE),
        'temp_files': ('postgresql.temp_files', RATE),
    }

    COMMON_BGW_METRICS = {
        'checkpoints_timed': ('postgresql.bgwriter.checkpoints_timed', MONOTONIC),
        'checkpoints_req': ('postgresql.bgwriter.checkpoints_requested', MONOTONIC),
        'buffers_checkpoint': ('postgresql.bgwriter.buffers_checkpoint', MONOTONIC),
        'buffers_clean': ('postgresql.bgwriter.buffers_clean', MONOTONIC),
        'maxwritten_clean': ('postgresql.bgwriter.maxwritten_clean', MONOTONIC),
        'buffers_backend': ('postgresql.bgwriter.buffers_backend', MONOTONIC),
        'buffers_alloc': ('postgresql.bgwriter.buffers_alloc', MONOTONIC),
    }

    NEWER_91_BGW_METRICS = {'buffers_backend_fsync': ('postgresql.bgwriter.buffers_backend_fsync', MONOTONIC)}

    NEWER_92_BGW_METRICS = {
        'checkpoint_write_time': ('postgresql.bgwriter.write_time', MONOTONIC),
        'checkpoint_sync_time': ('postgresql.bgwriter.sync_time', MONOTONIC),
    }

    COMMON_ARCHIVER_METRICS = {
        'archived_count': ('postgresql.archiver.archived_count', MONOTONIC),
        'failed_count': ('postgresql.archiver.failed_count', MONOTONIC),
    }

    LOCK_METRICS = {
        'descriptors': [('mode', 'lock_mode'), ('datname', 'db'), ('relname', 'table')],
        'metrics': {'lock_count': ('postgresql.locks', GAUGE)},
        'query': """
SELECT mode,
       pd.datname,
       pc.relname,
       count(*) AS %s
  FROM pg_locks l
  JOIN pg_database pd ON (l.database = pd.oid)
  JOIN pg_class pc ON (l.relation = pc.oid)
 WHERE l.mode IS NOT NULL
   AND pc.relname NOT LIKE 'pg_%%'
 GROUP BY pd.datname, pc.relname, mode""",
        'relation': False,
    }

    REL_METRICS = {
        'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
        # This field contains old metrics that need to be deprecated. For now we keep sending them.
        'deprecated_metrics': {'idx_tup_fetch': ('postgresql.index_rows_fetched', RATE)},
        'metrics': {
            'seq_scan': ('postgresql.seq_scans', RATE),
            'seq_tup_read': ('postgresql.seq_rows_read', RATE),
            'idx_scan': ('postgresql.index_scans', RATE),
            'idx_tup_fetch': ('postgresql.index_rel_rows_fetched', RATE),
            'n_tup_ins': ('postgresql.rows_inserted', RATE),
            'n_tup_upd': ('postgresql.rows_updated', RATE),
            'n_tup_del': ('postgresql.rows_deleted', RATE),
            'n_tup_hot_upd': ('postgresql.rows_hot_updated', RATE),
            'n_live_tup': ('postgresql.live_rows', GAUGE),
            'n_dead_tup': ('postgresql.dead_rows', GAUGE),
        },
        'query': """
SELECT relname,schemaname,%s
  FROM pg_stat_user_tables
 WHERE relname = ANY(array[%s])""",
        'relation': True,
    }

    IDX_METRICS = {
        'descriptors': [('relname', 'table'), ('schemaname', 'schema'), ('indexrelname', 'index')],
        'metrics': {
            'idx_scan': ('postgresql.index_scans', RATE),
            'idx_tup_read': ('postgresql.index_rows_read', RATE),
            'idx_tup_fetch': ('postgresql.index_rows_fetched', RATE),
        },
        'query': """
SELECT relname,
       schemaname,
       indexrelname,
       %s
  FROM pg_stat_user_indexes
 WHERE relname = ANY(array[%s])""",
        'relation': True,
    }

    SIZE_METRICS = {
        'descriptors': [('relname', 'table')],
        'metrics': {
            'pg_table_size(C.oid) as table_size': ('postgresql.table_size', GAUGE),
            'pg_indexes_size(C.oid) as index_size': ('postgresql.index_size', GAUGE),
            'pg_total_relation_size(C.oid) as total_size': ('postgresql.total_size', GAUGE),
        },
        'relation': True,
        'query': """
SELECT
  relname,
  %s
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
WHERE nspname NOT IN ('pg_catalog', 'information_schema') AND
  nspname !~ '^pg_toast' AND
  relkind IN ('r') AND
  relname = ANY(array[%s])""",
    }

    COUNT_METRICS = {
        'descriptors': [('schemaname', 'schema')],
        'metrics': {'pg_stat_user_tables': ('postgresql.table.count', GAUGE)},
        'relation': False,
        'query': """
SELECT schemaname, count(*) FROM
(
  SELECT schemaname
  FROM %s
  ORDER BY schemaname, relname
  LIMIT {table_count_limit}
) AS subquery GROUP BY schemaname
        """.format(
            table_count_limit=TABLE_COUNT_LIMIT
        ),
    }

    q1 = (
        'CASE WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0 ELSE GREATEST '
        '(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
    )
    q2 = 'abs(pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()))'
    REPLICATION_METRICS_10 = {
        q1: ('postgresql.replication_delay', GAUGE),
        q2: ('postgresql.replication_delay_bytes', GAUGE),
    }

    q = (
        'CASE WHEN pg_last_xlog_receive_location() = pg_last_xlog_replay_location() THEN 0 ELSE GREATEST '
        '(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
    )
    REPLICATION_METRICS_9_1 = {q: ('postgresql.replication_delay', GAUGE)}

    q1 = (
        'abs(pg_xlog_location_diff(pg_last_xlog_receive_location(), pg_last_xlog_replay_location())) '
        'AS replication_delay_bytes_dup'
    )
    q2 = (
        'abs(pg_xlog_location_diff(pg_last_xlog_receive_location(), pg_last_xlog_replay_location())) '
        'AS replication_delay_bytes'
    )
    REPLICATION_METRICS_9_2 = {
        # postgres.replication_delay_bytes is deprecated and will be removed in a future version.
        # Please use postgresql.replication_delay_bytes instead.
        q1: ('postgres.replication_delay_bytes', GAUGE),
        q2: ('postgresql.replication_delay_bytes', GAUGE),
    }

    REPLICATION_METRICS = {
        'descriptors': [],
        'metrics': {},
        'relation': False,
        'query': """
SELECT %s
 WHERE (SELECT pg_is_in_recovery())""",
    }

    CONNECTION_METRICS = {
        'descriptors': [],
        'metrics': {
            'MAX(setting) AS max_connections': ('postgresql.max_connections', GAUGE),
            'SUM(numbackends)/MAX(setting) AS pct_connections': ('postgresql.percent_usage_connections', GAUGE),
        },
        'relation': False,
        'query': """
WITH max_con AS (SELECT setting::float FROM pg_settings WHERE name = 'max_connections')
SELECT %s
  FROM pg_stat_database, max_con
""",
    }

    STATIO_METRICS = {
        'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
        'metrics': {
            'heap_blks_read': ('postgresql.heap_blocks_read', RATE),
            'heap_blks_hit': ('postgresql.heap_blocks_hit', RATE),
            'idx_blks_read': ('postgresql.index_blocks_read', RATE),
            'idx_blks_hit': ('postgresql.index_blocks_hit', RATE),
            'toast_blks_read': ('postgresql.toast_blocks_read', RATE),
            'toast_blks_hit': ('postgresql.toast_blocks_hit', RATE),
            'tidx_blks_read': ('postgresql.toast_index_blocks_read', RATE),
            'tidx_blks_hit': ('postgresql.toast_index_blocks_hit', RATE),
        },
        'query': """
SELECT relname,
       schemaname,
       %s
  FROM pg_statio_user_tables
 WHERE relname = ANY(array[%s])""",
        'relation': True,
    }

    FUNCTION_METRICS = {
        'descriptors': [('schemaname', 'schema'), ('funcname', 'function')],
        'metrics': {
            'calls': ('postgresql.function.calls', RATE),
            'total_time': ('postgresql.function.total_time', RATE),
            'self_time': ('postgresql.function.self_time', RATE),
        },
        'query': """
WITH overloaded_funcs AS (
 SELECT funcname
   FROM pg_stat_user_functions s
  GROUP BY s.funcname
 HAVING COUNT(*) > 1
)
SELECT s.schemaname,
       CASE WHEN o.funcname IS NULL OR p.proargnames IS NULL THEN p.proname
            ELSE p.proname || '_' || array_to_string(p.proargnames, '_')
        END funcname,
        %s
  FROM pg_proc p
  JOIN pg_stat_user_functions s
    ON p.oid = s.funcid
  LEFT JOIN overloaded_funcs o
    ON o.funcname = s.funcname;
""",
        'relation': False,
    }

    # The metrics we retrieve from pg_stat_activity when the postgres version >= 9.2
    ACTIVITY_METRICS_9_6 = [
        "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
        "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
        "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', 'datadog'))"
        "THEN 1 ELSE null END )",
        "COUNT(CASE WHEN wait_event is NOT NULL AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    ]

    # The metrics we retrieve from pg_stat_activity when the postgres version >= 9.2
    ACTIVITY_METRICS_9_2 = [
        "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
        "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
        "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', 'datadog'))"
        "THEN 1 ELSE null END )",
        "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    ]

    # The metrics we retrieve from pg_stat_activity when the postgres version >= 8.3
    ACTIVITY_METRICS_8_3 = [
        "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
        "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
        "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', 'datadog'))"
        "THEN 1 ELSE null END )",
        "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    ]

    # The metrics we retrieve from pg_stat_activity when the postgres version < 8.3
    ACTIVITY_METRICS_LT_8_3 = [
        "SUM(CASE WHEN query_start IS NOT NULL THEN 1 ELSE 0 END)",
        "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
        "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', 'datadog'))"
        "THEN 1 ELSE null END )",
        "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    ]

    # The metrics we collect from pg_stat_activity that we zip with one of the lists above
    ACTIVITY_DD_METRICS = [
        ('postgresql.transactions.open', GAUGE),
        ('postgresql.transactions.idle_in_transaction', GAUGE),
        ('postgresql.active_queries', GAUGE),
        ('postgresql.waiting_queries', GAUGE),
    ]

    # The base query for postgres version >= 10
    ACTIVITY_QUERY_10 = """
SELECT datname,
    %s
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY datid, datname
"""

    # The base query for postgres version < 10
    ACTIVITY_QUERY_LT_10 = """
SELECT datname,
    %s
FROM pg_stat_activity
GROUP BY datid, datname
"""

    # keep track of host/port present in any configured instance
    _known_servers = set()
    _known_servers_lock = threading.RLock()

    def __init__(self, name, init_config, agentConfig, instances=None):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.dbs = {}
        self.versions = {}
        self.instance_metrics = {}
        self.bgw_metrics = {}
        self.archiver_metrics = {}
        self.db_bgw_metrics = []
        self.db_archiver_metrics = []
        self.replication_metrics = {}
        self.activity_metrics = {}
        self.custom_metrics = {}

        # Deprecate custom_metrics in favor of custom_queries
        if instances is not None and any('custom_metrics' in instance for instance in instances):
            self.warning(
                "DEPRECATION NOTICE: Please use the new custom_queries option "
                "rather than the now deprecated custom_metrics"
            )

    @classmethod
    def _server_known(cls, host, port):
        """
        Return whether the hostname and port combination was already seen
        """
        with PostgreSql._known_servers_lock:
            return (host, port) in PostgreSql._known_servers

    @classmethod
    def _set_server_known(cls, host, port):
        """
        Store the host/port combination for this server
        """
        with PostgreSql._known_servers_lock:
            PostgreSql._known_servers.add((host, port))

    def _get_pg_attrs(self, instance):
        if is_affirmative(instance.get('use_psycopg2', False)):
            if psycopg2 is None:
                self.log.error("Unable to import psycopg2, falling back to pg8000")
            else:
                return psycopg2_connect, psycopg2.InterfaceError, psycopg2.ProgrammingError

        # Let's use pg8000
        return pg8000.connect, pg8000.InterfaceError, pg8000.ProgrammingError

    def _get_replication_role(self, key, db):
        cursor = db.cursor()
        cursor.execute('SELECT pg_is_in_recovery();')
        role = cursor.fetchone()[0]
        # value fetched for role is of <type 'bool'>
        return "standby" if role else "master"

    def _get_version(self, key, db):
        if key not in self.versions:
            cursor = db.cursor()
            cursor.execute('SHOW SERVER_VERSION;')
            version = cursor.fetchone()[0]
            try:
                version_parts = version.split(' ')[0].split('.')
                version = [int(part) for part in version_parts]
            except Exception:
                # Postgres might be in development, with format \d+[beta|rc]\d+
                match = re.match(r'(\d+)([a-zA-Z]+)(\d+)', version)
                if match:
                    version_parts = list(match.groups())

                    # We found a valid development version
                    if len(version_parts) == 3:
                        # Replace development tag with a negative number to properly compare versions
                        version_parts[1] = -1
                        version = [int(part) for part in version_parts]

            self.versions[key] = version

        self.service_metadata('version', self.versions[key])
        return self.versions[key]

    def _is_above(self, key, db, version_to_compare):
        version = self._get_version(key, db)
        if type(version) == list:
            # iterate from major down to bugfix
            for v, vc in zip_longest(version, version_to_compare, fillvalue=0):
                if v == vc:
                    continue

                return v > vc

            # return True if version is the same
            return True

        return False

    def _is_8_3_or_above(self, key, db):
        return self._is_above(key, db, [8, 3, 0])

    def _is_9_1_or_above(self, key, db):
        return self._is_above(key, db, [9, 1, 0])

    def _is_9_2_or_above(self, key, db):
        return self._is_above(key, db, [9, 2, 0])

    def _is_9_4_or_above(self, key, db):
        return self._is_above(key, db, [9, 4, 0])

    def _is_9_6_or_above(self, key, db):
        return self._is_above(key, db, [9, 6, 0])

    def _is_10_or_above(self, key, db):
        return self._is_above(key, db, [10, 0, 0])

    def _get_instance_metrics(self, key, db, database_size_metrics, collect_default_db):
        """
        Add NEWER_92_METRICS to the default set of COMMON_METRICS when server
        version is 9.2 or later.

        Store the list of metrics in the check instance to avoid rebuilding it at
        every collection cycle.

        In case we have multiple instances pointing to the same postgres server
        monitoring different databases, we want to collect server metrics
        only once. See https://github.com/DataDog/dd-agent/issues/1211
        """
        metrics = self.instance_metrics.get(key)

        if metrics is None:
            host, port, dbname = key
            # check whether we already collected server-wide metrics for this
            # postgres instance
            if self._server_known(host, port):
                # explicitly set instance metrics for this key to an empty list
                # so we don't get here more than once
                self.instance_metrics[key] = []
                self.log.debug(
                    "Not collecting instance metrics for key: {} as "
                    "they are already collected by another instance".format(key)
                )
                return None
            self._set_server_known(host, port)

            # select the right set of metrics to collect depending on postgres version
            if self._is_9_2_or_above(key, db):
                self.instance_metrics[key] = dict(self.COMMON_METRICS, **self.NEWER_92_METRICS)
            else:
                self.instance_metrics[key] = dict(self.COMMON_METRICS)

            # add size metrics if needed
            if database_size_metrics:
                self.instance_metrics[key].update(self.DATABASE_SIZE_METRICS)

            metrics = self.instance_metrics.get(key)

        # this will happen when the current key contains a postgres server that
        # we already know, let's avoid to collect duplicates
        if not metrics:
            return None

        res = {
            'descriptors': [('psd.datname', 'db')],
            'metrics': metrics,
            'query': "SELECT psd.datname, %s "
            "FROM pg_stat_database psd "
            "JOIN pg_database pd ON psd.datname = pd.datname "
            "WHERE psd.datname not ilike 'template%%' "
            "  AND psd.datname not ilike 'rdsadmin' "
            "  AND psd.datname not ilike 'azure_maintenance' ",
            'relation': False,
        }

        if not collect_default_db:
            res["query"] += "  AND psd.datname not ilike 'postgres'"

        return res

    def _get_bgw_metrics(self, key, db):
        """Use either COMMON_BGW_METRICS or COMMON_BGW_METRICS + NEWER_92_BGW_METRICS
        depending on the postgres version.
        Uses a dictionnary to save the result for each instance
        """
        # Extended 9.2+ metrics if needed
        metrics = self.bgw_metrics.get(key)

        if metrics is None:
            # Hack to make sure that if we have multiple instances that connect to
            # the same host, port, we don't collect metrics twice
            # as it will result in https://github.com/DataDog/dd-agent/issues/1211
            sub_key = key[:2]
            if sub_key in self.db_bgw_metrics:
                self.bgw_metrics[key] = None
                self.log.debug(
                    "Not collecting bgw metrics for key: {0} as "
                    "they are already collected by another instance".format(key)
                )
                return None

            self.db_bgw_metrics.append(sub_key)

            self.bgw_metrics[key] = dict(self.COMMON_BGW_METRICS)
            if self._is_9_1_or_above(key, db):
                self.bgw_metrics[key].update(self.NEWER_91_BGW_METRICS)
            if self._is_9_2_or_above(key, db):
                self.bgw_metrics[key].update(self.NEWER_92_BGW_METRICS)

            metrics = self.bgw_metrics.get(key)

        if not metrics:
            return None

        return {'descriptors': [], 'metrics': metrics, 'query': "select %s FROM pg_stat_bgwriter", 'relation': False}

    def _get_archiver_metrics(self, key, db):
        """Use COMMON_ARCHIVER_METRICS to read from pg_stat_archiver as
        defined in 9.4 (first version to have this table).
        Uses a dictionary to save the result for each instance
        """
        # While there's only one set for now, prepare for future additions to
        # the table, mirroring _get_bgw_metrics()
        metrics = self.archiver_metrics.get(key)

        if self._is_9_4_or_above(key, db) and metrics is None:
            # Collect from only one instance. See _get_bgw_metrics() for details on why.
            sub_key = key[:2]
            if sub_key in self.db_archiver_metrics:
                self.archiver_metrics[key] = None
                self.log.debug(
                    "Not collecting archiver metrics for key: {0} as "
                    "they are already collected by another instance".format(key)
                )
                return None

            self.db_archiver_metrics.append(sub_key)

            self.archiver_metrics[key] = dict(self.COMMON_ARCHIVER_METRICS)
            metrics = self.archiver_metrics.get(key)

        if not metrics:
            return None

        return {'descriptors': [], 'metrics': metrics, 'query': "select %s FROM pg_stat_archiver", 'relation': False}

    def _get_replication_metrics(self, key, db):
        """ Use either REPLICATION_METRICS_10, REPLICATION_METRICS_9_1, or
        REPLICATION_METRICS_9_1 + REPLICATION_METRICS_9_2, depending on the
        postgres version.
        Uses a dictionnary to save the result for each instance
        """
        metrics = self.replication_metrics.get(key)
        if self._is_10_or_above(key, db) and metrics is None:
            self.replication_metrics[key] = dict(self.REPLICATION_METRICS_10)
            metrics = self.replication_metrics.get(key)
        elif self._is_9_1_or_above(key, db) and metrics is None:
            self.replication_metrics[key] = dict(self.REPLICATION_METRICS_9_1)
            if self._is_9_2_or_above(key, db):
                self.replication_metrics[key].update(self.REPLICATION_METRICS_9_2)
            metrics = self.replication_metrics.get(key)
        return metrics

    def _get_activity_metrics(self, key, db):
        """ Use ACTIVITY_METRICS_LT_8_3 or ACTIVITY_METRICS_8_3 or ACTIVITY_METRICS_9_2
        depending on the postgres version in conjunction with ACTIVITY_QUERY_10 or ACTIVITY_QUERY_LT_10.
        Uses a dictionnary to save the result for each instance
        """
        metrics_data = self.activity_metrics.get(key)

        if metrics_data is None:
            query = self.ACTIVITY_QUERY_10 if self._is_10_or_above(key, db) else self.ACTIVITY_QUERY_LT_10
            metrics_query = None
            if self._is_9_6_or_above(key, db):
                metrics_query = self.ACTIVITY_METRICS_9_6
            elif self._is_9_2_or_above(key, db):
                metrics_query = self.ACTIVITY_METRICS_9_2
            elif self._is_8_3_or_above(key, db):
                metrics_query = self.ACTIVITY_METRICS_8_3
            else:
                metrics_query = self.ACTIVITY_METRICS_LT_8_3

            metrics = {k: v for k, v in zip(metrics_query, self.ACTIVITY_DD_METRICS)}
            self.activity_metrics[key] = (metrics, query)
        else:
            metrics, query = metrics_data

        return {'descriptors': [('datname', 'db')], 'metrics': metrics, 'query': query, 'relation': False}

    def _build_relations_config(self, yamlconfig):
        """Builds a dictionary from relations configuration while maintaining compatibility
        """
        config = {}
        for element in yamlconfig:
            try:
                if isinstance(element, str):
                    config[element] = {'relation_name': element, 'schemas': []}
                elif isinstance(element, dict):
                    name = element['relation_name']
                    config[name] = {}
                    config[name]['schemas'] = element['schemas']
                    config[name]['relation_name'] = name
                else:
                    self.log.warning('Unhandled relations config type: {}'.format(element))
            except KeyError:
                self.log.warning('Failed to parse config element={}, check syntax'.format(element))
        return config

    def _query_scope(
        self, cursor, scope, key, db, instance_tags, relations, is_custom_metrics, programming_error, relations_config
    ):
        if scope is None:
            return None

        if scope == self.REPLICATION_METRICS or not self._is_above(key, db, [9, 0, 0]):
            log_func = self.log.debug
        else:
            log_func = self.log.warning

        # build query
        cols = list(scope['metrics'])  # list of metrics to query, in some order
        # we must remember that order to parse results

        try:
            # if this is a relation-specific query, we need to list all relations last
            if scope['relation'] and len(relations) > 0:
                relnames = ', '.join("'{0}'".format(w) for w in relations_config)
                query = scope['query'] % (", ".join(cols), "%s")  # Keep the last %s intact
                self.log.debug("Running query: %s with relations: %s" % (query, relnames))
                cursor.execute(query % relnames)
            else:
                query = scope['query'] % (", ".join(cols))
                self.log.debug("Running query: %s" % query)
                cursor.execute(query.replace(r'%', r'%%'))

            results = cursor.fetchall()
        except programming_error as e:
            log_func("Not all metrics may be available: %s" % str(e))
            db.rollback()
            return None

        if not results:
            return None

        if is_custom_metrics and len(results) > MAX_CUSTOM_RESULTS:
            self.warning(
                "Query: {0} returned more than {1} results ({2}). Truncating".format(
                    query, MAX_CUSTOM_RESULTS, len(results)
                )
            )
            results = results[:MAX_CUSTOM_RESULTS]

        desc = scope['descriptors']

        # parse & submit results
        # A row should look like this
        # (descriptor, descriptor, ..., value, value, value, value, ...)
        # with descriptor a PG relation or index name, which we use to create the tags
        for row in results:
            # Check that all columns will be processed
            assert len(row) == len(cols) + len(desc)

            # build a map of descriptors and their values
            desc_map = dict(zip([x[1] for x in desc], row[0 : len(desc)]))
            if 'schema' in desc_map and relations:
                try:
                    relname = desc_map['table']
                    config_schemas = relations_config[relname]['schemas']
                    if config_schemas and desc_map['schema'] not in config_schemas:
                        return len(results)
                except KeyError:
                    pass

            # Build tags
            # descriptors are: (pg_name, dd_tag_name): value
            # Special-case the "db" tag, which overrides the one that is passed as instance_tag
            # The reason is that pg_stat_database returns all databases regardless of the
            # connection.
            if not scope['relation']:
                tags = [t for t in instance_tags if not t.startswith("db:")]
            else:
                tags = [t for t in instance_tags]

            tags += [("%s:%s" % (k, v)) for (k, v) in iteritems(desc_map)]

            # [(metric-map, value), (metric-map, value), ...]
            # metric-map is: (dd_name, "rate"|"gauge")
            # shift the results since the first columns will be the "descriptors"
            # To submit simply call the function for each value v
            # v[0] == (metric_name, submit_function)
            # v[1] == the actual value
            # tags are
            for v in zip([scope['metrics'][c] for c in cols], row[len(desc) :]):
                v[0][1](self, v[0][0], v[1], tags=tags)

        return len(results)

    def _collect_stats(
        self,
        key,
        db,
        instance_tags,
        relations,
        custom_metrics,
        collect_function_metrics,
        collect_count_metrics,
        collect_activity_metrics,
        collect_database_size_metrics,
        collect_default_db,
        interface_error,
        programming_error,
    ):
        """Query pg_stat_* for various metrics
        If relations is not an empty list, gather per-relation metrics
        on top of that.
        If custom_metrics is not an empty list, gather custom metrics defined in postgres.yaml
        """

        db_instance_metrics = self._get_instance_metrics(key, db, collect_database_size_metrics, collect_default_db)
        bgw_instance_metrics = self._get_bgw_metrics(key, db)
        archiver_instance_metrics = self._get_archiver_metrics(key, db)

        metric_scope = [self.CONNECTION_METRICS, self.LOCK_METRICS]

        if collect_function_metrics:
            metric_scope.append(self.FUNCTION_METRICS)
        if collect_count_metrics:
            metric_scope.append(self.COUNT_METRICS)

        # Do we need relation-specific metrics?
        relations_config = {}
        if relations:
            metric_scope += [self.REL_METRICS, self.IDX_METRICS, self.SIZE_METRICS, self.STATIO_METRICS]
            relations_config = self._build_relations_config(relations)

        replication_metrics = self._get_replication_metrics(key, db)
        if replication_metrics is not None:
            # FIXME: constants shouldn't be modified
            self.REPLICATION_METRICS['metrics'] = replication_metrics
            metric_scope.append(self.REPLICATION_METRICS)

        try:
            cursor = db.cursor()
            results_len = self._query_scope(
                cursor,
                db_instance_metrics,
                key,
                db,
                instance_tags,
                relations,
                False,
                programming_error,
                relations_config,
            )
            if results_len is not None:
                self.gauge(
                    "postgresql.db.count", results_len, tags=[t for t in instance_tags if not t.startswith("db:")]
                )

            self._query_scope(
                cursor,
                bgw_instance_metrics,
                key,
                db,
                instance_tags,
                relations,
                False,
                programming_error,
                relations_config,
            )
            self._query_scope(
                cursor,
                archiver_instance_metrics,
                key,
                db,
                instance_tags,
                relations,
                False,
                programming_error,
                relations_config,
            )

            if collect_activity_metrics:
                activity_metrics = self._get_activity_metrics(key, db)
                self._query_scope(
                    cursor,
                    activity_metrics,
                    key,
                    db,
                    instance_tags,
                    relations,
                    False,
                    programming_error,
                    relations_config,
                )

            for scope in list(metric_scope) + custom_metrics:
                self._query_scope(
                    cursor,
                    scope,
                    key,
                    db,
                    instance_tags,
                    relations,
                    scope in custom_metrics,
                    programming_error,
                    relations_config,
                )

            cursor.close()
        except (interface_error, socket.error) as e:
            self.log.error("Connection error: %s" % str(e))
            raise ShouldRestartException

    @classmethod
    def _get_service_check_tags(cls, host, port, tags):
        service_check_tags = ["host:%s" % host]
        service_check_tags.extend(tags)
        service_check_tags = list(set(service_check_tags))
        return service_check_tags

    def get_connection(self, key, host, port, user, password, dbname, ssl, connect_fct, tags, use_cached=True):
        """Get and memoize connections to instances"""
        if key in self.dbs and use_cached:
            return self.dbs[key]

        elif host != "" and user != "":
            try:
                if host == 'localhost' and password == '':
                    # Use ident method
                    connection = connect_fct("user=%s dbname=%s" % (user, dbname))
                elif port != '':
                    connection = connect_fct(
                        host=host, port=port, user=user, password=password, database=dbname, ssl=ssl
                    )
                elif host.startswith('/'):
                    # If the hostname starts with /, it's probably a path
                    # to a UNIX socket. This is similar behaviour to psql
                    connection = connect_fct(unix_sock=host, user=user, password=password, database=dbname)
                else:
                    connection = connect_fct(host=host, user=user, password=password, database=dbname, ssl=ssl)
                self.dbs[key] = connection
                return connection
            except Exception as e:
                message = u'Error establishing postgres connection: %s' % (str(e))
                service_check_tags = self._get_service_check_tags(host, port, tags)
                self.service_check(
                    self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=service_check_tags, message=message
                )
                raise
        else:
            if not host:
                raise ConfigurationError('Please specify a Postgres host to connect to.')
            elif not user:
                raise ConfigurationError('Please specify a user to connect to Postgres as.')

    def _get_custom_queries(self, db, tags, custom_queries, programming_error):
        """
        Given a list of custom_queries, execute each query and parse the result for metrics
        """
        for custom_query in custom_queries:
            metric_prefix = custom_query.get('metric_prefix')
            if not metric_prefix:
                self.log.error("custom query field `metric_prefix` is required")
                continue
            metric_prefix = metric_prefix.rstrip('.')

            query = custom_query.get('query')
            if not query:
                self.log.error("custom query field `query` is required for metric_prefix `{}`".format(metric_prefix))
                continue

            columns = custom_query.get('columns')
            if not columns:
                self.log.error("custom query field `columns` is required for metric_prefix `{}`".format(metric_prefix))
                continue

            cursor = db.cursor()
            with closing(cursor) as cursor:
                try:
                    self.log.debug("Running query: {}".format(query))
                    cursor.execute(query)
                except programming_error as e:
                    self.log.error("Error executing query for metric_prefix {}: {}".format(metric_prefix, str(e)))
                    db.rollback()
                    continue

                for row in cursor:
                    if not row:
                        self.log.debug(
                            "query result for metric_prefix {}: returned an empty result".format(metric_prefix)
                        )
                        continue

                    if len(columns) != len(row):
                        self.log.error(
                            "query result for metric_prefix {}: expected {} columns, got {}".format(
                                metric_prefix, len(columns), len(row)
                            )
                        )
                        continue

                    metric_info = []
                    query_tags = custom_query.get('tags', [])
                    query_tags.extend(tags)

                    for column, value in zip(columns, row):
                        # Columns can be ignored via configuration.
                        if not column:
                            continue

                        name = column.get('name')
                        if not name:
                            self.log.error(
                                "column field `name` is required for metric_prefix `{}`".format(metric_prefix)
                            )
                            break

                        column_type = column.get('type')
                        if not column_type:
                            self.log.error(
                                "column field `type` is required for column `{}` "
                                "of metric_prefix `{}`".format(name, metric_prefix)
                            )
                            break

                        if column_type == 'tag':
                            query_tags.append('{}:{}'.format(name, value))
                        else:
                            if not hasattr(self, column_type):
                                self.log.error(
                                    "invalid submission method `{}` for column `{}` of "
                                    "metric_prefix `{}`".format(column_type, name, metric_prefix)
                                )
                                break
                            try:
                                metric_info.append(('{}.{}'.format(metric_prefix, name), float(value), column_type))
                            except (ValueError, TypeError):
                                self.log.error(
                                    "non-numeric value `{}` for metric column `{}` of "
                                    "metric_prefix `{}`".format(value, name, metric_prefix)
                                )
                                break

                    # Only submit metrics if there were absolutely no errors - all or nothing.
                    else:
                        for info in metric_info:
                            metric, value, method = info
                            getattr(self, method)(metric, value, tags=query_tags)

    def _get_custom_metrics(self, custom_metrics, key):
        # Pre-processed cached custom_metrics
        if key in self.custom_metrics:
            return self.custom_metrics[key]

        # Otherwise pre-process custom metrics and verify definition
        required_parameters = ("descriptors", "metrics", "query", "relation")

        for m in custom_metrics:
            for param in required_parameters:
                if param not in m:
                    raise ConfigurationError('Missing {} parameter in custom metric'.format(param))

            self.log.debug("Metric: {0}".format(m))

            try:
                for ref, (_, mtype) in iteritems(m['metrics']):
                    cap_mtype = mtype.upper()
                    if cap_mtype not in ('RATE', 'GAUGE', 'MONOTONIC'):
                        raise ConfigurationError(
                            'Collector method {} is not known. '
                            'Known methods are RATE, GAUGE, MONOTONIC'.format(cap_mtype)
                        )

                    m['metrics'][ref][1] = getattr(PostgreSql, cap_mtype)
                    self.log.debug("Method: %s" % (str(mtype)))
            except Exception as e:
                raise Exception('Error processing custom metric `{}`: {}'.format(m, e))

        self.custom_metrics[key] = custom_metrics
        return custom_metrics

    def check(self, instance):
        host = instance.get('host', '')
        port = instance.get('port', '')
        if port != '':
            port = int(port)
        user = instance.get('username', '')
        password = instance.get('password', '')
        tags = instance.get('tags', [])
        dbname = instance.get('dbname', None)
        relations = instance.get('relations', [])
        ssl = is_affirmative(instance.get('ssl', False))
        collect_function_metrics = is_affirmative(instance.get('collect_function_metrics', False))
        # Default value for `count_metrics` is True for backward compatibility
        collect_count_metrics = is_affirmative(instance.get('collect_count_metrics', True))
        collect_activity_metrics = is_affirmative(instance.get('collect_activity_metrics', False))
        collect_database_size_metrics = is_affirmative(instance.get('collect_database_size_metrics', True))
        collect_default_db = is_affirmative(instance.get('collect_default_database', False))
        tag_replication_role = is_affirmative(instance.get('tag_replication_role', False))

        if relations and not dbname:
            self.warning('"dbname" parameter must be set when using the "relations" parameter.')

        if dbname is None:
            dbname = 'postgres'

        key = (host, port, dbname)

        custom_metrics = self._get_custom_metrics(instance.get('custom_metrics', []), key)
        custom_queries = instance.get('custom_queries', [])

        # Clean up tags in case there was a None entry in the instance
        # e.g. if the yaml contains tags: but no actual tags
        if tags is None:
            tags = []
        else:
            tags = list(set(tags))

        # preset tags to host
        tags.append('server:{}'.format(host))
        if port:
            tags.append('port:{}'.format(port))
        else:
            tags.append('port:socket')

        # preset tags to the database name
        tags.extend(["db:%s" % dbname])

        self.log.debug("Custom metrics: %s" % custom_metrics)

        connect_fct, interface_error, programming_error = self._get_pg_attrs(instance)

        # Collect metrics
        try:
            # Check version
            db = self.get_connection(key, host, port, user, password, dbname, ssl, connect_fct, tags)
            version = self._get_version(key, db)
            self.log.debug("Running check against version %s" % version)
            if tag_replication_role:
                tags.extend(["replication_role:{}".format(self._get_replication_role(key, db))])
            self._collect_stats(
                key,
                db,
                tags,
                relations,
                custom_metrics,
                collect_function_metrics,
                collect_count_metrics,
                collect_activity_metrics,
                collect_database_size_metrics,
                collect_default_db,
                interface_error,
                programming_error,
            )
            self._get_custom_queries(db, tags, custom_queries, programming_error)
        except ShouldRestartException:
            self.log.info("Resetting the connection")
            db = self.get_connection(key, host, port, user, password, dbname, ssl, connect_fct, tags, use_cached=False)
            self._collect_stats(
                key,
                db,
                tags,
                relations,
                custom_metrics,
                collect_function_metrics,
                collect_count_metrics,
                collect_activity_metrics,
                collect_database_size_metrics,
                collect_default_db,
                interface_error,
                programming_error,
            )
            self._get_custom_queries(db, tags, custom_queries, programming_error)

        service_check_tags = self._get_service_check_tags(host, port, tags)
        message = u'Established connection to postgres://%s:%s/%s' % (host, port, dbname)
        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=service_check_tags, message=message)
        try:
            # commit to close the current query transaction
            db.commit()
        except Exception as e:
            self.log.warning("Unable to commit: {0}".format(e))
