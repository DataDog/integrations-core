# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from datadog_checks.dev.replay.redaction import REDACTED, scrub_json

_POOL_MANAGER = '<POOL_MANAGER>'


def _json_safe(value: Any) -> Any:
    return scrub_json(value)


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


def _exception_record(exc: BaseException) -> dict[str, str]:
    return {
        'type': type(exc).__name__,
        'module': type(exc).__module__,
        'message': str(scrub_json(str(exc))),
    }


def _raise_recorded_exception(record: dict[str, Any]) -> None:
    exception = record.get('exception') or {}
    message = exception.get('message', '')
    exception_type = exception.get('type')

    try:
        from clickhouse_connect.driver import exceptions as clickhouse_exceptions
    except Exception:
        clickhouse_exceptions = None

    if clickhouse_exceptions is not None:
        for name in ('OperationalError', 'DatabaseError', 'ProgrammingError', 'Error'):
            if exception_type == name and hasattr(clickhouse_exceptions, name):
                raise getattr(clickhouse_exceptions, name)(message)
    if exception_type == 'OSError':
        raise OSError(message)
    if exception_type == 'RuntimeError':
        raise RuntimeError(message)
    raise Exception(message)


def _safe_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    safe = {}
    for key, value in kwargs.items():
        if str(key) == 'pool_mgr':
            safe[str(key)] = _POOL_MANAGER
        elif str(key).lower() == 'password':
            safe[str(key)] = REDACTED
        else:
            safe[str(key)] = _json_safe(value)
    return safe


def _call_identity(args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        'args': [_json_safe(arg) for arg in args],
        'kwargs': _safe_kwargs(kwargs),
    }


def _query_identity(query: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        'sql': str(query),
        **_call_identity(args, kwargs),
    }


def _command_identity(command: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        'command': str(command),
        **_call_identity(args, kwargs),
    }


class _ReplayQueryResult:
    def __init__(self, record: dict[str, Any]):
        self.result_rows = record.get('result_rows') or []
        self.column_names = record.get('column_names') or []
        self.column_types = record.get('column_types') or []

    @property
    def first_row(self) -> Any:
        if not self.result_rows:
            return None
        return self.result_rows[0]


class _RecordingClient:
    def __init__(self, client: Any, records: list[dict[str, Any]], fixture_path: Path):
        self._client = client
        self._records = records
        self._fixture_path = fixture_path

    def _append(self, record: dict[str, Any]) -> None:
        self._records.append(record)
        _write_records(self._fixture_path, self._records)

    def query(self, query: Any, *args: Any, **kwargs: Any) -> Any:
        record = {'operation': 'clickhouse.client.query', **_query_identity(query, args, kwargs)}
        try:
            result = self._client.query(query, *args, **kwargs)
        except Exception as exc:
            record.update({'result_rows': [], 'exception': _exception_record(exc)})
            self._append(record)
            raise

        record.update(
            {
                'result_rows': _json_safe(getattr(result, 'result_rows', [])),
                'column_names': _json_safe(getattr(result, 'column_names', [])),
                'column_types': _json_safe(getattr(result, 'column_types', [])),
                'exception': None,
            }
        )
        self._append(record)
        return result

    def command(self, command: Any, *args: Any, **kwargs: Any) -> Any:
        record = {'operation': 'clickhouse.client.command', **_command_identity(command, args, kwargs)}
        try:
            result = self._client.command(command, *args, **kwargs)
        except Exception as exc:
            record.update({'result': None, 'exception': _exception_record(exc)})
            self._append(record)
            raise

        record.update({'result': _json_safe(result), 'exception': None})
        self._append(record)
        return result

    def ping(self) -> bool:
        record = {'operation': 'clickhouse.client.ping'}
        try:
            result = self._client.ping()
        except Exception as exc:
            record.update({'result': None, 'exception': _exception_record(exc)})
            self._append(record)
            raise

        record.update({'result': bool(result), 'exception': None})
        self._append(record)
        return bool(result)

    def close(self) -> Any:
        record = {'operation': 'clickhouse.client.close'}
        try:
            result = self._client.close()
        except Exception as exc:
            record.update({'result': None, 'exception': _exception_record(exc)})
            self._append(record)
            raise

        record.update({'result': _json_safe(result), 'exception': None})
        self._append(record)
        return result

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _ReplayState:
    def __init__(self, records: list[dict[str, Any]], replayed: list[dict[str, Any]]):
        self.records = records
        self.replayed = replayed
        self.consumed: set[int] = set()

    def take(self, operation: str, *, expected: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return the first unconsumed matching ClickHouse operation.

        ClickHouse check versions can legitimately reorder independent queries
        during refactors. Replaying by operation identity instead of strict global
        sequence lets compare-check focus on output regressions while still
        failing on missing/new SQL, command, or connection shapes. Duplicate
        identical operations remain ordered by their appearance in the fixture.
        """
        saw_operation = False
        for index, record in enumerate(self.records):
            if index in self.consumed or record.get('operation') != operation:
                continue
            saw_operation = True
            if expected is not None and any(record.get(key) != value for key, value in expected.items()):
                continue
            self.consumed.add(index)
            self.replayed.append(record)
            if record.get('exception'):
                _raise_recorded_exception(record)
            return record

        if expected is not None and saw_operation:
            raise AssertionError(f'Recorded ClickHouse {operation} does not match replay identity')
        raise AssertionError(f'No recorded ClickHouse operation available for {operation}')


class _ReplayClient:
    def __init__(self, state: _ReplayState):
        self._state = state

    def query(self, query: Any, *args: Any, **kwargs: Any) -> _ReplayQueryResult:
        expected = _query_identity(query, args, kwargs)
        record = self._state.take(
            'clickhouse.client.query',
            expected={'sql': expected['sql'], 'args': expected['args'], 'kwargs': expected['kwargs']},
        )
        return _ReplayQueryResult(record)

    def command(self, command: Any, *args: Any, **kwargs: Any) -> Any:
        expected = _command_identity(command, args, kwargs)
        try:
            record = self._state.take(
                'clickhouse.client.command',
                expected={'command': expected['command'], 'args': expected['args'], 'kwargs': expected['kwargs']},
            )
        except AssertionError as exc:
            if str(command).strip().upper() != 'SELECT VERSION()':
                raise
            try:
                # Older ClickHouse check versions fetched the version through
                # client.query('SELECT version()') while newer versions use
                # client.command(...). Treat those two client API shapes as
                # equivalent so release-to-PR replay can focus on emitted output.
                query_record = self._state.take(
                    'clickhouse.client.query',
                    expected={'sql': 'SELECT version()', 'args': [], 'kwargs': {}},
                )
            except AssertionError:
                raise exc
            rows = query_record.get('result_rows') or []
            if rows and rows[0]:
                return rows[0][0]
            return None
        return record.get('result')

    def ping(self) -> bool:
        return bool(self._state.take('clickhouse.client.ping').get('result'))

    def close(self) -> Any:
        return self._state.take('clickhouse.client.close').get('result')


def install_live_recording_clickhouse_connect(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path
) -> list[dict[str, Any]]:
    """Record clickhouse-connect client calls while still querying the live database."""
    import clickhouse_connect

    records: list[dict[str, Any]] = []
    original_get_client = clickhouse_connect.get_client

    def recorded_get_client(*args: Any, **kwargs: Any) -> _RecordingClient:
        record = {'operation': 'clickhouse_connect.get_client', **_call_identity(args, kwargs)}
        try:
            client = original_get_client(*args, **kwargs)
        except Exception as exc:
            record['exception'] = _exception_record(exc)
            records.append(record)
            _write_records(fixture_path, records)
            raise

        record['exception'] = None
        records.append(record)
        _write_records(fixture_path, records)
        return _RecordingClient(client, records, fixture_path)

    monkeypatch.setattr(clickhouse_connect, 'get_client', recorded_get_client)
    return records


def install_replay_clickhouse_connect(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay clickhouse-connect client calls from recorded fixture records."""
    import clickhouse_connect

    records = json.loads(fixture_path.read_text())
    replayed: list[dict[str, Any]] = []
    state = _ReplayState(records, replayed)

    def replayed_get_client(*args: Any, **kwargs: Any) -> _ReplayClient:
        expected = _call_identity(args, kwargs)
        state.take(
            'clickhouse_connect.get_client',
            expected={'args': expected['args'], 'kwargs': expected['kwargs']},
        )
        return _ReplayClient(state)

    monkeypatch.setattr(clickhouse_connect, 'get_client', replayed_get_client)
    return replayed
