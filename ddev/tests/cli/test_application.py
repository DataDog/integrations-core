# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from datadog_checks.dev.tooling.constants import REPO_CHOICES, get_root, set_root

from ddev.cli.application import Application
from ddev.utils.fs import Path


@pytest.mark.parametrize('repo_name', ['core', 'extras', 'marketplace'])
def test_initialize_old_cli_here_uses_configured_repo_identity(tmp_path, repository, config_file, repo_name):
    set_root('')
    config_file.model.repo = repo_name
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.save()

    app = Application(lambda code: None, 1, False, False)
    app.config_file.global_path = config_file.global_path
    app.config_file.load()

    custom_cwd = Path(tmp_path, 'my-worktree')
    custom_cwd.mkdir()

    try:
        with custom_cwd.as_cwd():
            # Simulate `ddev --here` where repo identity should come from config, not directory name.
            app.set_repo(core=False, extras=False, marketplace=False, agent=False, here=True)
            app.initialize_old_cli()

        assert app['repo'] == repo_name
        assert app['repo_choice'] == repo_name
        assert app['repo_name'] == REPO_CHOICES[repo_name]
        assert app['repos'][repo_name] == str(custom_cwd)
        assert get_root() == str(custom_cwd)
    finally:
        set_root('')


def test_initialize_old_cli_explicit_core_path_unchanged(repository, config_file):
    set_root('')
    app = Application(lambda code: None, 1, False, False)
    app.config_file.global_path = config_file.global_path
    app.config_file.load()

    try:
        # Simulate explicit `ddev --core` selection.
        app.set_repo(core=True, extras=False, marketplace=False, agent=False, here=False)
        app.initialize_old_cli()

        assert app['repo'] == 'core'
        assert app['repo_choice'] == 'core'
        assert app['repo_name'] == 'integrations-core'
        assert app['repos']['core'] == str(repository.path)
        assert get_root() == str(repository.path)
    finally:
        set_root('')


def test_initialize_old_cli_here_populates_repo_choice_when_root_is_preinitialized(
    tmp_path, repository, config_file
):
    set_root(str(repository.path))
    app = Application(lambda code: None, 1, False, False)
    app.config_file.global_path = config_file.global_path
    app.config_file.load()

    custom_cwd = Path(tmp_path, 'my-worktree')
    custom_cwd.mkdir()

    try:
        with custom_cwd.as_cwd():
            app.set_repo(core=False, extras=False, marketplace=False, agent=False, here=True)
            app.initialize_old_cli()

        # initialize_root short-circuits when root is already set, but repo metadata should still exist.
        assert app['repo'] == 'core'
        assert app['repo_choice'] == 'core'
        assert app['repo_name'] == 'integrations-core'
        assert get_root() == str(repository.path)
    finally:
        set_root('')
