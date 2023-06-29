# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import os
import random
from contextlib import ExitStack
from typing import Generator

import pytest
import vcr
from click.testing import CliRunner as __CliRunner
from datadog_checks.dev.tooling.utils import set_root
from ddev.config.constants import AppEnvVars, ConfigEnvVars
from ddev.config.file import ConfigFile
from ddev.repo.core import Repository
from ddev.utils.ci import running_in_ci
from ddev.utils.fs import Path, temp_directory
from ddev.utils.platform import Platform

PLATFORM = Platform()


class ClonedRepo:
    def __init__(self, path: Path, original_branch: str, testing_branch: str):
        self.path = path
        self.original_branch = original_branch
        self.testing_branch = testing_branch

    def reset_branch(self):
        with self.path.as_cwd():
            # Hard reset
            PLATFORM.check_command_output(['git', 'checkout', '-fB', self.testing_branch, self.original_branch])

            # Remove untracked files
            PLATFORM.check_command_output(['git', 'clean', '-fd'])

            # Remove all tags
            tags_dir = self.path / '.git' / 'refs' / 'tags'
            if tags_dir.is_dir():
                tags_dir.remove()

    @staticmethod
    def new_branch():
        return os.urandom(10).hex()


class CliRunner(__CliRunner):
    def __init__(self, command):
        super().__init__()
        self._command = command

    def __call__(self, *args, **kwargs):
        # Exceptions should always be handled
        kwargs.setdefault('catch_exceptions', False)

        return self.invoke(self._command, args, **kwargs)


@pytest.fixture(scope='session')
def ddev():
    from ddev import cli

    return CliRunner(cli.ddev)


@pytest.fixture(scope='session')
def platform() -> Platform:
    return PLATFORM


@pytest.fixture(scope='session')
def local_repo() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope='session')
def valid_integrations(local_repo) -> list[str]:
    repo = Repository(local_repo.name, str(local_repo))
    return [path.name for path in repo.integrations.iter_all(['all'])]


@pytest.fixture
def valid_integration(valid_integrations) -> str:
    return random.choice(valid_integrations)


@pytest.fixture(autouse=True)
def config_file(tmp_path, monkeypatch) -> ConfigFile:
    for env_var in (
        'DD_SITE',
        'DD_LOGS_CONFIG_DD_URL',
        'DD_DD_URL',
        'DD_API_KEY',
        'DD_APP_KEY',
    ):
        monkeypatch.delenv(env_var, raising=False)

    path = Path(tmp_path, 'config.toml')
    monkeypatch.setenv(ConfigEnvVars.CONFIG, str(path))
    config = ConfigFile(path)
    config.restore()
    return config


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    path = Path(tmp_path, 'temp')
    path.mkdir()
    return path


@pytest.fixture(scope='session', autouse=True)
def isolation() -> Generator[Path, None, None]:
    with temp_directory() as d:
        default_env_vars = {AppEnvVars.NO_COLOR: '1'}
        with d.as_cwd(default_env_vars):
            yield d


@pytest.fixture(scope='session')
def local_clone(isolation, local_repo) -> Generator[ClonedRepo, None, None]:
    cloned_repo_path = isolation / local_repo.name

    PLATFORM.check_command_output(
        ['git', 'clone', '--local', '--shared', '--no-tags', str(local_repo), str(cloned_repo_path)]
    )
    with cloned_repo_path.as_cwd():
        PLATFORM.check_command_output(['git', 'config', 'user.name', 'Foo Bar'])
        PLATFORM.check_command_output(['git', 'config', 'user.email', 'foo@bar.baz'])
        PLATFORM.check_command_output(['git', 'config', 'commit.gpgsign', 'false'])

    cloned_repo = ClonedRepo(cloned_repo_path, 'origin/master', 'ddev-testing')
    cloned_repo.reset_branch()

    yield cloned_repo


@pytest.fixture
def repository(local_clone, config_file) -> Generator[ClonedRepo, None, None]:
    config_file.model.repos['core'] = str(local_clone.path)
    config_file.save()

    try:
        yield local_clone
    finally:
        set_root('')
        local_clone.reset_branch()


@pytest.fixture
def network_replay(local_repo):
    """
    To use, run once without record_mode='none' as an argument and then add it in for subsequent runs.
    """
    stack = ExitStack()

    def add_cassette(relative_path, *args, **kwargs):
        cassette = vcr.use_cassette(
            str(local_repo / "ddev" / "tests" / "fixtures" / "network" / relative_path), *args, **kwargs
        )
        stack.enter_context(cassette)
        return cassette

    with stack:
        yield add_cassette


@pytest.fixture(scope='session')
def helpers():
    # https://docs.pytest.org/en/latest/writing_plugins.html#assertion-rewriting
    pytest.register_assert_rewrite('tests.helpers.api')

    from .helpers import api

    return api


def pytest_runtest_setup(item):
    for marker in item.iter_markers():
        if marker.name == 'requires_ci' and not running_in_ci():  # no cov
            pytest.skip('Not running in CI')

        if marker.name == 'requires_windows' and not PLATFORM.windows:
            pytest.skip('Not running on Windows')

        if marker.name == 'requires_macos' and not PLATFORM.macos:
            pytest.skip('Not running on macOS')

        if marker.name == 'requires_linux' and not PLATFORM.linux:
            pytest.skip('Not running on Linux')

        if marker.name == 'requires_unix' and PLATFORM.windows:
            pytest.skip('Not running on a Linux-based platform')


def pytest_configure(config):
    config.addinivalue_line('markers', 'requires_windows: Tests intended for Windows operating systems')
    config.addinivalue_line('markers', 'requires_macos: Tests intended for macOS operating systems')
    config.addinivalue_line('markers', 'requires_linux: Tests intended for Linux operating systems')
    config.addinivalue_line('markers', 'requires_unix: Tests intended for Linux-based operating systems')
