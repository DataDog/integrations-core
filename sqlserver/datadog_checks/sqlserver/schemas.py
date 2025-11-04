# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, TypedDict

import orjson as json

from datadog_checks.sqlserver.utils import execute_query

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig
from datadog_checks.sqlserver.const import (
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
    c.name, t.name as data_type, dc.definition as column_default, c.is_nullable AS nullable, c.collation_name, c.precision, c.scale, c.max_length
FROM
    sys.columns c
    INNER JOIN sys.types t ON c.user_type_id = t.user_type_id
    LEFT JOIN sys.default_constraints dc ON c.default_object_id = dc.object_id
WHERE c.object_id = schema_tables.table_id
"""

PARTITIONS_QUERY = """
SELECT
    object_id AS id, COUNT(*) AS partition_count
FROM
    sys.partitions
WHERE
    object_id IN ({}) GROUP BY object_id;
"""

INDEX_QUERY = """
SELECT
    i.object_id AS table_id, i.name, i.type, i.is_unique, i.is_primary_key, i.is_unique_constraint,
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
    FK.parent_object_id AS table_id,
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


class MySqlDatabaseObject(DatabaseObject):
    schemas: list[TableObject]


class SQLServerSchemaCollector(SchemaCollector):
    _check: SQLServer

    def __init__(self, check: SQLServer):
        config = SchemaCollectorConfig()
        config.collection_interval = check._config.schema_config.get("collection_interval")
        # config.max_tables = check._config.collect_schemas.max_tables
        # config.exclude_databases =  check._config.collect_schemas.exclude_databases
        # config.include_databases =  check._config.collect_schemas.include_databases
        # config.exclude_schemas =  check._config.collect_schemas.exclude_schemas
        # config.include_schemas =  check._config.collect_schemas.include_schemas
        # config.exclude_tables =  check._config.collect_schemas.exclude_tables
        # config.include_tables =  check._config.collect_schemas.include_tables
        # config.max_columns =  check._config.collect_schemas.max_columns
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
                column_columns = """'name':columns.name, 
                'column_type':columns.column_type, 
                'column_default':columns.column_default,
                'nullable':columns.nullable, 
                'ordinal_position':columns.ordinal_position"""
                index_columns = """'name':indexes.name,
                'type':indexes.type, 
                'is_unique':indexes.is_unique,
                'is_primary_key':indexes.is_primary_key,
                'is_unique_constraint':indexes.is_unique_constraint,
                'is_disabled':indexes.is_disabled,
                'column_names':indexes.column_names"""
                constraint_columns = """'foreign_key_name':constraints.foreign_key_name, 
                'referencing_table':constraints.referencing_table,
                'referencing_column':constraints.referencing_column, 
                'referenced_table':constraints.referenced_table,
                'referenced_column':constraints.referenced_column, 
                'delete_action':constraints.delete_action,
                'update_action':constraints.update_action"""
                # partition_ctes = (
                #     f"""
                #     ,
                #     partition_keys AS (
                #         {PARTITION_KEY_QUERY}
                #     ),
                #     num_partitions AS (
                #         {NUM_PARTITIONS_QUERY}
                #     )
                # """
                #     if VersionUtils.transform_version(str(self._check.version))["version.major"] > "9"
                #     else ""
                # )
                # partition_joins = (
                #     """
                #     LEFT JOIN partition_keys ON tables.table_id = partition_keys.table_id
                #     LEFT JOIN num_partitions ON tables.table_id = num_partitions.table_id
                # """
                #     if VersionUtils.transform_version(str(self._check.version))["version.major"] > "9"
                #     else ""
                # )
                # parition_selects = (
                #     """
                # ,
                #     partition_keys.partition_key,
                #     num_partitions.num_partitions
                # """
                #     if VersionUtils.transform_version(str(self._check.version))["version.major"] > "9"
                #     else ""
                # )
                partition_ctes = ""
                partition_joins = ""
                partition_selects = ""
                # limit = int(self._config.max_tables or 1_000_000)
                limit = 1_000_000

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
                        LEFT JOIN tables ON schemas.schema_id = tables.schema_id
                        ORDER BY schemas.schema_name, tables.table_name
                    )
                    
                    {partition_ctes}
                    
                    SELECT schema_tables.schema_name, schema_tables.table_name,
                        json_query(({columns_query} FOR JSON PATH), '$') as columns
                        , json_query(({indexes_query} FOR JSON PATH), '$') as indexes
                        , json_query(({constraints_query} FOR JSON PATH), '$') as foreign_keys
                        {partition_selects}
                    FROM schema_tables
                        {partition_joins}
                    ;
                """
                # print(query)
                # cursor.execute("SET SESSION MAX_EXECUTION_TIME=60000;")
                cursor.execute(query)
                yield cursor

    def _get_next(self, cursor):
        return cursor.fetchone()

    def _get_all(self, cursor):
        return cursor.fetchall()

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        print(cursor_row)
        # We intentionally dont call super because MySQL has no logical databases
        object = super()._map_row(database, cursor_row)
        # Map the cursor row to the expected schema, and strip out None values
        object["tables"] = {
            "name": cursor_row.get("schema_name"),
            "id": cursor_row.get("schema_id"),
            "owner": cursor_row.get("owner_name"),
            "tables": [
                {
                    k: v
                    for k, v in {
                        "name": cursor_row.get("table_name"),
                        # The query can create duplicates of the joined tables
                        "columns": list(
                            {v and v['name']: v for v in json.loads(cursor_row.get("columns")) or []}.values()
                        ),
                        "indexes": list(
                            {v and v['name']: v for v in json.loads(cursor_row.get("indexes")) or []}.values()
                        ),
                        "foreign_keys": list(
                            {v and v['name']: v for v in json.loads(cursor_row.get("foreign_keys")) or []}.values()
                        ),
                        # "toast_table": cursor_row.get("toast_table"),
                        # "num_partitions": cursor_row.get("num_partitions"),
                        # "partition_key": cursor_row.get("partition_key"),
                    }.items()
                    if v is not None
                }
                if cursor_row.get("table_name") is not None
                else None
            ],
        }
        return object
