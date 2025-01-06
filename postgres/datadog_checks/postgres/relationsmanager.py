# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# ===================================== DEPRECATION NOTICE =====================================
# This module is pending deprecation. For authors and contributors: additional queries should be
# declared using the QueryExecutor and QueryManager APIs.

# Reason for deprecation:
# Many of the metrics in this module filter on relations and require customers to explicitly
# connect to every database on their instance via configuration. This is untenable for customers
# with many databases and a maintenance pain for most; it is also unnecessary for views which
# can retrieve all data from all databases when connected to the default database
# (e.g. pg_locks). So to improve the customer experience and usability of configuration APIs,
# future implementations of these metrics should support autodiscovery, eliminating the need
# to connect to a specific database.
# =============================================================================================

from typing import Any, Dict, List, Union  # noqa: F401

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.log import get_check_logger

ALL_SCHEMAS = object()
RELATION_NAME = 'relation_name'
RELATION_REGEX = 'relation_regex'
SCHEMAS = 'schemas'
RELKIND = 'relkind'

# The view pg_locks provides access to information about the locks held by active processes within the database server.
LOCK_METRICS = {
    'descriptors': [
        ('mode', 'lock_mode'),
        ('locktype', 'lock_type'),
        ('nspname', 'schema'),
        ('datname', 'db'),
        ('relname', 'table'),
        ('granted', 'granted'),
        ('fastpath', 'fastpath'),
    ],
    'metrics': {'lock_count': ('locks', AgentCheck.gauge)},
    'query': """
SELECT mode,
       locktype,
       pn.nspname,
       pd.datname,
       pc.relname,
       granted,
       fastpath,
       count(*) AS {metrics_columns}
  FROM pg_locks l
  JOIN pg_database pd ON (l.database = pd.oid)
  JOIN pg_class pc ON (l.relation = pc.oid)
  LEFT JOIN pg_namespace pn ON (pn.oid = pc.relnamespace)
 WHERE {relations}
   AND l.mode IS NOT NULL
   AND pc.relname NOT LIKE 'pg^_%%' ESCAPE '^'
 GROUP BY pd.datname, pc.relname, pn.nspname, locktype, mode, granted, fastpath""",
    'relation': True,
    'name': 'lock_metrics',
}


# The pg_stat_all_indexes view will contain one row for each index in the current database,
# showing statistics about accesses to that specific index.
# The pg_stat_user_indexes view contain the same information, but filtered to only show user indexes.
IDX_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema'), ('indexrelname', 'index')],
    'metrics': {
        'idx_scan': ('index_scans', AgentCheck.rate),
        'idx_tup_read': ('index_rows_read', AgentCheck.rate),
        'idx_tup_fetch': ('index_rows_fetched', AgentCheck.rate),
        'pg_relation_size(indexrelid) as index_size': ('individual_index_size', AgentCheck.gauge),
    },
    'query': """
SELECT relname,
       schemaname,
       indexrelname,
       {metrics_columns}
  FROM pg_stat_user_indexes
 WHERE {relations}""",
    'relation': True,
    'name': 'idx_metrics',
}


# The catalog pg_class catalogs tables and most everything else that has columns or is otherwise similar to a table.
# For this integration we are restricting the query to ordinary tables.
#
# Sizes: Calling pg_relation_size, pg_table_size, pg_indexes_size or pg_total_relation_size
# can be expensive as the relation needs to be locked and stat syscalls are made behind the hood.
#
# We want to limit those calls as much as possible at the cost of precision.
# We also want to get toast size separated from the main table size.
# We can't use pg_total_relation_size which includes both toast, index and table size.
# Same for pg_table_size which includes both toast, table size.
#
# We will mainly rely on pg_relation_size which only get the size of the main fork.
# To keep postgresql.table_size's old behaviour which was based on pg_table_size, we will
# approximate table_size to (relation_size + toast_size). This will ignore FSM and VM size
# but their sizes are dwarfed by the relation's size and it's an acceptable trade off
# to ignore them to lower the amount of stat calls.
#
# Previous version filtered on nspname !~ '^pg_toast'. Since pg_toast namespace only
# contains index and toast table, the filter was redundant with relkind = 'r'
#
# We also filter out tables with an AccessExclusiveLock to avoid query timeouts.
QUERY_PG_CLASS_SIZE = {
    'name': 'pg_class_size',
    'query': """
SELECT current_database(),
       s.schemaname, s.table, s.partition_of,
       s.relpages, s.reltuples, s.relallvisible,
       s.relation_size + s.toast_size,
       s.relation_size,
       s.index_size,
       s.toast_size,
       s.relation_size + s.index_size + s.toast_size
FROM
    (SELECT
      N.nspname as schemaname,
      relname as table,
      I.inhparent::regclass AS partition_of,
      C.relpages, C.reltuples, C.relallvisible,
      pg_relation_size(C.oid) as relation_size,
      CASE WHEN C.relhasindex THEN pg_indexes_size(C.oid) ELSE 0 END as index_size,
      CASE WHEN C.reltoastrelid > 0 THEN pg_relation_size(C.reltoastrelid) ELSE 0 END as toast_size
    FROM pg_class C
    LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
    LEFT JOIN pg_inherits I ON (I.inhrelid = C.oid)
    WHERE NOT (nspname = ANY('{{pg_catalog,information_schema}}')) AND
        NOT EXISTS (
            SELECT 1
            from pg_locks
            WHERE locktype = 'relation'
            AND mode = 'AccessExclusiveLock'
            AND granted = true
            AND relation = C.oid
      ) AND
      relkind = 'r' AND
      {relations} {limits}) as s""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'schema', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'partition_of', 'type': 'tag_not_null'},
        {'name': 'relation.pages', 'type': 'gauge'},
        {'name': 'relation.tuples', 'type': 'gauge'},
        {'name': 'relation.all_visible', 'type': 'gauge'},
        {'name': 'table_size', 'type': 'gauge'},
        {'name': 'relation_size', 'type': 'gauge'},
        {'name': 'index_size', 'type': 'gauge'},
        {'name': 'toast_size', 'type': 'gauge'},
        {'name': 'total_size', 'type': 'gauge'},
    ],
}

# We used to rely on pg_stat_user_tables to get tuples and scan metrics
# However, using this view is inefficient as it groups by aggregation on oid and schema
# behind the hood, leading to possible temporary bytes being written to handle the sort.
# To avoid this, we need to directly call the pg_stat_* functions
QUERY_PG_CLASS = {
    'name': 'pg_class',
    'query': """
SELECT
  current_database(),
  N.nspname,
  C.relname,
  pg_stat_get_numscans(C.oid),
  pg_stat_get_tuples_returned(C.oid),
  I.idx_scan,
  I.idx_tup_fetch,
  pg_stat_get_tuples_inserted(C.oid),
  pg_stat_get_tuples_updated(C.oid),
  pg_stat_get_tuples_deleted(C.oid),
  pg_stat_get_tuples_hot_updated(C.oid),
  pg_stat_get_live_tuples(C.oid),
  pg_stat_get_dead_tuples(C.oid),
  pg_stat_get_vacuum_count(C.oid),
  pg_stat_get_autovacuum_count(C.oid),
  pg_stat_get_analyze_count(C.oid),
  pg_stat_get_autoanalyze_count(C.oid),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_vacuum_time(C.oid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_autovacuum_time(C.oid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_analyze_time(C.oid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_autoanalyze_time(C.oid))),
  pg_stat_get_numscans(idx_toast.indexrelid),
  pg_stat_get_tuples_fetched(idx_toast.indexrelid),
  pg_stat_get_tuples_inserted(C.reltoastrelid),
  pg_stat_get_tuples_deleted(C.reltoastrelid),
  pg_stat_get_live_tuples(C.reltoastrelid),
  pg_stat_get_dead_tuples(C.reltoastrelid),
  pg_stat_get_vacuum_count(C.reltoastrelid),
  pg_stat_get_autovacuum_count(C.reltoastrelid),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_vacuum_time(C.reltoastrelid))),
  EXTRACT(EPOCH FROM age(CURRENT_TIMESTAMP, pg_stat_get_last_autovacuum_time(C.reltoastrelid))),
  C.xmin
FROM pg_class C
LEFT JOIN pg_namespace N ON (N.oid = C.relnamespace)
LEFT JOIN pg_index idx_toast ON (idx_toast.indrelid = C.reltoastrelid)
LEFT JOIN LATERAL (
    SELECT sum(pg_stat_get_numscans(indexrelid))::bigint AS idx_scan,
           sum(pg_stat_get_tuples_fetched(indexrelid))::bigint AS idx_tup_fetch
      FROM pg_index
     WHERE pg_index.indrelid = C.oid) I ON true
WHERE C.relkind = 'r'
    AND NOT (nspname = ANY('{{pg_catalog,information_schema}}'))
    AND NOT EXISTS (
        SELECT 1
        from pg_locks
        WHERE locktype = 'relation'
        AND mode = 'AccessExclusiveLock'
        AND granted = true
        AND relation = C.oid
    )
    AND {relations} {limits}
""",
    'columns': [
        {'name': 'db', 'type': 'tag'},
        {'name': 'schema', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'seq_scans', 'type': 'rate'},
        {'name': 'seq_rows_read', 'type': 'rate'},
        {'name': 'index_rel_scans', 'type': 'rate'},
        {'name': 'index_rel_rows_fetched', 'type': 'rate'},
        {'name': 'rows_inserted', 'type': 'rate'},
        {'name': 'rows_updated', 'type': 'rate'},
        {'name': 'rows_deleted', 'type': 'rate'},
        {'name': 'rows_hot_updated', 'type': 'rate'},
        {'name': 'live_rows', 'type': 'gauge'},
        {'name': 'dead_rows', 'type': 'gauge'},
        {'name': 'vacuumed', 'type': 'monotonic_count'},
        {'name': 'autovacuumed', 'type': 'monotonic_count'},
        {'name': 'analyzed', 'type': 'monotonic_count'},
        {'name': 'autoanalyzed', 'type': 'monotonic_count'},
        {'name': 'last_vacuum_age', 'type': 'gauge'},
        {'name': 'last_autovacuum_age', 'type': 'gauge'},
        {'name': 'last_analyze_age', 'type': 'gauge'},
        {'name': 'last_autoanalyze_age', 'type': 'gauge'},
        {'name': 'toast.index_scans', 'type': 'monotonic_count'},
        {'name': 'toast.rows_fetched', 'type': 'monotonic_count'},
        {'name': 'toast.rows_inserted', 'type': 'monotonic_count'},
        {'name': 'toast.rows_deleted', 'type': 'monotonic_count'},
        {'name': 'toast.live_rows', 'type': 'gauge'},
        {'name': 'toast.dead_rows', 'type': 'gauge'},
        {'name': 'toast.vacuumed', 'type': 'monotonic_count'},
        {'name': 'toast.autovacuumed', 'type': 'monotonic_count'},
        {'name': 'toast.last_vacuum_age', 'type': 'gauge'},
        {'name': 'toast.last_autovacuum_age', 'type': 'gauge'},
        {'name': 'relation.xmin', 'type': 'gauge'},
    ],
}


# The pg_statio_all_tables view will contain one row for each table in the current database,
# showing statistics about I/O on that specific table. The pg_statio_user_tables views contain the same information,
# but filtered to only show user tables.
STATIO_METRICS = {
    'descriptors': [('relname', 'table'), ('schemaname', 'schema')],
    'metrics': {
        'heap_blks_read': ('heap_blocks_read', AgentCheck.rate),
        'heap_blks_hit': ('heap_blocks_hit', AgentCheck.rate),
        'idx_blks_read': ('index_blocks_read', AgentCheck.rate),
        'idx_blks_hit': ('index_blocks_hit', AgentCheck.rate),
        'toast_blks_read': ('toast_blocks_read', AgentCheck.rate),
        'toast_blks_hit': ('toast_blocks_hit', AgentCheck.rate),
        'tidx_blks_read': ('toast_index_blocks_read', AgentCheck.rate),
        'tidx_blks_hit': ('toast_index_blocks_hit', AgentCheck.rate),
    },
    'query': """
SELECT relname,
       schemaname,
       {metrics_columns}
  FROM pg_statio_user_tables
 WHERE {relations}""",
    'relation': True,
    'name': 'statio_metrics',
}

# adapted from https://wiki.postgresql.org/wiki/Show_database_bloat and https://github.com/bucardo/check_postgres/
TABLE_BLOAT_QUERY = """
SELECT
    schemaname, relname,
    ROUND((CASE WHEN otta=0 THEN 0.0 ELSE sml.relpages::float/otta END)::numeric,1) AS tbloat
FROM (
    SELECT
    schemaname, tablename, cc.relname as relname, cc.reltuples, cc.relpages,
    CEIL((cc.reltuples*((datahdr+ma-
        (CASE WHEN datahdr%ma=0 THEN ma ELSE datahdr%ma END))+nullhdr2+4))/(bs-20::float)) AS otta
    FROM (
    SELECT
        ma,bs,schemaname,tablename,
        (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
        (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
    FROM (
        SELECT
    schemaname, tablename, hdr, ma, bs,
    SUM((1-null_frac)*avg_width) AS datawidth,
    MAX(null_frac) AS maxfracsum,
    hdr+(
        SELECT 1+count(*)/8
        FROM pg_stats s2
        WHERE null_frac<>0 AND s2.schemaname = s.schemaname AND s2.tablename = s.tablename
    ) AS nullhdr
        FROM pg_stats s, (
    SELECT
        (SELECT current_setting('block_size')::numeric) AS bs,
        CASE WHEN substring(v,12,3) IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr,
        CASE WHEN v ~ 'mingw32' THEN 8 ELSE 4 END AS ma
    FROM (SELECT version() AS v) AS foo
        ) AS constants
        GROUP BY 1,2,3,4,5
    ) AS foo
    ) AS rs
    JOIN pg_class cc ON cc.relname = rs.tablename
    JOIN pg_namespace nn ON cc.relnamespace = nn.oid
    AND nn.nspname = rs.schemaname
    AND nn.nspname <> 'information_schema'
) AS sml WHERE {relations};
"""

# The estimated table bloat
TABLE_BLOAT = {
    'descriptors': [('schemaname', 'schema'), ('relname', 'table')],
    'metrics': {
        'tbloat': ('table_bloat', AgentCheck.gauge),
    },
    'query': TABLE_BLOAT_QUERY,
    'relation': True,
    'name': 'table_bloat_metrics',
}


# adapted from https://wiki.postgresql.org/wiki/Show_database_bloat and https://github.com/bucardo/check_postgres/
INDEX_BLOAT_QUERY = """
SELECT
    schemaname, relname, iname,
    ROUND((CASE WHEN iotta=0 OR ipages=0 THEN 0.0 ELSE ipages::float/iotta END)::numeric,1) AS ibloat
FROM (
    SELECT
    schemaname, cc.relname as relname,
    COALESCE(c2.relname,'?') AS iname, COALESCE(c2.reltuples,0) AS ituples, COALESCE(c2.relpages,0) AS ipages,
    COALESCE(CEIL((c2.reltuples*(datahdr-12))/(bs-20::float)),0) AS iotta -- very rough approximation, assumes all cols
    FROM (
    SELECT
        ma,bs,schemaname,tablename,
        (datawidth+(hdr+ma-(case when hdr%ma=0 THEN ma ELSE hdr%ma END)))::numeric AS datahdr,
        (maxfracsum*(nullhdr+ma-(case when nullhdr%ma=0 THEN ma ELSE nullhdr%ma END))) AS nullhdr2
    FROM (
        SELECT
    schemaname, tablename, hdr, ma, bs,
    SUM((1-null_frac)*avg_width) AS datawidth,
    MAX(null_frac) AS maxfracsum,
    hdr+(
        SELECT 1+count(*)/8
        FROM pg_stats s2
        WHERE null_frac<>0 AND s2.schemaname = s.schemaname AND s2.tablename = s.tablename
    ) AS nullhdr
        FROM pg_stats s, (
    SELECT
        (SELECT current_setting('block_size')::numeric) AS bs,
        CASE WHEN substring(v,12,3) IN ('8.0','8.1','8.2') THEN 27 ELSE 23 END AS hdr,
        CASE WHEN v ~ 'mingw32' THEN 8 ELSE 4 END AS ma
    FROM (SELECT version() AS v) AS foo
        ) AS constants
        GROUP BY 1,2,3,4,5
    ) AS foo
    ) AS rs
    JOIN pg_class cc ON cc.relname = rs.tablename
    JOIN pg_namespace nn ON cc.relnamespace = nn.oid
    AND nn.nspname = rs.schemaname
    AND nn.nspname <> 'information_schema'
    LEFT JOIN pg_index i ON indrelid = cc.oid
    LEFT JOIN pg_class c2 ON c2.oid = i.indexrelid
) AS sml WHERE {relations};
"""

# The estimated table bloat
INDEX_BLOAT = {
    'descriptors': [('schemaname', 'schema'), ('relname', 'table'), ('iname', 'index')],
    'metrics': {
        'ibloat': ('index_bloat', AgentCheck.gauge),
    },
    'query': INDEX_BLOAT_QUERY,
    'relation': True,
    'name': 'index_bloat_metrics',
}

RELATION_METRICS = [LOCK_METRICS, IDX_METRICS, STATIO_METRICS]
DYNAMIC_RELATION_QUERIES = [QUERY_PG_CLASS, QUERY_PG_CLASS_SIZE]


class RelationsManager(object):
    """Builds queries to collect metrics about relations"""

    def __init__(self, yamlconfig, max_relations):
        # type: (List[Union[str, Dict]], int) -> None
        self.log = get_check_logger()
        self.config = self._build_relations_config(yamlconfig)
        self.max_relations = max_relations
        self.has_relations = len(self.config) > 0

    def filter_relation_query(self, query, schema_field):
        # type (str, str) -> str
        """Build a WHERE clause filtering relations based on relations_config and applies it to the given query"""
        relations_filter = []
        for r in self.config:
            relation_filter = []
            if r.get(RELATION_NAME):
                relation_filter.append("( relname = '{}'".format(r[RELATION_NAME]))
            elif r.get(RELATION_REGEX):
                relation_filter.append("( relname ~ '{}'".format(r[RELATION_REGEX]))

            if ALL_SCHEMAS not in r[SCHEMAS]:
                schema_filter = ','.join("'{}'".format(s) for s in r[SCHEMAS])
                relation_filter.append('AND {} = ANY(array[{}]::text[])'.format(schema_field, schema_filter))

            # TODO: explicitly declare `relkind` compatiblity in the query rather than implicitly checking query text
            if r.get(RELKIND) and 'FROM pg_locks' in query:
                relkind_filter = ','.join("'{}'".format(s) for s in r[RELKIND])
                relation_filter.append('AND relkind = ANY(array[{}])'.format(relkind_filter))

            relation_filter.append(')')
            relations_filter.append(' '.join(relation_filter))

        relations_filter = '(' + ' OR '.join(relations_filter) + ')'
        limits_filter = 'LIMIT {}'.format(self.max_relations)
        self.log.debug(
            "Running query: %s with relations matching: %s, limits %s", str(query), relations_filter, self.max_relations
        )
        return query.format(relations=relations_filter, limits=limits_filter)

    @staticmethod
    def validate_relations_config(yamlconfig):
        # type: (List[Union[str, Dict]]) -> None
        for element in yamlconfig:
            if isinstance(element, dict):
                if not (RELATION_NAME in element or RELATION_REGEX in element):
                    raise ConfigurationError(
                        "Parameter '%s' or '%s' is required for relation element %s",
                        RELATION_NAME,
                        RELATION_REGEX,
                        element,
                    )
                if RELATION_NAME in element and RELATION_REGEX in element:
                    raise ConfigurationError(
                        "Expecting only of parameters '%s', '%s' for relation element %s",
                        RELATION_NAME,
                        RELATION_REGEX,
                        element,
                    )
                if not isinstance(element.get(SCHEMAS, []), list):
                    raise ConfigurationError("Expected '%s' to be a list for %s", SCHEMAS, element)
                if not isinstance(element.get(RELKIND, []), list):
                    raise ConfigurationError("Expected '%s' to be a list for %s", RELKIND, element)
            elif not isinstance(element, str):
                raise ConfigurationError('Unhandled relations config type: %s', element)

    @staticmethod
    def _build_relations_config(yamlconfig):
        # type:  (List[Union[str, Dict]]) -> List[Dict[str, Any]]
        """Builds a list from relations configuration while maintaining compatibility"""
        relations = []
        for element in yamlconfig:
            config = {}
            if isinstance(element, str):
                config = {RELATION_NAME: element, SCHEMAS: [ALL_SCHEMAS]}
            elif isinstance(element, dict):
                config = element.copy()
                if len(config.get(SCHEMAS, [])) == 0:
                    config[SCHEMAS] = [ALL_SCHEMAS]
            relations.append(config)
        return relations
