# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import contextlib
import json
import time
from typing import Any, Iterator

import psycopg
from psycopg_pool import ConnectionPool

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.db.sql_commenter import add_sql_comment
from datadog_checks.base.utils.db.utils import default_json_event_encoding
from datadog_checks.do_query_actions.config_models import ConfigMixin
from datadog_checks.do_query_actions.postgres_connection import (
    AWSTokenProvider,
    AzureTokenProvider,
    PostgresConnectionArgs,
    TokenAwareConnection,
)

EVENT_TRACK_TYPE = 'do-query-results'


class DoQueryCursor(psycopg.Cursor):
    """psycopg cursor that prepends a SQL comment identifying the Datadog Agent."""

    _COMMENT_ATTRS = {'service': 'datadog-agent'}

    def execute(self, query, params=None, **kwargs):
        if isinstance(query, str):
            query = add_sql_comment(query, prepand=True, **self._COMMENT_ATTRS)
        return super().execute(query, params, **kwargs)


class DOQueryActionsCheck(AgentCheck, ConfigMixin):
    """Execute SQL queries against databases on individual schedules."""

    __NAMESPACE__ = 'do_query_actions'
    QUERY_STATUS_METRIC = 'query_status'

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)
        self._last_execution: dict[int, float] = {}
        self._pool: ConnectionPool | None = None

    def _build_base_tags(self) -> list[str]:
        tags = list(self.config.tags) if self.config.tags else []
        if self.config.config_id:
            tags.append(f'config_id:{self.config.config_id}')
        if self.config.db_type:
            tags.append(f'db_type:{self.config.db_type}')
        if self.config.db_identifier.dbname:
            tags.append(f'db_name:{self.config.db_identifier.dbname}')
        if self.config.db_identifier.host:
            tags.append(f'db_host:{self.config.db_identifier.host}')
        if self.config.port:
            tags.append(f'port:{self.config.port}')
        return tags

    def _build_token_provider(self) -> AWSTokenProvider | AzureTokenProvider | None:
        aws = self.config.aws
        if aws and aws.managed_authentication and aws.managed_authentication.enabled:
            return AWSTokenProvider(
                host=self.config.db_identifier.host,
                port=self.config.port or 5432,
                username=self.config.username,
                region=aws.region or '',
                role_arn=aws.managed_authentication.role_arn,
            )

        managed_auth = self.config.managed_authentication
        if managed_auth and managed_auth.enabled:
            return AzureTokenProvider(
                client_id=managed_auth.client_id or '',
                identity_scope=managed_auth.identity_scope,
            )

        return None

    def _create_postgres_pool(self) -> ConnectionPool:
        conn_args = PostgresConnectionArgs(
            username=self.config.username,
            host=self.config.db_identifier.host,
            port=self.config.port,
            password=self.config.password,
            ssl_mode=self.config.ssl,
            ssl_cert=self.config.ssl_cert,
            ssl_root_cert=self.config.ssl_root_cert,
            ssl_key=self.config.ssl_key,
            ssl_password=self.config.ssl_password,
        )
        kwargs = conn_args.as_kwargs(dbname=self.config.db_identifier.dbname)
        kwargs['autocommit'] = True
        kwargs['cursor_factory'] = DoQueryCursor

        token_provider = self._build_token_provider()
        if token_provider:
            kwargs['token_provider'] = token_provider

        return ConnectionPool(
            conninfo='',
            kwargs=kwargs,
            connection_class=TokenAwareConnection,
            min_size=1,
            max_size=1,
            open=True,
            reconnect_timeout=60,
        )

    def _get_or_create_postgres_pool(self) -> ConnectionPool:
        if self._pool is None:
            self.log.debug(
                "Creating connection pool for %s:%s/%s",
                self.config.db_identifier.host,
                self.config.port,
                self.config.db_identifier.dbname,
            )
            self._pool = self._create_postgres_pool()
        return self._pool

    @contextlib.contextmanager
    def _acquire_connection(self) -> Iterator[Any]:
        if self.config.db_type != 'postgres':
            raise ValueError(f"Unsupported db_type: {self.config.db_type!r}. Only 'postgres' is supported.")
        with self._get_or_create_postgres_pool().connection() as conn:
            yield conn

    def _get_due_queries(self) -> list[Any]:
        now = time.time()
        due = []
        for q in self.config.queries:
            last_run = self._last_execution.get(q.monitor_id, 0.0)
            if now - last_run >= q.interval_seconds:
                due.append(q)
        return due

    def _set_query_timeout(self, conn: Any, timeout_seconds: int) -> None:
        timeout_ms = int(timeout_seconds) * 1000
        with conn.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {timeout_ms}")

    def _execute_single_query(self, conn: Any, query_spec: Any) -> dict[str, Any]:
        """Execute a single query and return a structured result dict."""
        sql = query_spec.query
        timeout = query_spec.timeout_seconds
        monitor_id = query_spec.monitor_id
        start = time.time()

        try:
            self._set_query_timeout(conn, timeout)
            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = [list(row) for row in cursor.fetchall()] if cursor.description else []
            duration = time.time() - start
            return {
                'status': 'success',
                'columns': columns,
                'rows': rows,
                'row_count': len(rows),
                'duration_s': duration,
                'error': None,
            }
        except Exception as e:
            duration = time.time() - start
            self.log.warning(
                "Query failed for monitor_id=%d (%.3fs): %s",
                monitor_id,
                duration,
                e,
            )
            return {
                'status': 'error',
                'columns': [],
                'rows': [],
                'row_count': 0,
                'duration_s': duration,
                'error': str(e),
            }

    def _build_event_payload(self, query_spec: Any, result: dict[str, Any]) -> dict[str, Any]:
        entity = query_spec.entity.model_dump(exclude_none=True, by_alias=True)
        custom_fields = (
            query_spec.custom_sql_select_fields.model_dump(exclude_none=True)
            if query_spec.custom_sql_select_fields
            else None
        )

        return {
            'timestamp': int(time.time() * 1000),
            'config_id': self.config.config_id or '',
            'db_type': self.config.db_type,
            'db_host': self.config.db_identifier.host,
            'db_port': self.config.port,
            'db_name': self.config.db_identifier.dbname,
            'monitor_id': query_spec.monitor_id,
            'query': query_spec.query,
            'entity': entity,
            'custom_sql_select_fields': custom_fields,
            'status': result['status'],
            'columns': result['columns'],
            'rows': result['rows'],
            'row_count': result['row_count'],
            'duration_s': result['duration_s'],
            'error': result['error'],
        }

    def check(self, _: Any) -> None:
        base_tags = self._build_base_tags()
        due_queries = self._get_due_queries()

        if not due_queries:
            self.log.debug("No queries due for execution.")
            return

        try:
            with self._acquire_connection() as conn:
                now = time.time()
                for q in due_queries:
                    tags = base_tags + [f'monitor_id:{q.monitor_id}']

                    result = self._execute_single_query(conn, q)

                    self.gauge('query_execution_time', result['duration_s'], tags=tags)
                    success = result['status'] == 'success'
                    self.gauge(self.QUERY_STATUS_METRIC, 1 if success else 0, tags=tags)

                    payload = self._build_event_payload(q, result)
                    raw_event = json.dumps(payload, default=default_json_event_encoding)
                    self.log.debug("Query result for monitor_id=%d: %s", q.monitor_id, raw_event)
                    self.event_platform_event(raw_event, EVENT_TRACK_TYPE)

                    self._last_execution[q.monitor_id] = now

        except Exception:
            self.log.exception("Check execution failed")
            for q in due_queries:
                tags = base_tags + [f'monitor_id:{q.monitor_id}']
                self.gauge('query_execution_time', 0, tags=tags)
                self.gauge(self.QUERY_STATUS_METRIC, 0, tags=tags)

    def cancel(self) -> None:
        pool = self._pool
        self._pool = None
        if pool is not None:
            try:
                pool.close()
            except Exception:
                self.log.debug("Failed to close connection pool", exc_info=True)
