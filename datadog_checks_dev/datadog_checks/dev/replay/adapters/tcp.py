# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import base64
import json
from io import StringIO
from pathlib import Path
from typing import Any

import pytest


def _json_safe(value: Any) -> Any:
    if isinstance(value, bytes):
        return {'__bytes__': base64.b64encode(value).decode('ascii')}
    if isinstance(value, dict):
        return {_json_safe(key): _json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _from_json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value) == {'__bytes__'}:
            return base64.b64decode(value['__bytes__'].encode('ascii'))
        return {_from_json_safe(key): _from_json_safe(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_from_json_safe(item) for item in value]
    return value


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
    if exception_type == 'OSError':
        raise OSError(message)
    if exception_type == 'TimeoutError':
        raise TimeoutError(message)
    if exception_type == 'ConnectionError':
        raise ConnectionError(message)
    if exception_type == 'AssertionError':
        raise AssertionError(message)
    raise Exception(message)


def _args(args: tuple[Any, ...]) -> list[Any]:
    return [_json_safe(arg) for arg in args]


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


def install_live_recording_tcp_clients(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Record simple TCP-client calls used by memcache and ZooKeeper checks."""
    records: list[dict[str, Any]] = []
    _install_memcache_recorder(monkeypatch, fixture_path, records)
    _install_zookeeper_recorder(monkeypatch, fixture_path, records)
    return records


def install_replay_tcp_clients(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay simple TCP-client calls used by memcache and ZooKeeper checks."""
    records = json.loads(fixture_path.read_text())
    replayed: list[dict[str, Any]] = []
    _install_memcache_replay(monkeypatch, records, replayed)
    _install_zookeeper_replay(monkeypatch, records, replayed)
    return replayed


def _next_record(
    records: list[dict[str, Any]], replayed: list[dict[str, Any]], operation: str, args: list[Any]
) -> dict[str, Any]:
    if len(replayed) >= len(records):
        raise AssertionError(f'No recorded TCP client response available for {operation}')

    record = records[len(replayed)]
    if record['operation'] != operation or record.get('args', []) != args:
        raise AssertionError('Recorded TCP client operation does not match replay operation')

    replayed.append(record)
    if record.get('exception'):
        _raise_recorded_exception(record)
    return record


def _install_memcache_recorder(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, records: list[dict[str, Any]]
) -> None:
    try:
        import bmemcached
    except Exception:
        return

    original_stats = bmemcached.Client.stats

    def recorded_stats(client: Any, *args: Any, **kwargs: Any) -> Any:
        record = {'operation': 'bmemcached.Client.stats', 'args': _args(args), 'kwargs': _json_safe(kwargs)}
        try:
            result = original_stats(client, *args, **kwargs)
        except Exception as exc:
            record['exception'] = _exception_record(exc)
            records.append(record)
            _write_records(fixture_path, records)
            raise

        record['result'] = _json_safe(result)
        record['exception'] = None
        records.append(record)
        _write_records(fixture_path, records)
        return result

    monkeypatch.setattr(bmemcached.Client, 'stats', recorded_stats)


def _install_memcache_replay(
    monkeypatch: pytest.MonkeyPatch, records: list[dict[str, Any]], replayed: list[dict[str, Any]]
) -> None:
    try:
        import bmemcached
    except Exception:
        return

    def replayed_stats(client: Any, *args: Any, **kwargs: Any) -> Any:
        record = _next_record(records, replayed, 'bmemcached.Client.stats', _args(args))
        return _from_json_safe(record.get('result'))

    monkeypatch.setattr(bmemcached.Client, 'stats', replayed_stats)


def _install_zookeeper_recorder(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, records: list[dict[str, Any]]
) -> None:
    try:
        from datadog_checks.zk.zk import ZookeeperCheck
    except Exception:
        return

    original_send_command = ZookeeperCheck._send_command

    def recorded_send_command(check: Any, command: str) -> StringIO:
        record = {'operation': 'ZookeeperCheck._send_command', 'args': [command], 'kwargs': {}}
        try:
            result = original_send_command(check, command)
        except Exception as exc:
            record['exception'] = _exception_record(exc)
            records.append(record)
            _write_records(fixture_path, records)
            raise

        output = result.getvalue()
        record['result'] = output
        record['exception'] = None
        records.append(record)
        _write_records(fixture_path, records)
        return StringIO(output)

    monkeypatch.setattr(ZookeeperCheck, '_send_command', recorded_send_command)


def _install_zookeeper_replay(
    monkeypatch: pytest.MonkeyPatch, records: list[dict[str, Any]], replayed: list[dict[str, Any]]
) -> None:
    try:
        from datadog_checks.zk.zk import ZookeeperCheck
    except Exception:
        return

    def replayed_send_command(check: Any, command: str) -> StringIO:
        record = _next_record(records, replayed, 'ZookeeperCheck._send_command', [command])
        return StringIO(record.get('result', ''))

    monkeypatch.setattr(ZookeeperCheck, '_send_command', replayed_send_command)
