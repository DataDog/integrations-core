# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

import contextlib
from contextlib import closing
from typing import TYPE_CHECKING

from datadog_checks.base.utils.db.schemas import DatabaseInfo, SchemaCollector, SchemaCollectorConfig

if TYPE_CHECKING:
    from .config_models.instance import CollectSchemas
    from .sap_hana import SapHanaCheck

_SYSTEM_SCHEMAS = frozenset(['SYS', 'SYSTEM', 'PUBLIC'])
_SYSTEM_SCHEMA_PREFIX = '_SYS_'

CURRENT_DATABASE_QUERY = "SELECT DATABASE_NAME FROM SYS.M_DATABASE"
CURRENT_DATABASE_DESCRIPTION_QUERY = "SELECT DESCRIPTION FROM SYS.M_DATABASE"

SCHEMAS_QUERY = """
SELECT SCHEMA_NAME, SCHEMA_OWNER
FROM SYS.SCHEMAS
"""

TABLES_QUERY = """
SELECT TABLE_NAME, SCHEMA_NAME, TABLE_TYPE, IS_COLUMN_TABLE
FROM SYS.TABLES
WHERE IS_TEMPORARY = 'FALSE'
  AND IS_SYSTEM_TABLE = 'FALSE'
"""

COLUMNS_QUERY = """
SELECT SCHEMA_NAME, TABLE_NAME, COLUMN_NAME, DATA_TYPE_NAME, IS_NULLABLE, DEFAULT_VALUE, POSITION
FROM SYS.TABLE_COLUMNS
WHERE (SCHEMA_NAME, TABLE_NAME) IN ({placeholders})
ORDER BY SCHEMA_NAME, TABLE_NAME, POSITION
"""


def _is_system_schema(name):
    return name in _SYSTEM_SCHEMAS or name.startswith(_SYSTEM_SCHEMA_PREFIX)


class HanaSchemaCollectorConfig(SchemaCollectorConfig):
    def __init__(self, config: CollectSchemas):
        super().__init__()
        self.collection_interval = int(config.collection_interval or 600)
        self.max_tables = int(config.max_tables or 300)
        self.max_columns = int(config.max_columns or 50)
        self.exclude_schemas = set(config.exclude_schemas or ())
        self.include_schemas = set(config.include_schemas or ())


class HanaSchemaCollector(SchemaCollector):
    _check: SapHanaCheck
    _config: HanaSchemaCollectorConfig

    def __init__(self, check: SapHanaCheck, config: CollectSchemas):
        super().__init__(check, HanaSchemaCollectorConfig(config))

    @property
    def kind(self) -> str:
        return "saphana_databases"

    def _get_databases(self) -> list[DatabaseInfo]:
        try:
            with closing(self._check._conn.cursor()) as cursor:
                cursor.execute(CURRENT_DATABASE_QUERY)
                row = cursor.fetchone()
                if row:
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
            self._log.warning("Could not fetch current HANA database info: %s", e)
        return [{'name': self._check._server, 'description': ''}]

    @contextlib.contextmanager
    def _get_cursor(self, _database_name):
        conn = self._check._conn
        table_rows = []
        try:
            schemas = {}
            with closing(conn.cursor()) as cursor:
                cursor.execute(SCHEMAS_QUERY)
                for row in cursor.fetchall():
                    schema_name = row[0]
                    schema_owner = row[1] or ''
                    if _is_system_schema(schema_name):
                        continue
                    if self._config.include_schemas and schema_name not in self._config.include_schemas:
                        continue
                    if schema_name in self._config.exclude_schemas:
                        continue
                    schemas[schema_name] = {'owner': schema_owner, 'tables': {}}

            with closing(conn.cursor()) as cursor:
                cursor.execute(TABLES_QUERY)
                for row in cursor.fetchall():
                    table_name, schema_name, table_type, is_column_table = row[0], row[1], row[2], row[3]
                    if schema_name not in schemas:
                        continue
                    schemas[schema_name]['tables'][table_name] = {
                        'type': table_type or '',
                        'is_column_table': is_column_table == 'TRUE',
                        'columns': [],
                    }

            total = 0
            for schema_name in list(schemas.keys()):
                tables = schemas[schema_name]['tables']
                for table_name in list(tables.keys()):
                    if total >= self._config.max_tables:
                        del tables[table_name]
                    else:
                        total += 1
                if not tables:
                    del schemas[schema_name]

            surviving_tables = [
                (schema_name, table_name)
                for schema_name, schema_data in schemas.items()
                for table_name in schema_data['tables']
            ]
            if surviving_tables:
                placeholders = ', '.join('(?, ?)' for _ in surviving_tables)
                params = tuple(v for pair in surviving_tables for v in pair)
                with closing(conn.cursor()) as cursor:
                    cursor.execute(COLUMNS_QUERY.format(placeholders=placeholders), params)
                    for row in cursor.fetchall():
                        schema_name, table_name = row[0], row[1]
                        columns = schemas[schema_name]['tables'][table_name]['columns']
                        if len(columns) >= self._config.max_columns:
                            continue
                        columns.append(
                            {
                                'name': row[2],
                                'data_type': row[3] or '',
                                'nullable': row[4] == 'TRUE',
                                'default': row[5],
                                'position': row[6],
                            }
                        )

            for schema_name, schema_data in schemas.items():
                for table_name, table_data in schema_data['tables'].items():
                    table_rows.append(
                        {
                            'schema_name': schema_name,
                            'schema_owner': schema_data['owner'],
                            'table_name': table_name,
                            'table_type': table_data['type'],
                            'is_column_table': table_data['is_column_table'],
                            'columns': table_data['columns'],
                        }
                    )
        except Exception as e:
            self._log.error("Error fetching HANA schema data: %s", e)

        yield iter(table_rows)

    def _get_next(self, cursor):
        return next(cursor, None)

    def _map_row(self, database: DatabaseInfo, table_row) -> dict:
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
                            'columns': table_row['columns'],
                        }
                    ],
                }
            ],
        }
