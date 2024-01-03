# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.e2e.config import EnvDataStorage


def test_nonexistent(ddev, helpers, mocker):
    enter_shell = mocker.patch('ddev.e2e.agent.docker.DockerAgent.enter_shell')

    integration = 'postgres'
    environment = 'py3.12'

    result = ddev('env', 'shell', integration, environment)

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        f"""
        Environment `{environment}` for integration `{integration}` is not running
        """
    )

    enter_shell.assert_not_called()


def test_basic(ddev, data_dir, mocker):
    enter_shell = mocker.patch('ddev.e2e.agent.docker.DockerAgent.enter_shell')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'shell', integration, environment)

    assert result.exit_code == 0, result.output
    assert not result.output

    enter_shell.assert_called_once()
