# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from ddev.e2e.config import EnvDataStorage


def test_nonexistent(ddev, helpers, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'

    result = ddev('env', 'agent', integration, environment, 'status')

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        f"""
        Environment `{environment}` for integration `{integration}` is not running
        """
    )

    invoke.assert_not_called()


def test_not_trigger_run(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, 'status')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['status'], env_vars=None)


def test_env_vars(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, '--env', 'FOO=bar', '--env', 'BAZ=qux', 'status')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['status'], env_vars={'FOO': 'bar', 'BAZ': 'qux'})


def test_env_vars_trigger_run(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, '--env', 'FOO=bar', 'check', integration, '-l', 'debug')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['check', integration, '-l', 'debug'], env_vars={'FOO': 'bar'})


@pytest.mark.parametrize('env_value', ['FOO', '=FOO'])
def test_env_vars_malformed(ddev, helpers, data_dir, mocker, env_value):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, '--env', env_value, 'status')

    assert result.exit_code == 2, result.output
    assert result.output == helpers.dedent(
        f"""
        Usage: ddev env agent [OPTIONS] INTEGRATION ENVIRONMENT ARGS...

        Error: Invalid value for '--env': `{env_value}` is not in KEY=VALUE format
        """
    )

    invoke.assert_not_called()


def test_env_vars_not_supported(ddev, helpers, data_dir, mocker):
    invoke = mocker.patch(
        'ddev.e2e.agent.docker.DockerAgent.invoke',
        side_effect=NotImplementedError('Per-invocation env_vars are not supported for the Vagrant agent'),
    )

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, '--env', 'FOO=bar', 'status')

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        """
        Per-invocation env_vars are not supported for the Vagrant agent
        """
    )

    invoke.assert_called_once_with(['status'], env_vars={'FOO': 'bar'})


def test_env_vars_not_supported_trigger_run(ddev, helpers, data_dir, mocker):
    invoke = mocker.patch(
        'ddev.e2e.agent.docker.DockerAgent.invoke',
        side_effect=NotImplementedError('Per-invocation env_vars are not supported for the Vagrant agent'),
    )

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, '--env', 'FOO=bar', 'check', integration, '-l', 'debug')

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        """
        Per-invocation env_vars are not supported for the Vagrant agent
        """
    )

    invoke.assert_called_once_with(['check', integration, '-l', 'debug'], env_vars={'FOO': 'bar'})


def test_trigger_run(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, 'check', integration, '-l', 'debug')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['check', integration, '-l', 'debug'], env_vars=None)


def test_trigger_run_inject_integration(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, 'check', '-l', 'debug')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['check', integration, '-l', 'debug'], env_vars=None)


def test_temporary_config_is_restored_and_synchronized(ddev, data_dir, temp_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')
    sync_config = mocker.patch('ddev.e2e.agent.docker.DockerAgent.sync_config')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})
    original_config = {'instances': [{'host': 'original'}]}
    env_data.write_config(original_config)
    temporary_config = temp_dir / 'temporary.json'
    temporary_config.write_text('{"instances": []}')

    result = ddev(
        'env',
        'agent',
        integration,
        environment,
        '--config-file',
        str(temporary_config),
        'check',
    )

    assert result.exit_code == 0, result.output
    assert env_data.read_config() == original_config
    invoke.assert_called_once_with(['check', integration], env_vars=None)
    sync_config.assert_called_once_with()


def test_temporary_config_absence_is_restored_and_synchronized(ddev, data_dir, temp_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')
    sync_config = mocker.patch('ddev.e2e.agent.docker.DockerAgent.sync_config')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})
    temporary_config = temp_dir / 'temporary.json'
    temporary_config.write_text('{"instances": []}')

    result = ddev(
        'env',
        'agent',
        integration,
        environment,
        '--config-file',
        str(temporary_config),
        'check',
    )

    assert result.exit_code == 0, result.output
    assert not env_data.config_file.exists()
    invoke.assert_called_once_with(['check', integration], env_vars=None)
    sync_config.assert_called_once_with()
