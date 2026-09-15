# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def github_actions_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide the GitHub Actions metadata required to render running comments."""
    monkeypatch.setenv("GITHUB_SERVER_URL", "https://github.com")
    monkeypatch.setenv("GITHUB_REPOSITORY", "DataDog/integrations-core")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
