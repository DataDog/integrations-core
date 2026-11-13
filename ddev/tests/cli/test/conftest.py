# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ddev.config.file import ConfigFileWithOverrides
from ddev.repo.core import Repository
from ddev.utils.fs import Path


@pytest.fixture(autouse=True)
def test_repo(temp_dir: Path, config_file: ConfigFileWithOverrides, mocker: MockerFixture) -> Repository:
    for name in ('sample', 'hatch_only'):
        path = temp_dir / name
        path.mkdir()
        (path / 'pyproject.toml').write_text(
            f'[project]\nname = "{name}"\nversion = "1.0"\ndependencies = ["datadog-checks-base>=1.2.3"]\n'
        )
        (path / 'hatch.toml').write_text(
            '''
[env.collectors.datadog-checks]
[envs.default]
python = "3.13"
[[envs.default.matrix]]
version = ["foo", "bar"]
[envs.bench]
[envs.latest]
'''
        )
        if name == 'sample':
            (path / 'tests').mkdir()
    config_file.model.repos['core'] = str(temp_dir)
    config_file.save()
    mocker.patch('ddev.utils.git.GitRepository.worktrees', return_value=[])
    return Repository('core', str(temp_dir))


@pytest.fixture
def commands(mocker: MockerFixture) -> MagicMock:
    return mocker.patch('ddev.utils.platform.Platform.check_command_output', return_value='')
