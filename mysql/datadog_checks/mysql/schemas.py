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

SQL_DATABASES = """
SELECT schema_name as `schema_name`,
       default_character_set_name as `default_character_set_name`,
       default_collation_name as `default_collation_name`
       FROM information_schema.SCHEMATA
       WHERE schema_name not in ('sys', 'mysql', 'performance_schema', 'information_schema')"""

SQL_TABLES = """\
SELECT table_name as `table_name`,
       engine as `engine`,
       row_format as `row_format`,
       create_time as `create_time`,
       table_schema as `schema_name`
       FROM information_schema.TABLES
       WHERE TABLE_TYPE="BASE TABLE"
"""

SQL_COLUMNS = """\
SELECT table_name as `table_name`,
       table_schema as `schema_name`,
       column_name as `name`,
       column_type as `column_type`,
       column_default as `default`,
       is_nullable as `nullable`,
       ordinal_position as `ordinal_position`,
       column_key as `column_key`,
       extra as `extra`
FROM INFORMATION_SCHEMA.COLUMNS
"""

SQL_INDEXES = """\
SELECT
    table_name as `table_name`,
    table_schema as `schema_name`,
    index_name as `name`,
    collation as `collation`,
    cardinality as `cardinality`,
    index_type as `index_type`,
    seq_in_index as `seq_in_index`,
    column_name as `column_name`,
    sub_part as `sub_part`,
    packed as `packed`,
    nullable as `nullable`,
    non_unique as `non_unique`,
    NULL as `expression`
FROM INFORMATION_SCHEMA.STATISTICS
"""

SQL_INDEXES_8_0_13 = """\
SELECT
    table_name as `table_name`,
    table_schema as `schema_name`,
    index_name as `name`,
    collation as `collation`,
    cardinality as `cardinality`,
    index_type as `index_type`,
    seq_in_index as `seq_in_index`,
    column_name as `column_name`,
    sub_part as `sub_part`,
    packed as `packed`,
    nullable as `nullable`,
    non_unique as `non_unique`,
    expression as `expression`
FROM INFORMATION_SCHEMA.STATISTICS
"""

SQL_FOREIGN_KEYS = """\
SELECT
    kcu.constraint_schema as constraint_schema,
    kcu.constraint_name as name,
    kcu.table_name as table_name,
    kcu.table_schema as schema_name,
    group_concat(kcu.column_name order by kcu.ordinal_position asc) as column_names,
    kcu.referenced_table_schema as referenced_table_schema,
    kcu.referenced_table_name as referenced_table_name,
    group_concat(kcu.referenced_column_name) as referenced_column_names,
    rc.update_rule as update_action,
    rc.delete_rule as delete_action
FROM
    INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
LEFT JOIN
    INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
    ON kcu.CONSTRAINT_SCHEMA = rc.CONSTRAINT_SCHEMA
    AND kcu.CONSTRAINT_NAME = rc.CONSTRAINT_NAME
WHERE
    kcu.referenced_table_name is not null
GROUP BY
    kcu.constraint_schema,
    kcu.constraint_name,
    kcu.table_name,
    kcu.table_schema,
    kcu.referenced_table_schema,
    kcu.referenced_table_name,
    rc.update_rule,
    rc.delete_rule
"""

SQL_PARTITION = """\
SELECT
    table_name as `table_name`,
    table_schema as `schema_name`,
    partition_name as `name`,
    subpartition_name as `subpartition_name`,
    partition_ordinal_position as `partition_ordinal_position`,
    subpartition_ordinal_position as `subpartition_ordinal_position`,
    partition_method as `partition_method`,
    subpartition_method as `subpartition_method`,
    partition_expression as `partition_expression`,
    subpartition_expression as `subpartition_expression`,
    partition_description as `partition_description`,
    table_rows as `table_rows`,
    data_length as `data_length`
FROM INFORMATION_SCHEMA.PARTITIONS
WHERE
    partition_name IS NOT NULL
"""


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


class TableObject(TypedDict):
    id: str
    name: str
    columns: list
    indexes: list
    foreign_keys: list


class MySqlDatabaseObject(DatabaseObject):
    schemas: list[TableObject]


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
        indexes_query = SQL_INDEXES
        constraints_query = SQL_FOREIGN_KEYS
        column_columns = """'name', columns.name,
        'column_type', columns.column_type,
        'default', columns.default,
        'nullable', columns.nullable,
        'ordinal_position', columns.ordinal_position,
        'column_key', columns.column_key"""
        index_columns = """'name', indexes.name,
        'collation', indexes.collation,
            'cardinality', indexes.cardinality,
        'index_type', indexes.index_type,
        'seq_in_index', indexes.seq_in_index,
        'column_name', indexes.column_name,
        'sub_part', indexes.sub_part,
        'packed', indexes.packed,
        'nullable', indexes.nullable,
        'non_unique', indexes.non_unique
            """
        constraint_columns = """'name', constraints.name,
        'constraint_schema', constraints.constraint_schema,
        'table_name', constraints.table_name,
        'referenced_table_schema', constraints.referenced_table_schema,
        'referenced_table_name', constraints.referenced_table_name,
        'referenced_column_names', constraints.referenced_column_names
        """

        limit = int(self._config.max_tables or 1_000_000)

        query = f"""
            SELECT schema_tables.schema_name, schema_tables.table_name,
                json_arrayagg(json_object({column_columns})) columns,
                json_arrayagg(json_object({index_columns})) indexes,
                json_arrayagg(json_object({constraint_columns})) foreign_keys
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
            GROUP BY schema_tables.schema_name, schema_tables.table_name
            ;
        """
        return query

    def _get_next(self, cursor):
        return cursor.fetchone()

    def _get_all(self, cursor):
        return cursor.fetchall()

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        print(cursor_row)
        # We intentionally dont call super because MySQL has no logical databases
        object = {
            'name': cursor_row.get("schema_name"),
            'default_character_set_name': cursor_row.get("default_character_set_name"),
            'default_collation_name': cursor_row.get("default_collation_name"),
        }
        # Map the cursor row to the expected schema, and strip out None values
        object["tables"] = [
            {
                k: v
                for k, v in {
                    "name": cursor_row.get("table_name"),
                    # The query can create duplicates of the joined tables
                    "columns": list({v and v['name']: v for v in json.loads(cursor_row.get("columns")) or []}.values()),
                    "indexes": list({v and v['name']: v for v in json.loads(cursor_row.get("indexes")) or []}.values()),
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
        ]
        return object
