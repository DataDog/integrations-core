# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from unittest.mock import MagicMock

import pytest
from click.testing import Result
from pytest_mock import MockerFixture, MockType

from ddev.config.constants import ConfigEnvVars
from ddev.e2e.constants import E2EEnvVars
from ddev.utils.fs import Path
from ddev.utils.structures import EnvVars


@pytest.fixture(autouse=True)
def data_dir(temp_dir):
    d = temp_dir / 'data'
    d.mkdir()
    with EnvVars({ConfigEnvVars.DATA: str(d)}):
        yield d


@pytest.fixture
def write_result_file(mocker):
    def _write_result_file(result):
        written = False

        def _write(*args, **kwargs):
            nonlocal written
            if not written:
                Path(os.environ[E2EEnvVars.RESULT_FILE]).write_text(json.dumps(result))
                written = True

            return mocker.MagicMock(returncode=0)

        return _write

    return _write_result_file


@pytest.fixture(autouse=True)
def mock_repo_worktrees(mocker):
    from ddev.utils.git import GitRepository

    # Patch 'worktrees' on the Repository class
    # For all instances, it will now return an empty list, bypassing the git call.
    mocker.patch.object(GitRepository, "worktrees", return_value=[])


@pytest.fixture
def mock_commands(mocker: MockerFixture) -> tuple[MockType, MockType, MockType]:
    start_mock = mocker.patch(
        'ddev.cli.env.start.start',
        return_value=Result(
            return_value=0,
            runner=MagicMock(),
            stdout_bytes=b'',
            stderr_bytes=b'',
            exit_code=0,
            exception=None,
        ),
    )
    stop_mock = mocker.patch(
        'ddev.cli.env.stop.stop',
        return_value=Result(
            return_value=0,
            runner=MagicMock(),
            stdout_bytes=b'',
            stderr_bytes=b'',
            exit_code=0,
            exception=None,
        ),
    )
    test_mock = mocker.patch(
        'ddev.cli.test.test',
        return_value=Result(
            return_value=0,
            runner=MagicMock(),
            stdout_bytes=b'',
            stderr_bytes=b'',
            exit_code=0,
            exception=None,
        ),
    )
    return start_mock, stop_mock, test_mock
