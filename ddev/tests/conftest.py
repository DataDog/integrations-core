# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import random
from contextlib import ExitStack
from typing import Generator

import pytest
import vcr
from datadog_checks.dev.tooling.utils import set_root

from ddev.cli.application import Application
from ddev.cli.terminal import Terminal
from ddev.config.constants import AppEnvVars, ConfigEnvVars
from ddev.config.file import DDEV_TOML, ConfigFileWithOverrides
from ddev.e2e.constants import E2EEnvVars
from ddev.repo.core import Repository
from ddev.utils.ci import running_in_ci
from ddev.utils.fs import Path, temp_directory
from ddev.utils.github import GitHubManager
from ddev.utils.platform import Platform

from .helpers import APPLICATION, LOCAL_REPO_BRANCH, PLATFORM
from .helpers.git import ClonedRepo
from .helpers.runner import CliRunner

# Rewrite assertions on the assertions helper module
pytest.register_assert_rewrite('tests.helpers.assertions')


@pytest.fixture(scope='session')
def ddev():
    from ddev import cli

    return CliRunner(cli.ddev)


@pytest.fixture(scope='session')
def platform() -> Platform:
    return PLATFORM


@pytest.fixture(scope='session')
def app() -> Application:
    return APPLICATION


@pytest.fixture(scope='session')
def docker_path(platform):
    return platform.format_for_subprocess(['docker'], shell=False)[0]


@pytest.fixture(scope='session')
def terminal() -> Terminal:
    return Terminal(verbosity=0, enable_color=False, interactive=False)


@pytest.fixture(scope='session')
def local_repo() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope='session')
def valid_integrations(local_repo) -> list[str]:
    repo = Repository(local_repo.name, str(local_repo))
    return [path.name for path in repo.integrations.iter_all(['all'])]


@pytest.fixture
def github_manager(local_repo, config_file, terminal) -> GitHubManager:
    return GitHubManager(
        Repository(local_repo.name, str(local_repo)),
        user=config_file.model.github.user,
        token=config_file.model.github.token,
        status=terminal.status,
    )


@pytest.fixture
def valid_integration(valid_integrations) -> str:
    return random.choice(valid_integrations)


@pytest.fixture(autouse=True)
def config_file(tmp_path, monkeypatch, local_repo, mocker) -> ConfigFileWithOverrides:
    for env_var in (
        'FORCE_COLOR',
        'DD_ENV',
        'DD_SERVICE',
        'DD_SITE',
        'DD_LOGS_CONFIG_LOGS_DD_URL',
        'DD_DD_URL',
        'DD_API_KEY',
        'DD_APP_KEY',
        'DDEV_REPO',
        'DDEV_TEST_ENABLE_TRACING',
        'PYTHON_FILTER',
        E2EEnvVars.AGENT_BUILD,
        E2EEnvVars.AGENT_BUILD_PY2,
        'HATCH_VERBOSE',
        'HATCH_QUIET',
    ):
        monkeypatch.delenv(env_var, raising=False)

    path = Path(tmp_path, 'config.toml')
    monkeypatch.setenv(ConfigEnvVars.CONFIG, str(path))

    config = ConfigFileWithOverrides(path)
    config.reset()

    # Provide a real default for times when tests have no need to modify the repo
    config.global_model.repos['core'] = str(local_repo)
    config.save()

    return config


@pytest.fixture
def overrides_config(temp_dir) -> Generator[Path]:
    """Creates a temporary overrides config file in the temp current directory."""
    with temp_dir.as_cwd():
        ddev_toml = temp_dir / DDEV_TOML
        ddev_toml.touch()
        yield ddev_toml


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    path = Path(tmp_path, 'temp')
    path.mkdir()
    return path


@pytest.fixture(scope='session', autouse=True)
def isolation() -> Generator[Path, None, None]:
    with temp_directory() as d:
        data_dir = d / 'data'
        data_dir.mkdir()

        default_env_vars = {
            'DDEV_SELF_TESTING': 'true',
            ConfigEnvVars.DATA: str(data_dir),
            AppEnvVars.NO_COLOR: '1',
            'COLUMNS': '80',
            'LINES': '24',
        }
        with d.as_cwd(default_env_vars):
            yield d


@pytest.fixture(scope='session')
def local_clone(isolation, local_repo) -> Generator[ClonedRepo, None, None]:
    cloned_repo_path = isolation / local_repo.name

    # Debug: Write environment and git info to a file for artifact upload
    import os
    import subprocess

    # Write to multiple locations to ensure we capture the debug info
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    debug_file = Path(workspace) / 'local_clone_debug.txt'
    # Also try writing to the repo root (3 levels up from conftest.py)
    repo_root_debug = Path(__file__).resolve().parent.parent.parent.parent / 'local_clone_debug.txt'
    debug_lines = []
    debug_lines.append('=== DEBUG local_clone fixture ===')
    debug_lines.append(f'PYTHONPATH: {os.environ.get("PYTHONPATH", "not set")}')
    debug_lines.append(f'DD_TRACE_SUBPROCESS_ENABLED: {os.environ.get("DD_TRACE_SUBPROCESS_ENABLED", "not set")}')
    debug_lines.append(f'DDEV_TRACE_ENABLED: {os.environ.get("DDEV_TRACE_ENABLED", "not set")}')
    debug_lines.append(f'DD_CIVISIBILITY_ITR_ENABLED: {os.environ.get("DD_CIVISIBILITY_ITR_ENABLED", "not set")}')
    debug_lines.append(f'local_repo: {local_repo}')
    debug_lines.append(f'cloned_repo_path: {cloned_repo_path}')

    # Check if subprocess module is patched
    debug_lines.append(f'subprocess.Popen: {subprocess.Popen}')
    debug_lines.append(f'subprocess module file: {subprocess.__file__}')

    # Check for any git lock files
    git_dir = local_repo / '.git'
    if git_dir.exists():
        lock_files = list(git_dir.glob('*.lock')) + list(git_dir.glob('**/*.lock'))
        debug_lines.append(f'Git lock files found: {lock_files}')

    # Check if repo is shallow (use subprocess directly to avoid exit on failure)
    with local_repo.as_cwd():
        try:
            result = subprocess.run(['git', 'rev-parse', '--is-shallow-repository'], capture_output=True, text=True)
            is_shallow = result.stdout.strip() if result.returncode == 0 else f'error: {result.stderr}'
            debug_lines.append(f'Is shallow repository: {is_shallow}')

            # Check for partial clone / promisor remote (this config may not exist)
            result = subprocess.run(['git', 'config', '--get', 'remote.origin.promisor'], capture_output=True, text=True)
            promisor = result.stdout.strip() if result.returncode == 0 else 'not configured'
            debug_lines.append(f'Promisor remote configured: {promisor}')

            # Also check for partial clone filter
            result = subprocess.run(['git', 'config', '--get', 'remote.origin.partialclonefilter'], capture_output=True, text=True)
            partial_filter = result.stdout.strip() if result.returncode == 0 else 'not configured'
            debug_lines.append(f'Partial clone filter: {partial_filter}')
        except Exception as e:
            debug_lines.append(f'Error checking git config: {e}')

    # Get the current origin remote url
    with local_repo.as_cwd():
        origin_url = PLATFORM.check_command_output(['git', 'remote', 'get-url', 'origin']).strip()
        debug_lines.append(f'origin_url: {origin_url}')

    debug_lines.append(f'Running: git clone --local --shared --no-tags {local_repo} {cloned_repo_path}')

    # Write debug info to file (try multiple locations)
    for path in [debug_file, repo_root_debug]:
        try:
            path.write_text('\n'.join(debug_lines))
            debug_lines.append(f'Debug file written to: {path}')
        except Exception as e:
            debug_lines.append(f'Failed to write debug file to {path}: {e}')

    # Also print to stdout (will show if test fails)
    print('\n'.join(debug_lines))

    PLATFORM.check_command_output(
        ['git', 'clone', '--local', '--shared', '--no-tags', str(local_repo), str(cloned_repo_path)]
    )
    with cloned_repo_path.as_cwd():
        PLATFORM.check_command_output(['git', 'config', 'user.name', 'Foo Bar'])
        PLATFORM.check_command_output(['git', 'config', 'user.email', 'foo@bar.baz'])
        PLATFORM.check_command_output(['git', 'config', 'commit.gpgsign', 'false'])
        PLATFORM.check_command_output(['git', 'config', 'tag.gpgsign', 'false'])

        # Set url to point to the origin of the local source and not to the local repo
        PLATFORM.check_command_output(['git', 'remote', 'set-url', 'origin', origin_url])
        # Now fetch latest updates
        PLATFORM.check_command_output(['git', 'fetch', 'origin'])

        # Add a worktree within the repo and one outside of it that should be ignored by ddev
        # It is not a fast operation so lets do it once per session
        PLATFORM.check_command_output(['git', 'worktree', 'add', 'wt', 'HEAD'])
        PLATFORM.check_command_output(['git', 'worktree', 'add', '../wt2', 'HEAD'])

    cloned_repo = ClonedRepo(cloned_repo_path, 'origin/master', LOCAL_REPO_BRANCH)
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
def repository_as_cwd(repository: ClonedRepo) -> Generator[ClonedRepo, None, None]:
    with repository.path.as_cwd():
        yield repository


@pytest.fixture(scope='session')
def default_hostname():
    import socket

    return socket.gethostname().lower()


@pytest.fixture
def network_replay(local_repo):
    """
    To use, run once without record_mode='none' as an argument and then add it in for subsequent runs.
    """
    stack = ExitStack()

    def add_cassette(relative_path, *args, **kwargs):
        # https://vcrpy.readthedocs.io/en/latest/advanced.html#filter-sensitive-data-from-the-request
        for option, known_values in (
            ('filter_headers', ['authorization', 'dd-api-key', 'dd-application-key']),
            ('filter_query_parameters', ['api_key', 'app_key', 'application_key']),
            ('filter_post_data_parameters', ['api_key', 'app_key']),
        ):
            defined_values = list(kwargs.setdefault(option, []))
            defined_values.extend(known_values)
            kwargs[option] = defined_values

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
            pytest.skip('Only running in CI')

        if marker.name == 'requires_windows' and not PLATFORM.windows:
            pytest.skip('Only running on Windows')

        if marker.name == 'requires_macos' and not PLATFORM.macos:
            pytest.skip('Only running on macOS')

        if marker.name == 'requires_linux' and not PLATFORM.linux:
            pytest.skip('Only running on Linux')

        if marker.name == 'requires_unix' and PLATFORM.windows:
            pytest.skip('Only running on a Linux-based platform')


def pytest_configure(config):
    config.addinivalue_line('markers', 'requires_windows: Tests intended for Windows operating systems')
    config.addinivalue_line('markers', 'requires_macos: Tests intended for macOS operating systems')
    config.addinivalue_line('markers', 'requires_linux: Tests intended for Linux operating systems')
    config.addinivalue_line('markers', 'requires_unix: Tests intended for Linux-based operating systems')
    config.addinivalue_line('markers', 'requires_ci: Tests intended to only run in CI')
