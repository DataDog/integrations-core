# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
One-off Data Observability tasks.

The Agent schedules a separate run-once `mysql` check for each task that Remote Configuration
delivers. That check holds only the connection settings of the matched instance plus a
`do_task` block, so the user's own check is never touched. `MySql.__new__` builds it as a
`MySqlTaskCheck`, which runs each statement once on its own connection and streams every result as
`do-query-results` events: a chunk event each time 4 MiB of rows have been read, then one final
event per execution. The backend joins them back to the task by `task_id`, `statement_id` and
`result_id`.
"""

from __future__ import annotations

import time
import uuid
from contextlib import closing
from typing import TYPE_CHECKING, Any

import pymysql

from datadog_checks.base import DatabaseCheck
from datadog_checks.base.utils.format import json

from .config_models.instance import DoTask
from .cursor import CommenterCursor
from .data_observability import EVENT_TRACK_TYPE
from .do_query import DOQuerySession, NoResultSetError
from .instance_mixin import MySQLInstanceMixin
from .util import connect_with_session_variables
from .version_utils import parse_version

if TYPE_CHECKING:
    from .config_models.instance import Statement

# Hard cap on the rows one statement returns, whatever its max_rows asks for. The DO_QUERY_ACTIONS
# schema and agenttask enforce the same value.
MAX_TASK_STATEMENT_ROWS = 1_000_000

# Upper bound on one serialized event. Rows are sent in chunks of at most this size, which keeps
# every event well under the intake's per-event limit. A statement with a single row too large for a
# chunk fails.
MAX_EVENT_BYTES = 4 * 1024 * 1024

# Added to the task's longest statement timeout to get the client read timeout of its connection, so
# the server's statement timeout always fires first and is reported as such.
READ_TIMEOUT_MARGIN_SECONDS = 30

# Client errors that mean the connection is gone: can't connect, server gone away, lost
# connection during a query.
CONNECTION_ERROR_CODES = frozenset((2002, 2003, 2006, 2013))
# MySQL max_execution_time or MariaDB max_statement_time exceeded.
STATEMENT_TIMEOUT_ERROR_CODES = frozenset((3024, 1969))
LOCK_WAIT_TIMEOUT_ERROR_CODE = 1205


class RowTooLargeError(Exception):
    """A row is larger than a chunk event can hold, so the statement's result can't be sent."""

    error_kind = 'row_too_large'

    def __init__(self, row_index: int, row_bytes: int) -> None:
        super().__init__(
            f'Row {row_index} is {row_bytes} bytes encoded, more than the {MAX_EVENT_BYTES} bytes an event can '
            'hold; select fewer or smaller columns'
        )


class ChunkEmitError(Exception):
    """A chunk event could not be sent, so the result the backend receives would be incomplete."""

    error_kind = 'emit_error'

    def __init__(self, chunk_index: int) -> None:
        super().__init__(f'Could not send chunk {chunk_index} of the result; the Agent log has the cause')


class MySqlTaskCheck(MySQLInstanceMixin, DatabaseCheck):
    """
    Runs the statements of one `do_task` once and reports a result for each of them. It sends no
    integration metrics, service checks, health events or DBM data: those would carry the tags of
    the user's own instance, so for example a task that fails to connect would flip that instance's
    `mysql.can_connect` status. Its only output besides the result events is internal
    `dd.mysql.do_task.*` metrics.
    """

    DBMS = 'mysql'
    HA_SUPPORTED = True

    def __init__(self, name: str, init_config: dict[str, Any], instances: list[dict[str, Any]]) -> None:
        super().__init__(name, init_config, instances)
        self._init_instance(init_config)
        self._task = DoTask.model_validate(self.instance['do_task'])
        self._session: DOQuerySession | None = None
        self._server_version = None
        self._metric_tags: list[str] | None = None

    def check(self, _: Any) -> None:
        task = self._task
        statements = task.statements
        try:
            for index, statement in enumerate(statements):
                if self.is_cancelled:
                    # The task's config is gone (cancelled or expired), so nobody waits for the rest.
                    self.log.debug(
                        "Data Observability task %s cancelled, skipping %d statements",
                        task.task_id,
                        len(statements) - index,
                    )
                    return
                if self._session is None:
                    try:
                        self._connect()
                    except Exception as error:
                        self._close()
                        self.log.warning("Data Observability task %s could not connect: %s", task.task_id, error)
                        result = _error_result(error, 0.0, connecting=True)
                        for pending in statements[index:]:
                            sender = _ChunkSender(self, pending, str(uuid.uuid4()))
                            self._emit_final(pending, sender, [], result)
                        return
                if not self._run_statement(statement):
                    self.log.debug(
                        "Data Observability task %s cancelled while reading statement %s",
                        task.task_id,
                        statement.id,
                    )
                    return
        finally:
            self._close()

    def _connect(self) -> None:
        conn = connect_with_session_variables(
            mysql_version=self._server_version,
            **{**self._get_connection_args(), 'read_timeout': self._read_timeout()},
        )
        try:
            with closing(conn.cursor(CommenterCursor)) as cursor:
                if self._server_version is None:
                    cursor.execute("SELECT @@version, @@version_comment")
                    raw_version, version_comment = cursor.fetchone()
                    self._server_version = parse_version(raw_version, version_comment)
                # Task statements only read. A read-only session makes the server reject any write a
                # statement attempts, whatever the monitoring user is granted.
                cursor.execute("SET SESSION TRANSACTION READ ONLY")
                # Temporal values come back in UTC whatever the server's time zone is.
                cursor.execute("SET time_zone = '+00:00'")
        except Exception:
            _close_quietly(conn, self.log)
            raise
        self._session = DOQuerySession(conn, self._server_version, self._server_version.flavor == 'MariaDB')

    def _read_timeout(self) -> int:
        """
        The client read timeout of the task connection. The instance's read_timeout is meant for the
        mysql check's own queries: a shorter one would fail a statement that is within its own
        timeout, as a lost connection, and leave it running on the server.
        """
        return max(statement.timeout_seconds for statement in self._task.statements) + READ_TIMEOUT_MARGIN_SECONDS

    def _close(self) -> None:
        session = self._session
        self._session = None
        if session is not None:
            _close_quietly(session.conn, self.log)

    def _run_statement(self, statement: Statement) -> bool:
        """
        Run one statement, streaming its rows as chunk events, then send its final event. Returns
        False if the check was cancelled during the statement, in which case no final event is sent.
        """
        session = self._session
        # A new result_id for every execution, so the backend never mixes the chunks of two runs of
        # a statement, for example before and after an Agent restart.
        sender = _ChunkSender(self, statement, str(uuid.uuid4()))
        start = time.time()
        columns: list[str] = []
        try:
            columns, batches = session.stream(
                statement.dbname,
                statement.query,
                statement.timeout_seconds * 1000,
                min(statement.max_rows, MAX_TASK_STATEMENT_ROWS),
            )
            try:
                for batch in batches:
                    if self.is_cancelled:
                        # Nobody waits for the result. Closing the connection makes the server abort
                        # the statement on its next write.
                        self._close()
                        return False
                    for row in batch:
                        sender.add([_to_text(value) for value in row])
                sender.flush()
            finally:
                # Leaving the read early, cancelled or on a row or chunk that can't be sent, leaves
                # the rest of the result unread and the session unusable.
                batches.close()
        except Exception as error:
            if self.is_cancelled:
                # Nobody waits for the result, and the session may be mid-result.
                self._close()
                return False
            duration = time.time() - start
            result = _error_result(error, duration)
            if not session.conn.open:
                result['error_kind'] = 'connection_error'
            # Keep the connection only after a plain server error or a result that couldn't be sent,
            # which leave it in a known state (or the session unusable, checked below). A statement
            # that returned no result set may have changed the session, its read-only setting
            # included, so the next statement starts on a fresh one.
            if (
                not isinstance(error, (pymysql.err.DatabaseError, RowTooLargeError, ChunkEmitError))
                or isinstance(error, NoResultSetError)
                or result['error_kind'] == 'connection_error'
            ):
                self._close()
            self.log.warning(
                "Data Observability task %s statement %s failed (%.3fs): %s",
                self._task.task_id,
                statement.id,
                duration,
                error,
            )
            self.log.debug("Failed statement SQL: %s", statement.query)
        else:
            result = {
                'status': 'success',
                'duration_s': time.time() - start,
                'error': None,
                'error_kind': None,
                'error_code': None,
            }
        if not session.usable:
            # The connection may be mid-result, after any outcome: a read stopped early, rows past
            # max_rows, or a cursor that failed to close after a complete read.
            self._close()
        self._emit_final(statement, sender, columns, result)
        return True

    def _base_event(self) -> dict[str, Any]:
        return {
            'timestamp': int(time.time() * 1000),
            'config_id': self._task.config_id,
            'task_id': self._task.task_id,
            'db_type': 'mysql',
            'db_host': self.reported_hostname,
            'db_port': self._config.port,
        }

    def _emit_final(
        self,
        statement: Statement,
        sender: _ChunkSender,
        columns: list[str],
        result: dict[str, Any],
    ) -> None:
        # Rows read but not yet sent when a read fails are discarded: the final event counts only
        # the chunks already sent.
        final = {
            **sender.routing,
            'timestamp': int(time.time() * 1000),
            'kind': 'final',
            'db_name': statement.dbname,
            'query': statement.query,
            'timeout_ms': statement.timeout_seconds * 1000,
            'chunk_count': sender.sent_chunks,
            'row_count': sender.sent_rows,
            'columns': columns if result['status'] == 'success' else [],
            **result,
        }
        self._count_statement(result)
        self._emit(final)

    def _emit(self, event: dict[str, Any] | bytes, statement_id: str | None = None) -> bool:
        """Send one event, or its serialized payload. Returns False, logged and counted, if it fails."""
        if isinstance(event, dict):
            statement_id = event.get('statement_id')
        try:
            payload = event if isinstance(event, bytes) else json.encode_bytes(event)
            self.event_platform_event(payload, EVENT_TRACK_TYPE)
        except Exception as error:
            self.log.exception(
                "Failed to emit Data Observability task %s result for statement %s",
                self._task.task_id,
                statement_id,
            )
            self._count('dd.mysql.do_task.emit_failures', [f'exc_class:{type(error).__name__}'])
            return False
        return True

    def _count_statement(self, result: dict[str, Any]) -> None:
        tags = [f"status:{result['status']}"]
        if result['status'] == 'error':
            tags.append(f"error_kind:{result['error_kind']}")
        self._count('dd.mysql.do_task.statements', tags)

    def _base_metric_tags(self) -> list[str]:
        if self._metric_tags is None:
            self._metric_tags = [tag for tag in self.tag_manager.get_tags() if not tag.startswith('dd.internal')] + [
                'db_type:mysql'
            ]
        return self._metric_tags

    def _count(self, name: str, tags: list[str]) -> None:
        # Internal metrics must never cost the task a statement or a result.
        try:
            self.count(
                name,
                1,
                tags=self._base_metric_tags() + tags,
                hostname=self.reported_hostname,
                raw=True,
            )
        except Exception:
            self.log.debug(
                "Failed to submit %s for Data Observability task %s", name, self._task.task_id, exc_info=True
            )


class _ChunkSender:
    """Collects one execution's rows and sends a chunk event each time they reach the budget."""

    def __init__(self, check: MySqlTaskCheck, statement: Statement, result_id: str) -> None:
        self._check = check
        self.routing = {**check._base_event(), 'statement_id': statement.id, 'result_id': result_id}
        # Measure a chunk event without rows, with the chunk index at its widest, to get the space
        # the rows of one chunk may use.
        envelope = {**self.routing, 'kind': 'chunk', 'chunk_index': MAX_TASK_STATEMENT_ROWS, 'rows': []}
        self._budget = MAX_EVENT_BYTES - len(json.encode_bytes(envelope))
        # Rows are encoded once, as they are added; flush() splices them into the chunk event.
        self._rows: list[bytes] = []
        self._size = 0
        self.sent_chunks = 0
        self.sent_rows = 0

    def add(self, row: list[str | None]) -> None:
        """Add one row, sending the pending rows first if it doesn't fit in their chunk."""
        encoded = json.encode_bytes(row)
        # One more byte for the separating comma.
        row_size = len(encoded) + 1
        if row_size > self._budget:
            raise RowTooLargeError(self.sent_rows + len(self._rows), len(encoded))
        if self._size + row_size > self._budget:
            self.flush()
        self._rows.append(encoded)
        self._size += row_size

    def flush(self) -> None:
        """Send the pending rows as a chunk event. Raises ChunkEmitError if it can't be sent."""
        if not self._rows:
            return
        envelope = json.encode_bytes(
            {**self.routing, 'timestamp': int(time.time() * 1000), 'kind': 'chunk', 'chunk_index': self.sent_chunks}
        )
        # The envelope is a JSON object: its closing brace makes way for the rows array.
        payload = b''.join((envelope[:-1], b',"rows":[', b','.join(self._rows), b']}'))
        if not self._check._emit(payload, self.routing['statement_id']):
            raise ChunkEmitError(self.sent_chunks)
        self.sent_chunks += 1
        self.sent_rows += len(self._rows)
        self._rows, self._size = [], 0


def _close_quietly(conn: Any, log: Any) -> None:
    try:
        conn.close()
    except Exception:
        log.debug("Failed to close Data Observability task connection", exc_info=True)


def _error_result(error: Exception, duration: float, connecting: bool = False) -> dict[str, Any]:
    # Same classification as the Data Observability job, so both report one set of error kinds.
    # pymysql reports a closed socket as InterfaceError(0, ''); 0 is not a database error code.
    code = error.args[0] if error.args and isinstance(error.args[0], int) and error.args[0] else None
    if isinstance(error, (RowTooLargeError, ChunkEmitError)):
        kind = error.error_kind
    elif connecting or isinstance(error, pymysql.err.InterfaceError) or code in CONNECTION_ERROR_CODES:
        kind = 'connection_error'
    elif code in STATEMENT_TIMEOUT_ERROR_CODES:
        kind = 'statement_timeout'
    elif code == LOCK_WAIT_TIMEOUT_ERROR_CODE:
        kind = 'lock_timeout'
    else:
        kind = 'sql_error'
    message = str(error)
    if connecting:
        message = f'Statement not executed: could not connect to the database: {error}'
    return {
        'status': 'error',
        'duration_s': duration,
        'error': message,
        'error_kind': kind,
        'error_code': str(code) if code is not None else None,
    }


def _to_text(value: Any) -> str | None:
    """
    Render a column value as text, the only type the backend accepts besides null. Statements cast
    their columns to text in SQL; this keeps a value they don't cast readable.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode('utf-8', errors='replace')
    return str(value)
