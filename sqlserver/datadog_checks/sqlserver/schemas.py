# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, TypedDict

from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.utils import execute_query

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig
from datadog_checks.sqlserver.const import (
    DEFAULT_SCHEMAS_COLLECTION_INTERVAL,
    STATIC_INFO_MAJOR_VERSION,
    SWITCH_DB_STATEMENT,
)
from datadog_checks.sqlserver.queries import (
    COLUMN_QUERY,
    DB_QUERY,
    FOREIGN_KEY_QUERY,
    FOREIGN_KEY_QUERY_PRE_2017,
    INDEX_QUERY,
    INDEX_QUERY_PRE_2017,
    PARTITIONS_QUERY,
    SCHEMA_QUERY,
    TABLES_QUERY,
)


class DatabaseInfo(TypedDict):
    name: str
    id: str
    collation: str
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


class TableObject(TypedDict):
    id: str
    name: str
    columns: list
    indexes: list
    foreign_keys: list


class SchemaObject(TypedDict):
    name: str
    id: str
    owner: str
    tables: list[TableObject]


class SQLServerDatabaseObject(DatabaseObject):
    schemas: list[SchemaObject]


class SQLServerSchemaCollector(SchemaCollector):
    _check: SQLServer

    def __init__(self, check: SQLServer):
        config = SchemaCollectorConfig()
        config.collection_interval = check._config.schema_config.get(
            "collection_interval", DEFAULT_SCHEMAS_COLLECTION_INTERVAL
        )
        config.max_tables = check._config.schema_config.get('max_tables', 300)
        major_version = int(check.static_info_cache.get(STATIC_INFO_MAJOR_VERSION) or 0)
        self._is_2016_or_earlier = major_version <= 13
        super().__init__(check, config)

    @property
    def kind(self):
        return "sqlserver_databases"

    def _get_databases(self):
        database_names = self._check.get_databases()
        with self._check.connection.open_managed_default_connection():
            with self._check.connection.get_managed_cursor() as cursor:
                db_names_formatted = ",".join(["'{}'".format(t) for t in database_names])
                return execute_query(DB_QUERY.format(db_names_formatted), cursor, convert_results_to_str=True)

    @contextlib.contextmanager
    def _get_cursor(self, database_name):
        with self._check.connection.open_managed_default_connection():
            with self._check.connection.get_managed_cursor() as cursor:
                cursor.execute(SWITCH_DB_STATEMENT.format(database_name))
                query = self._get_tables_query()
                # print(query)
                cursor.execute(query)
                yield cursor

    def _get_tables_query(self):
        limit = int(self._config.max_tables or 1_000_000)

        # Note that we INNER JOIN tables to omit schemas with no tables
        # This is a simple way to omit the system tables like db_blah
        query = f"""
            WITH
            schemas AS (
                {SCHEMA_QUERY}
            ),
            tables AS (
                {TABLES_QUERY}
            ),
            schema_tables AS (
                SELECT TOP {limit} schemas.schema_name, schemas.schema_id, schemas.owner_name,
                tables.table_id, tables.table_name
                FROM schemas
                INNER JOIN tables ON schemas.schema_id = tables.schema_id
                ORDER BY schemas.schema_name, tables.table_name
            )
        """
        if self._is_2016_or_earlier:
            query += """
            SELECT schema_tables.schema_id, schema_tables.schema_name, schema_tables.owner_name,
                schema_tables.table_name, schema_tables.table_id
            FROM schema_tables
            ;
        """
            return query

        # For 2017 and later we can get all the data in one query
        query += f"""
            SELECT schema_tables.schema_id, schema_tables.schema_name, schema_tables.owner_name,
                schema_tables.table_name
                , json_query(({COLUMN_QUERY} FOR JSON PATH), '$') as columns
                , json_query(({INDEX_QUERY} FOR JSON PATH), '$') as indexes
                , json_query(({FOREIGN_KEY_QUERY} FOR JSON PATH), '$') as foreign_keys
                , ({PARTITIONS_QUERY}) as partition_count
            FROM schema_tables
            ;
        """
        return query

    def _get_next(self, cursor):
        return cursor.fetchone_dict()

    def _get_all(self, cursor):
        return cursor.fetchall_dict()

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        object = super()._map_row(database, cursor_row)
        if self._is_2016_or_earlier:
            # We need to fetch the related data for each table
            # Use a key_prefix to get a separate connection to avoid conflicts with the main connection
            with self._check.connection.open_managed_default_connection(key_prefix="schemas-pre-2017"):
                with self._check.connection.get_managed_cursor(key_prefix="schemas-pre-2017") as cursor:
                    table_id = str(cursor_row.get("table_id"))
                    columns_query = COLUMN_QUERY.replace("schema_tables.table_id", table_id)
                    cursor.execute(columns_query)
                    columns = cursor.fetchall_dict()
                    indexes_query = INDEX_QUERY_PRE_2017.replace("schema_tables.table_id", table_id)
                    cursor.execute(indexes_query)
                    indexes = cursor.fetchall_dict()
                    foreign_keys_query = FOREIGN_KEY_QUERY_PRE_2017.replace("schema_tables.table_id", table_id)
                    cursor.execute(foreign_keys_query)
                    foreign_keys = cursor.fetchall_dict()
                    partitions_query = PARTITIONS_QUERY.replace("schema_tables.table_id", table_id)
                    cursor.execute(partitions_query)
                    partition_row = cursor.fetchone_dict()
                    partition_count = partition_row.get("partition_count") if partition_row else None
        else:
            columns = json.loads(cursor_row.get("columns") or "[]")
            indexes = json.loads(cursor_row.get("indexes") or "[]")
            foreign_keys = json.loads(cursor_row.get("foreign_keys") or "[]")
            partition_count = cursor_row.get("partition_count")

        # Map the cursor row to the expected schema, and strip out None values
        object["schemas"] = [
            {
                "name": cursor_row.get("schema_name"),
                "id": str(cursor_row.get("schema_id")),  # Backend expects a string
                "owner_name": cursor_row.get("owner_name"),
                "tables": [
                    {
                        k: v
                        for k, v in {
                            "id": str(cursor_row.get("table_id")),  # Backend expects a string
                            "name": cursor_row.get("table_name"),
                            "columns": columns,
                            "indexes": indexes,
                            "foreign_keys": foreign_keys,
                            "partitions": {"partition_count": partition_count},
                        }.items()
                        if v is not None
                    }
                ]
                if cursor_row.get("table_name") is not None
                else [],
            }
        ]
        return object
