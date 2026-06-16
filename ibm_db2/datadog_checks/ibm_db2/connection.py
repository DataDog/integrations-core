# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections.abc import Sequence
from contextlib import contextmanager
from threading import RLock
from typing import Any, Iterator

import ibm_db

from datadog_checks.base.utils.common import to_native_string

from .utils import is_connection_error, scrub_connection_string


class Db2Connection:
    """Manage dedicated Db2 connections for DBM collectors."""

    def __init__(self, check, config) -> None:
        self._check = check
        self._config = config
        self._connections: dict[str, object] = {}
        self._connections_lock = RLock()

    def close(self, key_prefix: str | None = None) -> None:
        with self._connections_lock:
            keys = [key_prefix] if key_prefix is not None else list(self._connections)
            connections = [(key, self._connections.pop(key, None)) for key in keys]

        for key, connection in connections:
            if connection is not None:
                try:
                    ibm_db.close(connection)
                except Exception:
                    self._check.log.debug("Failed to close Db2 connection for key_prefix=%s", key, exc_info=True)

    def get_connection(self, key_prefix: str) -> object:
        with self._connections_lock:
            connection = self._connections.get(key_prefix)
            if connection is None:
                connection = self._connect()
                self._connections[key_prefix] = connection
            return connection

    @contextmanager
    def open_managed_default_connection(self, key_prefix: str) -> Iterator[object]:
        yield self.get_connection(key_prefix)

    def query(self, key_prefix: str, query: str, params: Sequence[Any] | None = None) -> tuple[list[dict], list[str]]:
        cursor = self._execute(key_prefix, query, params)
        try:
            columns = self._get_columns(cursor)
            rows = []
            row = ibm_db.fetch_assoc(cursor)
            while row is not False:
                rows.append(row)
                row = ibm_db.fetch_assoc(cursor)
            return rows, columns
        finally:
            try:
                ibm_db.free_result(cursor)
            except Exception:
                self._check.log.debug("Failed to free Db2 statement handle", exc_info=True)

    def execute(self, key_prefix: str, query: str, params: Sequence[Any] | None = None) -> object:
        return self._execute(key_prefix, query, params)

    def callproc(self, key_prefix: str, procedure: str, params: Sequence[Any]) -> tuple:
        connection = self.get_connection(key_prefix)
        try:
            return ibm_db.callproc(connection, procedure, tuple(params))
        except Exception as e:
            if not is_connection_error(e):
                raise
            self.close(key_prefix)
            return ibm_db.callproc(self.get_connection(key_prefix), procedure, tuple(params))

    def _connect(self) -> object:
        target, username, password = self._check.get_connection_data(
            self._config.db,
            self._config.username,
            self._config.password,
            self._config.host,
            self._config.port,
            self._config.security,
            self._config.tls_cert,
            self._config.connection_timeout,
        )
        connection_options = {ibm_db.ATTR_CASE: ibm_db.CASE_LOWER}

        self._check.log.debug("Attempting to connect to Db2 with `%s`...", scrub_connection_string(target))
        connection = ibm_db.connect(target, username, password, connection_options)
        ibm_db.exec_immediate(connection, 'SET CURRENT ISOLATION UR')
        return connection

    def _execute(self, key_prefix: str, query: str, params: Sequence[Any] | None = None) -> object:
        connection = self.get_connection(key_prefix)
        try:
            return self._execute_query(connection, query, params)
        except Exception as e:
            if not is_connection_error(e):
                raise
            self.close(key_prefix)
            return self._execute_query(self.get_connection(key_prefix), query, params)

    @staticmethod
    def _execute_query(connection: object, query: str, params: Sequence[Any] | None = None) -> object:
        if params is None:
            return ibm_db.exec_immediate(connection, query)

        cursor = ibm_db.prepare(connection, query)
        ibm_db.execute(cursor, tuple(params))
        return cursor

    def _get_columns(self, cursor: object) -> list[str]:
        try:
            return [to_native_string(ibm_db.field_name(cursor, i)).lower() for i in range(ibm_db.num_fields(cursor))]
        except Exception:
            self._check.log.debug("Unable to read Db2 statement columns", exc_info=True)
            return []
