# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from datadog_checks.dev.replay.redaction import scrub_json


def _normalize_cmd(cmd: Any) -> list[str]:
    if isinstance(cmd, (list, tuple)):
        return [str(part) for part in scrub_json(list(cmd))]
    return [str(scrub_json(str(cmd)))]


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
    if exception_type == 'OSError':
        raise OSError(message)
    if exception_type == 'ValueError':
        raise ValueError(message)
    if exception_type == 'RuntimeError':
        raise RuntimeError(message)
    raise Exception(message)


def _record_success(cmd: Any, stdout: str, stderr: str, returncode: int) -> dict[str, Any]:
    return {
        'argv': _normalize_cmd(cmd),
        'stdout': scrub_json(stdout),
        'stderr': scrub_json(stderr),
        'returncode': returncode,
        'exception': None,
    }


def _record_exception(cmd: Any, exc: BaseException) -> dict[str, Any]:
    return {
        'argv': _normalize_cmd(cmd),
        'stdout': None,
        'stderr': None,
        'returncode': None,
        'exception': _exception_record(exc),
    }


def install_live_recording_get_subprocess_output(
    monkeypatch: pytest.MonkeyPatch, fixture_path: Path
) -> list[dict[str, Any]]:
    """Record subprocess helper calls while still executing them live."""
    from datadog_checks.base.utils import subprocess_output

    records: list[dict[str, Any]] = []
    original_get_subprocess_output = subprocess_output.get_subprocess_output

    def recorded_get_subprocess_output(cmd: Any, log: Any, *args: Any, **kwargs: Any) -> tuple[str, str, int]:
        try:
            stdout, stderr, returncode = original_get_subprocess_output(cmd, log, *args, **kwargs)
        except Exception as exc:
            records.append(_record_exception(cmd, exc))
            fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
            raise

        records.append(_record_success(cmd, stdout, stderr, returncode))
        fixture_path.write_text(json.dumps(records, indent=2, sort_keys=True) + '\n')
        return stdout, stderr, returncode

    monkeypatch.setattr(subprocess_output, 'get_subprocess_output', recorded_get_subprocess_output)
    return records


def install_replay_get_subprocess_output(monkeypatch: pytest.MonkeyPatch, fixture_path: Path) -> list[dict[str, Any]]:
    """Replay subprocess helper calls from recorded fixture records in order."""
    from datadog_checks.base.utils import subprocess_output

    records = json.loads(fixture_path.read_text())
    replayed: list[dict[str, Any]] = []

    def replayed_get_subprocess_output(cmd: Any, log: Any, *args: Any, **kwargs: Any) -> tuple[str, str, int]:
        if len(replayed) >= len(records):
            raise AssertionError('No recorded subprocess output available for replay')

        record = records[len(replayed)]
        argv = _normalize_cmd(cmd)
        if record['argv'] != argv:
            raise AssertionError('Recorded subprocess command does not match replay command')

        replayed.append(record)
        if record.get('exception'):
            _raise_recorded_exception(record)

        return record['stdout'], record['stderr'], record['returncode']

    monkeypatch.setattr(subprocess_output, 'get_subprocess_output', replayed_get_subprocess_output)
    return replayed
