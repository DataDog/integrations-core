# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.repo.core import Repository


@pytest.fixture
def empty_repo(tmp_path_factory, config_file):
    """A clean repo on disk with no integrations, ready for `ddev create` to scaffold into."""
    repo_path = tmp_path_factory.mktemp('integrations-core')
    repo = Repository('integrations-core', str(repo_path))

    config_file.model.repos['core'] = str(repo.path)
    config_file.save()

    return repo


@pytest.fixture
def fail_on_second_write(monkeypatch):
    """Make `TemplateFile.write` raise `PermissionError` on its second invocation per test.

    Lets a test exercise the partial-write failure path without depending on a real
    filesystem permission flip mid-scaffold.
    """
    from ddev.cli.create import _scaffold as scaffold_module

    original_write = scaffold_module.TemplateFile.write
    call_count = {'n': 0}

    def flaky_write(self):
        call_count['n'] += 1
        if call_count['n'] == 2:
            raise PermissionError(13, 'simulated mid-write failure')
        return original_write(self)

    monkeypatch.setattr(scaffold_module.TemplateFile, 'write', flaky_write)
