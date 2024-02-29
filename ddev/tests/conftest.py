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

from ddev.cli.terminal import Terminal
from ddev.config.constants import AppEnvVars, ConfigEnvVars
from ddev.config.file import ConfigFile
from ddev.e2e.constants import E2EEnvVars
from ddev.repo.core import Repository
from ddev.utils.ci import running_in_ci
from ddev.utils.fs import Path, temp_directory
from ddev.utils.github import GitHubManager
from ddev.utils.platform import Platform

PLATFORM = Platform()
OLD_PYTHON_VERSION = "3.11"
NEW_PYTHON_VERSION = "3.12"


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
def config_file(tmp_path, monkeypatch, local_repo) -> ConfigFile:
    for env_var in (
        'FORCE_COLOR',
        'DD_ENV',
        'DD_SERVICE',
        'DD_SITE',
        'DD_LOGS_CONFIG_DD_URL',
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

    config = ConfigFile(path)
    config.reset()

    # Provide a real default for times when tests have no need to modify the repo
    config.model.repos['core'] = str(local_repo)
    config.save()

    return config


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
    '''
    Clone integrations-core git repo.

    This is being deprecated and removed, use empty_git_repo instead!
    '''
    cloned_repo_path = isolation / local_repo.name

    PLATFORM.check_command_output(
        ['git', 'clone', '--local', '--shared', '--no-tags', str(local_repo), str(cloned_repo_path)]
    )
    with cloned_repo_path.as_cwd():
        PLATFORM.check_command_output(['git', 'config', 'user.name', 'Foo Bar'])
        PLATFORM.check_command_output(['git', 'config', 'user.email', 'foo@bar.baz'])
        PLATFORM.check_command_output(['git', 'config', 'commit.gpgsign', 'false'])

    # We pin the clone of the repo used for testing to have reproducible tests.

    cloned_repo = ClonedRepo(cloned_repo_path, 'f7f18ca567bd7712e08692f4e73104706d9942f3', 'ddev-testing')
    cloned_repo.reset_branch()

    yield cloned_repo


@pytest.fixture
def repository(local_clone, config_file) -> Generator[ClonedRepo, None, None]:
    '''
    Fake repository for testing.

    This is being deprecated and removed, use fake_repo instead!
    '''
    config_file.model.repos['core'] = str(local_clone.path)
    config_file.save()

    try:
        yield local_clone
    finally:
        set_root('')
        local_clone.reset_branch()


def write_file(folder, file, content):
    folder.mkdir(exist_ok=True, parents=True)
    file_path = folder / file
    file_path.write_text(content)


@pytest.fixture
def empty_git_repo(tmp_path_factory):
    '''
    Initialize empty git repository to stand in for integrations-core.
    '''
    repo_path = Path(tmp_path_factory.mktemp('integrations-core'))
    with repo_path.as_cwd():
        PLATFORM.check_command_output(['git', 'init', str(repo_path)])
        PLATFORM.check_command_output(['git', 'config', 'user.name', 'Foo Bar'])
        PLATFORM.check_command_output(['git', 'config', 'user.email', 'foo@bar.baz'])
        PLATFORM.check_command_output(['git', 'config', 'commit.gpgsign', 'false'])
        PLATFORM.check_command_output(['touch', '.gitignore'])
        PLATFORM.check_command_output(['git', 'add', '.'])
        PLATFORM.check_command_output(['git', 'commit', '--message', 'let there be light'])

    yield repo_path


@pytest.fixture
def fake_repo(empty_git_repo, config_file):
    '''
    Fake repository for testing.
    '''
    repo_path = empty_git_repo
    repo = Repository('integrations-core', str(repo_path))

    config_file.model.repos['core'] = str(repo.path)
    config_file.save()

    write_file(
        repo_path / 'ddev' / 'src' / 'ddev' / 'repo',
        'constants.py',
        f"""# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CONFIG_DIRECTORY = '.ddev'
NOT_SHIPPABLE = frozenset(['datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'])
FULL_NAMES = {{
    'core': 'integrations-core',
    'extras': 'integrations-extras',
    'marketplace': 'marketplace',
    'agent': 'datadog-agent',
}}

# This is automatically maintained
PYTHON_VERSION = '{OLD_PYTHON_VERSION}'
""",
    )

    write_file(
        repo_path / 'dummy',
        'hatch.toml',
        f"""[env.collectors.datadog-checks]

[[envs.default.matrix]]
python = ["2.7", "{OLD_PYTHON_VERSION}"]

""",
    )

    write_file(
        repo_path / 'dummy',
        'metadata.csv',
        """metric_name,metric_type,interval,unit_name,per_unit_name,description,orientation,integration,short_name,curated_metric
dummy.metric,gauge,,,,description,0,dummy,,""",
    )

    for integration in ('dummy', 'datadog_checks_dependency_provider'):
        write_file(
            repo_path / integration,
            'pyproject.toml',
            f"""[project]
    name = "dummy"
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
    ]
    """,
        )

    write_file(
        repo_path / 'logs_only',
        'pyproject.toml',
        f"""[project]
    name = "dummy"
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: BSD License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
    ]
    """,
    )

    write_file(
        repo_path / '.github' / 'workflows',
        'build-ddev.yml',
        f"""name: build ddev
env:
  APP_NAME: ddev
  PYTHON_VERSION: "{OLD_PYTHON_VERSION}"
  PYOXIDIZER_VERSION: "0.24.0"
""",
    )

    write_file(
        repo_path / 'ddev',
        'pyproject.toml',
        f"""[tool.black]
target-version = ["py{OLD_PYTHON_VERSION.replace('.', '')}"]

[tool.ruff]
target-version = "py{OLD_PYTHON_VERSION.replace('.', '')}"
""",
    )

    write_file(
        repo_path
        / 'datadog_checks_dev'
        / 'datadog_checks'
        / 'dev'
        / 'tooling'
        / 'templates'
        / 'integration'
        / 'check'
        / '{check_name}',
        'pyproject.toml',
        f"""[project]
name = "dummy"
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "License :: OSI Approved :: BSD License",
    "Natural Language :: English",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 2.7",
    "Programming Language :: Python :: {OLD_PYTHON_VERSION}",
]
""",
    )

    yield repo


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
    config.addinivalue_line('markers', 'requires_ci: Tests intended to only run in CI')
