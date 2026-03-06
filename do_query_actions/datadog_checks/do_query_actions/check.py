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
from datadog_checks.do_query_actions.postgres_connection import (
    AWSTokenProvider,
    AzureTokenProvider,
    PostgresConnectionArgs,
    TokenAwareConnection,
    TokenProvider,
)
from datadog_checks.base.utils.db.sql_commenter import add_sql_comment
from datadog_checks.base.utils.db.utils import default_json_event_encoding

EVENT_TRACK_TYPE = 'do-query-results'


class DoQueryCursor(psycopg.Cursor):
    """psycopg cursor that prepends a SQL comment identifying the Datadog Agent."""

    _COMMENT_ATTRS = {'service': 'datadog-agent'}

    def execute(self, query, params=None, **kwargs):
        if isinstance(query, str):
            query = add_sql_comment(query, prepand=True, **self._COMMENT_ATTRS)
        return super().execute(query, params, **kwargs)


class DoQueryActionsCheck(AgentCheck):
    """Execute SQL queries against databases on individual schedules."""

    __NAMESPACE__ = 'do_query_actions'
    SERVICE_CHECK_NAME = 'query_status'

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)

        self._host: str = self.instance.get('host', '')
        self._port: int | None = self.instance.get('port')
        self._username: str = self.instance.get('username', '')
        self._password: str = self.instance.get('password', '')
        self._dbname: str = self.instance.get('dbname', '')
        self._remote_config_id: str = self.instance.get('remote_config_id', '')
        self._db_type: str = self.instance.get('db_type', '')
        self._queries: list[dict[str, Any]] = list(self.instance.get('queries', []))

        # SSL
        self._ssl: str | None = self.instance.get('ssl')
        self._ssl_cert: str | None = self.instance.get('ssl_cert')
        self._ssl_root_cert: str | None = self.instance.get('ssl_root_cert')
        self._ssl_key: str | None = self.instance.get('ssl_key')
        self._ssl_password: str | None = self.instance.get('ssl_password')

        # AWS / Azure auth
        self._aws: dict[str, Any] = self.instance.get('aws') or {}
        self._managed_authentication: dict[str, Any] = self.instance.get('managed_authentication') or {}

        self._last_execution: dict[int, float] = {}
        self._pool: ConnectionPool | None = None

    def _build_base_tags(self) -> list[str]:
        tags = list(self.instance.get('tags', []))
        if self._remote_config_id:
            tags.append(f'remote_config_id:{self._remote_config_id}')
        if self._db_type:
            tags.append(f'db_type:{self._db_type}')
        if self._dbname:
            tags.append(f'db_name:{self._dbname}')
        if self._host:
            tags.append(f'db_host:{self._host}')
        if self._port:
            tags.append(f'port:{self._port}')
        return tags

    def _build_token_provider(self) -> TokenProvider | None:
        aws_managed = self._aws.get('managed_authentication') or {}
        if aws_managed.get('enabled'):
            return AWSTokenProvider(
                host=self._host,
                port=self._port or 5432,
                username=self._username,
                region=self._aws.get('region', ''),
                role_arn=aws_managed.get('role_arn'),
            )

        azure_managed = self._managed_authentication
        if azure_managed.get('enabled'):
            return AzureTokenProvider(
                client_id=azure_managed.get('client_id', ''),
                identity_scope=azure_managed.get('identity_scope'),
            )

        return None

    def _create_postgres_pool(self) -> ConnectionPool:
        conn_args = PostgresConnectionArgs(
            username=self._username,
            host=self._host,
            port=self._port,
            password=self._password,
            ssl_mode=self._ssl,
            ssl_cert=self._ssl_cert,
            ssl_root_cert=self._ssl_root_cert,
            ssl_key=self._ssl_key,
            ssl_password=self._ssl_password,
        )
        kwargs = conn_args.as_kwargs(dbname=self._dbname)
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
            self.log.debug("Creating connection pool for %s:%s/%s", self._host, self._port, self._dbname)
            self._pool = self._create_postgres_pool()
        return self._pool

    @contextlib.contextmanager
    def _acquire_connection(self) -> Iterator[Any]:
        if self._db_type != 'postgres':
            self.log.error("Unsupported db_type: %r. Only 'postgres' is supported.", self._db_type)
            raise ValueError(f"Unsupported db_type: {self._db_type!r}. Only 'postgres' is supported.")
        with self._get_or_create_postgres_pool().connection() as conn:
            yield conn

    def _get_due_queries(self) -> list[dict[str, Any]]:
        now = time.time()
        due = []
        for q in self._queries:
            monitor_id = q.get('monitor_id', 0)
            interval = q.get('interval_seconds', 0)
            last_run = self._last_execution.get(monitor_id, 0.0)
            if now - last_run >= interval:
                due.append(q)
        return due

    def _set_query_timeout(self, conn: Any, timeout_seconds: int) -> None:
        with conn.cursor() as cursor:
            cursor.execute(f"SET statement_timeout = {int(timeout_seconds) * 1000}")

    def _execute_single_query(self, conn: Any, query_spec: dict[str, Any]) -> dict[str, Any]:
        """Execute a single query and return a structured result dict."""
        sql = query_spec.get('query', '')
        timeout = query_spec.get('timeout_seconds', 30)
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
                query_spec.get('monitor_id', 0),
                duration,
                e,
            )
            try:
                conn.rollback()
            except Exception as rollback_err:
                self.log.debug("Rollback failed: %s", rollback_err)
            return {
                'status': 'error',
                'columns': [],
                'rows': [],
                'row_count': 0,
                'duration_s': duration,
                'error': str(e),
            }

    def _build_event_payload(self, query_spec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        entity = query_spec.get('entity') or {}
        if hasattr(entity, 'model_dump'):
            entity = entity.model_dump(exclude_none=True)
        elif not isinstance(entity, dict):
            entity = dict(entity)

        return {
            'timestamp': int(time.time() * 1000),
            'remote_config_id': self._remote_config_id,
            'db_type': self._db_type,
            'db_host': self._host,
            'db_port': self._port,
            'db_name': self._dbname,
            'monitor_id': query_spec.get('monitor_id', 0),
            'query': query_spec.get('query', ''),
            'entity': entity,
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
                    monitor_id = q.get('monitor_id', 0)
                    tags = base_tags + [f'monitor_id:{monitor_id}']

                    result = self._execute_single_query(conn, q)

                    self.gauge('query_execution_time', result['duration_s'], tags=tags)
                    success = result['status'] == 'success'
                    self.gauge('query_success', 1 if success else 0, tags=tags)

                    if success:
                        self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, tags=tags)
                    else:
                        self.service_check(
                            self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=tags, message=result['error']
                        )

                    payload = self._build_event_payload(q, result)
                    raw_event = json.dumps(payload, default=default_json_event_encoding)
                    self.log.debug("Query result for monitor_id=%d: %s", monitor_id, raw_event)
                    self.event_platform_event(raw_event, EVENT_TRACK_TYPE)

                    self._last_execution[monitor_id] = now

        except Exception as e:
            error_msg = str(e)
            self.log.exception("Connection failed")
            for q in due_queries:
                monitor_id = q.get('monitor_id', 0)
                tags = base_tags + [f'monitor_id:{monitor_id}']
                self.gauge('query_execution_time', 0, tags=tags)
                self.gauge('query_success', 0, tags=tags)
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=tags, message=error_msg)

    def cancel(self) -> None:
        if self._pool is not None:
            self._pool.close()
            self._pool = None
