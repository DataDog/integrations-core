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


fmt = PartialFormatter()

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


COUNT_METRICS = {
    'descriptors': [('schemaname', 'schema')],
    'metrics': {'pg_stat_user_tables': ('postgresql.table.count', AgentCheck.gauge)},
    'relation': False,
    'use_global_db_tag': True,
    'query': fmt.format(
        """
SELECT schemaname, count(*) FROM
(
SELECT schemaname
FROM {metrics_columns}
ORDER BY schemaname, relname
LIMIT {table_count_limit}
) AS subquery GROUP BY schemaname
    """
    ),
}

q1 = (
    'CASE WHEN pg_last_wal_receive_lsn() IS NULL OR '
    'pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0 ELSE GREATEST '
    '(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
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
        pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn),
        pg_wal_lsn_diff(pg_current_wal_lsn(), confirmed_flush_lsn)
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
}

# The metrics we retrieve from pg_stat_activity when the postgres version >= 9.6
ACTIVITY_METRICS_9_6 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN wait_event is NOT NULL AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN wait_event is NOT NULL AND query !~ '^autovacuum:' AND state = 'active' THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "max(age(backend_xid))",
    "max(age(backend_xmin))",
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 9.2
ACTIVITY_METRICS_9_2 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' AND state = 'active' THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "null",  # backend_xid is not available
    "null",  # backend_xmin is not available
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 8.3
ACTIVITY_METRICS_8_3 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' AND state = 'active' THEN 1 ELSE null END )",
    "max(EXTRACT(EPOCH FROM (clock_timestamp() - xact_start)))",
    "null",  # backend_xid is not available
    "null",  # backend_xmin is not available
]

# The metrics we retrieve from pg_stat_activity when the postgres version < 8.3
ACTIVITY_METRICS_LT_8_3 = [
    "SUM(CASE WHEN query_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' AND state = 'active' THEN 1 ELSE null END )",
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
WHERE backend_type = 'client backend'
GROUP BY datid {aggregation_columns_group}
"""

# The base query for postgres version < 10
ACTIVITY_QUERY_LT_10 = """
SELECT {aggregation_columns_select}
    {{metrics_columns}}
FROM pg_stat_activity
GROUP BY datid {aggregation_columns_group}
"""
