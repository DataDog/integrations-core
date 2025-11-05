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
    SWITCH_DB_STATEMENT,
)


class DatabaseInfo(TypedDict):
    name: str
    id: str
    collation: str
    owner: str


DB_QUERY = """
SELECT
    db.database_id AS id, db.name AS name, db.collation_name AS collation, dp.name AS owner
FROM
    sys.databases db LEFT JOIN sys.database_principals dp ON db.owner_sid = dp.sid
WHERE db.name IN ({});
"""

SCHEMA_QUERY = """
SELECT
    s.name AS schema_name, s.schema_id AS schema_id, dp.name AS owner_name
FROM
    sys.schemas AS s JOIN sys.database_principals dp ON s.principal_id = dp.principal_id
WHERE s.name NOT IN ('sys', 'information_schema')
"""

TABLES_IN_SCHEMA_QUERY = """
SELECT
    object_id AS table_id, name AS table_name, schema_id
FROM
    sys.tables
"""

COLUMN_QUERY = """
SELECT
    c.name, t.name as data_type, coalesce(dc.definition, 'None') as "default", c.is_nullable AS nullable
FROM
    sys.columns c
    INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
    LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
WHERE c.object_id = schema_tables.table_id
"""

INDEX_QUERY = """
SELECT
    i.name, i.type, i.is_unique, i.is_primary_key, i.is_unique_constraint,
    i.is_disabled, STRING_AGG(c.name, ',') AS column_names
FROM
    sys.indexes i JOIN sys.index_columns ic ON i.object_id = ic.object_id
    AND i.index_id = ic.index_id JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
WHERE i.object_id = schema_tables.table_id
GROUP BY i.object_id, i.name, i.type,
    i.is_unique, i.is_primary_key, i.is_unique_constraint, i.is_disabled
"""

INDEX_QUERY_PRE_2017 = """
SELECT
    i.object_id AS id,
    i.name,
    i.type,
    i.is_unique,
    i.is_primary_key,
    i.is_unique_constraint,
    i.is_disabled,
    STUFF((
        SELECT ',' + c.name
        FROM sys.index_columns ic
        JOIN sys.columns c ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        WHERE ic.object_id = i.object_id AND ic.index_id = i.index_id
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS column_names
FROM
    sys.indexes i
WHERE i.object_id = schema_tables.table_id
GROUP BY
    i.object_id,
    i.name,
    i.index_id,
    i.type,
    i.is_unique,
    i.is_primary_key,
    i.is_unique_constraint,
    i.is_disabled
"""

FOREIGN_KEY_QUERY = """
SELECT
    FK.name AS foreign_key_name,
    OBJECT_NAME(FK.parent_object_id) AS referencing_table,
    STRING_AGG(COL_NAME(FKC.parent_object_id, FKC.parent_column_id),',') AS referencing_column,
    OBJECT_NAME(FK.referenced_object_id) AS referenced_table,
    STRING_AGG(COL_NAME(FKC.referenced_object_id, FKC.referenced_column_id),',') AS referenced_column,
    FK.delete_referential_action_desc AS delete_action,
    FK.update_referential_action_desc AS update_action
FROM
    sys.foreign_keys AS FK
    JOIN sys.foreign_key_columns AS FKC ON FK.object_id = FKC.constraint_object_id
WHERE FK.parent_object_id = schema_tables.table_id
GROUP BY
    FK.name,
    FK.parent_object_id,
    FK.referenced_object_id,
    FK.delete_referential_action_desc,
    FK.update_referential_action_desc
"""

FOREIGN_KEY_QUERY_PRE_2017 = """
SELECT
    FK.parent_object_id AS table_id,
    FK.name AS foreign_key_name,
    OBJECT_NAME(FK.parent_object_id) AS referencing_table,
    STUFF((
        SELECT ',' + COL_NAME(FKC.parent_object_id, FKC.parent_column_id)
        FROM sys.foreign_key_columns AS FKC
        WHERE FKC.constraint_object_id = FK.object_id
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS referencing_column,
    OBJECT_NAME(FK.referenced_object_id) AS referenced_table,
    STUFF((
        SELECT ',' + COL_NAME(FKC.referenced_object_id, FKC.referenced_column_id)
        FROM sys.foreign_key_columns AS FKC
        WHERE FKC.constraint_object_id = FK.object_id
        FOR XML PATH(''), TYPE).value('.', 'NVARCHAR(MAX)'), 1, 1, '') AS referenced_column,
    FK.delete_referential_action_desc AS delete_action,
    FK.update_referential_action_desc AS update_action
FROM
    sys.foreign_keys AS FK
GROUP BY
    FK.name,
    FK.object_id,
    FK.parent_object_id,
    FK.referenced_object_id,
    FK.delete_referential_action_desc,
    FK.update_referential_action_desc
"""

PARTITIONS_QUERY = """
SELECT
    COUNT(*) AS partition_count
FROM
    sys.partitions
WHERE
    object_id = schema_tables.table_id
GROUP BY object_id
"""


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

                schemas_query = SCHEMA_QUERY
                tables_query = TABLES_IN_SCHEMA_QUERY
                columns_query = COLUMN_QUERY
                indexes_query = INDEX_QUERY
                constraints_query = FOREIGN_KEY_QUERY
                partitions_query = PARTITIONS_QUERY

                limit = int(self._config.max_tables or 1_000_000)

                # Note that we INNER JOIN tables to omit schemas with no tables
                # This is a simple way to omit the system tables like db_blah
                query = f"""
                    WITH
                    schemas AS (
                        {schemas_query}
                    ),
                    tables AS (
                        {tables_query}
                    ),
                    schema_tables AS (
                        SELECT TOP {limit} schemas.schema_name, schemas.schema_id, schemas.owner_name,
                        tables.table_id, tables.table_name
                        FROM schemas
                        INNER JOIN tables ON schemas.schema_id = tables.schema_id
                        ORDER BY schemas.schema_name, tables.table_name
                    )

                    SELECT schema_tables.schema_id, schema_tables.schema_name, schema_tables.owner_name,
                        schema_tables.table_name
                        , json_query(({columns_query} FOR JSON PATH), '$') as columns
                        , json_query(({indexes_query} FOR JSON PATH), '$') as indexes
                        , json_query(({constraints_query} FOR JSON PATH), '$') as foreign_keys
                        , ({partitions_query}) as partition_count
                    FROM schema_tables
                    ;
                """
                # print(query)
                cursor.execute(query)
                yield cursor

    def _get_next(self, cursor):
        return cursor.fetchone_dict()

    def _get_all(self, cursor):
        return cursor.fetchall_dict()

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        object = super()._map_row(database, cursor_row)
        # Map the cursor row to the expected schema, and strip out None values
        object["schemas"] = [
            {
                "name": cursor_row.get("schema_name"),
                "id": cursor_row.get("schema_id"),
                "owner_name": cursor_row.get("owner_name"),
                "tables": [
                    {
                        k: v
                        for k, v in {
                            "id": cursor_row.get("table_id"),
                            "name": cursor_row.get("table_name"),
                            # The query can create duplicates of the joined tables
                            "columns": list(
                                {v and v['name']: v for v in json.loads(cursor_row.get("columns") or "[]")}.values()
                            ),
                            "indexes": list(
                                {v and v['name']: v for v in json.loads(cursor_row.get("indexes") or "[]")}.values()
                            ),
                            "foreign_keys": list(
                                {
                                    v and v['foreign_key_name']: v
                                    for v in json.loads(cursor_row.get("foreign_keys") or "[]")
                                }.values()
                            ),
                            "partitions": {"partition_count": cursor_row.get("partition_count")},
                        }.items()
                        if v is not None
                    }
                ]
                if cursor_row.get("table_name") is not None
                else [],
            }
        ]
        return object
