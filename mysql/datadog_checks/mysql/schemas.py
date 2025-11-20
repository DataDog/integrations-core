# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
from contextlib import closing
from typing import TYPE_CHECKING, TypedDict

import orjson as json

if TYPE_CHECKING:
    from datadog_checks.mysql import MySql

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig
from datadog_checks.mysql.cursor import CommenterDictCursor
from datadog_checks.mysql.queries import (
    SQL_COLUMNS,
    SQL_DATABASES,
    SQL_FOREIGN_KEYS,
    SQL_INDEXES,
    SQL_INDEXES_8_0_13,
    SQL_PARTITION,
    SQL_TABLES,
)


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


class MySqlSchemaCollectorConfig(SchemaCollectorConfig):
    max_execution_time: int
    max_tables: int


class MySqlSchemaCollector(SchemaCollector):
    _check: MySql
    _config: MySqlSchemaCollectorConfig

    def __init__(self, check: MySql):
        config = MySqlSchemaCollectorConfig()
        config.max_execution_time = check._config.schemas_config.get('max_execution_time', 60)
        config.max_tables = check._config.schemas_config.get('max_tables', 300)
        super().__init__(check, config)

    @property
    def kind(self):
        return "mysql_databases"

    @property
    def base_event(self):
        event = super().base_event
        event["flavor"] = self._check.version.flavor
        return event

    def _get_databases(self):
        # MySQL can query all schemas at once so we return a stub
        # and then fetch all databases with their tables in the _get_cursor method
        return [{'name': 'mysql'}]

    @contextlib.contextmanager
    def _get_cursor(self, database_name):
        with closing(self._check._mysql_metadata.get_db_connection().cursor(CommenterDictCursor)) as cursor:
            query = self._get_tables_query()
            max_execution_time = self._config.max_execution_time
            if self._check.is_mariadb:
                # MariaDB is in seconds
                cursor.execute(f"SET SESSION MAX_STATEMENT_TIME={max_execution_time};")
            else:
                # MySQL is in milliseconds
                cursor.execute(f"SET SESSION MAX_EXECUTION_TIME={max_execution_time * 1000};")
            cursor.execute(query)
            yield cursor

    def _get_tables_query(self):
        schemas_query = SQL_DATABASES
        tables_query = SQL_TABLES
        columns_query = SQL_COLUMNS
        indexes_query = (
            SQL_INDEXES_8_0_13
            if self._check.version.flavor == 'MySQL' and self._check.version.version_compatible((8, 0, 13))
            else SQL_INDEXES
        )
        constraints_query = SQL_FOREIGN_KEYS
        partition_query = SQL_PARTITION
        column_columns = """'name', columns.name,
        'column_type', columns.column_type,
        'default', columns.default,
        'nullable', columns.nullable,
        'ordinal_position', columns.ordinal_position,
        'column_key', columns.column_key"""
        index_columns = """'name', indexes.name,
        'cardinality', indexes.cardinality,
        'index_type', indexes.index_type,
        'non_unique', indexes.non_unique,
        'expression', indexes.expression,
        'columns', indexes.columns
            """
        constraint_columns = """'name', constraints.name,
        'constraint_schema', constraints.constraint_schema,
        'table_name', constraints.table_name,
        'column_names', constraints.column_names,
        'referenced_table_schema', constraints.referenced_table_schema,
        'referenced_table_name', constraints.referenced_table_name,
        'referenced_column_names', constraints.referenced_column_names,
        'update_action', constraints.update_action,
        'delete_action', constraints.delete_action
        """

        partition_columns = """'name', partitions.name,
        'partition_ordinal_position', partitions.partition_ordinal_position,
        'partition_method', partitions.partition_method,
        'partition_expression', partitions.partition_expression,
        'partition_description', partitions.partition_description,
        'subpartitions', partitions.subpartitions
        """

        limit = int(self._config.max_tables or 1_000_000)

        query = f"""
            SELECT schema_tables.schema_name, schema_tables.table_name,
                schema_tables.engine, schema_tables.row_format, schema_tables.create_time,
                json_arrayagg(json_object({column_columns})) columns,
                json_arrayagg(json_object({index_columns})) indexes,
                json_arrayagg(json_object({constraint_columns})) foreign_keys,
                json_arrayagg(json_object({partition_columns})) partitions
            FROM (
                SELECT `schemas`.schema_name, `schemas`.default_character_set_name, `schemas`.default_collation_name,
                tables.table_name, tables.engine, tables.row_format, tables.create_time
                FROM ({schemas_query}) `schemas`
                LEFT JOIN ({tables_query}) tables ON `schemas`.schema_name = tables.schema_name
                ORDER BY tables.table_name
                LIMIT {limit}
            ) schema_tables
                LEFT JOIN ({columns_query}) columns ON schema_tables.table_name = columns.table_name and
                    schema_tables.schema_name = columns.schema_name
                LEFT JOIN ({indexes_query}) indexes ON schema_tables.table_name = indexes.table_name and
                    schema_tables.schema_name = indexes.schema_name
                LEFT JOIN ({constraints_query}) constraints ON schema_tables.table_name = constraints.table_name and
                    schema_tables.schema_name = constraints.schema_name
                LEFT JOIN ({partition_query}) partitions ON schema_tables.table_name = partitions.table_name
            GROUP BY schema_tables.schema_name, schema_tables.table_name,
            schema_tables.engine, schema_tables.row_format, schema_tables.create_time
            ;
        """
        return query

    def _get_next(self, cursor):
        return cursor.fetchone()

    def _get_all(self, cursor):
        return cursor.fetchall()

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        # We intentionally dont call super because MySQL has no logical databases
        object = {
            "name": cursor_row.get("schema_name"),
            "default_character_set_name": cursor_row.get("default_character_set_name"),
            "default_collation_name": cursor_row.get("default_collation_name"),
        }
        # Map the cursor row to the expected schema, and strip out None values
        object["tables"] = [
            {
                k: v
                for k, v in {
                    "engine": cursor_row.get("engine"),
                    "row_format": cursor_row.get("row_format"),
                    "create_time": cursor_row.get("create_time"),
                    "name": cursor_row.get("table_name"),
                    # The query can create duplicates of the joined tables
                    "columns": list(
                        {
                            v['name']: {
                                **{k: v_ for k, v_ in v.items() if k == 'default' or v_ is not None},
                                'nullable': v['nullable'] == 'YES',
                            }
                            for v in json.loads(cursor_row.get("columns")) or []
                            if v and v.get('name') is not None
                        }.values()
                    ),
                    "indexes": list(
                        {
                            v['name']: {
                                **{
                                    k: v2
                                    for k, v2 in {
                                        **v,
                                        'non_unique': v['non_unique'] == 1,
                                        'columns': list(
                                            {
                                                c['name']: {
                                                    **{k: v_ for k, v_ in c.items() if v_ is not None},
                                                    'nullable': c['nullable'] == 'YES',
                                                }
                                                for c in v['columns'] or []
                                                if c and c.get('name') is not None
                                            }.values()
                                        ),
                                    }.items()
                                    if v2 is not None
                                }
                            }
                            for v in json.loads(cursor_row.get("indexes")) or []
                            if v and v.get('name') is not None
                        }.values()
                    ),
                    "foreign_keys": list(
                        {
                            v['name']: v
                            for v in (json.loads(cursor_row.get("foreign_keys")) or [])
                            if v and v.get('name') is not None
                        }.values()
                    ),
                    "partitions": list(
                        {
                            v['name']: {
                                **v,
                                'subpartitions': list(
                                    {
                                        v2['name']: v2
                                        for v2 in v['subpartitions'] or []
                                        if v2 and v2.get('name') is not None
                                    }.values()
                                ),
                                "data_length": sum(v2.get('data_length', 0) for v2 in (v['subpartitions'] or [])),
                                "table_rows": sum(v2.get('table_rows', 0) for v2 in (v['subpartitions'] or [])),
                            }
                            for v in (json.loads(cursor_row.get("partitions")) or [])
                            if v and v.get('name') is not None
                        }.values()
                    ),
                }.items()
                if v is not None
            }
            if cursor_row.get("table_name") is not None
            else None
        ]
        return object
