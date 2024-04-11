# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import string
from enum import Enum
from typing import Any, List, Tuple  # noqa: F401

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import CheckException


class PartialFormatter(string.Formatter):
    """Follows PEP3101, used to format only specified args in a string.
    Ex:
    > print("This is a {type} with {nb_params} parameters.".format(type='string'))
    > "This is a string with {nb_params} parameters."
    """

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, '{' + key + '}')
        else:
            return string.Formatter.get_value(self, key, args, kwargs)


class DatabaseConfigurationError(Enum):
    """
    Denotes the possible database configuration errors
    """

    pg_stat_statements_not_created = 'pg-stat-statements-not-created'
    pg_stat_statements_not_loaded = 'pg-stat-statements-not-loaded'
    undefined_explain_function = 'undefined-explain-function'
    high_pg_stat_statements_max = 'high-pg-stat-statements-max-configuration'
    autodiscovered_databases_exceeds_limit = 'autodiscovered-databases-exceeds-limit'
    autodiscovered_metrics_exceeds_collection_interval = "autodiscovered-metrics-exceeds-collection-interval"


class DBExplainError(Enum):
    """
    Denotes the various reasons a query may not have an explain statement.
    """

    # may be due to a misconfiguration of the database during setup or the Agent is
    # not able to access the required function
    database_error = 'database_error'

    # datatype mismatch occurs when return type is not json, for instance when multiple queries are explained
    datatype_mismatch = 'datatype_mismatch'

    # this could be the result of a missing EXPLAIN function
    invalid_schema = 'invalid_schema'

    # a value retrieved from the EXPLAIN function could be invalid
    invalid_result = 'invalid_result'

    # some statements cannot be explained i.e AUTOVACUUM
    no_plans_possible = 'no_plans_possible'

    # there could be a problem with the EXPLAIN function (missing, invalid permissions, or an incorrect definition)
    failed_function = 'failed_function'

    # a truncated statement can't be explained
    query_truncated = "query_truncated"

    # connection error may be due to a misconfiguration during setup
    connection_error = 'connection_error'

    # clients using the extended query protocol or prepared statements can't be explained due to
    # the separation of the parsed query and raw bind parameters
    parameterized_query = 'parameterized_query'

    # search path may be different when the client executed a query from where we executed it.
    undefined_table = 'undefined_table'

    # the statement was explained with the prepared statement workaround
    explained_with_prepared_statement = 'explained_with_prepared_statement'

    # the statement was tried to be explained with the prepared statement workaround but failedd
    failed_to_explain_with_prepared_statement = 'failed_to_explain_with_prepared_statement'

    # the statement was tried to be explained with the prepared statement workaround but no plan was returned
    no_plan_returned_with_prepared_statement = 'no_plan_returned_with_prepared_statement'


class DatabaseHealthCheckError(Exception):
    pass


def warning_with_tags(warning_message, *args, **kwargs):
    if args:
        warning_message = warning_message % args

    return "{msg}\n{tags}".format(
        msg=warning_message, tags=" ".join('{key}={value}'.format(key=k, value=v) for k, v in sorted(kwargs.items()))
    )


def milliseconds_to_nanoseconds(value):
    """Convert from ms to ns (used for pg_stat* conversion to metrics with units in ns)"""
    return value * 1000000


def get_schema_field(descriptors):
    # type: (List[Tuple[Any, str]]) -> str
    """Return column containing the schema name for that query."""
    for column, name in descriptors:
        if name == 'schema':
            return column
    raise CheckException("The descriptors are missing a schema field")


def payload_pg_version(version):
    if not version:
        return ""
    return 'v{major}.{minor}.{patch}'.format(major=version.major, minor=version.minor, patch=version.patch)


def get_list_chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


fmt = PartialFormatter()

AWS_RDS_HOSTNAME_SUFFIX = ".rds.amazonaws.com"
AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPE = {
    "flexible_server": "azure_postgresql_flexible_server",
    "single_server": "azure_postgresql_server",
    "virtual_machine": "azure_virtual_machine_instance",
}

DBM_MIGRATED_METRICS = {
    'numbackends': ('postgresql.connections', AgentCheck.gauge),
}

COMMON_METRICS = {
    'xact_commit': ('postgresql.commits', AgentCheck.rate),
    'xact_rollback': ('postgresql.rollbacks', AgentCheck.rate),
    'blks_read': ('postgresql.disk_read', AgentCheck.rate),
    'blks_hit': ('postgresql.buffer_hit', AgentCheck.rate),
    'tup_returned': ('postgresql.rows_returned', AgentCheck.rate),
    'tup_fetched': ('postgresql.rows_fetched', AgentCheck.rate),
    'tup_inserted': ('postgresql.rows_inserted', AgentCheck.rate),
    'tup_updated': ('postgresql.rows_updated', AgentCheck.rate),
    'tup_deleted': ('postgresql.rows_deleted', AgentCheck.rate),
    '2^31 - age(datfrozenxid) as wraparound': ('postgresql.before_xid_wraparound', AgentCheck.gauge),
}

DATABASE_SIZE_METRICS = {
    'pg_database_size(psd.datname) as pg_database_size': ('postgresql.database_size', AgentCheck.gauge)
}

NEWER_92_METRICS = {
    'deadlocks': ('postgresql.deadlocks', AgentCheck.rate),
    'temp_bytes': ('postgresql.temp_bytes', AgentCheck.rate),
    'temp_files': ('postgresql.temp_files', AgentCheck.rate),
}

CHECKSUM_METRICS = {'checksum_failures': ('postgresql.checksums.checksum_failures', AgentCheck.monotonic_count)}

NEWER_14_METRICS = {
    'session_time': ('postgresql.sessions.session_time', AgentCheck.monotonic_count),
    'active_time': ('postgresql.sessions.active_time', AgentCheck.monotonic_count),
    'idle_in_transaction_time': ('postgresql.sessions.idle_in_transaction_time', AgentCheck.monotonic_count),
    'sessions': ('postgresql.sessions.count', AgentCheck.monotonic_count),
    'sessions_abandoned': ('postgresql.sessions.abandoned', AgentCheck.monotonic_count),
    'sessions_fatal': ('postgresql.sessions.fatal', AgentCheck.monotonic_count),
    'sessions_killed': ('postgresql.sessions.killed', AgentCheck.monotonic_count),
}

QUERY_PG_STAT_DATABASE = {
    'name': 'pg_stat_database',
    'query': """
        SELECT
            datname,
            deadlocks
        FROM pg_stat_database
    """.strip(),
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'postgresql.deadlocks.count', 'type': 'monotonic_count'},
    ],
}

QUERY_PG_STAT_DATABASE_CONFLICTS = {
    'name': 'pg_stat_database_conflicts',
    'query': """
        SELECT
            datname,
            confl_tablespace,
            confl_lock,
            confl_snapshot,
            confl_bufferpin,
            confl_deadlock
        FROM pg_stat_database_conflicts
    """.strip(),
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'postgresql.conflicts.tablespace', 'type': 'monotonic_count'},
        {'name': 'postgresql.conflicts.lock', 'type': 'monotonic_count'},
        {'name': 'postgresql.conflicts.snapshot', 'type': 'monotonic_count'},
        {'name': 'postgresql.conflicts.bufferpin', 'type': 'monotonic_count'},
        {'name': 'postgresql.conflicts.deadlock', 'type': 'monotonic_count'},
    ],
}

QUERY_PG_UPTIME = {
    'name': 'pg_uptime',
    'query': "SELECT FLOOR(EXTRACT(EPOCH FROM current_timestamp - pg_postmaster_start_time()))",
    'columns': [
        {'name': 'postgresql.uptime', 'type': 'gauge'},
    ],
}

QUERY_PG_CONTROL_CHECKPOINT = {
    'name': 'pg_control_checkpoint',
    'query': """
        SELECT timeline_id,
               EXTRACT (EPOCH FROM now() - checkpoint_time)
        FROM pg_control_checkpoint();
""",
    'columns': [
        {'name': 'postgresql.control.timeline_id', 'type': 'gauge'},
        {'name': 'postgresql.control.checkpoint_delay', 'type': 'gauge'},
    ],
}

COMMON_BGW_METRICS = {
    'checkpoints_timed': ('postgresql.bgwriter.checkpoints_timed', AgentCheck.monotonic_count),
    'checkpoints_req': ('postgresql.bgwriter.checkpoints_requested', AgentCheck.monotonic_count),
    'buffers_checkpoint': ('postgresql.bgwriter.buffers_checkpoint', AgentCheck.monotonic_count),
    'buffers_clean': ('postgresql.bgwriter.buffers_clean', AgentCheck.monotonic_count),
    'maxwritten_clean': ('postgresql.bgwriter.maxwritten_clean', AgentCheck.monotonic_count),
    'buffers_backend': ('postgresql.bgwriter.buffers_backend', AgentCheck.monotonic_count),
    'buffers_alloc': ('postgresql.bgwriter.buffers_alloc', AgentCheck.monotonic_count),
}

NEWER_91_BGW_METRICS = {
    'buffers_backend_fsync': ('postgresql.bgwriter.buffers_backend_fsync', AgentCheck.monotonic_count)
}

NEWER_92_BGW_METRICS = {
    'checkpoint_write_time': ('postgresql.bgwriter.write_time', AgentCheck.monotonic_count),
    'checkpoint_sync_time': ('postgresql.bgwriter.sync_time', AgentCheck.monotonic_count),
}

COMMON_ARCHIVER_METRICS = {
    'archived_count': ('postgresql.archiver.archived_count', AgentCheck.monotonic_count),
    'failed_count': ('postgresql.archiver.failed_count', AgentCheck.monotonic_count),
}


# We used to use pg_stat_user_tables to count the number of tables and limit using max_relations.
# This created multiple issues:
# - pg_stat_user_tables is a view that group pg_class results by C.oid, N.nspname, C.relname. Doing the group by
#   will generate a sort
# - pg_stat_user_tables processes elements from pg_class that are dropped like toast tables and system tables
# - we added another layer of sort (ORDER BY relname, relnamespace) to make the max_relations filter stable
# Those sorts will eventually spill on temporary blocks if the number of relations is high enough, making this
# query expensive to run.
# In the end, we only care about the table count per schema so it's better to process the pg_class table directly.
# We can filter tuples as much as possibles (we only care about relations and partition tables) and only do the
# pg_namespace at the end, removing an expensive nested loop.
COUNT_METRICS = {
    'descriptors': [('schemaname', 'schema')],
    'metrics': {'count (*)': ('postgresql.table.count', AgentCheck.gauge)},
    'relation': False,
    'use_global_db_tag': True,
    'query': """
SELECT N.nspname AS schemaname, {metrics_columns} FROM
    (SELECT C.relnamespace
    FROM pg_class C
    WHERE C.relkind IN ('r', 'p')) AS subquery
LEFT JOIN pg_namespace N ON (N.oid = relnamespace)
WHERE N.nspname NOT IN ('pg_catalog', 'information_schema')
GROUP BY N.nspname;
    """,
    'name': 'count_metrics',
}

q1 = (
    'CASE WHEN exists(SELECT * FROM pg_stat_wal_receiver) '
    'AND (pg_last_wal_receive_lsn() IS NULL '
    'OR pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn()) THEN 0 '
    'ELSE GREATEST(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
)
q2 = 'abs(pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()))'
REPLICATION_METRICS_10 = {
    q1: ('postgresql.replication_delay', AgentCheck.gauge),
    q2: ('postgresql.replication_delay_bytes', AgentCheck.gauge),
}

q = (
    'CASE WHEN pg_last_xlog_receive_location() IS NULL OR '
    'pg_last_xlog_receive_location() = pg_last_xlog_replay_location() THEN 0 ELSE GREATEST '
    '(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
)
REPLICATION_METRICS_9_1 = {q: ('postgresql.replication_delay', AgentCheck.gauge)}

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
    q1: ('postgres.replication_delay_bytes', AgentCheck.gauge),
    q2: ('postgresql.replication_delay_bytes', AgentCheck.gauge),
}

REPLICATION_METRICS = {
    'descriptors': [],
    'metrics': {},
    'relation': False,
    'query': """
SELECT {metrics_columns}
 WHERE (SELECT pg_is_in_recovery())""",
    'name': 'replication_metrics',
}

# Requires postgres 10+
REPLICATION_STATS_METRICS = {
    'descriptors': [
        ('application_name', 'wal_app_name'),
        ('state', 'wal_state'),
        ('sync_state', 'wal_sync_state'),
        ('client_addr', 'wal_client_addr'),
    ],
    'metrics': {
        'GREATEST (0, EXTRACT(epoch from write_lag)) as write_lag': (
            'postgresql.replication.wal_write_lag',
            AgentCheck.gauge,
        ),
        'GREATEST (0, EXTRACT(epoch from flush_lag)) AS flush_lag': (
            'postgresql.replication.wal_flush_lag',
            AgentCheck.gauge,
        ),
        'GREATEST (0, EXTRACT(epoch from replay_lag)) AS replay_lag': (
            'postgresql.replication.wal_replay_lag',
            AgentCheck.gauge,
        ),
        'GREATEST (0, age(backend_xmin)) as backend_xmin_age': (
            'postgresql.replication.backend_xmin_age',
            AgentCheck.gauge,
        ),
    },
    'relation': False,
    'query': """
SELECT application_name, state, sync_state, client_addr, {metrics_columns}
FROM pg_stat_replication
""",
    'name': 'replication_stats_metrics',
}


QUERY_PG_STAT_WAL_RECEIVER = {
    'name': 'pg_stat_wal_receiver',
    'query': """
        WITH connected(c) AS (VALUES (1))
        SELECT CASE WHEN status IS NULL THEN 'disconnected' ELSE status END AS connected,
               c,
               received_tli,
               EXTRACT(EPOCH FROM (clock_timestamp() - last_msg_send_time)),
               EXTRACT(EPOCH FROM (clock_timestamp() - last_msg_receipt_time)),
               EXTRACT(EPOCH FROM (clock_timestamp() - latest_end_time))
        FROM pg_stat_wal_receiver
        RIGHT JOIN connected ON (true);
    """.strip(),
    'columns': [
        {'name': 'status', 'type': 'tag'},
        {'name': 'postgresql.wal_receiver.connected', 'type': 'gauge'},
        {'name': 'postgresql.wal_receiver.received_timeline', 'type': 'gauge'},
        {'name': 'postgresql.wal_receiver.last_msg_send_age', 'type': 'gauge'},
        {'name': 'postgresql.wal_receiver.last_msg_receipt_age', 'type': 'gauge'},
        {'name': 'postgresql.wal_receiver.latest_end_age', 'type': 'gauge'},
    ],
}

QUERY_PG_REPLICATION_SLOTS = {
    'name': 'pg_replication_slots',
    'query': """
    SELECT
        slot_name,
        slot_type,
        CASE WHEN temporary THEN 'temporary' ELSE 'permanent' END,
        CASE WHEN active THEN 'active' ELSE 'inactive' END,
        CASE WHEN xmin IS NULL THEN NULL ELSE age(xmin) END,
        pg_wal_lsn_diff(
        CASE WHEN pg_is_in_recovery() THEN pg_last_wal_receive_lsn() ELSE pg_current_wal_lsn() END, restart_lsn),
        pg_wal_lsn_diff(
        CASE WHEN pg_is_in_recovery() THEN pg_last_wal_receive_lsn() ELSE pg_current_wal_lsn() END, confirmed_flush_lsn)
    FROM pg_replication_slots;
    """.strip(),
    'columns': [
        {'name': 'slot_name', 'type': 'tag'},
        {'name': 'slot_type', 'type': 'tag'},
        {'name': 'slot_persistence', 'type': 'tag'},
        {'name': 'slot_state', 'type': 'tag'},
        {'name': 'postgresql.replication_slot.xmin_age', 'type': 'gauge'},
        {'name': 'postgresql.replication_slot.restart_delay_bytes', 'type': 'gauge'},
        {'name': 'postgresql.replication_slot.confirmed_flush_delay_bytes', 'type': 'gauge'},
    ],
}

# Require PG14+
QUERY_PG_REPLICATION_SLOTS_STATS = {
    'name': 'pg_replication_slots_stats',
    'columns': [
        {'name': 'slot_name', 'type': 'tag'},
        {'name': 'slot_type', 'type': 'tag'},
        {'name': 'slot_state', 'type': 'tag'},
        {'name': 'postgresql.replication_slot.spill_txns', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.spill_count', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.spill_bytes', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.stream_txns', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.stream_count', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.stream_bytes', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.total_txns', 'type': 'monotonic_count'},
        {'name': 'postgresql.replication_slot.total_bytes', 'type': 'monotonic_count'},
    ],
    'query': """
SELECT
    stat.slot_name,
    slot_type,
    CASE WHEN active THEN 'active' ELSE 'inactive' END,
    spill_txns, spill_count, spill_bytes,
    stream_txns, stream_count, stream_bytes,
    total_txns, total_bytes
FROM pg_stat_replication_slots AS stat
JOIN pg_replication_slots ON pg_replication_slots.slot_name = stat.slot_name
""".strip(),
}

CONNECTION_METRICS = {
    'descriptors': [],
    'metrics': {
        'MAX(setting) AS max_connections': ('postgresql.max_connections', AgentCheck.gauge),
        'SUM(numbackends)/MAX(setting) AS pct_connections': ('postgresql.percent_usage_connections', AgentCheck.gauge),
    },
    'relation': False,
    'query': """
WITH max_con AS (SELECT setting::float FROM pg_settings WHERE name = 'max_connections')
SELECT {metrics_columns}
  FROM pg_stat_database, max_con
""",
    'name': 'connections_metrics',
}

SLRU_METRICS = {
    'descriptors': [('name', 'slru_name')],
    'metrics': {
        'blks_zeroed': ('postgresql.slru.blks_zeroed', AgentCheck.monotonic_count),
        'blks_hit': ('postgresql.slru.blks_hit', AgentCheck.monotonic_count),
        'blks_read': ('postgresql.slru.blks_read', AgentCheck.monotonic_count),
        'blks_written ': ('postgresql.slru.blks_written', AgentCheck.monotonic_count),
        'blks_exists': ('postgresql.slru.blks_exists', AgentCheck.monotonic_count),
        'flushes': ('postgresql.slru.flushes', AgentCheck.monotonic_count),
        'truncates': ('postgresql.slru.truncates', AgentCheck.monotonic_count),
    },
    'relation': False,
    'query': """
SELECT name, {metrics_columns}
  FROM pg_stat_slru
""",
    'name': 'slru_metrics',
}

SNAPSHOT_TXID_METRICS = {
    'name': 'pg_snapshot',
    # Use CTE to only do a single call to pg_current_snapshot
    # FROM LATERAL was necessary given that pg_snapshot_xip returns a setof xid8
    'query': """
WITH snap AS (
    SELECT * from pg_current_snapshot()
), xip_count AS (
    SELECT COUNT(xip_list) FROM LATERAL (SELECT pg_snapshot_xip(pg_current_snapshot) FROM snap) as xip_list
)
select pg_snapshot_xmin(pg_current_snapshot), pg_snapshot_xmax(pg_current_snapshot), count from snap, xip_count;
""",
    'columns': [
        {'name': 'postgresql.snapshot.xmin', 'type': 'gauge'},
        {'name': 'postgresql.snapshot.xmax', 'type': 'gauge'},
        {'name': 'postgresql.snapshot.xip_count', 'type': 'gauge'},
    ],
}

# Use txid_current_snapshot for PG < 13
SNAPSHOT_TXID_METRICS_LT_13 = {
    'name': 'pg_snapshot_lt_13',
    'query': """
WITH snap AS (
    SELECT * from txid_current_snapshot()
), xip_count AS (
    SELECT COUNT(xip_list) FROM LATERAL (SELECT txid_snapshot_xip(txid_current_snapshot) FROM snap) as xip_list
)
select txid_snapshot_xmin(txid_current_snapshot), txid_snapshot_xmax(txid_current_snapshot), count from snap, xip_count;
""",
    'columns': [
        {'name': 'postgresql.snapshot.xmin', 'type': 'gauge'},
        {'name': 'postgresql.snapshot.xmax', 'type': 'gauge'},
        {'name': 'postgresql.snapshot.xip_count', 'type': 'gauge'},
    ],
}

# Requires PG10+
VACUUM_PROGRESS_METRICS = {
    'name': 'vacuum_progress_metrics',
    'query': """
SELECT v.datname, c.relname, v.phase,
       v.heap_blks_total, v.heap_blks_scanned, v.heap_blks_vacuumed,
       v.index_vacuum_count, v.max_dead_tuples, v.num_dead_tuples
  FROM pg_stat_progress_vacuum as v
  JOIN pg_class c on c.oid = v.relid
""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'phase', 'type': 'tag'},
        {'name': 'postgresql.vacuum.heap_blks_total', 'type': 'gauge'},
        {'name': 'postgresql.vacuum.heap_blks_scanned', 'type': 'gauge'},
        {'name': 'postgresql.vacuum.heap_blks_vacuumed', 'type': 'gauge'},
        {'name': 'postgresql.vacuum.index_vacuum_count', 'type': 'gauge'},
        {'name': 'postgresql.vacuum.max_dead_tuples', 'type': 'gauge'},
        {'name': 'postgresql.vacuum.num_dead_tuples', 'type': 'gauge'},
    ],
}

# Requires PG13+
ANALYZE_PROGRESS_METRICS = {
    'name': 'analyze_progress_metrics',
    'query': """
SELECT r.datname, c.relname, child.relname, r.phase,
       r.sample_blks_total, r.sample_blks_scanned,
       r.ext_stats_total, r.ext_stats_computed,
       r.child_tables_total, r.child_tables_done
  FROM pg_stat_progress_analyze as r
  JOIN pg_class c on c.oid = r.relid
  LEFT JOIN pg_class child on child.oid = r.current_child_table_relid
""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'child_relation', 'type': 'tag_not_null'},
        {'name': 'phase', 'type': 'tag'},
        {'name': 'postgresql.analyze.sample_blks_total', 'type': 'gauge'},
        {'name': 'postgresql.analyze.sample_blks_scanned', 'type': 'gauge'},
        {'name': 'postgresql.analyze.ext_stats_total', 'type': 'gauge'},
        {'name': 'postgresql.analyze.ext_stats_computed', 'type': 'gauge'},
        {'name': 'postgresql.analyze.child_tables_total', 'type': 'gauge'},
        {'name': 'postgresql.analyze.child_tables_done', 'type': 'gauge'},
    ],
}

# Requires PG12+
CLUSTER_VACUUM_PROGRESS_METRICS = {
    'name': 'cluster_vacuum_progress_metrics',
    'query': """
SELECT
       v.datname, c.relname, v.command, v.phase,
       i.relname,
       heap_tuples_scanned, heap_tuples_written, heap_blks_total, heap_blks_scanned, index_rebuild_count
  FROM pg_stat_progress_cluster as v
  LEFT JOIN pg_class c on c.oid = v.relid
  LEFT JOIN pg_class i on i.oid = v.cluster_index_relid
""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'command', 'type': 'tag'},
        {'name': 'phase', 'type': 'tag'},
        {'name': 'index', 'type': 'tag_not_null'},
        {'name': 'postgresql.cluster_vacuum.heap_tuples_scanned', 'type': 'gauge'},
        {'name': 'postgresql.cluster_vacuum.heap_tuples_written', 'type': 'gauge'},
        {'name': 'postgresql.cluster_vacuum.heap_blks_total', 'type': 'gauge'},
        {'name': 'postgresql.cluster_vacuum.heap_blks_scanned', 'type': 'gauge'},
        {'name': 'postgresql.cluster_vacuum.index_rebuild_count', 'type': 'gauge'},
    ],
}

# Requires PG12+
INDEX_PROGRESS_METRICS = {
    'name': 'index_progress_metrics',
    'query': """
SELECT
       p.datname, c.relname, i.relname, p.command, p.phase,
       lockers_total, lockers_done,
       blocks_total, blocks_done,
       tuples_total, tuples_done,
       partitions_total, partitions_done
  FROM pg_stat_progress_create_index as p
  LEFT JOIN pg_class c on c.oid = p.relid
  LEFT JOIN pg_class i on i.oid = p.index_relid
""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'index', 'type': 'tag_not_null'},
        {'name': 'command', 'type': 'tag'},
        {'name': 'phase', 'type': 'tag'},
        {'name': 'postgresql.create_index.lockers_total', 'type': 'gauge'},
        {'name': 'postgresql.create_index.lockers_done', 'type': 'gauge'},
        {'name': 'postgresql.create_index.blocks_total', 'type': 'gauge'},
        {'name': 'postgresql.create_index.blocks_done', 'type': 'gauge'},
        {'name': 'postgresql.create_index.tuples_total', 'type': 'gauge'},
        {'name': 'postgresql.create_index.tuples_done', 'type': 'gauge'},
        {'name': 'postgresql.create_index.partitions_total', 'type': 'gauge'},
        {'name': 'postgresql.create_index.partitions_done', 'type': 'gauge'},
    ],
}

WAL_FILE_METRICS = {
    'name': 'wal_metrics',
    'query': """
SELECT
count(*),
sum(size),
EXTRACT (EPOCH FROM now() - min(modification))
  FROM pg_ls_waldir();
""",
    'columns': [
        {'name': 'postgresql.wal_count', 'type': 'gauge'},
        {'name': 'postgresql.wal_size', 'type': 'gauge'},
        {'name': 'postgresql.wal_age', 'type': 'gauge'},
    ],
}

STAT_WAL_METRICS = {
    'name': 'stat_wal_metrics',
    'query': """
SELECT wal_records, wal_fpi,
       wal_bytes, wal_buffers_full,
       wal_write, wal_sync,
       wal_write_time, wal_sync_time
  FROM pg_stat_wal
""",
    'columns': [
        {'name': 'postgresql.wal.records', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.full_page_images', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.bytes', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.buffers_full', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.write', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.sync', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.write_time', 'type': 'monotonic_count'},
        {'name': 'postgresql.wal.sync_time', 'type': 'monotonic_count'},
    ],
}

FUNCTION_METRICS = {
    'descriptors': [('schemaname', 'schema'), ('funcname', 'function')],
    'metrics': {
        'calls': ('postgresql.function.calls', AgentCheck.rate),
        'total_time': ('postgresql.function.total_time', AgentCheck.rate),
        'self_time': ('postgresql.function.self_time', AgentCheck.rate),
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
        {metrics_columns}
  FROM pg_proc p
  JOIN pg_stat_user_functions s
    ON p.oid = s.funcid
  LEFT JOIN overloaded_funcs o
    ON o.funcname = s.funcname;
""",
    'relation': False,
    'use_global_db_tag': True,
    'name': 'function_metrics',
}

# The metrics we retrieve from pg_stat_activity when the postgres version >= 10
# The query will have a where condition removing manual vacuum and backends
# other than client backends
ACTIVITY_METRICS_10 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (usename NOT IN ('postgres', '{dd__user}')) THEN 1 ELSE null END )",
    "COUNT(CASE WHEN wait_event is NOT NULL THEN 1 ELSE null END)",
    "COUNT(CASE WHEN wait_event is NOT NULL AND state = 'active' THEN 1 ELSE null END)",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "max(age(backend_xid))",
    "max(age(backend_xmin))",
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 9.6
ACTIVITY_METRICS_9_6 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND usename NOT IN ('postgres', '{dd__user}')) THEN 1 ELSE null END )",
    "COUNT(CASE WHEN wait_event is NOT NULL AND query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN wait_event is NOT NULL AND query !~* '^vacuum ' AND query !~ '^autovacuum:' AND state = 'active' "
    "THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "max(age(backend_xid))",
    "max(age(backend_xmin))",
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 9.2
ACTIVITY_METRICS_9_2 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND usename NOT IN ('postgres', '{dd__user}')) THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~* '^vacuum ' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND state = 'active' THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "null",  # backend_xid is not available
    "null",  # backend_xmin is not available
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 8.3
ACTIVITY_METRICS_8_3 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND usename NOT IN ('postgres', '{dd__user}')) THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~* '^vacuum ' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND state = 'active' THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "null",  # backend_xid is not available
    "null",  # backend_xmin is not available
]

# The metrics we retrieve from pg_stat_activity when the postgres version < 8.3
ACTIVITY_METRICS_LT_8_3 = [
    "SUM(CASE WHEN query_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND usename NOT IN ('postgres', '{dd__user}')) THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~* '^vacuum ' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~* '^vacuum ' AND query !~ '^autovacuum:' "
    "AND state = 'active' THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - query_start)))",
    "null",  # backend_xid is not available
    "null",  # backend_xmin is not available
]

# The metrics we collect from pg_stat_activity that we zip with one of the lists above
ACTIVITY_DD_METRICS = [
    ('postgresql.transactions.open', AgentCheck.gauge),
    ('postgresql.transactions.idle_in_transaction', AgentCheck.gauge),
    ('postgresql.active_queries', AgentCheck.gauge),
    ('postgresql.waiting_queries', AgentCheck.gauge),
    ('postgresql.active_waiting_queries', AgentCheck.gauge),
    ('postgresql.activity.xact_start_age', AgentCheck.gauge),
    ('postgresql.activity.backend_xid_age', AgentCheck.gauge),
    ('postgresql.activity.backend_xmin_age', AgentCheck.gauge),
]

# The base query for postgres version >= 10
ACTIVITY_QUERY_10 = """
SELECT {aggregation_columns_select}
    {{metrics_columns}}
FROM pg_stat_activity
WHERE backend_type = 'client backend' AND query !~* '^vacuum '
GROUP BY datid {aggregation_columns_group}
"""

# The base query for postgres version < 10
ACTIVITY_QUERY_LT_10 = """
SELECT {aggregation_columns_select}
    {{metrics_columns}}
FROM pg_stat_activity
GROUP BY datid {aggregation_columns_group}
"""

# Requires PG10+
STAT_SUBSCRIPTION_METRICS = {
    'name': 'stat_subscription_metrics',
    'query': """
SELECT  subname,
        EXTRACT(EPOCH FROM (age(current_timestamp, last_msg_send_time))),
        EXTRACT(EPOCH FROM (age(current_timestamp, last_msg_receipt_time))),
        EXTRACT(EPOCH FROM (age(current_timestamp, latest_end_time)))
FROM pg_stat_subscription
""",
    'columns': [
        {'name': 'subscription_name', 'type': 'tag'},
        {'name': 'postgresql.subscription.last_msg_send_age', 'type': 'gauge'},
        {'name': 'postgresql.subscription.last_msg_receipt_age', 'type': 'gauge'},
        {'name': 'postgresql.subscription.latest_end_age', 'type': 'gauge'},
    ],
}

# Requires PG14+
# While pg_subscription is available since PG10,
# pg_subscription.oid is only publicly accessible starting PG14.
SUBSCRIPTION_STATE_METRICS = {
    'name': 'subscription_state_metrics',
    'query': """
select
    pg_subscription.subname,
    srrelid::regclass,
    CASE srsubstate
        WHEN 'i' THEN 'initialize'
        WHEN 'd' THEN 'data_copy'
        WHEN 'f' THEN 'finished_copy'
        WHEN 's' THEN 'synchronized'
        WHEN 'r' THEN 'ready'
    END,
    1
from pg_subscription_rel
join pg_subscription ON pg_subscription.oid = pg_subscription_rel.srsubid""".strip(),
    'columns': [
        {'name': 'subscription_name', 'type': 'tag'},
        {'name': 'relation', 'type': 'tag'},
        {'name': 'state', 'type': 'tag'},
        {'name': 'postgresql.subscription.state', 'type': 'gauge'},
    ],
}

# Requires PG15+
STAT_SUBSCRIPTION_STATS_METRICS = {
    'name': 'stat_subscription_stats_metrics',
    'query': """
SELECT subname,
       apply_error_count,
       sync_error_count
FROM pg_stat_subscription_stats
""",
    'columns': [
        {'name': 'subscription_name', 'type': 'tag'},
        {'name': 'postgresql.subscription.apply_error', 'type': 'monotonic_count'},
        {'name': 'postgresql.subscription.sync_error', 'type': 'monotonic_count'},
    ],
}
