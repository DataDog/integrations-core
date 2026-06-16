# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import Any

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig

DEFAULT_SCHEMAS_COLLECTION_INTERVAL = 3600
DEFAULT_MAX_TABLES = 300
DEFAULT_MAX_COLUMNS = 50
KEY_PREFIX = 'dbm-schemas-'
SYSTEM_SCHEMAS = ('SYSTOOLS', 'SYSPUBLIC', 'NULLID', 'SQLJ')

SCHEMAS_QUERY = """\
SELECT
    S.SCHEMANAME AS schema_name,
    S.OWNER AS schema_owner
FROM SYSCAT.SCHEMATA S
WHERE {schema_filter}
ORDER BY S.SCHEMANAME
"""

TABLES_QUERY = """\
SELECT
    T.TABSCHEMA AS schema_name,
    T.TABNAME AS table_name,
    T.OWNER AS table_owner,
    T.TYPE AS table_type,
    T.CARD AS estimated_rows
FROM SYSCAT.TABLES T
WHERE {schema_filter}
  AND T.TYPE = 'T'
  {table_filter}
ORDER BY T.TABSCHEMA, T.TABNAME
FETCH FIRST {max_tables} ROWS ONLY
"""

COLUMNS_QUERY = """\
SELECT
    C.TABSCHEMA AS schema_name,
    C.TABNAME AS table_name,
    C.COLNAME AS name,
    C.COLNO AS ordinal,
    C.TYPENAME AS typename,
    C.LENGTH AS length,
    C.SCALE AS scale,
    C.NULLS AS nulls,
    C.DEFAULT AS default_value
FROM SYSCAT.COLUMNS C
WHERE {table_filter}
ORDER BY C.TABSCHEMA, C.TABNAME, C.COLNO
"""

INDEXES_QUERY = """\
SELECT
    I.INDSCHEMA AS index_schema,
    I.INDNAME AS name,
    I.TABSCHEMA AS schema_name,
    I.TABNAME AS table_name,
    I.UNIQUERULE AS uniquerule,
    I.INDEXTYPE AS index_type,
    I.COLCOUNT AS column_count
FROM SYSCAT.INDEXES I
WHERE {table_filter}
ORDER BY I.TABSCHEMA, I.TABNAME, I.INDSCHEMA, I.INDNAME
"""

INDEX_COLUMNS_QUERY = """\
SELECT
    IC.INDSCHEMA AS index_schema,
    IC.INDNAME AS index_name,
    IC.COLNAME AS name,
    IC.COLSEQ AS ordinal,
    IC.COLORDER AS column_order
FROM SYSCAT.INDEXCOLUSE IC
JOIN SYSCAT.INDEXES I
  ON I.INDSCHEMA = IC.INDSCHEMA
 AND I.INDNAME = IC.INDNAME
WHERE {table_filter}
ORDER BY IC.INDSCHEMA, IC.INDNAME, IC.COLSEQ
"""

FOREIGN_KEYS_QUERY = """\
SELECT
    R.CONSTNAME AS name,
    R.TABSCHEMA AS schema_name,
    R.TABNAME AS table_name,
    R.REFTABSCHEMA AS referenced_schema_name,
    R.REFTABNAME AS referenced_table_name,
    R.REFKEYNAME AS referenced_key_name,
    R.DELETERULE AS delete_rule,
    R.UPDATERULE AS update_rule
FROM SYSCAT.REFERENCES R
WHERE {table_filter}
ORDER BY R.TABSCHEMA, R.TABNAME, R.CONSTNAME
"""

KEY_COLUMNS_QUERY = """\
SELECT
    K.CONSTNAME AS constraint_name,
    K.TABSCHEMA AS schema_name,
    K.TABNAME AS table_name,
    K.COLNAME AS name,
    K.COLSEQ AS ordinal
FROM SYSCAT.KEYCOLUSE K
WHERE {table_filter}
ORDER BY K.TABSCHEMA, K.TABNAME, K.CONSTNAME, K.COLSEQ
"""


class Db2SchemaCollectorConfig(SchemaCollectorConfig):
    max_tables: int
    max_columns: int
    include_schemas: list[str]
    exclude_schemas: list[str]
    include_tables: list[str]
    exclude_tables: list[str]
    max_query_duration: float


class Db2SchemaCollector(SchemaCollector):
    """Collect Db2 schema metadata from SYSCAT catalog views."""

    def __init__(self, check, config) -> None:
        schema_config = config.schemas_config
        collector_config = Db2SchemaCollectorConfig()
        collector_config.collection_interval = _positive_float(
            schema_config.get('collection_interval'), DEFAULT_SCHEMAS_COLLECTION_INTERVAL
        )
        collector_config.max_tables = _positive_int(schema_config.get('max_tables'), DEFAULT_MAX_TABLES)
        collector_config.max_columns = _positive_int(schema_config.get('max_columns'), DEFAULT_MAX_COLUMNS)
        collector_config.max_query_duration = _positive_float(
            schema_config.get('max_query_duration', schema_config.get('max_execution_time')), 60
        )
        collector_config.include_schemas = list(schema_config.get('include_schemas', []) or [])
        collector_config.exclude_schemas = list(schema_config.get('exclude_schemas', []) or [])
        collector_config.include_tables = list(schema_config.get('include_tables', []) or [])
        collector_config.exclude_tables = list(schema_config.get('exclude_tables', []) or [])
        super().__init__(check, collector_config)

    @property
    def kind(self) -> str:
        return 'db2_databases'

    def _get_databases(self) -> list[dict[str, str]]:
        return [{'name': self._check._config.db, 'id': self._check._config.db}]

    def _get_cursor(self, database):
        return Db2SchemaCursor(self._check, self._config)

    def _get_next(self, cursor):
        return cursor.next_table()

    def _map_row(self, database: dict[str, str], cursor_row) -> dict[str, Any]:
        schema, table = cursor_row
        row = super()._map_row(database, cursor_row)
        row['schemas'] = [
            _strip_none_values(
                {
                    'id': schema['name'],
                    'name': schema['name'],
                    'owner': schema.get('owner'),
                    'tables': [table] if table is not None else [],
                }
            )
        ]
        return row


class Db2SchemaCursor:
    """Adapter used by SchemaCollector around Db2's list-returning query API."""

    def __init__(self, check, config: Db2SchemaCollectorConfig) -> None:
        self._check = check
        self._config = config
        self._rows: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
        self._index = 0

    def __enter__(self):
        self._rows = self._load_rows()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self._rows = []

    def next_table(self):
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def _load_rows(self) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
        schemas = self._get_schemas()
        tables = self._get_tables()
        if not tables:
            return [(schema, None) for schema in schemas]

        table_keys = [(table['schema_name'], table['table_name']) for table in tables]
        columns = self._get_columns(table_keys)
        indexes = self._get_indexes(table_keys)
        foreign_keys = self._get_foreign_keys(table_keys)

        schema_by_name = {schema['name']: schema for schema in schemas}
        rows = []
        seen_schemas = set()
        for table in tables:
            schema_name = table['schema_name']
            schema = schema_by_name.get(schema_name, {'name': schema_name})
            seen_schemas.add(schema_name)
            rows.append((schema, _strip_none_values(self._build_table(table, columns, indexes, foreign_keys))))

        for schema in schemas:
            if schema['name'] not in seen_schemas:
                rows.append((schema, None))
        return rows

    def _get_schemas(self) -> list[dict[str, Any]]:
        schema_filter, params = self._schema_filter('S.SCHEMANAME')
        query = SCHEMAS_QUERY.format(schema_filter=schema_filter)
        rows, _ = self._check.connection.query(KEY_PREFIX, query, params=params)
        return [
            _strip_none_values({'name': row.get('schema_name'), 'owner': row.get('schema_owner')})
            for row in _lowercase_rows(rows)
            if row.get('schema_name')
        ]

    def _get_tables(self) -> list[dict[str, Any]]:
        schema_filter, schema_params = self._schema_filter('T.TABSCHEMA')
        table_filter, table_params = self._like_filter(
            'T.TABNAME', self._config.include_tables, self._config.exclude_tables
        )
        if table_filter:
            table_filter = 'AND ' + table_filter
        query = TABLES_QUERY.format(
            schema_filter=schema_filter,
            table_filter=table_filter,
            max_tables=int(self._config.max_tables),
        )
        rows, _ = self._check.connection.query(KEY_PREFIX, query, params=schema_params + table_params)
        return _lowercase_rows(rows)

    def _get_columns(self, table_keys: list[tuple[Any, Any]]) -> dict[tuple[Any, Any], list[dict[str, Any]]]:
        query, params = self._table_scoped_query(COLUMNS_QUERY, 'C', table_keys)
        rows, _ = self._check.connection.query(KEY_PREFIX, query, params=params)
        columns: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
        for row in _lowercase_rows(rows):
            key = (row.get('schema_name'), row.get('table_name'))
            columns.setdefault(key, []).append(
                _strip_none_values(
                    {
                        'name': row.get('name'),
                        'data_type': _render_data_type(row.get('typename'), row.get('length'), row.get('scale')),
                        'nullable': row.get('nulls') == 'Y',
                        'default': row.get('default_value'),
                        'ordinal': row.get('ordinal'),
                    }
                )
            )
        return columns

    def _get_indexes(self, table_keys: list[tuple[Any, Any]]) -> dict[tuple[Any, Any], list[dict[str, Any]]]:
        index_query, params = self._table_scoped_query(INDEXES_QUERY, 'I', table_keys)
        index_rows, _ = self._check.connection.query(KEY_PREFIX, index_query, params=params)
        column_query, params = self._table_scoped_query(INDEX_COLUMNS_QUERY, 'I', table_keys)
        column_rows, _ = self._check.connection.query(KEY_PREFIX, column_query, params=params)

        columns_by_index: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
        for row in _lowercase_rows(column_rows):
            key = (row.get('index_schema'), row.get('index_name'))
            columns_by_index.setdefault(key, []).append(row)

        indexes: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
        for row in _lowercase_rows(index_rows):
            table_key = (row.get('schema_name'), row.get('table_name'))
            index_key = (row.get('index_schema'), row.get('name'))
            index_columns = columns_by_index.get(index_key, [])
            index = _strip_none_values(
                {
                    'name': row.get('name'),
                    'is_unique': row.get('uniquerule') in ('P', 'U'),
                    'is_primary': row.get('uniquerule') == 'P',
                    'index_type': row.get('index_type'),
                    'columns': [column.get('name') for column in index_columns if column.get('column_order') != 'I'],
                    'included_columns': [
                        column.get('name') for column in index_columns if column.get('column_order') == 'I'
                    ],
                    'definition': _index_definition(row, index_columns),
                }
            )
            indexes.setdefault(table_key, []).append(index)
        return indexes

    def _get_foreign_keys(self, table_keys: list[tuple[Any, Any]]) -> dict[tuple[Any, Any], list[dict[str, Any]]]:
        fk_query, params = self._table_scoped_query(FOREIGN_KEYS_QUERY, 'R', table_keys)
        fk_rows, _ = self._check.connection.query(KEY_PREFIX, fk_query, params=params)
        fk_rows = _lowercase_rows(fk_rows)
        if not fk_rows:
            return {}

        key_scope = _foreign_key_column_scope(table_keys, fk_rows)
        if not key_scope:
            return {}

        key_query, params = self._table_scoped_query(KEY_COLUMNS_QUERY, 'K', key_scope)
        key_rows, _ = self._check.connection.query(KEY_PREFIX, key_query, params=params)
        columns_by_constraint: dict[tuple[Any, Any, Any], list[str]] = {}
        for row in _lowercase_rows(key_rows):
            key = (row.get('schema_name'), row.get('table_name'), row.get('constraint_name'))
            columns_by_constraint.setdefault(key, []).append(row.get('name'))

        foreign_keys: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
        for row in fk_rows:
            table_key = (row.get('schema_name'), row.get('table_name'))
            column_names = columns_by_constraint.get(
                (row.get('schema_name'), row.get('table_name'), row.get('name')), []
            )
            referenced_column_names = columns_by_constraint.get(
                (
                    row.get('referenced_schema_name'),
                    row.get('referenced_table_name'),
                    row.get('referenced_key_name'),
                ),
                [],
            )
            foreign_key = _strip_none_values(
                {
                    'name': row.get('name'),
                    'referenced_table': _qualified_name(
                        row.get('referenced_schema_name'), row.get('referenced_table_name')
                    ),
                    'column_names': column_names,
                    'referenced_column_names': referenced_column_names,
                    'definition': _foreign_key_definition(row, column_names, referenced_column_names),
                }
            )
            foreign_keys.setdefault(table_key, []).append(foreign_key)
        return foreign_keys

    def _build_table(
        self,
        table: dict[str, Any],
        columns: dict[tuple[Any, Any], list[dict[str, Any]]],
        indexes: dict[tuple[Any, Any], list[dict[str, Any]]],
        foreign_keys: dict[tuple[Any, Any], list[dict[str, Any]]],
    ) -> dict[str, Any]:
        table_key = (table.get('schema_name'), table.get('table_name'))
        return {
            'id': _qualified_name(*table_key),
            'name': table.get('table_name'),
            'owner': table.get('table_owner'),
            'columns': columns.get(table_key, [])[: self._config.max_columns],
            'indexes': indexes.get(table_key, []),
            'foreign_keys': foreign_keys.get(table_key, []),
            'table_type': table.get('table_type'),
            'estimated_rows': table.get('estimated_rows'),
        }

    def _schema_filter(self, column: str) -> tuple[str, list[Any]]:
        clauses = [
            f"UPPER({column}) NOT LIKE 'SYS%'",
            f"UPPER({column}) NOT IN ({', '.join(repr(schema) for schema in SYSTEM_SCHEMAS)})",
        ]
        like_filter, params = self._like_filter(column, self._config.include_schemas, self._config.exclude_schemas)
        if like_filter:
            clauses.append(like_filter)
        return ' AND '.join(clauses), params

    @staticmethod
    def _like_filter(column: str, include_patterns: list[str], exclude_patterns: list[str]) -> tuple[str, list[Any]]:
        clauses = []
        params: list[Any] = []
        for pattern in exclude_patterns:
            clauses.append(f'UPPER({column}) NOT LIKE UPPER(?)')
            params.append(pattern)
        if include_patterns:
            clauses.append('(' + ' OR '.join(f'UPPER({column}) LIKE UPPER(?)' for _ in include_patterns) + ')')
            params.extend(include_patterns)
        return ' AND '.join(clauses), params

    @staticmethod
    def _table_scoped_query(query: str, alias: str, table_keys: list[tuple[Any, Any]]) -> tuple[str, list[Any]]:
        table_filter = _table_filter(alias, table_keys)
        return query.format(table_filter=table_filter), [value for key in table_keys for value in key]


def _table_filter(alias: str, table_keys: list[tuple[Any, Any]]) -> str:
    return '(' + ' OR '.join(f'({alias}.TABSCHEMA = ? AND {alias}.TABNAME = ?)' for _ in table_keys) + ')'


def _foreign_key_column_scope(
    table_keys: list[tuple[Any, Any]], foreign_keys: list[dict[str, Any]]
) -> list[tuple[Any, Any]]:
    scope = set(table_keys)
    for row in foreign_keys:
        scope.add((row.get('referenced_schema_name'), row.get('referenced_table_name')))
    return sorted(key for key in scope if all(key))


def _render_data_type(typename: Any, length: Any, scale: Any) -> str | None:
    if typename is None:
        return None

    typename = str(typename).upper()
    if typename in {'DECIMAL', 'NUMERIC'} and length is not None and scale is not None:
        return '{}({},{})'.format(typename, length, scale)
    if typename in {'CHAR', 'CHARACTER', 'VARCHAR', 'GRAPHIC', 'VARGRAPHIC'} and length is not None:
        return '{}({})'.format(typename, length)
    return typename


def _index_definition(row: dict[str, Any], columns: list[dict[str, Any]]) -> str | None:
    key_columns = [column for column in columns if column.get('column_order') != 'I']
    if not row.get('name') or not key_columns:
        return None

    unique = 'UNIQUE ' if row.get('uniquerule') in ('P', 'U') else ''
    column_definitions = ', '.join(_index_column_definition(column) for column in key_columns)
    definition = 'CREATE {}INDEX {} ON {} ({})'.format(
        unique,
        _qualified_identifier(row.get('index_schema'), row.get('name')),
        _qualified_identifier(row.get('schema_name'), row.get('table_name')),
        column_definitions,
    )
    included_columns = [column for column in columns if column.get('column_order') == 'I']
    if included_columns:
        definition += ' INCLUDE ({})'.format(
            ', '.join(_quote_identifier(column.get('name')) for column in included_columns)
        )
    return definition


def _index_column_definition(column: dict[str, Any]) -> str:
    direction = ' DESC' if column.get('column_order') == 'D' else ' ASC'
    return _quote_identifier(column.get('name')) + direction


def _foreign_key_definition(
    row: dict[str, Any], column_names: list[str], referenced_column_names: list[str]
) -> str | None:
    if not row.get('name') or not column_names:
        return None

    definition = 'FOREIGN KEY ({}) REFERENCES {} ({})'.format(
        ', '.join(_quote_identifier(column) for column in column_names),
        _qualified_identifier(row.get('referenced_schema_name'), row.get('referenced_table_name')),
        ', '.join(_quote_identifier(column) for column in referenced_column_names),
    )
    delete_rule = _rule_name(row.get('delete_rule'))
    update_rule = _rule_name(row.get('update_rule'))
    if delete_rule:
        definition += ' ON DELETE {}'.format(delete_rule)
    if update_rule:
        definition += ' ON UPDATE {}'.format(update_rule)
    return definition


def _rule_name(rule: Any) -> str | None:
    return {'A': 'NO ACTION', 'C': 'CASCADE', 'N': 'SET NULL', 'R': 'RESTRICT'}.get(rule)


def _qualified_name(schema: Any, name: Any) -> str | None:
    if schema is None or name is None:
        return None
    return '{}.{}'.format(schema, name)


def _qualified_identifier(schema: Any, name: Any) -> str:
    return '{}.{}'.format(_quote_identifier(schema), _quote_identifier(name))


def _quote_identifier(identifier: Any) -> str:
    return '"{}"'.format(str(identifier).replace('"', '""'))


def _lowercase_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{str(key).lower(): value for key, value in row.items()} for row in rows]


def _strip_none_values(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if value is not None}


def _positive_float(value: Any, default: float) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _positive_int(value: Any, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default
