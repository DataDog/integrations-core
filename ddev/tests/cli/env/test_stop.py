# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ddev.e2e.config import EnvDataStorage


def test_nonexistent(ddev, helpers, mocker):
    mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))
    stop = mocker.patch('ddev.e2e.agent.docker.DockerAgent.stop')

    integration = 'postgres'
    environment = 'py3.12'

    result = ddev('env', 'stop', integration, environment)

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        f"""
        Environment `{environment}` for integration `{integration}` is not running
        """
    )

    stop.assert_not_called()


def test_basic(ddev, helpers, data_dir, mocker):
    mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))
    stop = mocker.patch('ddev.e2e.agent.docker.DockerAgent.stop')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)
    env_data.write_metadata({})

    result = ddev('env', 'stop', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        ────────────────────────── Stopping: postgres:py3.12 ───────────────────────────
        """
    )

    assert not env_data.exists()

    stop.assert_called_once()


def test_stop_all(ddev, helpers, data_dir, mocker):
    mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))
    stop = mocker.patch('ddev.e2e.agent.docker.DockerAgent.stop')

    running_env = [('postgres', 'py3.12'), ('sqlserver', 'py3.8'), ('cockroachdb', 'py3.7')]

    for intg, env in running_env:
        env_data = EnvDataStorage(data_dir).get(intg, env)
        env_data.write_metadata({})

    result = ddev('env', 'stop', 'all', 'all')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        ───────────────────────── Stopping: cockroachdb:py3.7 ──────────────────────────
        ────────────────────────── Stopping: postgres:py3.12 ───────────────────────────
        ────────────────────────── Stopping: sqlserver:py3.8 ───────────────────────────
        """
    )

    for intg, env in running_env:
        env_data = EnvDataStorage(data_dir).get(intg, env)
        assert not env_data.exists()

    assert stop.call_count == 3
