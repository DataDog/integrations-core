# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def _exception_record(exc: BaseException) -> dict[str, str]:
    return {
        'type': type(exc).__name__,
        'module': type(exc).__module__,
        'message': str(exc),
    }


def _write_records(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')


def _record_result(value: Any) -> dict[str, Any]:
    return {'result': value, 'exception': None}


def _record_exception(exc: BaseException) -> dict[str, Any]:
    return {'result': None, 'exception': _exception_record(exc)}


def _raise_recorded_exception(record: dict[str, Any]) -> None:
    exception = record.get('exception') or {}
    message = exception.get('message', '')
    exception_type = exception.get('type')
    if exception_type == 'NoSuchProcess':
        import psutil

        raise psutil.NoSuchProcess(pid=None, name=message)
    if exception_type == 'AccessDenied':
        import psutil

        raise psutil.AccessDenied(pid=None, name=message)
    if exception_type in {'OSError', 'FileNotFoundError'}:
        raise OSError(message)
    raise Exception(message)


def _normalize_cmdline(cmdline: Any) -> list[str]:
    if cmdline is None:
        return []
    return [str(part) for part in cmdline]


def _cpu_times_to_list(cpu_times: Any) -> list[float]:
    return [float(part) for part in cpu_times]


class _RecordingProcess:
    def __init__(self, process: Any, records: list[dict[str, Any]], fixture_path: Path):
        self._process = process
        self._records = records
        self._fixture_path = fixture_path
        self.pid = getattr(process, 'pid', None)

    @property
    def name(self) -> str | None:
        return getattr(self._process, 'name', None)

    def cmdline(self) -> list[str]:
        try:
            cmdline = _normalize_cmdline(self._process.cmdline())
        except Exception as exc:
            result = _record_exception(exc)
            self._records.append({'operation': 'psutil.Process.cmdline', 'pid': self.pid, **result})
            _write_records(self._fixture_path, self._records)
            raise

        self._records.append({'operation': 'psutil.Process.cmdline', 'pid': self.pid, **_record_result(cmdline)})
        _write_records(self._fixture_path, self._records)
        return cmdline

    def children(self) -> list['_RecordingProcess']:
        try:
            children = self._process.children()
        except Exception as exc:
            result = _record_exception(exc)
            self._records.append({'operation': 'psutil.Process.children', 'pid': self.pid, **result})
            _write_records(self._fixture_path, self._records)
            raise

        child_pids = [getattr(child, 'pid', None) for child in children]
        self._records.append({'operation': 'psutil.Process.children', 'pid': self.pid, **_record_result(child_pids)})
        _write_records(self._fixture_path, self._records)
        return [_RecordingProcess(child, self._records, self._fixture_path) for child in children]

    def cpu_times(self) -> list[float]:
        try:
            cpu_times = _cpu_times_to_list(self._process.cpu_times())
        except Exception as exc:
            result = _record_exception(exc)
            self._records.append({'operation': 'psutil.Process.cpu_times', 'pid': self.pid, **result})
            _write_records(self._fixture_path, self._records)
            raise

        self._records.append({'operation': 'psutil.Process.cpu_times', 'pid': self.pid, **_record_result(cpu_times)})
        _write_records(self._fixture_path, self._records)
        return cpu_times


class _ReplayCursor:
    def __init__(self, records: list[dict[str, Any]]):
        self._records = records
        self._index = 0

    def next(self, operation: str, pid: int | None = None) -> dict[str, Any]:
        if self._index >= len(self._records):
            raise AssertionError(f'No recorded process operation available for {operation}')
        record = self._records[self._index]
        if record.get('operation') != operation:
            raise AssertionError('Recorded process operation does not match replay operation')
        if pid is not None and record.get('pid') != pid:
            raise AssertionError('Recorded process pid does not match replay pid')
        self._index += 1
        if record.get('exception'):
            _raise_recorded_exception(record)
        return record


class _ReplayProcess:
    def __init__(self, pid: int | None, cursor: _ReplayCursor):
        self.pid = pid
        self._cursor = cursor
        self.name = None

    def cmdline(self) -> list[str]:
        return self._cursor.next('psutil.Process.cmdline', self.pid).get('result') or []

    def children(self) -> list['_ReplayProcess']:
        child_pids = self._cursor.next('psutil.Process.children', self.pid).get('result') or []
        return [_ReplayProcess(pid, self._cursor) for pid in child_pids]

    def cpu_times(self) -> list[float]:
        return self._cursor.next('psutil.Process.cpu_times', self.pid).get('result') or []


def _install_gunicorn_version_recorder(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path, records: list[dict[str, Any]]
) -> None:
    try:
        from datadog_checks.gunicorn import gunicorn
    except Exception:
        return

    original_get_gunicorn_version = gunicorn.get_gunicorn_version

    def recorded_get_gunicorn_version(cmd: str) -> tuple[str, str, int]:
        try:
            stdout, stderr, returncode = original_get_gunicorn_version(cmd)
        except Exception as exc:
            records.append({'operation': 'gunicorn.get_gunicorn_version', 'cmd': cmd, **_record_exception(exc)})
            _write_records(fixture_path, records)
            raise

        result = {'stdout': stdout, 'stderr': stderr, 'returncode': returncode}
        records.append({'operation': 'gunicorn.get_gunicorn_version', 'cmd': cmd, **_record_result(result)})
        _write_records(fixture_path, records)
        return stdout, stderr, returncode

    monkeypatch.setattr(gunicorn, 'get_gunicorn_version', recorded_get_gunicorn_version)


def _install_gunicorn_version_replay(monkeypatch: pytest.MonkeyPatch, cursor: _ReplayCursor) -> None:
    try:
        from datadog_checks.gunicorn import gunicorn
    except Exception:
        return

    def replayed_get_gunicorn_version(cmd: str) -> tuple[str, str, int]:
        record = cursor.next('gunicorn.get_gunicorn_version')
        if record.get('cmd') != cmd:
            raise AssertionError('Recorded gunicorn version command does not match replay command')
        result = record.get('result') or {}
        return result.get('stdout', ''), result.get('stderr', ''), result.get('returncode', 0)

    monkeypatch.setattr(gunicorn, 'get_gunicorn_version', replayed_get_gunicorn_version)


def install_live_recording_process_state(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Record psutil process-state calls and Gunicorn version probing while executing live."""
    import psutil

    records: list[dict[str, Any]] = []
    original_process_iter = psutil.process_iter

    def recorded_process_iter(*args: Any, **kwargs: Any) -> list[_RecordingProcess]:
        processes = list(original_process_iter(*args, **kwargs))
        pids = [getattr(process, 'pid', None) for process in processes]
        records.append({'operation': 'psutil.process_iter', 'result': pids, 'exception': None})
        _write_records(fixture_path, records)
        return [_RecordingProcess(process, records, fixture_path) for process in processes]

    monkeypatch.setattr(psutil, 'process_iter', recorded_process_iter)
    _install_gunicorn_version_recorder(monkeypatch, fixture_path, records)
    return records


def install_replay_process_state(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay psutil process-state calls and Gunicorn version probing from fixture records."""
    import psutil

    records = json.loads(fixture_path.read_text())
    cursor = _ReplayCursor(records)
    replayed: list[dict[str, Any]] = []

    def replayed_process_iter(*args: Any, **kwargs: Any) -> list[_ReplayProcess]:
        record = cursor.next('psutil.process_iter')
        replayed.append(record)
        return [_ReplayProcess(pid, cursor) for pid in (record.get('result') or [])]

    monkeypatch.setattr(psutil, 'process_iter', replayed_process_iter)
    _install_gunicorn_version_replay(monkeypatch, cursor)
    monkeypatch.setattr('time.sleep', lambda seconds: None)
    return replayed
