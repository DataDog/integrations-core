# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def no_anthropic_env(monkeypatch):
    """Keep the developer's real keys out of the test so the no-key path is reachable."""
    monkeypatch.delenv('DD_ANTHROPIC_API_KEY', raising=False)
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)


@pytest.fixture(autouse=True)
def restore_cwd():
    """The command chdirs into the repo root on the orchestrator path; undo it for the next test."""
    cwd = os.getcwd()
    yield
    os.chdir(cwd)


@pytest.fixture
def docker_dir(tmp_path):
    """A valid `--docker-path` directory."""
    path = tmp_path / 'docker'
    path.mkdir()
    (path / 'docker-compose.yaml').write_text('services: {}\n')
    return path


@pytest.fixture
def prd_file(tmp_path):
    """A valid, non-empty `--prd` file."""
    path = tmp_path / 'prd.md'
    path.write_text('Drop the foo_total metric.\n')
    return path


@pytest.fixture
def ai_repo(tmp_path_factory, config_file):
    """An empty repo that `app.repo.path` resolves to, isolated from the real checkout."""
    repo_path = tmp_path_factory.mktemp('ai-repo')
    config_file.model.repos['core'] = str(repo_path)
    config_file.save()
    return repo_path


@pytest.fixture
def with_api_key(config_file):
    """Set an Anthropic key in config so validation gets past the key check."""
    config_file.model.ai.anthropic_api_key = 'sk-test'
    config_file.save()
    return config_file
