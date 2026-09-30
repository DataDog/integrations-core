# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
One-off Data Observability tasks.

The Agent schedules a separate run-once `mysql` check for each task that Remote Configuration
delivers. That check holds only the connection settings of the matched instance plus a
`do_task` block, so the user's own check is never touched. The task runs each statement once on
its own connection and reports every result as `do-query-results` events, which the backend
joins back to the task by `task_id`, `statement_id` and `result_id`.
"""

from __future__ import annotations

import datetime
import time
import uuid
from contextlib import closing
from decimal import Decimal
from typing import TYPE_CHECKING, Any

import pymysql

from datadog_checks.base.utils.format import json

from .cursor import CommenterCursor, CommenterSSCursor
from .data_observability import EVENT_TRACK_TYPE
from .util import connect_with_session_variables
from .version_utils import parse_version

if TYPE_CHECKING:
    from .config_models.instance import DoTask, Statement
    from .mysql import MySql

# Hard cap on the rows one statement returns, whatever its max_rows asks for. Like a LIMIT, rows
# past the limit are not returned.
MAX_TASK_STATEMENT_ROWS = 10_000

# Upper bound on one serialized event. Larger results are split into chunks, which keeps every
# event well under the intake's per-event limit.
MAX_EVENT_BYTES = 4 * 1024 * 1024

# Client errors that mean the connection is gone: can't connect, server gone away, lost
# connection during a query.
CONNECTION_ERROR_CODES = frozenset((2002, 2003, 2006, 2013))
# MySQL max_execution_time or MariaDB max_statement_time exceeded.
STATEMENT_TIMEOUT_ERROR_CODES = frozenset((3024, 1969))
LOCK_WAIT_TIMEOUT_ERROR_CODE = 1205

# MySQL added max_execution_time in 5.7.4.
MAX_EXECUTION_TIME_MIN_VERSION = (5, 7, 4)


class MySQLDataObservabilityTask:
    """Runs the statements of one `do_task` once and reports a result for each of them."""

    def __init__(self, check: MySql, task: DoTask) -> None:
        self._check = check
        self._task = task
        self._log = check.log
        self._conn: Any = None
        self._version = None
        self._current_dbname: str | None = None
        self._current_timeout_seconds: int | None = None
        self._metric_tags: list[str] | None = None

    def run(self) -> None:
        task = self._task
        if time.time() >= task.expires_at:
            # The Agent drops stale tasks too; this catches a task that sat in the queue.
            self._log.warning("Not running Data Observability task %s: it expired at %d", task.task_id, task.expires_at)
            self._emit_task_error('expired', f'Task expired at {task.expires_at} before it ran')
            self._count('dd.mysql.do_task.runs', ['outcome:expired'])
            return

        statements = task.statements
        try:
            for index, statement in enumerate(statements):
                if self._check.is_cancelled:
                    # The task's config is gone (cancelled or expired), so nobody waits for the rest.
                    self._log.debug(
                        "Data Observability task %s cancelled, skipping %d statements",
                        task.task_id,
                        len(statements) - index,
                    )
                    self._count('dd.mysql.do_task.runs', ['outcome:cancelled'])
                    return
                if self._conn is None:
                    try:
                        self._connect()
                    except Exception as error:
                        self._close()
                        self._log.warning("Data Observability task %s could not connect: %s", task.task_id, error)
                        result = _error_result(error, 0.0, 'connect')
                        for pending in statements[index:]:
                            self._emit_result(pending, result)
                        self._count('dd.mysql.do_task.runs', ['outcome:connection_error'])
                        return
                self._emit_result(statement, self._execute(statement))
            self._count('dd.mysql.do_task.runs', ['outcome:completed'])
        finally:
            self._close()

    def _connect(self) -> None:
        self._conn = connect_with_session_variables(mysql_version=self._version, **self._check._get_connection_args())
        with closing(self._conn.cursor(CommenterCursor)) as cursor:
            if self._version is None:
                cursor.execute("SELECT @@version, @@version_comment")
                raw_version, version_comment = cursor.fetchone()
                self._version = parse_version(raw_version, version_comment)
            # Task statements only read. A read-only session makes the server reject any write a
            # statement attempts, whatever the monitoring user is granted.
            cursor.execute("SET SESSION TRANSACTION READ ONLY")
            # Temporal values come back in UTC whatever the server's time zone is.
            cursor.execute("SET time_zone = '+00:00'")

    def _close(self) -> None:
        conn = self._conn
        self._conn = None
        self._current_dbname = None
        self._current_timeout_seconds = None
        if conn is not None:
            try:
                conn.close()
            except Exception:
                self._log.debug("Failed to close Data Observability task connection", exc_info=True)

    def _set_statement_timeout(self, timeout_seconds: int) -> None:
        is_mariadb = self._version.flavor == 'MariaDB'
        if not is_mariadb and not self._version.version_compatible(MAX_EXECUTION_TIME_MIN_VERSION):
            return
        if timeout_seconds == self._current_timeout_seconds:
            return
        if is_mariadb:
            variable, value = 'max_statement_time', timeout_seconds
        else:
            variable, value = 'max_execution_time', timeout_seconds * 1000
        with closing(self._conn.cursor(CommenterCursor)) as cursor:
            cursor.execute(f"SET SESSION {variable} = %s", (value,))
        self._current_timeout_seconds = timeout_seconds

    def _execute(self, statement: Statement) -> dict[str, Any]:
        conn = self._conn
        limit = min(statement.max_rows, MAX_TASK_STATEMENT_ROWS)
        phase = 'execute'
        cursor = None
        start = time.time()
        try:
            self._set_statement_timeout(statement.timeout_seconds)
            # A streaming cursor fetches rows as fetchmany() asks for them, so the check never holds
            # more than `limit` of them. Like every other Agent query, statements carry the
            # service='datadog-agent' comment, which marks them as the Agent's in DBM.
            cursor = conn.cursor(CommenterSSCursor)
            if statement.dbname != self._current_dbname:
                cursor.execute(f"USE {_quote_identifier(statement.dbname)}")
                self._current_dbname = statement.dbname
            cursor.execute(statement.query)
            if cursor.description is None:
                # Only statements that return rows are supported. Anything else may have changed the
                # session, its read-only setting included, so the next statement gets a fresh one.
                self._close()
                error = pymysql.err.ProgrammingError(
                    "Query returned no result set — only SELECT statements are supported"
                )
                return _error_result(error, time.time() - start, 'execute')
            columns = [description[0] for description in cursor.description]
            phase = 'fetch'
            rows = cursor.fetchmany(limit)
            cursor.close()
        except Exception as error:
            duration = time.time() - start
            result = _error_result(error, duration, phase)
            if not conn.open:
                result['error_kind'] = 'connection_error'
            # Keep the connection only after a plain server error. Anything else can leave it
            # mid-result, so the next statement starts on a fresh one.
            if isinstance(error, pymysql.err.DatabaseError) and result['error_kind'] != 'connection_error':
                try:
                    if cursor is not None:
                        cursor.close()
                except Exception:
                    self._close()
            else:
                self._close()
            self._log.warning(
                "Data Observability task %s statement %s failed (%.3fs): %s",
                self._task.task_id,
                statement.id,
                duration,
                error,
            )
            self._log.debug("Failed statement SQL: %s", statement.query)
            return result

        return {
            'status': 'success',
            'columns': columns,
            'rows': [[_to_text(value) for value in row] for row in rows],
            'row_count': len(rows),
            'duration_s': time.time() - start,
            'error': None,
            'error_kind': None,
            'error_code': None,
            'error_phase': None,
        }

    def _base_event(self) -> dict[str, Any]:
        return {
            'timestamp': int(time.time() * 1000),
            'config_id': self._task.config_id,
            'task_id': self._task.task_id,
            'db_type': 'mysql',
            'db_host': self._check.reported_hostname,
            'db_port': self._check._config.port,
        }

    def _emit_result(self, statement: Statement, result: dict[str, Any]) -> None:
        self._record_statement(result)
        event = {
            **self._base_event(),
            'statement_id': statement.id,
            # New for every execution, so the backend never mixes the chunks of two runs of a
            # statement, for example before and after an Agent restart.
            'result_id': str(uuid.uuid4()),
            'db_name': statement.dbname,
            'query': statement.query,
            'timeout_ms': statement.timeout_seconds * 1000,
            **result,
        }
        rows = event['rows']
        # Measure the event without rows, with chunk fields at their widest, to get the space the
        # rows of one chunk may use.
        envelope = {**event, 'rows': [], 'chunk_index': MAX_TASK_STATEMENT_ROWS, 'chunk_count': MAX_TASK_STATEMENT_ROWS}
        chunks = _split_rows(rows, MAX_EVENT_BYTES - len(json.encode_bytes(envelope)))
        for index, chunk in enumerate(chunks):
            self._emit(
                {**event, 'chunk_index': index, 'chunk_count': len(chunks), 'rows': chunk, 'row_count': len(chunk)}
            )

    def _emit_task_error(self, error_kind: str, message: str) -> None:
        self._emit(
            {
                **self._base_event(),
                'chunk_index': 0,
                'chunk_count': 1,
                'status': 'error',
                'columns': [],
                'rows': [],
                'row_count': 0,
                'duration_s': 0.0,
                'error': message,
                'error_kind': error_kind,
                'error_code': None,
                'error_phase': 'schedule',
            }
        )

    def _emit(self, event: dict[str, Any]) -> None:
        try:
            self._check.event_platform_event(json.encode(event), EVENT_TRACK_TYPE)
        except Exception as error:
            self._log.exception(
                "Failed to emit Data Observability task %s result for statement %s",
                self._task.task_id,
                event.get('statement_id'),
            )
            self._count('dd.mysql.do_task.emit_failures', [f'exc_class:{type(error).__name__}'])
            return
        self._count('dd.mysql.do_task.events')

    def _record_statement(self, result: dict[str, Any]) -> None:
        status_tag = f"status:{result['status']}"
        tags = [status_tag]
        if result['status'] == 'error':
            tags += [f"error_kind:{result['error_kind']}", f"error_phase:{result['error_phase']}"]
        self._count('dd.mysql.do_task.statements', tags)
        if result['error_phase'] == 'connect':
            # The statement never ran, so it has no execution time.
            return
        self._histogram('dd.mysql.do_task.statement_execution_time', result['duration_s'], [status_tag])
        if result['status'] == 'success':
            self._histogram('dd.mysql.do_task.statement_rows', result['row_count'])

    def _base_metric_tags(self) -> list[str]:
        if self._metric_tags is None:
            self._metric_tags = [
                tag for tag in self._check.tag_manager.get_tags() if not tag.startswith('dd.internal')
            ] + ['db_type:mysql']
        return self._metric_tags

    def _count(self, name: str, tags: list[str] | None = None) -> None:
        self._submit(self._check.count, name, 1, tags)

    def _histogram(self, name: str, value: float, tags: list[str] | None = None) -> None:
        self._submit(self._check.histogram, name, value, tags)

    def _submit(self, submit: Any, name: str, value: float, tags: list[str] | None) -> None:
        # Internal metrics must never cost the task a statement or a result.
        try:
            submit(
                name,
                value,
                tags=self._base_metric_tags() + (tags or []),
                hostname=self._check.reported_hostname,
                raw=True,
            )
        except Exception:
            self._log.debug(
                "Failed to submit %s for Data Observability task %s", name, self._task.task_id, exc_info=True
            )


def _error_result(error: Exception, duration: float, phase: str) -> dict[str, Any]:
    # Same classification as the Data Observability job, so both report one set of error kinds.
    code = error.args[0] if error.args and isinstance(error.args[0], int) else None
    if phase == 'connect' or isinstance(error, pymysql.err.InterfaceError) or code in CONNECTION_ERROR_CODES:
        kind = 'connection_error'
    elif code in STATEMENT_TIMEOUT_ERROR_CODES:
        kind = 'statement_timeout'
    elif code == LOCK_WAIT_TIMEOUT_ERROR_CODE:
        kind = 'lock_timeout'
    else:
        kind = 'sql_error'
    message = str(error)
    if phase == 'connect':
        message = f'Statement not executed: could not connect to the database: {error}'
    return {
        'status': 'error',
        'columns': [],
        'rows': [],
        'row_count': 0,
        'duration_s': duration,
        'error': message,
        'error_kind': kind,
        'error_code': code,
        'error_phase': phase,
    }


def _quote_identifier(name: str) -> str:
    """Quote a MySQL identifier, doubling any backtick in it, so every database name works as-is."""
    return '`' + name.replace('`', '``') + '`'


def _split_rows(rows: list[list[str | None]], budget: int) -> list[list[list[str | None]]]:
    """
    Split rows into consecutive chunks whose JSON encoding fits in `budget` bytes. Every chunk
    holds at least one row, and there is always at least one chunk.
    """
    chunks: list[list[list[str | None]]] = [[]]
    size = 0
    for row in rows:
        # One more byte for the separating comma.
        row_size = len(json.encode_bytes(row)) + 1
        if chunks[-1] and size + row_size > budget:
            chunks.append([])
            size = 0
        chunks[-1].append(row)
        size += row_size
    return chunks


def _to_text(value: Any) -> str | None:
    """
    Render a column value as text, the only type the backend accepts besides null. Statements
    should cast in SQL; this covers the values pymysql returns when they don't.
    """
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode('utf-8', errors='replace')
    if isinstance(value, datetime.datetime):
        # MySQL's own DATETIME text format.
        return value.isoformat(sep=' ')
    if isinstance(value, datetime.timedelta):
        return _format_time(value)
    if isinstance(value, Decimal):
        # Plain notation keeps every digit the server sent, never an exponent.
        return format(value, 'f')
    return str(value)


def _format_time(value: datetime.timedelta) -> str:
    """Render a TIME value, which pymysql returns as a timedelta, the way MySQL prints it."""
    total_microseconds = (value.days * 86_400 + value.seconds) * 1_000_000 + value.microseconds
    sign = '-' if total_microseconds < 0 else ''
    seconds, microseconds = divmod(abs(total_microseconds), 1_000_000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    text = f'{sign}{hours:02d}:{minutes:02d}:{seconds:02d}'
    if microseconds:
        text += f'.{microseconds:06d}'
    return text
