# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from datadog_checks.base.utils.db.schemas import SchemaCollector
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.queries import SCHEMA_QUERY, VIEW_COLUMN_QUERY, VIEWS_QUERY
from datadog_checks.sqlserver.schemas import DatabaseInfo, DatabaseObject, SQLServerSchemaCollector

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer


class ViewColumnObjectBase(TypedDict):
    data_type: str
    name: str
    nullable: bool


class ViewColumnObject(ViewColumnObjectBase, total=False):
    default: str | None
    ordinal_position: str | None


class ViewObject(TypedDict):
    id: str
    name: str
    create_date: str
    modify_date: str
    definition: str | None
    columns: list[ViewColumnObject]


class ViewSchemaObject(TypedDict):
    name: str
    id: str
    owner_name: str
    tables: list
    views: list[ViewObject]


class SQLServerViewCollector(SQLServerSchemaCollector):
    _check: SQLServer

    def __init__(self, check: SQLServer):
        super().__init__(check)
        self._config.max_views = check._config.schema_config.get('max_views', 1000)

    @property
    def kind(self) -> str:
        return "sqlserver_views"

    @property
    def object_count_metric_name(self) -> str:
        return f"dd.{self._check.dbms}.schema.views_count"

    def _get_tables_query(self) -> str:
        limit = int(self._config.max_views or 1_000_000)
        query = f"""
            WITH
            schemas AS (
                {SCHEMA_QUERY}
            ),
            views AS (
                {VIEWS_QUERY}
            ),
            schema_views AS (
                SELECT TOP {limit} schemas.schema_name, schemas.schema_id, schemas.owner_name,
                    views.view_id, views.view_name, views.create_date, views.modify_date, views.definition
                FROM schemas
                INNER JOIN views ON schemas.schema_id = views.schema_id
                ORDER BY schemas.schema_name, views.view_name
            )
        """
        if self._is_2016_or_earlier:
            query += """
            SELECT schema_views.schema_id, schema_views.schema_name, schema_views.owner_name,
                schema_views.view_name, schema_views.view_id,
                schema_views.create_date, schema_views.modify_date, schema_views.definition
            FROM schema_views
            ;
        """
            return query

        query += f"""
            SELECT schema_views.schema_id, schema_views.schema_name, schema_views.owner_name,
                schema_views.view_name, schema_views.view_id,
                schema_views.create_date, schema_views.modify_date, schema_views.definition,
                json_query(({VIEW_COLUMN_QUERY} FOR JSON PATH), '$') AS columns
            FROM schema_views
            ;
        """
        return query

    def _map_row(self, database: DatabaseInfo, cursor_row) -> DatabaseObject:
        object = SchemaCollector._map_row(self, database, cursor_row)
        if self._is_2016_or_earlier:
            cursor = self._pre_2017_cursor
            if cursor is None:
                raise RuntimeError("pre-2017 view cursor is not initialized")
            view_id = str(cursor_row.get("view_id"))
            columns_query = VIEW_COLUMN_QUERY.replace("schema_views.view_id", view_id)
            cursor.execute(columns_query)
            columns = cursor.fetchall_dict()
        else:
            columns = json.loads(cursor_row.get("columns") or "[]")

        object["schemas"] = [
            {
                "name": cursor_row.get("schema_name"),
                "id": str(cursor_row.get("schema_id")),
                "owner_name": cursor_row.get("owner_name"),
                "tables": [],
                "views": [
                    {
                        "id": str(cursor_row.get("view_id")),
                        "name": cursor_row.get("view_name"),
                        "create_date": cursor_row.get("create_date"),
                        "modify_date": cursor_row.get("modify_date"),
                        "definition": cursor_row.get("definition"),
                        "columns": [column for column in columns if column.get("name") is not None],
                    }
                ],
            }
        ]
        return object
