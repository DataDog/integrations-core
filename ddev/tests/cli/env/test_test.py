# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import shlex
from collections.abc import Callable, Mapping
from typing import Any

import pytest
from click.exceptions import Exit
from click.testing import Result
from pytest_mock import MockerFixture, MockType

from ddev.e2e.config import EnvData, EnvDataStorage
from ddev.utils.fs import Path
from tests.helpers.environments import make_catalog
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
    hatch_json_output: dict[str, dict[str, Any]] | None = None,
):
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': {}, 'config': {}}))

    if hatch_json_output is not None:
        mocker.patch('ddev.testing.selection.load_environment_catalog', return_value=make_catalog(hatch_json_output))


def assert_commands_run(mock_commands: tuple[MockType, MockType, MockType], call_count: int = 1):
    assert mock_commands[0].call_count == call_count
    assert mock_commands[1].call_count == call_count
    assert mock_commands[2].call_count == call_count


@pytest.mark.parametrize(
    'e2e_env, predicate',
    [
        (False, lambda result: "Excluded postgres:py3.12 by e2e-env option." in result.output),
        (True, lambda result: "Excluded postgres:py3.12" not in result.output),
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

    result = ddev('env', 'test', 'postgres', '--envs', 'py3.12')
    assert result.exit_code == 0, result.output
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
        result = ddev('env', 'test', 'postgres', '--envs', environment)
        assert result.exit_code == 0, result.output
        assert_commands_run(mock_commands, command_call_count)


@pytest.mark.parametrize(
    'ignore_teardown_errors, cleanup_error, test_exit_code, expected_exit_code',
    [
        (False, Exit(1), None, 1),
        (True, Exit(1), None, 0),
        (True, Exit(1), 2, 2),
        (True, RuntimeError('cleanup failed'), None, 0),
    ],
)
def test_automatic_cleanup_failure(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
    mock_commands: tuple[MockType, MockType, MockType],
    ignore_teardown_errors: bool,
    cleanup_error: Exception,
    test_exit_code: int | None,
    expected_exit_code: int,
):
    setup(mocker, write_result_file, hatch_json_output={'py3.12': BASE_ENV_CONFIG})
    mocker.patch.object(EnvData, 'read_metadata', return_value={})
    mock_commands[1].side_effect = cleanup_error
    if test_exit_code is not None:
        mock_commands[2].side_effect = SystemExit(test_exit_code)

    args = ('--ignore-teardown-errors',) if ignore_teardown_errors else ()
    result = ddev('env', 'test', *args, 'postgres', '--envs', 'py3.12')

    assert result.exit_code == expected_exit_code, result.output
    if ignore_teardown_errors:
        assert f'Automatic teardown failed for `postgres:py3.12` ({cleanup_error!r})' in result.output
        assert 'The next environment may fail' not in result.output
    assert_commands_run(mock_commands)


@pytest.mark.parametrize('first_test_fails', [False, True])
def test_automatic_cleanup_failure_in_multi_environment_run(
    ddev: CliRunner,
    data_dir: Path,
    write_result_file: Callable[[Mapping[str, Any]], None],
    mocker: MockerFixture,
    mock_commands: tuple[MockType, MockType, MockType],
    first_test_fails: bool,
):
    setup(mocker, write_result_file, hatch_json_output={'py3.12': BASE_ENV_CONFIG, 'py3.13': BASE_ENV_CONFIG})
    mocker.patch.object(EnvData, 'read_metadata', return_value={})
    mock_commands[1].side_effect = [Exit(1), None]
    mock_commands[2].side_effect = [SystemExit(2)] if first_test_fails else [None, SystemExit(2)]

    result = ddev('env', 'test', '--ignore-teardown-errors', 'postgres', '--envs', 'all')

    assert result.exit_code == 2, result.output
    assert 'Automatic teardown failed for `postgres:py3.12` (Exit(1)).' in result.output
    next_environment_warning = 'The next environment may fail to start if cleanup was incomplete.'
    if first_test_fails:
        assert next_environment_warning not in result.output
    else:
        assert next_environment_warning in result.output
    assert_commands_run(mock_commands, 1 if first_test_fails else 2)


@pytest.mark.parametrize(
    'args, message',
    [
        (('py3.12',), '--pytest-args'),
        (('--', '-m', 'not flaky'), '--pytest-args'),
        (('--envs', 'typo'), 'Unknown environments: typo'),
        (('--envs', 'py3.12,typo'), 'Unknown environments: typo'),
        (('--envs', 'all,py3.12'), 'alone'),
        (('--envs', 'active,py3.12'), 'alone'),
        (('--pytest-args', '-m'), 'requires a marker expression'),
        (('--pytest-args', '-m "unit'), 'No closing quotation'),
    ],
)
def test_invalid_requests_do_not_change_lifecycle(
    ddev: CliRunner,
    mocker: MockerFixture,
    mock_commands: tuple[MockType, MockType, MockType],
    args: tuple[str, ...],
    message: str,
):
    mocker.patch(
        'ddev.testing.selection.load_environment_catalog', return_value=make_catalog({'py3.12': BASE_ENV_CONFIG})
    )
    result = ddev('env', 'test', 'postgres', '--recreate', *args)
    assert result.exit_code == 2, result.output
    assert message in result.output
    assert_commands_run(mock_commands, 0)


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


@pytest.mark.parametrize('active, recreate', [(False, False), (True, False), (True, True)])
def test_reuse_and_recreation_preserve_lifecycle(
    ddev: CliRunner,
    mocker: MockerFixture,
    mock_commands: tuple[MockType, MockType, MockType],
    active: bool,
    recreate: bool,
):
    mocker.patch('ddev.testing.selection.load_environment_catalog', return_value=make_catalog({'selected': {}}))
    mocker.patch.object(EnvData, 'read_metadata', return_value={})
    mocker.patch.object(EnvDataStorage, 'get_environments', return_value=['selected'] if active else [])
    args = ('--recreate',) if recreate else ()
    result = ddev('env', 'test', 'postgres', '--envs', 'selected', *args)
    assert result.exit_code == 0, result.output
    assert mock_commands[0].call_args.kwargs['ignore_state'] == (active and not recreate)
    assert mock_commands[1].call_args.kwargs['ignore_state'] == active
    assert mock_commands[1].call_count == (2 if active and recreate else 1)
    assert mock_commands[2].call_args.kwargs['recreate'] == recreate


def test_multiple_selection_forwards_pytest_once(ddev: CliRunner, mocker: MockerFixture):
    from ddev.e2e.constants import E2EMetadata

    mocker.patch('ddev.cli.env.start.start')
    mocker.patch('ddev.cli.env.stop.stop')
    mocker.patch(
        'ddev.testing.selection.load_environment_catalog',
        return_value=make_catalog({'first': {}, 'second': {}}, {'default': ['first', 'second']}),
    )
    mocker.patch.object(EnvData, 'read_metadata', return_value={E2EMetadata.ENV_VARS: {'DDEV_E2E_TEST_VAR': 'value'}})
    mocker.patch.dict(os.environ, {'DDEV_TEST_ENABLE_TRACING': '1'})
    observed: list[tuple[list[str], str | None, str | None]] = []

    def record(command: list[str], **kwargs: Any) -> str:
        observed.append((command, os.environ.get('DDEV_E2E_TEST_VAR'), os.environ.get('DDEV_REPO')))
        return ''

    run = mocker.patch('ddev.utils.platform.Platform.check_command_output', side_effect=record)
    parse = mocker.spy(shlex, 'split')
    pytest_string = '-m "a or b" --markers "tests/a file.py"'
    result = ddev('env', 'test', 'postgres', '--envs', 'second,default', '--pytest-args', pytest_string)
    assert result.exit_code == 0, result.output
    commands = [call.args[0] for call in run.call_args_list]
    assert [command[command.index('--env') + 1] for command in commands] == ['second', 'first']
    for command, metadata_var, repo in observed:
        assert command[-4:] == ['-m', '(a or b) and e2e', '--markers', 'tests/a file.py']
        assert '--ddtrace' in command
        assert metadata_var == 'value'
        assert repo == 'core'
    assert [call.args[0] for call in parse.call_args_list].count(pytest_string) == 1
