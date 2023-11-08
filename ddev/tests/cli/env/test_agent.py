# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
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

    invoke.assert_called_once_with(['status'])


def test_trigger_run(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, 'check', integration, '-l', 'debug')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['check', integration, '-l', 'debug'])


def test_trigger_run_inject_integration(ddev, data_dir, mocker):
    invoke = mocker.patch('ddev.e2e.agent.docker.DockerAgent.invoke')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'agent', integration, environment, 'check', '-l', 'debug')

    assert result.exit_code == 0, result.output
    assert not result.output

    invoke.assert_called_once_with(['check', integration, '-l', 'debug'])
