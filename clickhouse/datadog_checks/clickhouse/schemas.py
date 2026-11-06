# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from datadog_checks.clickhouse import ClickhouseCheck

from datadog_checks.base.utils.db.schemas import SchemaCollector, SchemaCollectorConfig

_SYSTEM_DATABASE_NAMES = ("'system'", "'INFORMATION_SCHEMA'", "'information_schema'")

# Single stub so the base-class loop runs exactly once; actual database names
# come from the `database` column of each cursor row.
_CLUSTER_STUB = {'name': '_cluster_'}

_TABLES_COLUMNS_QUERY = """\
WITH
tables AS (
    SELECT
        database,
        name,
        engine,
        toString(uuid) AS uuid,
        create_table_query,
        sorting_key,
        partition_key,
        primary_key,
        sampling_key,
        toInt64(toUnixTimestamp(metadata_modification_time)) AS metadata_modified_at
    FROM {tables_table}
    WHERE database NOT IN ({system_dbs})
      {db_filters}
      {table_filters}
    ORDER BY database, name
    LIMIT 1 BY (database, name)
    LIMIT {max_tables}
),
columns AS (
    SELECT database, table, name, type, default_expression, comment, toInt32(position) AS position
    FROM {columns_table}
    WHERE (database, table) IN (SELECT database, name FROM tables)
    ORDER BY database, table, position
    LIMIT 1 BY (database, table, name)
    LIMIT {limit_columns}
)
SELECT
    t.database,
    t.name,
    t.engine,
    t.uuid,
    t.create_table_query,
    t.sorting_key,
    t.partition_key,
    t.primary_key,
    t.sampling_key,
    t.metadata_modified_at,
    groupArrayIf({max_columns})(
        tuple(c.name, c.type, c.default_expression, c.comment, c.position),
        c.name IS NOT NULL
    ) AS columns
FROM tables t
LEFT JOIN columns c ON t.database = c.database AND t.name = c.table
GROUP BY
    t.database, t.name, t.engine, t.uuid, t.create_table_query,
    t.sorting_key, t.partition_key, t.primary_key, t.sampling_key,
    t.metadata_modified_at
ORDER BY t.database, t.name
"""


class ClickhouseSchemaCollectorConfig(SchemaCollectorConfig):
    max_tables: int
    max_columns: int
    max_query_duration: int
    include_databases: tuple[str, ...]
    exclude_databases: tuple[str, ...]
    include_tables: tuple[str, ...]
    exclude_tables: tuple[str, ...]


class ClickhouseSchemaCollector(SchemaCollector):
    """Collects ClickHouse schema metadata via a single CTE query per cycle."""

    _check: ClickhouseCheck
    _config: ClickhouseSchemaCollectorConfig

    def __init__(self, check: ClickhouseCheck):
        config = ClickhouseSchemaCollectorConfig()
        config.collection_interval = check._config.collect_schemas.collection_interval
        config.max_tables = check._config.collect_schemas.max_tables
        config.max_columns = check._config.collect_schemas.max_columns
        config.max_query_duration = check._config.collect_schemas.max_query_duration
        config.include_databases = check._config.collect_schemas.include_databases
        config.exclude_databases = check._config.collect_schemas.exclude_databases
        config.include_tables = check._config.collect_schemas.include_tables
        config.exclude_tables = check._config.collect_schemas.exclude_tables

        super().__init__(check, config)
        self._db_client = None
        self._cancel_event = None

    @property
    def kind(self) -> str:
        return 'clickhouse_databases'

    @property
    def base_event(self) -> dict[str, Any]:
        event = super().base_event
        event['collector_id'] = self._check.check_id
        return event

    def close(self) -> None:
        if self._db_client:
            try:
                self._db_client.close()
            except Exception as e:
                self._log.debug("Error closing schema collector client: %s", e)
            self._db_client = None

    def _check_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise Exception("Job loop cancelled. Aborting query.")

    def _get_databases(self) -> list[dict[str, str]]:
        return [_CLUSTER_STUB]

    @contextlib.contextmanager
    def _get_cursor(self, _database_name: str):
        self._db_client = self._check.create_dbm_client()
        self._db_client.set_client_setting('max_execution_time', self._config.max_query_duration)
        try:
            db_filters, db_params = _build_match_clauses(
                'database', self._config.include_databases, self._config.exclude_databases, 'db'
            )
            table_filters, table_params = _build_match_clauses(
                'name', self._config.include_tables, self._config.exclude_tables, 'table'
            )

            # Only structural pieces (trusted system-table identifiers and
            # validated integer limits) are interpolated; user-supplied regex
            # patterns are bound as query parameters below.
            fmt = {
                'tables_table': self._check.get_system_table('tables'),
                'columns_table': self._check.get_system_table('columns'),
                'system_dbs': ", ".join(_SYSTEM_DATABASE_NAMES),
                'max_tables': self._config.max_tables,
                'max_columns': self._config.max_columns,
                'limit_columns': self._config.max_tables * self._config.max_columns,
                'db_filters': db_filters,
                'table_filters': table_filters,
            }
            query_parameters = {**db_params, **table_params}
            self._check_cancelled()
            with self._db_client.query_rows_stream(
                _TABLES_COLUMNS_QUERY.format(**fmt), parameters=query_parameters
            ) as stream:
                yield stream
        finally:
            self.close()

    def _get_next(self, cursor) -> tuple | None:
        return next(cursor, None)

    def _map_row(self, _database: dict[str, str], cursor_row: tuple) -> dict[str, Any]:
        # Tables and views are emitted in a single `tables` list, matching the
        # canonical DBM schema payload shape (postgres/mysql/sqlserver). The
        # `engine` field on each item distinguishes views (View, MaterializedView,
        # LiveView, WindowView) from regular tables.
        actual_db_name = cursor_row[0]
        return {'name': actual_db_name, 'tables': [self._build_item(cursor_row)]}

    def _build_item(self, row: tuple) -> dict[str, Any]:
        (
            database,
            name,
            engine,
            uuid_str,
            create_query,
            sorting_key,
            partition_key,
            primary_key,
            sampling_key,
            metadata_modified_at,
            raw_columns,
        ) = row
        cols = [
            {
                'name': col[0],
                'type': col[1],
                'default': col[2] or '',
                'comment': col[3] or '',
                'position': int(col[4] or 0),
            }
            for col in (raw_columns or [])
        ]
        return {
            'name': name,
            'engine': engine,
            'uuid': uuid_str,
            'sorting_key': sorting_key or '',
            'partition_key': partition_key or '',
            'primary_key': primary_key or '',
            'sampling_key': sampling_key or '',
            'create_query': create_query,
            'columns': cols,
            'metadata_modified_at': int(metadata_modified_at or 0),
            'is_refreshable': 'REFRESH' in (create_query or '').upper(),
        }


def _build_match_clauses(
    column: str,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
    param_prefix: str,
) -> tuple[str, dict[str, str]]:
    """Build regex match clauses using bound query parameters rather than string
    interpolation, so user-supplied patterns cannot be used for SQL injection.

    Returns the clause text (with ``{name:String}`` placeholders) and the dict of
    parameter values to pass to ``query_rows_stream(parameters=...)``.
    """
    clauses: list[str] = []
    params: dict[str, str] = {}
    for i, pattern in enumerate(exclude_patterns):
        key = f'{param_prefix}_exclude_{i}'
        clauses.append(f"AND NOT match({column}, {{{key}:String}})")
        params[key] = pattern
    if include_patterns:
        ors = []
        for i, pattern in enumerate(include_patterns):
            key = f'{param_prefix}_include_{i}'
            ors.append(f"match({column}, {{{key}:String}})")
            params[key] = pattern
        clauses.append(f"AND ({' OR '.join(ors)})")
    return "\n  ".join(clauses), params
