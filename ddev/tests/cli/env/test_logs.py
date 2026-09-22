# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.e2e.config import EnvDataStorage


def test_nonexistent(ddev, helpers, mocker):
    show_logs = mocker.patch('ddev.e2e.agent.docker.DockerAgent.show_logs')

    integration = 'postgres'
    environment = 'py3.13'

    result = ddev('env', 'logs', integration, environment)

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        f"""
        Environment `{environment}` for integration `{integration}` is not running
        """
    )
    show_logs.assert_not_called()


def test_basic(ddev, data_dir, mocker):
    show_logs = mocker.patch('ddev.e2e.agent.docker.DockerAgent.show_logs')

    integration = 'postgres'
    environment = 'py3.13'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'logs', integration, environment)

    assert result.exit_code == 0, result.output
    assert not result.output
    show_logs.assert_called_once_with()


def test_log_failure_is_propagated(ddev, data_dir, mocker):
    show_logs = mocker.patch(
        'ddev.e2e.agent.docker.DockerAgent.show_logs', side_effect=RuntimeError('Agent logs are unavailable')
    )

    integration = 'postgres'
    environment = 'py3.13'
    EnvDataStorage(data_dir).get(integration, environment).write_metadata({})

    result = ddev('env', 'logs', integration, environment)

    assert result.exit_code == 1
    assert 'Agent logs are unavailable' in result.output
    show_logs.assert_called_once_with()
