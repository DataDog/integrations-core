# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from datadog_checks.base.utils.db.schemas import SchemaCollector
from datadog_checks.postgres.schemas import DatabaseInfo, DatabaseObject, PostgresSchemaCollector

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql


VIEW_COLUMNS_QUERY = """
SELECT a.attname                            AS name,
       format_type(a.atttypid, a.atttypmod) AS data_type,
       NOT a.attnotnull                     AS nullable,
       pg_get_expr(ad.adbin, ad.adrelid)    AS default,
       selected_views.view_id,
       a.attnum                            AS ordinal_position
FROM   selected_views
       INNER JOIN pg_attribute a
               ON a.attrelid = selected_views.view_id
       LEFT JOIN pg_attrdef ad
              ON ad.adrelid = a.attrelid
                 AND ad.adnum = a.attnum
WHERE  a.attnum > 0
       AND NOT a.attisdropped
"""


class ViewColumnObject(TypedDict):
    data_type: str
    default: str | None
    name: str
    nullable: bool


class ViewObject(TypedDict):
    columns: list[ViewColumnObject]
    definition: str | None
    id: str
    name: str
    owner: str
    relkind: str


class ViewSchemaObject(TypedDict):
    id: str
    name: str
    owner: str
    tables: list
    views: list[ViewObject]


class PostgresViewCollector(PostgresSchemaCollector):
    _check: PostgreSql

    def __init__(self, check: PostgreSql):
        super().__init__(check)
        self._max_views = int(check._config.collect_schemas.max_views or 1000)

    @property
    def kind(self) -> str:
        return "pg_views"

    @property
    def object_count_metric_name(self) -> str:
        return f"dd.{self._check.dbms}.schema.views_count"

    def get_rows_query(self) -> tuple[str, list[str]]:
        schemas_query, schemas_params = self._get_schemas_query()
        limit = self._max_views or 1_000_000
        query = f"""
            WITH
            schemas AS (
                {schemas_query}
            ),
            selected_views AS (
                SELECT schemas.schema_id, schemas.schema_name, schemas.schema_owner,
                    c.oid AS view_id, c.relname AS view_name,
                    c.relowner::regrole::text AS view_owner, c.relkind::text AS relkind
                FROM schemas
                INNER JOIN pg_class c ON schemas.schema_id = c.relnamespace
                WHERE c.relkind IN ('v', 'm')
                ORDER BY schemas.schema_name, c.relname
                LIMIT {limit}
            ),
            views AS (
                SELECT selected_views.*,
                    pg_get_viewdef(selected_views.view_id, true) AS definition
                FROM selected_views
            ),
            columns AS (
                {VIEW_COLUMNS_QUERY}
            )

            SELECT views.schema_id, views.schema_name, views.schema_owner,
                views.view_id, views.view_name, views.view_owner,
                views.relkind, views.definition,
                array_agg(
                    json_build_object(
                        'data_type', columns.data_type,
                        'default', columns.default,
                        'name', columns.name,
                        'nullable', columns.nullable
                    ) ORDER BY columns.ordinal_position
                ) FILTER (WHERE columns.name IS NOT NULL) AS columns
            FROM views
                LEFT JOIN columns ON views.view_id = columns.view_id
            GROUP BY views.schema_id, views.schema_name, views.schema_owner,
                views.view_id, views.view_name, views.view_owner,
                views.relkind, views.definition
            ;
        """
        return query, schemas_params

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        object = SchemaCollector._map_row(self, database, cursor_row)
        object["schemas"] = [
            {
                "id": str(cursor_row.get("schema_id")),
                "name": cursor_row.get("schema_name"),
                "owner": cursor_row.get("schema_owner"),
                "tables": [],
                "views": [
                    {
                        "columns": (cursor_row.get("columns") or [])[: self._config.max_columns],
                        "definition": cursor_row.get("definition"),
                        "id": str(cursor_row.get("view_id")),
                        "name": cursor_row.get("view_name"),
                        "owner": cursor_row.get("view_owner"),
                        "relkind": cursor_row.get("relkind"),
                    }
                ],
            }
        ]
        return object
