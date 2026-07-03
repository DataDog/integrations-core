# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""SAP HANA schema collection for DBM.

Control flow (the base `SchemaCollector.collect_schemas` drives this, see
`datadog_checks.base.utils.db.schemas`):

    _get_databases()  -> the single current tenant, or [] to skip the cycle
    _get_cursor(db)   -> HanaSchemaQueryBuilder builds+runs one catalog query, streams rows
    _get_next(cursor) -> groups consecutive rows by (schema, table) into one object
    _map_row(...)     -> shapes the object into the DBM metadata payload
    maybe_flush(...)  -> emits a payload once enough columns have accumulated

Responsibility split:
  * HanaSchemaQueryBuilder owns all SQL/query-policy decisions (the catalog query, schema
    include/exclude filters, the optional table-statistics join, and the SQL-level caps).
  * HanaSchemaCollector owns runtime concerns (streaming, row grouping, payload flushing).

Collection-policy decisions, all enforced in one query for cost control:
  * Tables and views are capped in SQL (`LIMIT max_tables` / `LIMIT max_views`) so an oversized
    tenant never streams more objects than configured. Tables and views are capped
    independently rather than sharing one budget.
  * Columns are capped in SQL via a `ROW_NUMBER()` window (`rn <= max_columns`) so the server
    sends at most `max_columns` rows per object; `_get_next` re-applies the same cap as a
    defensive client-side guard.
  * System schemas (`SYS`, `SYSTEM`, `PUBLIC`, and `_SYS_*`) are always excluded; visibility
    is otherwise governed by the catalog-view grants the monitoring user holds, not by
    per-object privileges.
  * The `SYS.M_TABLE_STATISTICS` join (row counts + last-modified time) is added only when a
    one-time permission probe succeeds, so a missing grant degrades gracefully.

Payloads flush by accumulated column count rather than the base class's per-table count; see
`PAYLOAD_COLUMN_CHUNK_SIZE` below and the memory benchmark in
`sap_hana/benchmarks/schema_collection_memory/` for the rationale and measured impact.
"""

from __future__ import annotations

import contextlib
from contextlib import closing
from typing import TYPE_CHECKING

from datadog_checks.base.utils.db.schemas import DatabaseInfo, SchemaCollector, SchemaCollectorConfig

if TYPE_CHECKING:
    from .config_models.instance import CollectSchemas
    from .sap_hana import SapHanaCheck

# Flush a schema payload once this many columns have accumulated. The base SchemaCollector
# chunks payloads by table count (`payload_chunk_size`, default 10,000 tables), but a HANA
# tenant is a single "database", so that threshold rarely trips: every table for the tenant
# stays resident and is emitted as one large `json.dumps`. Chunking by accumulated column
# count instead bounds payload size and peak memory regardless of how wide the tables are.
# The memory benchmark in `sap_hana/benchmarks/schema_collection_memory/` shows the impact:
# collecting 1000 tables x 1000 columns with limits disabled produced 21 payloads (~95 MB,
# ~94 MiB peak RSS), while the limited run emitted 1 payload (~1.8 MB, ~61 MiB peak RSS).
PAYLOAD_COLUMN_CHUNK_SIZE = 50_000

CURRENT_DATABASE_QUERY = "SELECT DATABASE_NAME FROM SYS.M_DATABASE"
CURRENT_DATABASE_DESCRIPTION_QUERY = "SELECT DESCRIPTION FROM SYS.M_DATABASE"

STATS_PERMISSION_PROBE = "SELECT COUNT(*) FROM SYS.M_TABLE_STATISTICS"

# Fragment conditionally inserted when the monitoring user has SELECT on SYS.M_TABLE_STATISTICS.
STATS_JOIN_FRAGMENT = """\
    LEFT JOIN SYS.M_TABLE_STATISTICS ts
      ON ts.SCHEMA_NAME = t.SCHEMA_NAME AND ts.TABLE_NAME = t.TABLE_NAME"""

# Queries SYS.M_TABLES (tables with live row counts) and SYS.VIEWS separately, then unions them.
# Table columns come from SYS.TABLE_COLUMNS; view columns from SYS.VIEW_COLUMNS (TABLE_COLUMNS
# does not cover views in HANA). System schemas are excluded; '_SYS_' uses ESCAPE because '_' is
# a LIKE wildcard. Placeholders:
#   {stats_join}      STATS_JOIN_FRAGMENT or empty string
#   {stats_column}    ts.LAST_MODIFY_TIME AS LAST_UPDATED_ON  or  NULL AS LAST_UPDATED_ON
#   {include_clause}  AND t.SCHEMA_NAME IN (...)  or empty
#   {exclude_clause}  AND t.SCHEMA_NAME NOT IN (...)  or empty
#   {include_clause_v} / {exclude_clause_v}  same filters for v.SCHEMA_NAME
# SELECT column order: SCHEMA_NAME[0] TABLE_NAME[1] OBJECT_TYPE[2] IS_COLUMN_TABLE[3]
#   SCHEMA_OWNER[4] ROW_COUNT[5] LAST_UPDATED_ON[6]
#   COLUMN_NAME[7] DATA_TYPE_NAME[8] IS_NULLABLE[9] DEFAULT_VALUE[10] POSITION[11]
SCHEMA_OBJECTS_QUERY = r"""
WITH limited_tables AS (
    SELECT t.SCHEMA_NAME, t.TABLE_NAME,
           'TABLE' AS OBJECT_TYPE,
           CASE WHEN t.TABLE_TYPE = 'COLUMN' THEN 'TRUE' ELSE 'FALSE' END AS IS_COLUMN_TABLE,
           s.SCHEMA_OWNER,
           CAST(t.RECORD_COUNT AS BIGINT) AS ROW_COUNT,
           {stats_column}
    FROM SYS.M_TABLES t
    LEFT JOIN SYS.SCHEMAS s ON s.SCHEMA_NAME = t.SCHEMA_NAME
    {stats_join}
    WHERE t.TABLE_TYPE NOT LIKE '%TEMPORARY%'
      AND t.SCHEMA_NAME NOT IN ('SYS', 'SYSTEM', 'PUBLIC')
      AND t.SCHEMA_NAME NOT LIKE '\_SYS\_%' ESCAPE '\'
      {include_clause}
      {exclude_clause}
    ORDER BY t.SCHEMA_NAME, t.TABLE_NAME
    LIMIT {max_tables}
),
limited_views AS (
    SELECT v.SCHEMA_NAME, v.VIEW_NAME AS TABLE_NAME,
           'VIEW' AS OBJECT_TYPE,
           NULL AS IS_COLUMN_TABLE,
           s.SCHEMA_OWNER,
           NULL AS ROW_COUNT,
           NULL AS LAST_UPDATED_ON
    FROM SYS.VIEWS v
    LEFT JOIN SYS.SCHEMAS s ON s.SCHEMA_NAME = v.SCHEMA_NAME
    WHERE v.SCHEMA_NAME NOT IN ('SYS', 'SYSTEM', 'PUBLIC')
      AND v.SCHEMA_NAME NOT LIKE '\_SYS\_%' ESCAPE '\'
      {include_clause_v}
      {exclude_clause_v}
    ORDER BY v.SCHEMA_NAME, v.VIEW_NAME
    LIMIT {max_views}
),
all_objects AS (
    SELECT * FROM limited_tables
    UNION ALL
    SELECT * FROM limited_views
),
limited_columns AS (
    SELECT c.SCHEMA_NAME, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE_NAME,
           c.IS_NULLABLE, c.DEFAULT_VALUE, c.POSITION,
           ROW_NUMBER() OVER (PARTITION BY c.SCHEMA_NAME, c.TABLE_NAME ORDER BY c.POSITION) AS rn
    FROM SYS.TABLE_COLUMNS c
    INNER JOIN limited_tables lt ON lt.SCHEMA_NAME = c.SCHEMA_NAME AND lt.TABLE_NAME = c.TABLE_NAME
),
limited_view_columns AS (
    SELECT c.SCHEMA_NAME, c.VIEW_NAME AS TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE_NAME,
           c.IS_NULLABLE, c.DEFAULT_VALUE, c.POSITION,
           ROW_NUMBER() OVER (PARTITION BY c.SCHEMA_NAME, c.VIEW_NAME ORDER BY c.POSITION) AS rn
    FROM SYS.VIEW_COLUMNS c
    INNER JOIN limited_views lv ON lv.SCHEMA_NAME = c.SCHEMA_NAME AND lv.TABLE_NAME = c.VIEW_NAME
),
all_columns AS (
    SELECT * FROM limited_columns
    UNION ALL
    SELECT * FROM limited_view_columns
)
SELECT ao.SCHEMA_NAME, ao.TABLE_NAME, ao.OBJECT_TYPE, ao.IS_COLUMN_TABLE, ao.SCHEMA_OWNER,
       ao.ROW_COUNT, ao.LAST_UPDATED_ON,
       ac.COLUMN_NAME, ac.DATA_TYPE_NAME, ac.IS_NULLABLE, ac.DEFAULT_VALUE, ac.POSITION
FROM all_objects ao
LEFT JOIN all_columns ac
  ON ac.SCHEMA_NAME = ao.SCHEMA_NAME AND ac.TABLE_NAME = ao.TABLE_NAME
  AND ac.rn <= {max_columns}
ORDER BY ao.SCHEMA_NAME, ao.TABLE_NAME, ac.POSITION
"""


class HanaSchemaCollectorConfig(SchemaCollectorConfig):
    def __init__(self, config: CollectSchemas):
        super().__init__()
        self.collection_interval = int(config.collection_interval or 600)
        self.max_tables = int(config.max_tables or 2000)
        self.max_views = int(config.max_views or 2000)
        self.max_columns = int(config.max_columns or 500)
        self.exclude_schemas = set(config.exclude_schemas or ())
        self.include_schemas = set(config.include_schemas or ())
        self.payload_column_chunk_size = PAYLOAD_COLUMN_CHUNK_SIZE


class HanaSchemaQueryBuilder:
    """Builds the catalog query that collects schema metadata in SQL.

    Owns the query-policy decisions: schema include/exclude filters, the optional table
    statistics join, and the SQL-level table/view/column caps. The collector delegates here so
    that runtime concerns (streaming, row grouping, payload flushing) stay separate.
    """

    def __init__(self, config: HanaSchemaCollectorConfig, log):
        self._config = config
        self._log = log
        self._has_table_statistics: bool | None = None

    def ensure_stats_permission(self, conn) -> None:
        """Probe SELECT access to SYS.M_TABLE_STATISTICS once and cache the result."""
        if self._has_table_statistics is not None:
            return
        try:
            with closing(conn.cursor()) as cur:
                cur.execute(STATS_PERMISSION_PROBE)
                cur.fetchone()
            self._has_table_statistics = True
        except Exception as e:
            self._log.debug("SYS.M_TABLE_STATISTICS not accessible, skipping stats join: %s", e)
            self._has_table_statistics = False

    def build(self) -> tuple[str, tuple]:
        """Return the catalog query and its bind parameters."""
        include_clause, include_clause_v, include_params = self._schema_clause('IN', self._config.include_schemas)
        exclude_clause, exclude_clause_v, exclude_params = self._schema_clause('NOT IN', self._config.exclude_schemas)
        # Both limited_tables and limited_views CTEs carry the same ?-placeholders, so params repeat.
        params = include_params + exclude_params + include_params + exclude_params
        if self._has_table_statistics:
            stats_join = STATS_JOIN_FRAGMENT
            stats_column = 'ts.LAST_MODIFY_TIME AS LAST_UPDATED_ON'
        else:
            stats_join = ''
            stats_column = 'NULL AS LAST_UPDATED_ON'
        query = SCHEMA_OBJECTS_QUERY.format(
            include_clause=include_clause,
            exclude_clause=exclude_clause,
            include_clause_v=include_clause_v,
            exclude_clause_v=exclude_clause_v,
            stats_join=stats_join,
            stats_column=stats_column,
            max_tables=int(self._config.max_tables),
            max_views=int(self._config.max_views),
            max_columns=int(self._config.max_columns),
        )
        return query, tuple(params)

    @staticmethod
    def _schema_clause(operator: str, schemas):
        """Build matching SCHEMA_NAME filters for the tables (t) and views (v) CTEs."""
        if not schemas:
            return '', '', []
        names = sorted(schemas)
        placeholders = ', '.join('?' for _ in names)
        table_clause = 'AND t.SCHEMA_NAME {} ({})'.format(operator, placeholders)
        view_clause = 'AND v.SCHEMA_NAME {} ({})'.format(operator, placeholders)
        return table_clause, view_clause, names


class HanaSchemaCollector(SchemaCollector):
    _check: SapHanaCheck
    _config: HanaSchemaCollectorConfig

    def __init__(self, check: SapHanaCheck, config: CollectSchemas):
        super().__init__(check, HanaSchemaCollectorConfig(config))
        self._query_builder = HanaSchemaQueryBuilder(self._config, self._log)
        self._pending_row = None

    def _reset(self) -> None:
        super()._reset()
        self._queued_column_count = 0

    def maybe_flush(self, is_last_payload: bool) -> None:
        if self._queued_column_count >= self._config.payload_column_chunk_size:
            saved = self._config.payload_chunk_size
            self._config.payload_chunk_size = 0
            super().maybe_flush(is_last_payload)
            self._config.payload_chunk_size = saved
            self._queued_column_count = 0
        else:
            super().maybe_flush(is_last_payload)

    @property
    def kind(self) -> str:
        return "saphana_databases"

    def _get_databases(self) -> list[DatabaseInfo]:
        try:
            with closing(self._check._conn.cursor()) as cursor:
                cursor.execute(CURRENT_DATABASE_QUERY)
                row = cursor.fetchone()
                if not row:
                    self._log.warning("SYS.M_DATABASE returned no rows; skipping schema collection")
                    return []
                db_name = row[0]
                description = ''
                try:
                    cursor.execute(CURRENT_DATABASE_DESCRIPTION_QUERY)
                    desc_row = cursor.fetchone()
                    if desc_row:
                        description = desc_row[0] or ''
                except Exception:
                    pass
                return [{'name': db_name, 'description': description}]
        except Exception as e:
            self._log.warning("Could not determine current HANA database; skipping schema collection: %s", e)
            return []

    @contextlib.contextmanager
    def _get_cursor(self, _database_name):
        conn = self._check._conn
        self._query_builder.ensure_stats_permission(conn)
        query, params = self._query_builder.build()
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, params)
            self._pending_row = cursor.fetchone()
            try:
                yield cursor
            finally:
                self._pending_row = None

    def _get_next(self, cursor):
        """Assemble one table/view from consecutive cursor rows sharing the same (schema, table) key."""
        row = self._pending_row
        if row is None:
            return None
        schema_name, table_name = row[0], row[1]
        table_type, is_column_table, schema_owner = row[2], row[3], row[4]
        row_count, last_updated_on = row[5], row[6]
        columns = []
        while row is not None and row[0] == schema_name and row[1] == table_name:
            column_name = row[7]
            if column_name is not None and len(columns) < self._config.max_columns:
                columns.append(
                    {
                        'name': column_name,
                        'data_type': row[8] or '',
                        'nullable': row[9] == 'TRUE',
                        'default': row[10],
                        'position': row[11],
                    }
                )
            row = cursor.fetchone()
        self._pending_row = row
        return {
            'schema_name': schema_name,
            'schema_owner': schema_owner or '',
            'table_name': table_name,
            'table_type': table_type or '',
            'is_column_table': is_column_table == 'TRUE',
            'row_count': row_count,
            'last_updated_on': last_updated_on,
            'columns': columns,
        }

    def _map_row(self, database: DatabaseInfo, table_row) -> dict:
        self._queued_column_count += len(table_row['columns'])
        last_updated_on = table_row['last_updated_on']
        return {
            **database,
            'schemas': [
                {
                    'name': table_row['schema_name'],
                    'owner': table_row['schema_owner'],
                    'tables': [
                        {
                            'name': table_row['table_name'],
                            'type': table_row['table_type'],
                            'is_column_table': table_row['is_column_table'],
                            'row_count': table_row['row_count'],
                            'last_updated_on': str(last_updated_on) if last_updated_on is not None else None,
                            'columns': table_row['columns'],
                        }
                    ],
                }
            ],
        }
