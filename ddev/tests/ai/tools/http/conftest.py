# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest

from ddev.ai.tools.http.response_store import ResponseStore


@pytest.fixture
def store(tmp_path: Path) -> ResponseStore:
    return ResponseStore(tmp_path / "responses")
