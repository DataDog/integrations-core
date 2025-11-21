# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, TypedDict

from psycopg.rows import dict_row

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig
from datadog_checks.postgres.version_utils import V10, V11, VersionUtils


class DatabaseInfo(TypedDict):
    description: str
    name: str
    id: str
    encoding: str
    owner: str


# The schema collector sends lists of DatabaseObjects to the agent
# The format is for backwards compatibility with the current backend
class DatabaseObject(TypedDict):
    # Splat of database info
    description: str
    name: str
    id: str
    encoding: str
    owner: str


PG_TABLES_QUERY_V10_PLUS = """
SELECT c.oid                 AS table_id,
       c.relnamespace        AS schema_id,
       c.relname             AS table_name,
       c.relhasindex         AS has_indexes,
       c.relowner :: regrole AS owner,
       ( CASE
           WHEN c.relkind = 'p' THEN TRUE
           ELSE FALSE
         END )               AS has_partitions,
       t.relname             AS toast_table
FROM   pg_class c
       left join pg_class t
              ON c.reltoastrelid = t.oid
WHERE  c.relkind IN ( 'r', 'p', 'f' )
       AND c.relispartition != 't'
"""

PG_TABLES_QUERY_V9 = """
SELECT c.oid                 AS table_id,
       c.relnamespace        AS schema_id,
       c.relname             AS table_name,
       c.relhasindex         AS has_indexes,
       c.relowner :: regrole AS owner,
       t.relname             AS toast_table
FROM   pg_class c
       left join pg_class t
              ON c.reltoastrelid = t.oid
WHERE  c.relkind IN ( 'r', 'f' )
"""


SCHEMA_QUERY = """
SELECT nsp.oid                 AS schema_id,
       nspname             AS schema_name,
       nspowner :: regrole AS schema_owner
FROM   pg_namespace nsp
       LEFT JOIN pg_roles r on nsp.nspowner = r.oid
WHERE  nspname NOT IN ( 'information_schema', 'pg_catalog' )
       AND nspname NOT LIKE 'pg_toast%'
       AND nspname NOT LIKE 'pg_temp_%'
"""

COLUMNS_QUERY = """
SELECT attname                          AS name,
       Format_type(atttypid, atttypmod) AS data_type,
       NOT attnotnull                   AS nullable,
       pg_get_expr(adbin, adrelid)      AS default,
       attrelid AS table_id
FROM   pg_attribute
       LEFT JOIN pg_attrdef ad
              ON adrelid = attrelid
                 AND adnum = attnum
WHERE  attnum > 0
       AND NOT attisdropped
"""


PG_INDEXES_QUERY = """
SELECT
    c.relname AS name,
    ix.indrelid AS table_id,
    pg_get_indexdef(c.oid) AS definition,
    ix.indisunique AS is_unique,
    ix.indisexclusion AS is_exclusion,
    ix.indimmediate AS is_immediate,
    ix.indisclustered AS is_clustered,
    ix.indisvalid AS is_valid,
    ix.indcheckxmin AS is_checkxmin,
    ix.indisready AS is_ready,
    ix.indislive AS is_live,
    ix.indisreplident AS is_replident,
    ix.indpred IS NOT NULL AS is_partial
FROM
    pg_index ix
JOIN
    pg_class c
ON
    c.oid = ix.indexrelid
"""


PG_CONSTRAINTS_QUERY = """
SELECT conname                   AS name,
       pg_get_constraintdef(oid) AS definition,
       conrelid AS table_id
FROM   pg_constraint
WHERE  contype = 'f'
"""


PARTITION_KEY_QUERY = """
SELECT relname,
       pg_get_partkeydef(oid) AS partition_key,
       oid AS table_id
FROM   pg_class
"""

NUM_PARTITIONS_QUERY = """
SELECT count(inhrelid :: regclass) AS num_partitions, inhparent as table_id
FROM   pg_inherits
GROUP BY inhparent
"""

PARTITION_ACTIVITY_QUERY = """
SELECT pi.inhparent :: regclass         AS parent_table_name,
       SUM(COALESCE(psu.seq_scan, 0) + COALESCE(psu.idx_scan, 0)) AS total_activity,
       pi.inhparent as table_id
FROM   pg_catalog.pg_stat_user_tables psu
       join pg_class pc
         ON psu.relname = pc.relname
       join pg_inherits pi
         ON pi.inhrelid = pc.oid
GROUP BY pi.inhparent
"""


class TableObject(TypedDict):
    id: str
    name: str
    columns: list
    indexes: list
    foreign_keys: list


class SchemaObject(TypedDict):
    id: str
    name: str
    owner: str
    tables: list[TableObject]


class PostgresDatabaseObject(DatabaseObject):
    schemas: list[SchemaObject]


DATABASE_INFORMATION_QUERY = """
SELECT db.oid::text                  AS id,
       datname                       AS NAME,
       pg_encoding_to_char(encoding) AS encoding,
       rolname                       AS owner,
       description
FROM   pg_catalog.pg_database db
       LEFT JOIN pg_catalog.pg_description dc
              ON dc.objoid = db.oid
       JOIN pg_roles a
         ON datdba = a.oid
        WHERE datname NOT LIKE 'template%'
"""


class PostgresSchemaCollectorConfig(SchemaCollectorConfig):
    max_tables: int
    exclude_databases: list[str]
    include_databases: list[str]
    exclude_schemas: list[str]
    include_schemas: list[str]
    exclude_tables: list[str]
    include_tables: list[str]
    max_columns: int
    max_query_duration: int


class PostgresSchemaCollector(SchemaCollector):
    _check: PostgreSql
    _config: PostgresSchemaCollectorConfig

    def __init__(self, check: PostgreSql):
        config = PostgresSchemaCollectorConfig()
        config.collection_interval = check._config.collect_schemas.collection_interval
        config.max_tables = check._config.collect_schemas.max_tables
        config.exclude_databases = check._config.collect_schemas.exclude_databases
        config.include_databases = check._config.collect_schemas.include_databases
        config.exclude_schemas = check._config.collect_schemas.exclude_schemas
        config.include_schemas = check._config.collect_schemas.include_schemas
        config.exclude_tables = check._config.collect_schemas.exclude_tables
        config.include_tables = check._config.collect_schemas.include_tables
        config.max_columns = int(check._config.collect_schemas.max_columns)
        config.max_query_duration = int(check._config.collect_schemas.max_query_duration)
        super().__init__(check, config)

    @property
    def kind(self):
        return "pg_databases"

    def _get_databases(self):
        with self._check._get_main_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                query = DATABASE_INFORMATION_QUERY
                for exclude_regex in self._config.exclude_databases:
                    query += " AND datname !~ '{}'".format(exclude_regex)
                if self._config.include_databases:
                    query += f" AND ({
                        ' OR '.join(f"datname ~ '{include_regex}'" for include_regex in self._config.include_databases)
                    })"

                # Autodiscovery trumps exclude and include
                if self._check.autodiscovery:
                    autodiscovery_databases = self._check.autodiscovery.get_items()
                    if autodiscovery_databases:
                        query += " AND datname IN ({})".format(", ".join(f"'{db}'" for db in autodiscovery_databases))

                cursor.execute(query)
                return cursor.fetchall()

    @contextlib.contextmanager
    def _get_cursor(self, database_name):
        with self._check.db_pool.get_connection(database_name) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                query = self.get_rows_query()
                cursor.execute(f"SET statement_timeout = '{self._config.max_query_duration}s';")
                cursor.execute(query)
                yield cursor

    def _get_schemas_query(self):
        query = SCHEMA_QUERY
        for exclude_regex in self._config.exclude_schemas:
            query += " AND nspname !~ '{}'".format(exclude_regex)
        if self._config.include_schemas:
            query += f" AND ({
                ' OR '.join(f"nspname ~ '{include_regex}'" for include_regex in self._config.include_schemas)
            })"
        if self._check._config.ignore_schemas_owned_by:
            query += " AND nspowner :: regrole :: text not IN ({})".format(
                ", ".join(f"'{owner}'" for owner in self._check._config.ignore_schemas_owned_by)
            )
        return query

    def _get_tables_query(self):
        if VersionUtils.parse_version(str(self._check.version)) < V10:
            query = PG_TABLES_QUERY_V9
        else:
            query = PG_TABLES_QUERY_V10_PLUS
        for exclude_regex in self._config.exclude_tables:
            query += " AND c.relname !~ '{}'".format(exclude_regex)
        if self._config.include_tables:
            query += f" AND ({
                ' OR '.join(f"c.relname ~ '{include_regex}'" for include_regex in self._config.include_tables)
            })"
        return query

    def get_rows_query(self):
        schemas_query = self._get_schemas_query()
        tables_query = self._get_tables_query()
        columns_query = COLUMNS_QUERY
        indexes_query = PG_INDEXES_QUERY
        constraints_query = PG_CONSTRAINTS_QUERY
        is_at_least_11 = VersionUtils.parse_version(str(self._check.version)) >= V11
        partitions_ctes = (
            f"""
            ,
            partition_keys AS (
                {PARTITION_KEY_QUERY}
            ),
            num_partitions AS (
                {NUM_PARTITIONS_QUERY}
            )
        """
            if is_at_least_11
            else ""
        )
        partition_joins = (
            """
            LEFT JOIN partition_keys ON schema_tables.table_id = partition_keys.table_id
            LEFT JOIN num_partitions ON schema_tables.table_id = num_partitions.table_id
        """
            if is_at_least_11
            else ""
        )
        # There should only ever by one partition key and one partition count
        # so we can use the array_agg to get the first element and avoid complicating
        # the group by
        parition_selects = (
            """
        ,
            (array_agg(partition_keys.partition_key))[1] partition_key,
            (array_agg(num_partitions.num_partitions))[1] num_partitions
        """
            if is_at_least_11
            else ""
        )
        limit = int(self._config.max_tables or 1_000_000)

        query = f"""
            WITH
            schemas AS(
                {schemas_query}
            ),
            tables AS (
                {tables_query}
            ),
            schema_tables AS (
                SELECT schemas.schema_id, schemas.schema_name,
                tables.table_id, tables.table_name
                FROM schemas
                LEFT JOIN tables ON schemas.schema_id = tables.schema_id
                ORDER BY schemas.schema_name, tables.table_name
                LIMIT {limit}
            ),
            columns AS (
                {columns_query}
            ),
            indexes AS (
                {indexes_query}
            ),
            constraints AS (
                {constraints_query}
            )
            {partitions_ctes}

            SELECT schema_tables.schema_id, schema_tables.schema_name,
            schema_tables.table_id, schema_tables.table_name,
                array_agg(row_to_json(columns.*)) FILTER (WHERE columns.name IS NOT NULL) as columns,
                array_agg(row_to_json(indexes.*)) FILTER (WHERE indexes.name IS NOT NULL) as indexes,
                array_agg(row_to_json(constraints.*)) FILTER (WHERE constraints.name IS NOT NULL)
                    as foreign_keys
                {parition_selects}
            FROM schema_tables
                LEFT JOIN columns ON schema_tables.table_id = columns.table_id
                LEFT JOIN indexes ON schema_tables.table_id = indexes.table_id
                LEFT JOIN constraints ON schema_tables.table_id = constraints.table_id
                {partition_joins}
            GROUP BY schema_tables.schema_id, schema_tables.schema_name,
                schema_tables.table_id, schema_tables.table_name
            ;
        """

        return query

    def _get_next(self, cursor):
        return cursor.fetchone()

    def _get_all(self, cursor):
        return cursor.fetchall()

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        object = super()._map_row(database, cursor_row)
        # Map the cursor row to the expected schema, and strip out None values
        object["schemas"] = [
            {
                k: v
                for k, v in {
                    "id": str(cursor_row.get("schema_id")),
                    "name": cursor_row.get("schema_name"),
                    "owner": cursor_row.get("schema_owner"),
                    "tables": [
                        {
                            k: v
                            for k, v in {
                                "id": str(cursor_row.get("table_id")),
                                "name": cursor_row.get("table_name"),
                                "owner": cursor_row.get("owner"),
                                # The query can create duplicates of the joined tables
                                "columns": list({v and v['name']: v for v in cursor_row.get("columns") or []}.values())[
                                    : self._config.max_columns
                                ],
                                "indexes": list({v and v['name']: v for v in cursor_row.get("indexes") or []}.values()),
                                "foreign_keys": list(
                                    {v and v['name']: v for v in cursor_row.get("foreign_keys") or []}.values()
                                ),
                                "toast_table": cursor_row.get("toast_table"),
                                "num_partitions": cursor_row.get("num_partitions"),
                                "partition_key": cursor_row.get("partition_key"),
                            }.items()
                            if v is not None
                        }
                    ],
                }.items()
                if v is not None
            }
        ]
        return object
