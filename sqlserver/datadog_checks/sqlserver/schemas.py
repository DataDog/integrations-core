# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, TypedDict

from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.utils import construct_use_statement, execute_query, is_azure_database

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig
from datadog_checks.sqlserver.const import (
    DEFAULT_SCHEMAS_COLLECTION_INTERVAL,
    STATIC_INFO_ENGINE_EDITION,
    STATIC_INFO_MAJOR_VERSION,
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
    VIEWS_QUERY,
)

KEY_PREFIX = "dbm-schemas-"
KEY_PREFIX_PRE_2017 = "dbm-schemas-pre-2017"
# The modern schema query uses database-scoped JSON output, which requires SQL Server 2016 compatibility.
MINIMUM_JSON_COMPATIBILITY_LEVEL = 130


class DatabaseInfo(TypedDict):
    name: str
    id: str
    collation: str
    owner: str
    compatibility_level: str


# The schema collector sends lists of DatabaseObjects to the agent
# The format is for backwards compatibility with the current backend
class DatabaseObject(TypedDict):
    # Splat of database info
    description: str
    name: str
    id: str
    encoding: str
    owner: str


class ColumnObjectBase(TypedDict):
    data_type: str
    name: str
    nullable: bool


class ColumnObject(ColumnObjectBase, total=False):
    default: str | None
    ordinal_position: str | None


class TableObject(TypedDict):
    id: str
    name: str
    columns: list[ColumnObject]
    indexes: list
    foreign_keys: list


class ViewObject(TypedDict):
    id: str
    name: str
    create_date: str
    modify_date: str
    definition: str | None
    columns: list[ColumnObject]


class SchemaObject(TypedDict):
    name: str
    id: str
    owner_name: str


class TableSchemaObject(SchemaObject):
    tables: list[TableObject]


class ViewSchemaObject(SchemaObject):
    views: list[ViewObject]


class SQLServerDatabaseObject(DatabaseObject):
    schemas: list[TableSchemaObject | ViewSchemaObject]


class SQLServerSchemaCollector(SchemaCollector):
    _check: SQLServer

    def __init__(self, check: SQLServer):
        config = SchemaCollectorConfig()
        config.collection_interval = check._config.schema_config.get(
            "collection_interval", DEFAULT_SCHEMAS_COLLECTION_INTERVAL
        )
        config.max_tables = check._config.schema_config.get('max_tables', 300)
        config.max_views = check._config.schema_config.get('max_views', 1000)
        self._is_2016_or_earlier = None
        self._database_compatibility_levels: dict[str, int] = {}
        self._pre_2017_cursor = None
        super().__init__(check, config)

    @property
    def kind(self):
        return "sqlserver_databases"

    def _get_databases(self) -> list[DatabaseInfo]:
        database_names = self._check.get_databases()
        with self._check.connection.open_managed_default_connection(KEY_PREFIX):
            with self._check.connection.get_managed_cursor(KEY_PREFIX) as cursor:
                if not database_names:
                    return []
                placeholders = ",".join(["?"] * len(database_names))
                query = DB_QUERY.format(placeholders)
                databases = execute_query(query, cursor, convert_results_to_str=True, parameters=tuple(database_names))
                self._record_database_compatibility_levels(databases)
                return databases

    @contextlib.contextmanager
    def _get_cursor(self, database_name):
        with contextlib.ExitStack() as stack:
            try:
                stack.enter_context(self._check.connection.open_managed_default_connection(KEY_PREFIX))
                cursor = stack.enter_context(self._check.connection.get_managed_cursor(KEY_PREFIX))
                switch_db_statement = construct_use_statement(database_name)
                cursor.execute(switch_db_statement)
                self._is_2016_or_earlier = self._should_use_legacy_schema_query(database_name)

                if self._is_2016_or_earlier:
                    stack.enter_context(self._check.connection.open_managed_default_connection(KEY_PREFIX_PRE_2017))
                    self._pre_2017_cursor = stack.enter_context(
                        self._check.connection.get_managed_cursor(KEY_PREFIX_PRE_2017)
                    )
                    self._pre_2017_cursor.execute(switch_db_statement)

                query = self._get_schema_objects_query()
                cursor.execute(query)
                yield cursor
            finally:
                self._pre_2017_cursor = None

    def _record_database_compatibility_levels(self, databases: list[DatabaseInfo]) -> None:
        self._database_compatibility_levels = {}
        for database in databases:
            self._database_compatibility_levels[database["name"]] = int(database["compatibility_level"])

    def _should_use_legacy_schema_query(self, database_name: str) -> bool:
        """
        Return whether the current database needs the legacy schema query.

        The modern schema query depends on two SQL Server features:
        - STRING_AGG, used to build index column lists. On self-managed SQL Server, this requires SQL Server 2017
          or later. Azure SQL Database and Azure SQL Managed Instance report ProductMajorVersion 12 while still
          supporting STRING_AGG, so only self-managed SQL Server uses this version gate.
        - JSON output, used for column, index, and foreign key metadata. This is controlled by each database's
          compatibility_level and requires level 130 or higher.

        If ProductMajorVersion is missing, use the legacy query because we cannot confirm that STRING_AGG is
        available.
        """
        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION)
        if not is_azure_database(engine_edition):
            major_version = int(self._check.static_info_cache.get(STATIC_INFO_MAJOR_VERSION) or 0)
            if major_version == 0:
                self._check.log.debug("major_version is not available yet, using legacy schema query")
                return True
            if major_version <= 13:
                return True

        compatibility_level = self._database_compatibility_levels.get(database_name)
        if compatibility_level is None:
            self._check.log.debug(
                "compatibility_level is not available for SQL Server database %s, using pre-2017 schema query",
                database_name,
            )
            return True
        return compatibility_level < MINIMUM_JSON_COMPATIBILITY_LEVEL

    def _get_schema_objects_query(self):
        table_limit = int(self._config.max_tables or 1_000_000)
        view_limit = int(self._config.max_views or 1_000_000)

        # Limit tables and views independently, then combine them into one result stream.
        # `_map_row` uses object_type to place each object in its corresponding schema list.
        query = f"""
            WITH
            schemas AS (
                {SCHEMA_QUERY}
            ),
            tables AS (
                {TABLES_QUERY}
            ),
            views AS (
                {VIEWS_QUERY}
            ),
            limited_tables AS (
                SELECT TOP {table_limit} schemas.schema_name, schemas.schema_id, schemas.owner_name,
                tables.table_id, tables.table_name
                FROM schemas
                INNER JOIN tables ON schemas.schema_id = tables.schema_id
                ORDER BY schemas.schema_name, tables.table_name
            ),
            limited_views AS (
                SELECT TOP {view_limit} schemas.schema_name, schemas.schema_id, schemas.owner_name,
                views.view_id, views.view_name, views.create_date, views.modify_date, views.definition
                FROM schemas
                INNER JOIN views ON schemas.schema_id = views.schema_id
                ORDER BY schemas.schema_name, views.view_name
            ),
            schema_tables AS (
                SELECT schema_name, schema_id, owner_name, table_id, table_name,
                    'TABLE' AS object_type,
                    CAST(NULL AS varchar(33)) AS create_date,
                    CAST(NULL AS varchar(33)) AS modify_date,
                    CAST(NULL AS nvarchar(max)) AS definition
                FROM limited_tables
                UNION ALL
                SELECT schema_name, schema_id, owner_name, view_id AS table_id, view_name AS table_name,
                    'VIEW' AS object_type, create_date, modify_date, definition
                FROM limited_views
            )
        """
        if self._is_2016_or_earlier:
            query += """
            SELECT schema_tables.schema_id, schema_tables.schema_name, schema_tables.owner_name,
                schema_tables.table_name, schema_tables.table_id, schema_tables.object_type,
                schema_tables.create_date, schema_tables.modify_date, schema_tables.definition
            FROM schema_tables
            ;
        """
            return query

        # For 2017 and later we can get all the data in one query
        query += f"""
            SELECT schema_tables.schema_id, schema_tables.schema_name, schema_tables.owner_name,
                schema_tables.table_name, schema_tables.table_id, schema_tables.object_type,
                schema_tables.create_date, schema_tables.modify_date, schema_tables.definition
                , json_query(({COLUMN_QUERY} FOR JSON PATH), '$') as columns
                , CASE WHEN schema_tables.object_type = 'TABLE'
                    THEN json_query(({INDEX_QUERY} FOR JSON PATH), '$') ELSE json_query('[]') END as indexes
                , CASE WHEN schema_tables.object_type = 'TABLE'
                    THEN json_query(({FOREIGN_KEY_QUERY} FOR JSON PATH), '$') ELSE json_query('[]') END as foreign_keys
                , CASE WHEN schema_tables.object_type = 'TABLE' THEN ({PARTITIONS_QUERY}) END as partition_count
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
        is_view = cursor_row.get("object_type") == "VIEW"
        if self._is_2016_or_earlier:
            # We need to fetch the related data for each table or view.
            # Use a separate connection to avoid conflicts with the main cursor while it streams table rows.
            cursor = self._pre_2017_cursor
            if cursor is None:
                raise RuntimeError("pre-2017 schema cursor is not initialized")

            table_id = str(cursor_row.get("table_id"))
            columns_query = COLUMN_QUERY.replace("schema_tables.table_id", table_id)
            cursor.execute(columns_query)
            columns = cursor.fetchall_dict()
            if is_view:
                indexes = []
                foreign_keys = []
                partition_count = None
            else:
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
        schema = {
            "name": cursor_row.get("schema_name"),
            "id": str(cursor_row.get("schema_id")),  # Backend expects a string
            "owner_name": cursor_row.get("owner_name"),
        }
        if is_view:
            schema["views"] = [
                {
                    "id": str(cursor_row.get("table_id")),  # Backend expects a string
                    "name": cursor_row.get("table_name"),
                    "create_date": cursor_row.get("create_date"),
                    "modify_date": cursor_row.get("modify_date"),
                    "definition": cursor_row.get("definition"),
                    "columns": [column for column in columns if column.get("name") is not None],
                }
            ]
        else:
            schema["tables"] = [
                {
                    k: v
                    for k, v in {
                        "id": str(cursor_row.get("table_id")),  # Backend expects a string
                        "name": cursor_row.get("table_name"),
                        "columns": [column for column in columns if column.get("name") is not None],
                        "indexes": [index for index in indexes if index.get("name") is not None],
                        "foreign_keys": [
                            foreign_key
                            for foreign_key in foreign_keys
                            if foreign_key.get("foreign_key_name") is not None
                        ],
                        "partitions": {"partition_count": partition_count},
                    }.items()
                    if v is not None
                }
            ]
        object["schemas"] = [schema]
        return object
