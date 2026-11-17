# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from datadog_checks.postgres.schemas import (
    COLUMNS_QUERY,
    PG_INDEXES_QUERY,
    DatabaseInfo,
    DatabaseObject,
    PostgresSchemaCollector,
)

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql

VIEW_PAYLOAD_CHUNK_SIZE = 500

PG_VIEWS_QUERY = """
SELECT c.oid                         AS view_id,
       c.relnamespace                AS schema_id,
       c.relname                     AS view_name,
       c.relowner :: regrole :: text AS view_owner,
       c.relkind::text               AS relkind
FROM   pg_class c
WHERE  c.relkind IN ( 'v', 'm' )
"""


class ViewObject(TypedDict, total=False):
    id: str
    name: str
    owner: str
    relkind: str
    definition: str
    columns: list
    indexes: list


class ViewSchemaObject(TypedDict, total=False):
    id: str
    name: str
    owner: str
    tables: list
    views: list[ViewObject]


class PostgresViewCollector(PostgresSchemaCollector):
    def __init__(self, check: PostgreSql):
        super().__init__(check)
        self._max_views = int(check._config.collect_schemas.max_views or 0)
        self._config.payload_chunk_size = VIEW_PAYLOAD_CHUNK_SIZE

    @property
    def kind(self) -> str:
        return "pg_views"

    @property
    def object_count_metric_name(self) -> str:
        return f"dd.{self._check.dbms}.schema.views_count"

    def get_rows_query(self):
        schemas_query, schemas_params = self._get_schemas_query()
        limit = int(self._max_views or 1_000_000)
        query = f"""
            WITH
            schemas AS (
                {schemas_query}
            ),
            views AS (
                {PG_VIEWS_QUERY}
            ),
            schema_views AS (
                SELECT schemas.schema_id, schemas.schema_name, schemas.schema_owner,
                views.view_id, views.view_name, views.view_owner, views.relkind
                FROM schemas
                JOIN views ON schemas.schema_id = views.schema_id
                ORDER BY schemas.schema_name, views.view_name
                LIMIT {limit}
            ),
            columns AS (
                {COLUMNS_QUERY}
            ),
            indexes AS (
                {PG_INDEXES_QUERY}
            )

            SELECT schema_views.schema_id, schema_views.schema_name, schema_views.schema_owner,
            schema_views.view_id, schema_views.view_name, schema_views.view_owner, schema_views.relkind,
                pg_get_viewdef(schema_views.view_id) AS definition,
                array_agg(row_to_json(columns.*)) FILTER (WHERE columns.name IS NOT NULL) AS columns,
                array_agg(row_to_json(indexes.*)) FILTER (WHERE indexes.name IS NOT NULL) AS indexes
            FROM schema_views
                LEFT JOIN columns ON schema_views.view_id = columns.table_id
                LEFT JOIN indexes ON schema_views.view_id = indexes.table_id
            GROUP BY schema_views.schema_id, schema_views.schema_name, schema_views.schema_owner,
                schema_views.view_id, schema_views.view_name, schema_views.view_owner, schema_views.relkind
            ;
        """
        return query, schemas_params

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        view = {
            "id": str(cursor_row.get("view_id")),
            "name": cursor_row.get("view_name"),
            "owner": cursor_row.get("view_owner"),
            "relkind": cursor_row.get("relkind"),
            "definition": cursor_row.get("definition"),
            "columns": list({v['name']: v for v in cursor_row.get("columns") or []}.values())[
                : self._config.max_columns
            ],
            "indexes": list({v['name']: v for v in cursor_row.get("indexes") or []}.values()),
        }
        schema = {
            "id": str(cursor_row.get("schema_id")),
            "name": cursor_row.get("schema_name"),
            "owner": cursor_row.get("schema_owner"),
            "tables": [],
            "views": [{k: v for k, v in view.items() if v is not None}],
        }
        return {**database, "schemas": [{k: v for k, v in schema.items() if v is not None}]}
