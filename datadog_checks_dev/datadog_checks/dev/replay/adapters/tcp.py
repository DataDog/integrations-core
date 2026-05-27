# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import base64
import json
import socket
from pathlib import Path
from typing import Any

import pytest

from datadog_checks.dev.replay.redaction import scrub_json


def _bytes_record(data: bytes) -> str:
    return base64.b64encode(data).decode('ascii')


def _record_bytes(data: str) -> bytes:
    return base64.b64decode(data.encode('ascii'))


def _json_safe_address(address: Any) -> Any:
    if isinstance(address, tuple):
        return [_json_safe_address(part) for part in address]
    if isinstance(address, list):
        return [_json_safe_address(part) for part in address]
    return address


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
    if exception_type == 'timeout':
        raise socket.timeout(message)
    if exception_type == 'gaierror':
        raise socket.gaierror(message)
    if exception_type in {'OSError', 'error'}:
        raise OSError(message)
    raise Exception(message)


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


class _RecordingSocket:
    def __init__(self, sock: socket.socket, records: list[dict[str, Any]], fixture_path: Path):
        self._sock = sock
        self._records = records
        self._fixture_path = fixture_path

    def _append(self, record: dict[str, Any]) -> None:
        self._records.append(record)
        _write_records(self._fixture_path, self._records)

    def send(self, data: bytes, *args: Any, **kwargs: Any) -> int:
        sent = self._sock.send(data, *args, **kwargs)
        self._append({'operation': 'socket.send', 'data_b64': _bytes_record(data[:sent]), 'exception': None})
        return sent

    def sendall(self, data: bytes, *args: Any, **kwargs: Any) -> None:
        self._sock.sendall(data, *args, **kwargs)
        self._append({'operation': 'socket.sendall', 'data_b64': _bytes_record(data), 'exception': None})
        return None

    def recv(self, bufsize: int, *args: Any, **kwargs: Any) -> bytes:
        try:
            data = self._sock.recv(bufsize, *args, **kwargs)
        except Exception as exc:
            self._append({'operation': 'socket.recv', 'bufsize': bufsize, 'exception': _exception_record(exc)})
            raise
        self._append(
            {'operation': 'socket.recv', 'bufsize': bufsize, 'data_b64': _bytes_record(data), 'exception': None}
        )
        return data

    def settimeout(self, timeout: float | None) -> None:
        self._sock.settimeout(timeout)
        self._append({'operation': 'socket.settimeout', 'timeout': timeout, 'exception': None})

    def close(self) -> None:
        self._sock.close()
        self._append({'operation': 'socket.close', 'exception': None})

    def __enter__(self) -> '_RecordingSocket':
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._sock, name)


class _ReplaySocket:
    def __init__(self, records: list[dict[str, Any]], replayed: list[dict[str, Any]]):
        self._records = records
        self._replayed = replayed
        self._pending_recv = b''

    def _next(self, operation: str) -> dict[str, Any]:
        if len(self._replayed) >= len(self._records):
            raise AssertionError(f'No recorded TCP socket operation available for {operation}')
        record = self._records[len(self._replayed)]
        if record.get('operation') != operation:
            raise AssertionError('Recorded TCP socket operation does not match replay operation')
        self._replayed.append(record)
        if record.get('exception'):
            _raise_recorded_exception(record)
        return record

    def send(self, data: bytes, *args: Any, **kwargs: Any) -> int:
        record = self._next('socket.send')
        if _record_bytes(record['data_b64']) != data:
            raise AssertionError('Recorded TCP socket send does not match replay send')
        return len(data)

    def sendall(self, data: bytes, *args: Any, **kwargs: Any) -> None:
        record = self._next('socket.sendall')
        if _record_bytes(record['data_b64']) != data:
            raise AssertionError('Recorded TCP socket sendall does not match replay sendall')
        return None

    def recv(self, bufsize: int, *args: Any, **kwargs: Any) -> bytes:
        if not self._pending_recv:
            record = self._next('socket.recv')
            self._pending_recv = _record_bytes(record.get('data_b64', ''))

        data = self._pending_recv[:bufsize]
        self._pending_recv = self._pending_recv[bufsize:]
        return data

    def settimeout(self, timeout: float | None) -> None:
        record = self._next('socket.settimeout')
        if record.get('timeout') != timeout:
            raise AssertionError('Recorded TCP socket timeout does not match replay timeout')

    def close(self) -> None:
        self._next('socket.close')

    def __enter__(self) -> '_ReplaySocket':
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()


def install_live_recording_tcp_clients(
    monkeypatch: pytest.MonkeyPatch,
    fixture_path: Path,
    check_name: str | None = None,
    *,
    strict: bool = True,
) -> list[dict[str, Any]]:
    """Record plain TCP traffic through socket.create_connection."""
    records: list[dict[str, Any]] = []
    original_create_connection = socket.create_connection

    def recorded_create_connection(
        address: Any, timeout: float | object = socket._GLOBAL_DEFAULT_TIMEOUT, source_address: Any = None
    ) -> _RecordingSocket:
        record = {
            'operation': 'socket.create_connection',
            'address': _json_safe_address(address),
            'timeout': None if timeout is socket._GLOBAL_DEFAULT_TIMEOUT else timeout,
            'source_address': _json_safe_address(source_address),
        }
        try:
            sock = original_create_connection(address, timeout, source_address)
        except Exception as exc:
            record['exception'] = _exception_record(exc)
            records.append(record)
            _write_records(fixture_path, records)
            raise

        record['exception'] = None
        records.append(record)
        _write_records(fixture_path, records)
        return _RecordingSocket(sock, records, fixture_path)

    monkeypatch.setattr(socket, 'create_connection', recorded_create_connection)
    return records


def install_replay_tcp_clients(
    monkeypatch: pytest.MonkeyPatch,
    fixture_path: Path,
    check_name: str | None = None,
    *,
    strict: bool = True,
) -> list[dict[str, Any]]:
    """Replay plain TCP traffic recorded through socket.create_connection."""
    records = json.loads(fixture_path.read_text())
    replayed: list[dict[str, Any]] = []

    def replayed_create_connection(
        address: Any, timeout: float | object = socket._GLOBAL_DEFAULT_TIMEOUT, source_address: Any = None
    ) -> _ReplaySocket:
        if len(replayed) >= len(records):
            raise AssertionError('No recorded TCP socket connection available for replay')
        record = records[len(replayed)]
        if record.get('operation') != 'socket.create_connection':
            raise AssertionError('Recorded TCP socket operation does not match replay connection')
        expected_timeout = None if timeout is socket._GLOBAL_DEFAULT_TIMEOUT else timeout
        if record.get('address') != _json_safe_address(address) or record.get('timeout') != expected_timeout:
            raise AssertionError('Recorded TCP socket connection does not match replay connection')
        replayed.append(record)
        if record.get('exception'):
            _raise_recorded_exception(record)
        return _ReplaySocket(records, replayed)

    monkeypatch.setattr(socket, 'create_connection', replayed_create_connection)
    return replayed
