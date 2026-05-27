# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Build the bind-mountable shim bundle for the Agent container.

The bundle layout is:

    <bundle>/
        sitecustomize.py
        ddev_shim_autoload.pth
        ddev_shim/
            __init__.py
            _pytest_monkeypatch.py
            bootstrap.py
            redaction.py
            adapters/
                __init__.py
                requests.py
                subprocess.py
                tcp.py
                process.py
                psycopg.py
                clickhouse_connect.py

The bundle is assembled by copying:

- the static payload at ``shim_payload/`` (sitecustomize, .pth, bootstrap,
  monkeypatch stub, package ``__init__``),
- the live adapter modules from ``datadog_checks/dev/replay/adapters/`` and
  ``datadog_checks/dev/replay/redaction.py``, with all internal
  ``datadog_checks.dev.replay.*`` imports rewritten to ``ddev_shim.*``.

Keeping the adapter copy live ensures the in-Agent shim and the no-Agent
pytest harness never drift apart.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_PAYLOAD_DIR = _THIS_DIR / 'shim_payload'
_REPLAY_ROOT = _THIS_DIR.parent  # datadog_checks/dev/replay
_ADAPTERS_SRC = _REPLAY_ROOT / 'adapters'
_REDACTION_SRC = _REPLAY_ROOT / 'redaction.py'

_IMPORT_REWRITES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r'^from datadog_checks\.dev\.replay\.adapters\.(\w+) import', re.M), r'from ddev_shim.adapters.\1 import'),
    (re.compile(r'^from datadog_checks\.dev\.replay\.adapters import', re.M), r'from ddev_shim.adapters import'),
    (re.compile(r'^from datadog_checks\.dev\.replay\.redaction import', re.M), r'from ddev_shim.redaction import'),
    (re.compile(r'^from datadog_checks\.dev\.replay\.adapter_stats import', re.M), r'from ddev_shim.adapter_stats import'),
    # ``import pytest`` -> shim-internal stand-in. The replay adapters only
    # use ``pytest.MonkeyPatch`` as a type hint, never call any other
    # pytest API. Replacing the import with a small shim module keeps the
    # type hints valid without dragging pytest into the Agent image.
    (re.compile(r'^import pytest\b', re.M), 'from ddev_shim import _pytest_monkeypatch as pytest'),
)


def _rewrite_imports(source: str) -> str:
    out = source
    for pattern, replacement in _IMPORT_REWRITES:
        out = pattern.sub(replacement, out)
    return out


def build_bundle(target_dir: Path) -> Path:
    """Materialise the shim bundle at ``target_dir``.

    Returns the absolute path of the directory. Safe to call repeatedly;
    re-uses ``target_dir`` and overwrites contents.
    """

    target_dir = target_dir.resolve()
    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True)

    # Copy static payload (sitecustomize, .pth, ddev_shim/{__init__,bootstrap,_pytest_monkeypatch})
    shutil.copytree(_PAYLOAD_DIR, target_dir, dirs_exist_ok=True)

    pkg_dir = target_dir / 'ddev_shim'
    adapters_dir = pkg_dir / 'adapters'
    adapters_dir.mkdir(exist_ok=True)

    # Copy redaction.py (small, no internal cross-deps beyond stdlib)
    (pkg_dir / 'redaction.py').write_text(_rewrite_imports(_REDACTION_SRC.read_text()))

    # Copy every adapter module + the adapters package __init__.
    for src in sorted(_ADAPTERS_SRC.glob('*.py')):
        (adapters_dir / src.name).write_text(_rewrite_imports(src.read_text()))

    # adapter_stats.py is only used by output.py (which we do not ship) but
    # the rewrite layer references it. Provide an empty stub to satisfy
    # any incidental imports.
    (pkg_dir / 'adapter_stats.py').write_text(
        '"""Stub. The full implementation lives in datadog_checks_dev only."""\n'
        'def summarize_adapter_records(*_args, **_kwargs):\n'
        '    return {}\n'
    )

    return target_dir
