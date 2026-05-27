# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Bootstrap the replay adapters inside an Agent embedded Python process.

Activation strategy:

1. ``sitecustomize.py`` calls :func:`activate` at every interpreter start.
2. We read ``DDEV_REPLAY_CONFIG`` (path) to learn:
   - replay mode (``record`` | ``replay``)
   - check name
   - fixture file path (a manifest pointing to per-adapter component files)
   - enabled adapter set
   - replay time base and reading interval (for time freezing)
3. We install all enabled adapters using :class:`MonkeyPatch` from this
   package. The adapters themselves are the same source that runs in the
   no-Agent harness, copied in by the shim builder with their internal
   ``datadog_checks.dev.replay.*`` imports rewritten to ``ddev_shim.*``.
4. We freeze ``time.time``, ``time.monotonic``, and ``time.perf_counter``
   to a deterministic offset that advances by ``reading_interval`` each
   time the shim sees a new reading marker file. The Agent's
   ``--check-times`` loop runs the check N times; we detect the boundary
   by checking the ``DDEV_REPLAY_RUN_MARKER`` file modification time and
   advancing the offset accordingly.
5. Errors during activation are written to ``DDEV_REPLAY_BOOTSTRAP_LOG``
   (stderr fallback). A failed activation never raises — the Agent must
   continue to boot so the membership/inventory probes still work.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any

_ACTIVATED = False
_MONKEYPATCH: Any = None  # holds the singleton ddev_shim MonkeyPatch
_CONFIG: dict[str, Any] = {}


def _log(msg: str) -> None:
    path = os.environ.get('DDEV_REPLAY_BOOTSTRAP_LOG')
    line = f'[ddev_shim] {msg}\n'
    try:
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'a', encoding='utf-8') as fh:
                fh.write(line)
        else:
            sys.stderr.write(line)
    except Exception:  # noqa: BLE001 - logging must never break boot
        pass


def _read_config() -> dict[str, Any] | None:
    cfg_path = os.environ.get('DDEV_REPLAY_CONFIG')
    if not cfg_path:
        return None
    try:
        return json.loads(Path(cfg_path).read_text())
    except FileNotFoundError:
        _log(f'replay config not found at {cfg_path}; shim disabled')
        return None
    except Exception as exc:  # noqa: BLE001
        _log(f'failed to read replay config: {exc!r}')
        return None


def _install_time_freeze(monkeypatch: Any, base: float, interval: float) -> None:
    """Pin time.* to a deterministic schedule.

    The Agent runs the check N times via ``--check-times`` / ``--check-rate``.
    Each invocation advances the shim's reading counter by one and adds
    ``interval`` seconds to the frozen clock. The counter is stored in a
    file under ``DDEV_REPLAY_RUN_MARKER`` so it survives across the brief
    process boundary between Agent CLI and rtloader sub-interpreter.
    """

    marker = os.environ.get('DDEV_REPLAY_RUN_MARKER')

    def _read_index() -> int:
        if not marker:
            return 0
        try:
            return int(Path(marker).read_text().strip() or '0')
        except FileNotFoundError:
            return 0
        except Exception:  # noqa: BLE001
            return 0

    def _frozen_now() -> float:
        return base + _read_index() * interval

    monkeypatch.setattr(time, 'time', _frozen_now)
    monkeypatch.setattr(time, 'monotonic', _frozen_now)
    monkeypatch.setattr(time, 'perf_counter', _frozen_now)

    # Sleep is a no-op: the check should not actually pause during replay.
    monkeypatch.setattr(time, 'sleep', lambda _s: None)


def activate() -> None:
    """Idempotent shim activation called from ``sitecustomize.py``."""
    global _ACTIVATED, _MONKEYPATCH, _CONFIG
    if _ACTIVATED:
        return

    config = _read_config()
    if config is None:
        return

    _CONFIG = config
    mode = config.get('mode')
    if mode not in {'record', 'replay'}:
        _log(f'unsupported replay mode {mode!r}; shim disabled')
        return

    fixture = config.get('fixture')
    if not fixture:
        _log('no fixture in replay config; shim disabled')
        return

    enabled = tuple(config.get('adapters') or ())
    check_name = config.get('check_name')
    base_time = float(config.get('replay_time', 1_700_000_000.0))
    interval = float(config.get('reading_interval', 1.0))

    try:
        # Lazy imports so a broken adapter file cannot prevent boot.
        from ddev_shim._pytest_monkeypatch import MonkeyPatch
        from ddev_shim.adapters import install_replay_adapters

        mp = MonkeyPatch()
        _install_time_freeze(mp, base_time, interval)
        records = install_replay_adapters(mp, mode, Path(fixture), check_name, enabled or None)
        _MONKEYPATCH = mp
        _ACTIVATED = True
        _log(f'activated mode={mode} adapters={list(records)} check={check_name!r}')
    except Exception as exc:  # noqa: BLE001
        _log(f'activation failed: {exc!r}\n{traceback.format_exc()}')


def deactivate() -> None:
    """Best-effort revert. Used in tests; the Agent does not call this."""
    global _ACTIVATED, _MONKEYPATCH
    if _MONKEYPATCH is not None:
        try:
            _MONKEYPATCH.undo()
        except Exception:  # noqa: BLE001
            pass
    _MONKEYPATCH = None
    _ACTIVATED = False
