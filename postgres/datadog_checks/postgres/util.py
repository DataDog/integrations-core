# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import string

from datadog_checks.base import AgentCheck

ALL_SCHEMAS = object()


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


def get_schema_field(descriptors):
    """Return column containg the schema name for that query."""
    for column, name in descriptors:
        if name == 'schema':
            return column


def build_relations_filter(relations_config, schema_field):
    """Build a WHERE clause filtering relations based on relations_config."""
    relations_filter = []
    for r in relations_config.values():
        relation_filter = []
        if r.get('relation_name'):
            relation_filter.append("( relname = '{}'".format(r['relation_name']))
        elif r.get('relation_regex'):
            relation_filter.append("( relname ~ '{}'".format(r['relation_regex']))
        if ALL_SCHEMAS not in r['schemas']:
            schema_filter = ' ,'.join("'{}'".format(s) for s in r['schemas'])
            relation_filter.append('AND {} = ANY(array[{}]::text[])'.format(schema_field, schema_filter))
        relation_filter.append(')')
        relations_filter.append(' '.join(relation_filter))

    return ' OR '.join(relations_filter)


fmt = PartialFormatter()


COMMON_METRICS = {
    'numbackends': ('postgresql.connections', AgentCheck.gauge),
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

LOCK_METRICS = {
    'descriptors': [
        ('mode', 'lock_mode'),
        ('locktype', 'lock_type'),
        ('nspname', 'schema'),
        ('datname', 'db'),
        ('relname', 'table'),
    ],
    'metrics': {'lock_count': ('postgresql.locks', AgentCheck.gauge)},
    'query': """
SELECT mode,
       locktype,
       pn.nspname,
       pd.datname,
       pc.relname,
       count(*) AS {metrics_columns}
  FROM pg_locks l
  JOIN pg_database pd ON (l.database = pd.oid)
  JOIN pg_class pc ON (l.relation = pc.oid)
  LEFT JOIN pg_namespace pn ON (pn.oid = pc.relnamespace)
 WHERE l.mode IS NOT NULL
   AND pc.relname NOT LIKE 'pg_%%'
 GROUP BY pd.datname, pc.relname, pn.nspname, locktype, mode""",
    'relation': False,
}

REL_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
    # This field contains old metrics that need to be deprecated. For now we keep sending them.
    'deprecated_metrics': {'idx_tup_fetch': ('postgresql.index_rows_fetched', AgentCheck.rate)},
    'metrics': {
        'seq_scan': ('postgresql.seq_scans', AgentCheck.rate),
        'seq_tup_read': ('postgresql.seq_rows_read', AgentCheck.rate),
        'idx_scan': ('postgresql.index_scans', AgentCheck.rate),
        'idx_tup_fetch': ('postgresql.index_rel_rows_fetched', AgentCheck.rate),
        'n_tup_ins': ('postgresql.rows_inserted', AgentCheck.rate),
        'n_tup_upd': ('postgresql.rows_updated', AgentCheck.rate),
        'n_tup_del': ('postgresql.rows_deleted', AgentCheck.rate),
        'n_tup_hot_upd': ('postgresql.rows_hot_updated', AgentCheck.rate),
        'n_live_tup': ('postgresql.live_rows', AgentCheck.gauge),
        'n_dead_tup': ('postgresql.dead_rows', AgentCheck.gauge),
    },
    'query': """
SELECT relname,schemaname,{metrics_columns}
  FROM pg_stat_user_tables
 WHERE {relations}""",
    'relation': True,
}

IDX_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema'), ('indexrelname', 'index')],
    'metrics': {
        'idx_scan': ('postgresql.index_scans', AgentCheck.rate),
        'idx_tup_read': ('postgresql.index_rows_read', AgentCheck.rate),
        'idx_tup_fetch': ('postgresql.index_rows_fetched', AgentCheck.rate),
    },
    'query': """
SELECT relname,
       schemaname,
       indexrelname,
       {metrics_columns}
  FROM pg_stat_user_indexes
 WHERE {relations}""",
    'relation': True,
}

SIZE_METRICS = {
    'descriptors': [('nspname', 'schema'), ('relname', 'table')],
    'metrics': {
        'pg_table_size(C.oid) as table_size': ('postgresql.table_size', AgentCheck.gauge),
        'pg_indexes_size(C.oid) as index_size': ('postgresql.index_size', AgentCheck.gauge),
        'pg_total_relation_size(C.oid) as total_size': ('postgresql.total_size', AgentCheck.gauge),
    },
    'relation': True,
    'query': """
SELECT
  N.nspname,
  relname,
  {metrics_columns}
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
WHERE nspname NOT IN ('pg_catalog', 'information_schema') AND
  nspname !~ '^pg_toast' AND
  relkind = 'r' AND
  {relations}""",
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
    'CASE WHEN pg_last_wal_receive_lsn() = pg_last_wal_replay_lsn() THEN 0 ELSE GREATEST '
    '(0, EXTRACT (EPOCH FROM now() - pg_last_xact_replay_timestamp())) END'
)
q2 = 'abs(pg_wal_lsn_diff(pg_last_wal_receive_lsn(), pg_last_wal_replay_lsn()))'
REPLICATION_METRICS_10 = {
    q1: ('postgresql.replication_delay', AgentCheck.gauge),
    q2: ('postgresql.replication_delay_bytes', AgentCheck.gauge),
}

q = (
    'CASE WHEN pg_last_xlog_receive_location() = pg_last_xlog_replay_location() THEN 0 ELSE GREATEST '
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

STATIO_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
    'metrics': {
        'heap_blks_read': ('postgresql.heap_blocks_read', AgentCheck.rate),
        'heap_blks_hit': ('postgresql.heap_blocks_hit', AgentCheck.rate),
        'idx_blks_read': ('postgresql.index_blocks_read', AgentCheck.rate),
        'idx_blks_hit': ('postgresql.index_blocks_hit', AgentCheck.rate),
        'toast_blks_read': ('postgresql.toast_blocks_read', AgentCheck.rate),
        'toast_blks_hit': ('postgresql.toast_blocks_hit', AgentCheck.rate),
        'tidx_blks_read': ('postgresql.toast_index_blocks_read', AgentCheck.rate),
        'tidx_blks_hit': ('postgresql.toast_index_blocks_hit', AgentCheck.rate),
    },
    'query': """
SELECT relname,
       schemaname,
       {metrics_columns}
  FROM pg_statio_user_tables
 WHERE {relations}""",
    'relation': True,
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

# The metrics we retrieve from pg_stat_activity when the postgres version >= 9.2
ACTIVITY_METRICS_9_6 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN wait_event is NOT NULL AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 9.2
ACTIVITY_METRICS_9_2 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
]

# The metrics we retrieve from pg_stat_activity when the postgres version >= 8.3
ACTIVITY_METRICS_8_3 = [
    "SUM(CASE WHEN xact_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
]

# The metrics we retrieve from pg_stat_activity when the postgres version < 8.3
ACTIVITY_METRICS_LT_8_3 = [
    "SUM(CASE WHEN query_start IS NOT NULL THEN 1 ELSE 0 END)",
    "SUM(CASE WHEN current_query LIKE '<IDLE> in transaction' THEN 1 ELSE 0 END)",
    "COUNT(CASE WHEN state = 'active' AND (query !~ '^autovacuum:' AND usename NOT IN ('postgres', '{dd__user}'))"
    "THEN 1 ELSE null END )",
    "COUNT(CASE WHEN waiting = 't' AND query !~ '^autovacuum:' THEN 1 ELSE null END )",
]

# The metrics we collect from pg_stat_activity that we zip with one of the lists above
ACTIVITY_DD_METRICS = [
    ('postgresql.transactions.open', AgentCheck.gauge),
    ('postgresql.transactions.idle_in_transaction', AgentCheck.gauge),
    ('postgresql.active_queries', AgentCheck.gauge),
    ('postgresql.waiting_queries', AgentCheck.gauge),
]

# The base query for postgres version >= 10
ACTIVITY_QUERY_10 = """
SELECT datname,
    {metrics_columns}
FROM pg_stat_activity
WHERE backend_type = 'client backend'
GROUP BY datid, datname
"""

# The base query for postgres version < 10
ACTIVITY_QUERY_LT_10 = """
SELECT datname,
    {metrics_columns}
FROM pg_stat_activity
GROUP BY datid, datname
"""
