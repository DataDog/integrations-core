# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from datadog_checks.base.utils.db.schemas import SchemaCollector
from datadog_checks.postgres.schemas import DatabaseInfo, DatabaseObject, PostgresSchemaCollector

if TYPE_CHECKING:
    from datadog_checks.postgres import PostgreSql


PG_VIEWS_QUERY = """
SELECT c.oid                         AS view_id,
       c.relnamespace                AS schema_id,
       c.relname                     AS view_name,
       c.relowner::regrole::text     AS view_owner,
       c.relkind::text               AS relkind,
       pg_get_viewdef(c.oid, true)   AS definition
FROM   pg_class c
WHERE  c.relkind IN ('v', 'm')
"""


VIEW_COLUMNS_QUERY = """
SELECT attname                           AS name,
       format_type(atttypid, atttypmod)  AS data_type,
       NOT attnotnull                    AS nullable,
       pg_get_expr(adbin, adrelid)       AS default,
       attrelid                          AS view_id,
       attnum                            AS ordinal_position
FROM   pg_attribute
       LEFT JOIN pg_attrdef ad
              ON adrelid = attrelid
                 AND adnum = attnum
WHERE  attnum > 0
       AND NOT attisdropped
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
            views AS (
                {PG_VIEWS_QUERY}
            ),
            schema_views AS (
                SELECT schemas.schema_id, schemas.schema_name, schemas.schema_owner,
                    views.view_id, views.view_name, views.view_owner, views.relkind, views.definition
                FROM schemas
                INNER JOIN views ON schemas.schema_id = views.schema_id
                ORDER BY schemas.schema_name, views.view_name
                LIMIT {limit}
            ),
            columns AS (
                {VIEW_COLUMNS_QUERY}
            )

            SELECT schema_views.schema_id, schema_views.schema_name, schema_views.schema_owner,
                schema_views.view_id, schema_views.view_name, schema_views.view_owner,
                schema_views.relkind, schema_views.definition,
                array_agg(
                    json_build_object(
                        'data_type', columns.data_type,
                        'default', columns.default,
                        'name', columns.name,
                        'nullable', columns.nullable
                    ) ORDER BY columns.ordinal_position
                ) FILTER (WHERE columns.name IS NOT NULL) AS columns
            FROM schema_views
                LEFT JOIN columns ON schema_views.view_id = columns.view_id
            GROUP BY schema_views.schema_id, schema_views.schema_name, schema_views.schema_owner,
                schema_views.view_id, schema_views.view_name, schema_views.view_owner,
                schema_views.relkind, schema_views.definition
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
