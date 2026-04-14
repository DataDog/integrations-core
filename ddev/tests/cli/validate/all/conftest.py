# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _clean_github_env(monkeypatch):
    """Provide a consistent GitHub Actions environment for all tests."""
    for key in ("GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REF", "GITHUB_STEP_SUMMARY"):
        monkeypatch.delenv(key, raising=False)


def completed_process(returncode=0, stdout="", stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


@pytest.fixture
def mock_app():
    """Mock Application that records display calls and raises SystemExit on abort."""
    app = MagicMock()
    app.abort.side_effect = SystemExit(1)
    return app
