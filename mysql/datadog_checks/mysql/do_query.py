# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Running Data Observability SQL, shared by monitor queries and one-off tasks."""

from __future__ import annotations

from contextlib import closing
from typing import Any

import pymysql

from .cursor import CommenterCursor, CommenterSSCursor

# Hard cap on the rows one query returns, whatever it asks for.
MAX_RESULT_ROWS = 10_000

# MySQL added max_execution_time in 5.7.4.
MAX_EXECUTION_TIME_MIN_VERSION = (5, 7, 4)


class NoResultSetError(pymysql.err.ProgrammingError):
    """The query ran but returned no result set. Only SELECT statements are supported."""

    def __init__(self) -> None:
        super().__init__("Query returned no result set — only SELECT statements are supported")


def quote_identifier(name: str) -> str:
    """Quote a MySQL identifier, doubling any backtick in it, so every database name works as-is."""
    return '`' + name.replace('`', '``') + '`'


class DOQuerySession:
    """
    Runs Data Observability queries on a connection that runs nothing else, so session settings
    (database, timeout, row limit) stay in place and are only changed when a query needs other
    values. Use a new session for every new connection.
    """

    def __init__(self, conn: Any, version: Any, is_mariadb: bool) -> None:
        self.conn = conn
        self._version = version
        self._is_mariadb = is_mariadb
        self._dbname: str | None = None
        self._timeout_ms: int | None = None
        self._row_limit: int | None = None
        # False once a failed query left the connection mid-result; the caller must reconnect.
        self.usable = True

    def run(self, dbname: str, query: str, timeout_ms: int, max_rows: int) -> tuple[list[str], list[tuple]]:
        """
        Run one query and return its columns and at most `max_rows` rows, capped at
        MAX_RESULT_ROWS. Raises NoResultSetError if the query returns no result set, and the
        driver's error if it fails.
        """
        limit = min(max_rows, MAX_RESULT_ROWS)
        self._set_timeout(timeout_ms)
        self._set_row_limit(limit)
        # A streaming cursor fetches rows as fetchmany() asks for them instead of buffering the whole
        # result. Like every other Agent query, queries carry the service='datadog-agent' comment,
        # which marks them as the Agent's in DBM.
        cursor = self.conn.cursor(CommenterSSCursor)
        try:
            if dbname != self._dbname:
                cursor.execute(f"USE {quote_identifier(dbname)}")
                self._dbname = dbname
            cursor.execute(query)
            if cursor.description is None:
                raise NoResultSetError()
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchmany(limit)
            cursor.close()
        except Exception:
            try:
                cursor.close()
            except Exception:
                self.usable = False
            raise
        return columns, rows

    def _set_timeout(self, timeout_ms: int) -> None:
        if not self._is_mariadb and not self._version.version_compatible(MAX_EXECUTION_TIME_MIN_VERSION):
            # Older MySQL servers have no statement timeout; the query still runs without one.
            return
        if timeout_ms == self._timeout_ms:
            return
        if self._is_mariadb:
            variable, value = 'max_statement_time', timeout_ms / 1000
        else:
            variable, value = 'max_execution_time', timeout_ms
        self._set_session_variable(variable, value)
        self._timeout_ms = timeout_ms

    def _set_row_limit(self, limit: int) -> None:
        # The server stops after `limit` rows, as if the query ended with LIMIT, instead of producing
        # rows the check would never read. A LIMIT in the query itself takes precedence.
        if limit == self._row_limit:
            return
        self._set_session_variable('sql_select_limit', limit)
        self._row_limit = limit

    def _set_session_variable(self, variable: str, value: Any) -> None:
        with closing(self.conn.cursor(CommenterCursor)) as cursor:
            cursor.execute(f"SET SESSION {variable} = %s", (value,))
