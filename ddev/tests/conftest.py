# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from typing import Generator

import pytest

from ddev.config.constants import ConfigEnvVars
from ddev.config.file import ConfigFile
from ddev.utils.ci import running_in_ci
from ddev.utils.fs import Path, temp_directory
from ddev.utils.platform import Platform

PLATFORM = Platform()


@pytest.fixture(scope='session')
def local_repo() -> Path:
    return Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def config_file(tmp_path) -> ConfigFile:
    path = Path(tmp_path, 'config.toml')
    os.environ[ConfigEnvVars.CONFIG] = str(path)
    config = ConfigFile(path)
    config.restore()
    return config


@pytest.fixture(scope='session', autouse=True)
def isolation() -> Generator[Path, None, None]:
    with temp_directory() as d:
        with d.as_cwd():
            yield d


@pytest.fixture(scope='session')
def local_clone(isolation, local_repo) -> Generator[Path, None, None]:
    cloned_repo = isolation / local_repo.name

    PLATFORM.check_command_output(['git', 'clone', '--local', '--shared', str(local_repo), str(cloned_repo)])

    yield cloned_repo


@pytest.fixture
def repository(local_clone, config_file) -> Generator[Path, None, None]:
    config_file.model.repos['core'] = str(local_clone)
    config_file.save()

    with local_clone.as_cwd():
        try:
            yield local_clone
        finally:
            PLATFORM.check_command_output(['git', 'reset', '--hard'])


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
