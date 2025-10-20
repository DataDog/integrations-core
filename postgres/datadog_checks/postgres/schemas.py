# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypedDict

import orjson as json
from psycopg.rows import dict_row

if TYPE_CHECKING:
    from datadog_checks.base import AgentCheck
    from datadog_checks.postgres import PostgreSql

from datadog_checks.postgres.version_utils import VersionUtils

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


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


class SchemaCollector(ABC):
    def __init__(self, check: AgentCheck):
        self._check = check
        self._log = check.log
        self._config = check._config.collect_schemas

        self._reset()

    def _reset(self):
        self._collection_started_at = None
        self._collection_payloads_count = 0
        self._queued_rows = []
        self._total_rows_count = 0

    def collect_schemas(self) -> bool:
        """
        Collects and submits all applicable schema metadata to the agent.
        Returns False if the previous collection was still in progress.
        """
        if self._collection_started_at is not None:
            return False
        status = "success"
        try:
            self._collection_started_at = int(time.time() * 1000)
            databases = self._get_databases()
            for database in databases:
                database_name = database['name']
                if not database_name:
                    self._check.log("database has no name %v", database)
                    continue
                with self._get_cursor(database_name) as cursor:
                    next = self._get_next(cursor)
                    while next:
                        self._queued_rows.append(self._map_row(database, next))
                        self._total_rows_count += 1
                        next = self._get_next(cursor)
                        is_last_payload = database is databases[-1] and next is None
                        self.maybe_flush(is_last_payload)

        except Exception as e:
            status = "error"
            self._log.error("Error collecting schema metadata: %s", e)
            raise e
        finally:
            self._check.histogram(
                "dd.postgres.schema.time",
                int(time.time() * 1000) - self._collection_started_at,
                tags=self._check.tags + ["status:" + status],
                hostname=self._check.reported_hostname,
                raw=True,
            )
            self._check.gauge(
                "dd.postgres.schema.tables_count",
                self._total_rows_count,
                tags=self._check.tags + ["status:" + status],
                hostname=self._check.reported_hostname,
                raw=True,
            )

            self._reset()
        return True

    @property
    def base_event(self):
        return {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "agent_version": datadog_agent.get_version(),
            "collection_interval": self._config.collection_interval,
            "dbms_version": str(self._check.version),
            "tags": self._check.tags,
            "cloud_metadata": self._check.cloud_metadata,
            "collection_started_at": self._collection_started_at,
        }

    def maybe_flush(self, is_last_payload):
        if len(self._queued_rows) > 10 or is_last_payload:
            event = self.base_event.copy()
            event['timestamp'] = int(time.time() * 1000)
            event["metadata"] = self._queued_rows
            self._collection_payloads_count += 1
            if is_last_payload:
                event["collection_payloads_count"] = self._collection_payloads_count
            self._check.database_monitoring_metadata(json.dumps(event))

            self._queued_rows = []

    @abstractmethod
    def _get_databases(self) -> list[DatabaseInfo]:
        pass

    @abstractmethod
    def _get_cursor(self, database):
        pass

    @abstractmethod
    def _get_next(self, cursor):
        pass

    @abstractmethod
    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        """
        Maps a cursor row to a dict that matches the schema expected by DBM.
        """
        return {
            **database,
        }


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
GROUP BY inhparent;
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
SELECT db.oid                        AS id,
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


class PostgresSchemaCollector(SchemaCollector):
    def __init__(self, check: PostgreSql):
        super().__init__(check)
        self._check = check

    @property
    def base_event(self):
        return {
            **super().base_event,
            "dbms": "postgres",
            "kind": "pg_databases",
        }

    def _get_databases(self):
        with self._check._get_main_db() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                query = DATABASE_INFORMATION_QUERY
                for exclude_regex in self._config.exclude_databases:
                    query += " AND datname !~ '{}'".format(exclude_regex)
                if self._config.include_databases:
                    query += f" AND ({' OR '.join(f"datname ~ '{include_regex}'" for include_regex in self._config.include_databases)})"

                # Autodiscovery trumps exclude and include
                autodiscovery_databases = self._check.autodiscovery.get_items()
                if autodiscovery_databases:
                    query += " AND datname IN ({})".format(", ".join(f"'{db}'" for db in autodiscovery_databases))

                cursor.execute(query)
                return cursor.fetchall()

    @contextlib.contextmanager
    def _get_cursor(self, database_name):
        with self._check.db_pool.get_connection(database_name) as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                schemas_query = self._get_schemas_query()
                tables_query = self._get_tables_query()
                columns_query = COLUMNS_QUERY
                indexes_query = PG_INDEXES_QUERY
                constraints_query = PG_CONSTRAINTS_QUERY
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
                    if VersionUtils.transform_version(str(self._check.version))["version.major"] > "9"
                    else ""
                )
                partition_joins = (
                    """
                    LEFT JOIN partition_keys ON tables.table_id = partition_keys.table_id
                    LEFT JOIN num_partitions ON tables.table_id = num_partitions.table_id
                """
                    if VersionUtils.transform_version(str(self._check.version))["version.major"] > "9"
                    else ""
                )
                parition_selects = (
                    """
                ,
                    partition_keys.partition_key,
                    num_partitions.num_partitions
                """
                    if VersionUtils.transform_version(str(self._check.version))["version.major"] > "9"
                    else ""
                )

                limit = self._config.max_tables or 1_000_000
                query = f"""
                    WITH
                    schemas AS(
                        {schemas_query}
                    ),
                    tables AS (
                        {tables_query}
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

                    SELECT schemas.schema_id, schemas.schema_name,
                        tables.table_id, tables.table_name,
                        array_agg(row_to_json(columns.*)) FILTER (WHERE columns.name IS NOT NULL) as columns,
                        array_agg(row_to_json(indexes.*)) FILTER (WHERE indexes.name IS NOT NULL) as indexes,
                        array_agg(row_to_json(constraints.*)) FILTER (WHERE constraints.name IS NOT NULL)
                          as foreign_keys
                        {parition_selects}
                    FROM schemas
                        LEFT JOIN tables ON schemas.schema_id = tables.schema_id
                        LEFT JOIN columns ON tables.table_id = columns.table_id
                        LEFT JOIN indexes ON tables.table_id = indexes.table_id
                        LEFT JOIN constraints ON tables.table_id = constraints.table_id
                        {partition_joins}
                    GROUP BY schemas.schema_id, schemas.schema_name, tables.table_id, tables.table_name
                    LIMIT {limit}
                    ;
                """
                # print(query)
                cursor.execute(query)
                yield cursor

    def _get_schemas_query(self):
        query = SCHEMA_QUERY
        for exclude_regex in self._config.exclude_schemas:
            query += " AND nspname !~ '{}'".format(exclude_regex)
        if self._config.include_schemas:
            query += f" AND ({' OR '.join(f"nspname ~ '{include_regex}'" for include_regex in self._config.include_schemas)})"            
        if self._check._config.ignore_schemas_owned_by:
            query += " AND nspowner :: regrole :: text not IN ({})".format(
                ", ".join(f"'{owner}'" for owner in self._check._config.ignore_schemas_owned_by)
            )
        return query

    def _get_tables_query(self):
        if VersionUtils.transform_version(str(self._check.version))["version.major"] == "9":
            query = PG_TABLES_QUERY_V9
        else:
            query = PG_TABLES_QUERY_V10_PLUS
        for exclude_regex in self._config.exclude_tables:
            query += " AND c.relname !~ '{}'".format(exclude_regex)
        if self._config.include_tables:
            query += f" AND ({' OR '.join(f"c.relname ~ '{include_regex}'" for include_regex in self._config.include_tables)})"
        return query

    def _get_next(self, cursor):
        return cursor.fetchone()

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
                                "columns": list({v and v['name']: v for v in cursor_row.get("columns") or []}.values()),
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
