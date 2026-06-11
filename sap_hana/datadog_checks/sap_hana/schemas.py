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

CURRENT_DATABASE_QUERY = "SELECT DATABASE_NAME FROM SYS.M_DATABASE"
CURRENT_DATABASE_DESCRIPTION_QUERY = "SELECT DESCRIPTION FROM SYS.M_DATABASE"

# Single query that filters and caps tables in the database (not in Python) and joins their columns.
# The limited_tables CTE applies the schema filters and max_tables LIMIT before the column join, so
# the server never returns more than max_tables tables' worth of rows. Results are ordered so each
# table's columns arrive contiguously and can be assembled one table at a time while streaming the
# cursor. System schemas are excluded here; '_' is a LIKE wildcard, so '_SYS_' is escaped.
SCHEMA_TABLES_QUERY = r"""
WITH limited_tables AS (
    SELECT t.SCHEMA_NAME, t.TABLE_NAME, t.TABLE_TYPE, t.IS_COLUMN_TABLE, s.SCHEMA_OWNER
    FROM SYS.TABLES t
    LEFT JOIN SYS.SCHEMAS s ON s.SCHEMA_NAME = t.SCHEMA_NAME
    WHERE t.IS_TEMPORARY = 'FALSE'
      AND t.IS_SYSTEM_TABLE = 'FALSE'
      AND t.SCHEMA_NAME NOT IN ('SYS', 'SYSTEM', 'PUBLIC')
      AND t.SCHEMA_NAME NOT LIKE '\_SYS\_%' ESCAPE '\'
      {include_clause}
      {exclude_clause}
    ORDER BY t.SCHEMA_NAME, t.TABLE_NAME
    LIMIT {max_tables}
),
limited_columns AS (
    SELECT c.SCHEMA_NAME, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE_NAME,
           c.IS_NULLABLE, c.DEFAULT_VALUE, c.POSITION,
           ROW_NUMBER() OVER (PARTITION BY c.SCHEMA_NAME, c.TABLE_NAME ORDER BY c.POSITION) AS rn
    FROM SYS.TABLE_COLUMNS c
    INNER JOIN limited_tables lt ON lt.SCHEMA_NAME = c.SCHEMA_NAME AND lt.TABLE_NAME = c.TABLE_NAME
)
SELECT lt.SCHEMA_NAME, lt.TABLE_NAME, lt.TABLE_TYPE, lt.IS_COLUMN_TABLE, lt.SCHEMA_OWNER,
       lc.COLUMN_NAME, lc.DATA_TYPE_NAME, lc.IS_NULLABLE, lc.DEFAULT_VALUE, lc.POSITION
FROM limited_tables lt
LEFT JOIN limited_columns lc
  ON lc.SCHEMA_NAME = lt.SCHEMA_NAME AND lc.TABLE_NAME = lt.TABLE_NAME
  AND lc.rn <= {max_columns}
ORDER BY lt.SCHEMA_NAME, lt.TABLE_NAME, lc.POSITION
"""


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
        self._pending_row = None

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

    def _build_query(self):
        """Build the schema/tables/columns query with schema filters and the table cap pushed into SQL."""
        include_clause = ''
        exclude_clause = ''
        params = []
        if self._config.include_schemas:
            include = sorted(self._config.include_schemas)
            placeholders = ', '.join('?' for _ in include)
            include_clause = 'AND t.SCHEMA_NAME IN ({})'.format(placeholders)
            params.extend(include)
        if self._config.exclude_schemas:
            exclude = sorted(self._config.exclude_schemas)
            placeholders = ', '.join('?' for _ in exclude)
            exclude_clause = 'AND t.SCHEMA_NAME NOT IN ({})'.format(placeholders)
            params.extend(exclude)
        query = SCHEMA_TABLES_QUERY.format(
            include_clause=include_clause,
            exclude_clause=exclude_clause,
            max_tables=int(self._config.max_tables),
            max_columns=int(self._config.max_columns),
        )
        return query, tuple(params)

    @contextlib.contextmanager
    def _get_cursor(self, _database_name):
        conn = self._check._conn
        query, params = self._build_query()
        with closing(conn.cursor()) as cursor:
            cursor.execute(query, params)
            self._pending_row = cursor.fetchone()
            try:
                yield cursor
            finally:
                self._pending_row = None

    def _get_next(self, cursor):
        """Assemble one table from consecutive cursor rows sharing the same (schema, table) key."""
        row = self._pending_row
        if row is None:
            return None
        schema_name, table_name = row[0], row[1]
        table_type, is_column_table, schema_owner = row[2], row[3], row[4]
        columns = []
        while row is not None and row[0] == schema_name and row[1] == table_name:
            column_name = row[5]
            if column_name is not None and len(columns) < self._config.max_columns:
                columns.append(
                    {
                        'name': column_name,
                        'data_type': row[6] or '',
                        'nullable': row[7] == 'TRUE',
                        'default': row[8],
                        'position': row[9],
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
            'columns': columns,
        }

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
