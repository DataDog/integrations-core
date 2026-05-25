# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

_REDACTED = '******'


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _exception_record(exc: BaseException) -> dict[str, str]:
    return {
        'type': type(exc).__name__,
        'module': type(exc).__module__,
        'message': str(exc),
    }


def _raise_recorded_exception(record: dict[str, Any]) -> None:
    exception = record.get('exception') or {}
    message = exception.get('message', '')
    exception_type = exception.get('type')

    try:
        import psycopg as pg
    except Exception:
        pg = None

    if pg is not None:
        if exception_type == 'ProgrammingError':
            raise pg.ProgrammingError(message)
        if exception_type == 'OperationalError':
            raise pg.OperationalError(message)
        if exception_type == 'InterfaceError':
            raise pg.InterfaceError(message)
        if exception_type == 'Error':
            raise pg.Error(message)
    if exception_type == 'OSError':
        raise OSError(message)
    raise Exception(message)


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


def _redact_connect_value(key: str, value: Any) -> Any:
    if key.lower() in {'password', 'pass'}:
        return _REDACTED
    if isinstance(value, str) and 'password=' in value:
        return value.replace(value.split('password=', 1)[1].split()[0], _REDACTED)
    return _json_safe(value)


def _connect_record(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        'args': [_json_safe(arg) for arg in args],
        'kwargs': {str(key): _redact_connect_value(str(key), value) for key, value in kwargs.items()},
    }


def _row_factory_name(row_factory: Any) -> str | None:
    if row_factory is None:
        return None
    return getattr(row_factory, '__name__', str(row_factory))


class _RecordingConnection:
    def __init__(self, connection: Any, records: list[dict[str, Any]], fixture_path: Path):
        self._connection = connection
        self._records = records
        self._fixture_path = fixture_path

    def cursor(self, *args: Any, **kwargs: Any) -> '_RecordingCursor':
        cursor = self._connection.cursor(*args, **kwargs)
        return _RecordingCursor(cursor, self._records, self._fixture_path, args, kwargs)

    def close(self) -> Any:
        return self._connection.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._connection, name)


class _RecordingCursor:
    def __init__(
        self,
        cursor: Any,
        records: list[dict[str, Any]],
        fixture_path: Path,
        cursor_args: tuple[Any, ...],
        cursor_kwargs: dict[str, Any],
    ):
        self._cursor = cursor
        self._records = records
        self._fixture_path = fixture_path
        self._cursor_args = cursor_args
        self._cursor_kwargs = cursor_kwargs
        self._rows: list[Any] = []
        self._index = 0

    def __enter__(self) -> '_RecordingCursor':
        if hasattr(self._cursor, '__enter__'):
            self._cursor.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> Any:
        if hasattr(self._cursor, '__exit__'):
            return self._cursor.__exit__(exc_type, exc, traceback)
        return None

    def execute(self, sql: Any, params: Any = None, *args: Any, **kwargs: Any) -> '_RecordingCursor':
        record = {
            'operation': 'psycopg.cursor.execute',
            'sql': str(sql),
            'params': _json_safe(params),
            'cursor_args': [_json_safe(arg) for arg in self._cursor_args],
            'row_factory': _row_factory_name(self._cursor_kwargs.get('row_factory')),
        }
        try:
            self._cursor.execute(sql, params, *args, **kwargs)
            self._rows = [_json_safe(row) for row in self._cursor.fetchall()]
            self._index = 0
        except Exception as exc:
            record['rows'] = []
            record['exception'] = _exception_record(exc)
            self._records.append(record)
            _write_records(self._fixture_path, self._records)
            raise

        record['rows'] = self._rows
        record['exception'] = None
        self._records.append(record)
        _write_records(self._fixture_path, self._records)
        return self

    def fetchone(self) -> Any:
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def __iter__(self) -> '_RecordingCursor':
        return self

    def __next__(self) -> Any:
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    def close(self) -> Any:
        return self._cursor.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class _ReplayCursorState:
    def __init__(self, records: list[dict[str, Any]]):
        self.records = records
        self.index = 0

    def next(self, operation: str) -> dict[str, Any]:
        if self.index >= len(self.records):
            raise AssertionError(f'No recorded psycopg operation available for {operation}')
        record = self.records[self.index]
        if record.get('operation') != operation:
            raise AssertionError('Recorded psycopg operation does not match replay operation')
        self.index += 1
        if record.get('exception'):
            _raise_recorded_exception(record)
        return record


class _ReplayConnection:
    def __init__(self, state: _ReplayCursorState):
        self._state = state
        self.closed = False

    def cursor(self, *args: Any, **kwargs: Any) -> '_ReplayCursor':
        return _ReplayCursor(self._state, args, kwargs)

    def close(self) -> None:
        self.closed = True


class _ReplayCursor:
    def __init__(self, state: _ReplayCursorState, cursor_args: tuple[Any, ...], cursor_kwargs: dict[str, Any]):
        self._state = state
        self._cursor_args = cursor_args
        self._cursor_kwargs = cursor_kwargs
        self._rows: list[Any] = []
        self._index = 0

    def __enter__(self) -> '_ReplayCursor':
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    def execute(self, sql: Any, params: Any = None, *args: Any, **kwargs: Any) -> '_ReplayCursor':
        record = self._state.next('psycopg.cursor.execute')
        if record.get('sql') != str(sql) or record.get('params') != _json_safe(params):
            raise AssertionError('Recorded psycopg query does not match replay query')
        expected_row_factory = record.get('row_factory')
        actual_row_factory = _row_factory_name(self._cursor_kwargs.get('row_factory'))
        if expected_row_factory != actual_row_factory:
            raise AssertionError('Recorded psycopg row factory does not match replay row factory')
        self._rows = record.get('rows') or []
        self._index = 0
        return self

    def fetchone(self) -> Any:
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def __iter__(self) -> '_ReplayCursor':
        return self

    def __next__(self) -> Any:
        row = self.fetchone()
        if row is None:
            raise StopIteration
        return row

    def close(self) -> None:
        return None


def install_live_recording_psycopg(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Record psycopg query results while still querying the live database."""
    import psycopg as pg

    records: list[dict[str, Any]] = []
    original_connect = pg.connect

    def recorded_connect(*args: Any, **kwargs: Any) -> _RecordingConnection:
        record = {'operation': 'psycopg.connect', **_connect_record(args, kwargs)}
        try:
            connection = original_connect(*args, **kwargs)
        except Exception as exc:
            record['exception'] = _exception_record(exc)
            records.append(record)
            _write_records(fixture_path, records)
            raise

        record['exception'] = None
        records.append(record)
        _write_records(fixture_path, records)
        return _RecordingConnection(connection, records, fixture_path)

    monkeypatch.setattr(pg, 'connect', recorded_connect)
    return records


def install_replay_psycopg(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay psycopg query results from fixture records."""
    import psycopg as pg

    records = json.loads(fixture_path.read_text())
    state = _ReplayCursorState(records)
    replayed: list[dict[str, Any]] = []

    def replayed_connect(*args: Any, **kwargs: Any) -> _ReplayConnection:
        record = state.next('psycopg.connect')
        expected = _connect_record(args, kwargs)
        if record.get('args') != expected['args'] or record.get('kwargs') != expected['kwargs']:
            raise AssertionError('Recorded psycopg connection does not match replay connection')
        replayed.append(record)
        return _ReplayConnection(state)

    monkeypatch.setattr(pg, 'connect', replayed_connect)
    return replayed
