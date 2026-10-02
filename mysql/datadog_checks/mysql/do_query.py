# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Running Data Observability SQL, shared by monitor queries and one-off tasks."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import closing
from typing import Any

import pymysql

from .cursor import CommenterCursor, CommenterSSCursor

# Hard cap on the rows one monitor query returns, whatever it asks for. One-off tasks have their
# own cap, MAX_TASK_STATEMENT_ROWS in do_task.py.
MAX_RESULT_ROWS = 10_000

# Rows read per fetchmany() call when streaming, so a large result is never held at once.
FETCH_BATCH_ROWS = 1_000

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
        # False once a query left the connection mid-result, after a failed cursor close or a read
        # stopped early; the caller must reconnect.
        self.usable = True

    def run(self, dbname: str, query: str, timeout_ms: int, max_rows: int) -> tuple[list[str], list[tuple]]:
        """
        Run one query and return its columns and at most `max_rows` rows, read in one call.
        Raises NoResultSetError if the query returns no result set, and the driver's error if it
        fails.
        """
        columns, batches = self.stream(dbname, query, timeout_ms, max_rows, batch_rows=max_rows)
        return columns, [row for batch in batches for row in batch]

    def stream(
        self, dbname: str, query: str, timeout_ms: int, max_rows: int, batch_rows: int = FETCH_BATCH_ROWS
    ) -> tuple[list[str], Generator[list[tuple], None, None]]:
        """
        Run one query and return its columns and an iterator over batches of at most `batch_rows`
        rows, at most `max_rows` rows in all. Errors before the result set raise here; errors
        while reading raise from the iterator.

        The iterator must be exhausted or closed. Closing it early leaves the connection
        mid-result: the session becomes unusable and the caller must close the connection rather
        than the cursor, because closing an unbuffered cursor reads every remaining row.
        """
        self._set_timeout(timeout_ms)
        self._set_row_limit(max_rows)
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
        except Exception:
            self._close_cursor(cursor)
            raise
        columns = [description[0] for description in cursor.description]
        return columns, self._batches(cursor, max_rows, batch_rows)

    def _batches(self, cursor: Any, max_rows: int, batch_rows: int) -> Generator[list[tuple], None, None]:
        read = 0
        try:
            while read < max_rows:
                size = min(batch_rows, max_rows - read)
                batch = cursor.fetchmany(size)
                if batch:
                    read += len(batch)
                    yield batch
                if len(batch) < size:
                    break
        except GeneratorExit:
            # Stopped early by the caller. Closing the cursor would read every remaining row.
            self.usable = False
            raise
        except Exception:
            # A read error ended the result (server error packet or lost connection).
            self._close_cursor(cursor)
            raise
        # The server has sent everything up to sql_select_limit; this reads the EOF only.
        self._close_cursor(cursor)

    def _close_cursor(self, cursor: Any) -> None:
        try:
            cursor.close()
        except Exception:
            self.usable = False

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
