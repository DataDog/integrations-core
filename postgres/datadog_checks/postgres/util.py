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
    undefined_activity_view = 'undefined-pg-stat-activity-view'
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
    'numbackends': ('connections', AgentCheck.gauge),
}

COMMON_METRICS = {
    'xact_commit': ('commits', AgentCheck.rate),
    'xact_rollback': ('rollbacks', AgentCheck.rate),
    'blks_read': ('disk_read', AgentCheck.rate),
    'blks_hit': ('buffer_hit', AgentCheck.rate),
    'tup_returned': ('rows_returned', AgentCheck.rate),
    'tup_fetched': ('rows_fetched', AgentCheck.rate),
    'tup_inserted': ('rows_inserted', AgentCheck.rate),
    'tup_updated': ('rows_updated', AgentCheck.rate),
    'tup_deleted': ('rows_deleted', AgentCheck.rate),
    '2^31 - age(datfrozenxid) as wraparound': ('before_xid_wraparound', AgentCheck.gauge),
}

DATABASE_SIZE_METRICS = {'pg_database_size(psd.datname) as pg_database_size': ('database_size', AgentCheck.gauge)}

NEWER_92_METRICS = {
    'deadlocks': ('deadlocks', AgentCheck.rate),
    'temp_bytes': ('temp_bytes', AgentCheck.rate),
    'temp_files': ('temp_files', AgentCheck.rate),
    'blk_read_time': ('blk_read_time', AgentCheck.monotonic_count),
    'blk_write_time': ('blk_write_time', AgentCheck.monotonic_count),
}

CHECKSUM_METRICS = {'checksum_failures': ('checksums.checksum_failures', AgentCheck.monotonic_count)}

NEWER_14_METRICS = {
    'session_time': ('sessions.session_time', AgentCheck.monotonic_count),
    'active_time': ('sessions.active_time', AgentCheck.monotonic_count),
    'idle_in_transaction_time': ('sessions.idle_in_transaction_time', AgentCheck.monotonic_count),
    'sessions': ('sessions.count', AgentCheck.monotonic_count),
    'sessions_abandoned': ('sessions.abandoned', AgentCheck.monotonic_count),
    'sessions_fatal': ('sessions.fatal', AgentCheck.monotonic_count),
    'sessions_killed': ('sessions.killed', AgentCheck.monotonic_count),
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
        {'name': 'deadlocks.count', 'type': 'monotonic_count'},
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
        {'name': 'conflicts.tablespace', 'type': 'monotonic_count'},
        {'name': 'conflicts.lock', 'type': 'monotonic_count'},
        {'name': 'conflicts.snapshot', 'type': 'monotonic_count'},
        {'name': 'conflicts.bufferpin', 'type': 'monotonic_count'},
        {'name': 'conflicts.deadlock', 'type': 'monotonic_count'},
    ],
}

QUERY_PG_UPTIME = {
    'name': 'pg_uptime',
    'query': "SELECT FLOOR(EXTRACT(EPOCH FROM current_timestamp - pg_postmaster_start_time()))",
    'columns': [
        {'name': 'uptime', 'type': 'gauge'},
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
        {'name': 'control.timeline_id', 'type': 'gauge'},
        {'name': 'control.checkpoint_delay', 'type': 'gauge'},
    ],
}

COMMON_BGW_METRICS = {
    'checkpoints_timed': ('bgwriter.checkpoints_timed', AgentCheck.monotonic_count),
    'checkpoints_req': ('bgwriter.checkpoints_requested', AgentCheck.monotonic_count),
    'buffers_checkpoint': ('bgwriter.buffers_checkpoint', AgentCheck.monotonic_count),
    'buffers_clean': ('bgwriter.buffers_clean', AgentCheck.monotonic_count),
    'maxwritten_clean': ('bgwriter.maxwritten_clean', AgentCheck.monotonic_count),
    'buffers_backend': ('bgwriter.buffers_backend', AgentCheck.monotonic_count),
    'buffers_alloc': ('bgwriter.buffers_alloc', AgentCheck.monotonic_count),
}

NEWER_91_BGW_METRICS = {'buffers_backend_fsync': ('bgwriter.buffers_backend_fsync', AgentCheck.monotonic_count)}

NEWER_92_BGW_METRICS = {
    'checkpoint_write_time': ('bgwriter.write_time', AgentCheck.monotonic_count),
    'checkpoint_sync_time': ('bgwriter.sync_time', AgentCheck.monotonic_count),
}

COMMON_ARCHIVER_METRICS = {
    'archived_count': ('archiver.archived_count', AgentCheck.monotonic_count),
    'failed_count': ('archiver.failed_count', AgentCheck.monotonic_count),
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
    'metrics': {'count (*)': ('table.count', AgentCheck.gauge)},
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
    q1: ('replication_delay', AgentCheck.gauge),
    q2: ('replication_delay_bytes', AgentCheck.gauge),
}

q = (
    'CASE WHEN pg_last_xlog_receive_location() IS NULL OR '
    'pg_last_xlog_receive_location() = pg_last_xlog_replay_location() THEN 0 ELSE GREATEST '
    '(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
)
REPLICATION_METRICS_9_1 = {q: ('replication_delay', AgentCheck.gauge)}

q2 = (
    'abs(pg_xlog_location_diff(pg_last_xlog_receive_location(), pg_last_xlog_replay_location())) '
    'AS replication_delay_bytes'
)
REPLICATION_METRICS_9_2 = {
    q2: ('replication_delay_bytes', AgentCheck.gauge),
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
            'replication.wal_write_lag',
            AgentCheck.gauge,
        ),
        'GREATEST (0, EXTRACT(epoch from flush_lag)) AS flush_lag': (
            'replication.wal_flush_lag',
            AgentCheck.gauge,
        ),
        'GREATEST (0, EXTRACT(epoch from replay_lag)) AS replay_lag': (
            'replication.wal_replay_lag',
            AgentCheck.gauge,
        ),
        'GREATEST (0, age(backend_xmin)) as backend_xmin_age': (
            'replication.backend_xmin_age',
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
        {'name': 'wal_receiver.connected', 'type': 'gauge'},
        {'name': 'wal_receiver.received_timeline', 'type': 'gauge'},
        {'name': 'wal_receiver.last_msg_send_age', 'type': 'gauge'},
        {'name': 'wal_receiver.last_msg_receipt_age', 'type': 'gauge'},
        {'name': 'wal_receiver.latest_end_age', 'type': 'gauge'},
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
        CASE WHEN catalog_xmin IS NULL THEN NULL ELSE age(catalog_xmin) END,
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
        {'name': 'replication_slot.xmin_age', 'type': 'gauge'},
        {'name': 'replication_slot.catalog_xmin_age', 'type': 'gauge'},
        {'name': 'replication_slot.restart_delay_bytes', 'type': 'gauge'},
        {'name': 'replication_slot.confirmed_flush_delay_bytes', 'type': 'gauge'},
    ],
}

# Require PG14+
QUERY_PG_REPLICATION_SLOTS_STATS = {
    'name': 'pg_replication_slots_stats',
    'columns': [
        {'name': 'slot_name', 'type': 'tag'},
        {'name': 'slot_type', 'type': 'tag'},
        {'name': 'slot_state', 'type': 'tag'},
        {'name': 'replication_slot.spill_txns', 'type': 'monotonic_count'},
        {'name': 'replication_slot.spill_count', 'type': 'monotonic_count'},
        {'name': 'replication_slot.spill_bytes', 'type': 'monotonic_count'},
        {'name': 'replication_slot.stream_txns', 'type': 'monotonic_count'},
        {'name': 'replication_slot.stream_count', 'type': 'monotonic_count'},
        {'name': 'replication_slot.stream_bytes', 'type': 'monotonic_count'},
        {'name': 'replication_slot.total_txns', 'type': 'monotonic_count'},
        {'name': 'replication_slot.total_bytes', 'type': 'monotonic_count'},
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
        'MAX(setting) AS max_connections': ('max_connections', AgentCheck.gauge),
        'SUM(numbackends)/MAX(setting) AS pct_connections': ('percent_usage_connections', AgentCheck.gauge),
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
        'blks_zeroed': ('slru.blks_zeroed', AgentCheck.monotonic_count),
        'blks_hit': ('slru.blks_hit', AgentCheck.monotonic_count),
        'blks_read': ('slru.blks_read', AgentCheck.monotonic_count),
        'blks_written ': ('slru.blks_written', AgentCheck.monotonic_count),
        'blks_exists': ('slru.blks_exists', AgentCheck.monotonic_count),
        'flushes': ('slru.flushes', AgentCheck.monotonic_count),
        'truncates': ('slru.truncates', AgentCheck.monotonic_count),
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
        {'name': 'snapshot.xmin', 'type': 'gauge'},
        {'name': 'snapshot.xmax', 'type': 'gauge'},
        {'name': 'snapshot.xip_count', 'type': 'gauge'},
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
        {'name': 'snapshot.xmin', 'type': 'gauge'},
        {'name': 'snapshot.xmax', 'type': 'gauge'},
        {'name': 'snapshot.xip_count', 'type': 'gauge'},
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
        {'name': 'vacuum.heap_blks_total', 'type': 'gauge'},
        {'name': 'vacuum.heap_blks_scanned', 'type': 'gauge'},
        {'name': 'vacuum.heap_blks_vacuumed', 'type': 'gauge'},
        {'name': 'vacuum.index_vacuum_count', 'type': 'gauge'},
        {'name': 'vacuum.max_dead_tuples', 'type': 'gauge'},
        {'name': 'vacuum.num_dead_tuples', 'type': 'gauge'},
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
        {'name': 'analyze.sample_blks_total', 'type': 'gauge'},
        {'name': 'analyze.sample_blks_scanned', 'type': 'gauge'},
        {'name': 'analyze.ext_stats_total', 'type': 'gauge'},
        {'name': 'analyze.ext_stats_computed', 'type': 'gauge'},
        {'name': 'analyze.child_tables_total', 'type': 'gauge'},
        {'name': 'analyze.child_tables_done', 'type': 'gauge'},
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
        {'name': 'cluster_vacuum.heap_tuples_scanned', 'type': 'gauge'},
        {'name': 'cluster_vacuum.heap_tuples_written', 'type': 'gauge'},
        {'name': 'cluster_vacuum.heap_blks_total', 'type': 'gauge'},
        {'name': 'cluster_vacuum.heap_blks_scanned', 'type': 'gauge'},
        {'name': 'cluster_vacuum.index_rebuild_count', 'type': 'gauge'},
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
        {'name': 'create_index.lockers_total', 'type': 'gauge'},
        {'name': 'create_index.lockers_done', 'type': 'gauge'},
        {'name': 'create_index.blocks_total', 'type': 'gauge'},
        {'name': 'create_index.blocks_done', 'type': 'gauge'},
        {'name': 'create_index.tuples_total', 'type': 'gauge'},
        {'name': 'create_index.tuples_done', 'type': 'gauge'},
        {'name': 'create_index.partitions_total', 'type': 'gauge'},
        {'name': 'create_index.partitions_done', 'type': 'gauge'},
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
        {'name': 'wal_count', 'type': 'gauge'},
        {'name': 'wal_size', 'type': 'gauge'},
        {'name': 'wal_age', 'type': 'gauge'},
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
        {'name': 'wal.records', 'type': 'monotonic_count'},
        {'name': 'wal.full_page_images', 'type': 'monotonic_count'},
        {'name': 'wal.bytes', 'type': 'monotonic_count'},
        {'name': 'wal.buffers_full', 'type': 'monotonic_count'},
        {'name': 'wal.write', 'type': 'monotonic_count'},
        {'name': 'wal.sync', 'type': 'monotonic_count'},
        {'name': 'wal.write_time', 'type': 'monotonic_count'},
        {'name': 'wal.sync_time', 'type': 'monotonic_count'},
    ],
}

FUNCTION_METRICS = {
    'descriptors': [('schemaname', 'schema'), ('funcname', 'function')],
    'metrics': {
        'calls': ('function.calls', AgentCheck.rate),
        'total_time': ('function.total_time', AgentCheck.rate),
        'self_time': ('function.self_time', AgentCheck.rate),
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

# pg_buffercache is implemented with a function scan. Thus, the planner doesn't
# have much reliable estimation on the number of rows returned by pg_buffercache.
# The function's pgproc.prorows is used and 1000 is used as a default value.
# On top of that, the function is volatile, preventing possible inlining and
# optimisation.
# It is very likely that we have way more buffers than relations: 16GB of shared_buffers
# will have 2097152 buffers returned by pg_buffercache while pg_class will mostly be
# around thousands of rows. Therefore, we write the query as a CTE aggregating on reldatabase
# and relfilenode. Given that the function is volatile, this will force the CTE to be
# materialized and we should have less or the same cardinality as output as pg_class's
# rows.
# This is more efficient than the cte-less version which will rely on a merge join and thus
# sort the output of pg_buffercache.
BUFFERCACHE_METRICS = {
    'name': 'buffercache_metrics',
    'query': """
WITH buffer_by_relfilenode AS (
    SELECT reldatabase, relfilenode,
        NULLIF(COUNT(CASE WHEN relfilenode IS NOT NULL THEN 1 END), 0) as used,
        COUNT(CASE WHEN relfilenode IS NULL THEN 1 END) as unused,
        SUM(usagecount) as sum_usagecount,
        NULLIF(SUM(isdirty::int), 0) as sum_dirty,
        NULLIF(SUM(pinning_backends), 0) as sum_pinning
    FROM pg_buffercache
    GROUP BY reldatabase, relfilenode
)
SELECT COALESCE(d.datname, 'shared'), n.nspname, c.relname,
       used, unused, sum_usagecount, sum_dirty, sum_pinning
  FROM buffer_by_relfilenode b
  LEFT JOIN pg_database d ON b.reldatabase = d.oid
  LEFT JOIN pg_class c ON b.relfilenode = pg_relation_filenode(c.oid)
  LEFT JOIN pg_namespace n ON n.oid = c.relnamespace;
""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'schema', 'type': 'tag_not_null'},
        {'name': 'relation', 'type': 'tag_not_null'},
        {'name': 'buffercache.used_buffers', 'type': 'gauge'},
        {'name': 'buffercache.unused_buffers', 'type': 'gauge'},
        {'name': 'buffercache.usage_count', 'type': 'gauge'},
        {'name': 'buffercache.dirty_buffers', 'type': 'gauge'},
        {'name': 'buffercache.pinning_backends', 'type': 'gauge'},
    ],
}

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
    ('transactions.open', AgentCheck.gauge),
    ('transactions.idle_in_transaction', AgentCheck.gauge),
    ('active_queries', AgentCheck.gauge),
    ('waiting_queries', AgentCheck.gauge),
    ('active_waiting_queries', AgentCheck.gauge),
    ('activity.xact_start_age', AgentCheck.gauge),
    ('activity.backend_xid_age', AgentCheck.gauge),
    ('activity.backend_xmin_age', AgentCheck.gauge),
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
        {'name': 'subscription.last_msg_send_age', 'type': 'gauge'},
        {'name': 'subscription.last_msg_receipt_age', 'type': 'gauge'},
        {'name': 'subscription.latest_end_age', 'type': 'gauge'},
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
        {'name': 'subscription.state', 'type': 'gauge'},
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
        {'name': 'subscription.apply_error', 'type': 'monotonic_count'},
        {'name': 'subscription.sync_error', 'type': 'monotonic_count'},
    ],
}

# Requires PG16+
# Capping at 200 rows for caution. This should always return less data points than that. Adjust if needed
STAT_IO_METRICS = {
    'name': 'stat_io_metrics',
    'query': """
SELECT backend_type,
       object,
       context,
       evictions,
       extend_time,
       extends,
       fsync_time,
       fsyncs,
       hits,
       read_time,
       reads,
       write_time,
       writes
FROM pg_stat_io
LIMIT 200
""",
    'columns': [
        {'name': 'backend_type', 'type': 'tag'},
        {'name': 'object', 'type': 'tag'},
        {'name': 'context', 'type': 'tag'},
        {'name': 'io.evictions', 'type': 'monotonic_count'},
        {'name': 'io.extend_time', 'type': 'monotonic_count'},
        {'name': 'io.extends', 'type': 'monotonic_count'},
        {'name': 'io.fsync_time', 'type': 'monotonic_count'},
        {'name': 'io.fsyncs', 'type': 'monotonic_count'},
        {'name': 'io.hits', 'type': 'monotonic_count'},
        {'name': 'io.read_time', 'type': 'monotonic_count'},
        {'name': 'io.reads', 'type': 'monotonic_count'},
        {'name': 'io.write_time', 'type': 'monotonic_count'},
        {'name': 'io.writes', 'type': 'monotonic_count'},
    ],
}
