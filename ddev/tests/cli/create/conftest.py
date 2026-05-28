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
