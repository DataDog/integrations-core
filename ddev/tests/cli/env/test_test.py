# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from collections.abc import Callable, Generator, Mapping
from typing import Any
from unittest.mock import MagicMock

import pytest
from click.testing import Result
from pytest_mock import MockerFixture, MockType

from ddev.e2e.config import EnvData, EnvDataStorage
from ddev.utils.fs import Path
from tests.helpers.mocks import MockPopen
from tests.helpers.runner import CliRunner

BASE_ENV_CONFIG = {
    'type': 'virtual',
    'dependencies': [],
    'test-env': True,
    'e2e-env': True,
    'benchmark-env': True,
    'latest-env': True,
    'python': '3.12',
    'scripts': {},
    'platforms': [],
    'pre-install-commands': [],
    'post-install-commands': [],
    'skip-install': False,
}


def setup(
    mocker: MockerFixture,
    write_result_file: Callable[[Mapping[str, Any]], None],
    hatch_json_output: Mapping[str, Any] | str | None = None,
):
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': {}, 'config': {}}))

    if hatch_json_output is not None:
        if isinstance(hatch_json_output, str):
            hatch_output = hatch_json_output.encode()
        elif isinstance(hatch_json_output, dict):
            hatch_output = json.dumps(hatch_json_output).encode()
        else:
            pytest.fail('Invalid hatch_json_output type')

        mocker.patch('subprocess.Popen', return_value=MockPopen(returncode=0, stdout=hatch_output))


@pytest.fixture()
def mock_commands(mocker: MockerFixture) -> Generator[tuple[MockType, MockType, MockType]]:
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
    yield start_mock, stop_mock, test_mock


def assert_commands_run(mock_commands: tuple[MockType, MockType, MockType], call_count: int = 1):
    assert mock_commands[0].call_count == call_count
    assert mock_commands[1].call_count == call_count
    assert mock_commands[2].call_count == call_count


@pytest.mark.parametrize(
    'e2e_env, predicate',
    [
        (False, lambda result: "disabled by e2e-env option" in result.output),
        (True, lambda result: "disabled by e2e-env option" not in result.output),
    ],
    ids=['e2e-env-false', 'e2e-env-true'],
)
def test_env_vars_repo(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
    e2e_env: bool,
    predicate: Callable[[Result], bool],
    mock_commands: tuple[MockType, MockType, MockType],
):
    setup(mocker, write_result_file, hatch_json_output={'py3.12': {**BASE_ENV_CONFIG, 'e2e-env': e2e_env}})
    mocker.patch.object(EnvData, 'read_metadata', return_value={})

    result = ddev('env', 'test', 'postgres', 'py3.12')
    assert result.exit_code == 0, result.output
    # Ensure test was not skipped
    assert predicate(result)
    assert_commands_run(mock_commands, 1 if e2e_env else 0)


@pytest.mark.parametrize('environment, command_call_count', [('active', 0), ('all', 2), ('py3.12', 1)])
def test_environment_runs_for_enabled_environments(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
    environment: str,
    mock_commands: tuple[MockType, MockType, MockType],
    command_call_count: int,
):
    setup(
        mocker,
        write_result_file,
        hatch_json_output={
            'py3.12': BASE_ENV_CONFIG,
            'py3.13': {**BASE_ENV_CONFIG, 'e2e-env': False},
            'py3.13-v1': BASE_ENV_CONFIG,
        },
    )
    with mocker.patch.object(EnvData, 'read_metadata', return_value={}):
        result = ddev('env', 'test', 'postgres', environment)
        assert result.exit_code == 0, result.output
        assert_commands_run(mock_commands, command_call_count)


def test_command_errors_out_when_cannot_parse_json_output_from_hatch(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
):
    setup(mocker, write_result_file, hatch_json_output='invalid json')
    result = ddev('env', 'test', 'postgres', 'py3.12')
    assert result.exit_code == 1, result.output


def test_runningin_ci_triggers_all_environments_when_not_supplied(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
    mock_commands: tuple[MockType, MockType, MockType],
):
    setup(mocker, write_result_file, hatch_json_output={'py3.12': BASE_ENV_CONFIG, 'py3.13': BASE_ENV_CONFIG})
    mocker.patch('ddev.utils.ci.running_in_ci', return_value=True)

    with mocker.patch.object(EnvData, 'read_metadata', return_value={}):
        result = ddev('env', 'test', 'postgres')
        assert result.exit_code == 0, result.output
        assert_commands_run(mock_commands, 2)


def test_run_only_active_environments_when_not_running_in_ci_and_active_environments_exist(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
    mock_commands: tuple[MockType, MockType, MockType],
):
    setup(mocker, write_result_file, hatch_json_output={'py3.12': BASE_ENV_CONFIG, 'py3.13': BASE_ENV_CONFIG})
    mocker.patch('ddev.utils.ci.running_in_ci', return_value=False)

    with (
        mocker.patch.object(EnvData, 'read_metadata', return_value={}),
        mocker.patch.object(EnvDataStorage, 'get_environments', return_value=['py3.12']),
    ):
        result = ddev('env', 'test', 'postgres')
        assert result.exit_code == 0, result.output
        assert_commands_run(mock_commands, 1)
