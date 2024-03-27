# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

import pytest
from datadog_checks.dev.env import serialize_data

from ddev.e2e.config import EnvDataStorage
from ddev.e2e.constants import DEFAULT_DOGSTATSD_PORT, E2EEnvVars, E2EMetadata
from ddev.utils.fs import Path
from ddev.utils.structures import EnvVars


@pytest.fixture(autouse=True)
def free_port(mocker):
    port = 9000
    mocker.patch('ddev.e2e.agent.docker._find_free_port', return_value=port)
    return port


class TestValidations:
    def test_no_result_file(self, ddev, helpers, mocker):
        result_file = Path()

        def _save_result_file(*args, **kwargs):
            nonlocal result_file
            result_file = Path(os.environ[E2EEnvVars.RESULT_FILE])
            return mocker.MagicMock(returncode=0)

        mocker.patch('subprocess.run', side_effect=_save_result_file)

        integration = 'postgres'
        environment = 'py3.12'

        result = ddev('env', 'start', integration, environment)

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            f"""
            ─────────────────────────────── Starting: py3.12 ───────────────────────────────
            No E2E result file found: {result_file}
            """
        )

    def test_already_exists(self, ddev, helpers, data_dir, mocker):
        mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        integration = 'postgres'
        environment = 'py3.12'
        env_data = EnvDataStorage(data_dir).get(integration, environment)
        env_data.write_metadata({})

        result = ddev('env', 'start', integration, environment)

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            f"""
            Environment `{environment}` for integration `{integration}` is already running
            """
        )


def test_stop_on_error(ddev, helpers, data_dir, write_result_file, mocker):
    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start', side_effect=Exception('foo'))
    stop = mocker.patch('ddev.e2e.agent.docker.DockerAgent.stop')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 1, result.output
    assert result.output == helpers.dedent(
        """
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────
        Unable to start the Agent: foo
        ────────────────────────── Stopping: postgres:py3.12 ───────────────────────────
        """
    )

    assert not env_data.exists()

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )
    stop.assert_called_once()


def test_basic(ddev, helpers, data_dir, write_result_file, mocker):
    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )


def test_agent_build_config(ddev, config_file, helpers, data_dir, write_result_file, mocker):
    config_file.model.agent = '7'
    config_file.save()

    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent:7',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )


def test_agent_build_env_var(ddev, config_file, helpers, data_dir, write_result_file, mocker):
    config_file.model.agent = '7'
    config_file.save()

    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    with EnvVars({E2EEnvVars.AGENT_BUILD: 'datadog/agent:6'}):
        result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent:6',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )


def test_agent_build_flag(ddev, config_file, helpers, data_dir, write_result_file, mocker):
    config_file.model.agent = '7'
    config_file.save()

    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    with EnvVars({E2EEnvVars.AGENT_BUILD: 'datadog/agent:6'}):
        result = ddev('env', 'start', integration, environment, '-a', 'datadog/agent:7-rc')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent:7-rc',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )


def test_local_dev(ddev, helpers, local_repo, data_dir, write_result_file, mocker):
    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment, '--dev')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={local_repo / integration: '[deps]'},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )


def test_local_base(ddev, helpers, local_repo, data_dir, write_result_file, mocker):
    metadata = {}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment, '--base')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={
            local_repo / 'datadog_checks_base': '[db,deps,http,json,kube]',
            local_repo / integration: '[deps]',
        },
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com'},
    )


def test_env_vars(ddev, helpers, data_dir, write_result_file, mocker):
    metadata = {'env_vars': {'FOO': 'BAZ', 'BAZ': 'BAR'}}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment, '-e', 'FOO=BAR')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com', 'FOO': 'BAR', 'BAZ': 'BAR'},
    )


def test_env_vars_override_config(ddev, helpers, data_dir, write_result_file, mocker):
    metadata = {'env_vars': {'FOO': 'BAZ', 'BAZ': 'BAR'}}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev(
        'env',
        'start',
        integration,
        environment,
        '-e',
        'FOO=BAR',
        '-e',
        'DD_API_KEY=key',
        '-e',
        'DD_SITE=site',
        '-e',
        'DD_DD_URL=url',
        '-e',
        'DD_LOGS_CONFIG_DD_URL=log_config_url',
    )

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={
            'DD_DD_URL': 'url',
            'DD_SITE': 'site',
            'FOO': 'BAR',
            'BAZ': 'BAR',
            'DD_LOGS_CONFIG_DD_URL': 'log_config_url',
            'DD_API_KEY': 'key',
        },
    )


def test_logs_detection(ddev, helpers, data_dir, write_result_file, mocker):
    metadata = {E2EMetadata.ENV_VARS: {f'{E2EEnvVars.LOGS_DIR_PREFIX}1': 'path'}}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={'DD_DD_URL': 'https://app.datadoghq.com', 'DD_SITE': 'datadoghq.com', 'DD_LOGS_ENABLED': 'true'},
    )


def test_dogstatsd(ddev, helpers, data_dir, write_result_file, mocker):
    metadata = {'dogstatsd': 'true'}
    config = {}
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}
    assert env_data.read_metadata() == metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={
            'DD_DD_URL': 'https://app.datadoghq.com',
            'DD_SITE': 'datadoghq.com',
            'DD_DOGSTATSD_PORT': str(DEFAULT_DOGSTATSD_PORT),
            'DD_DOGSTATSD_NON_LOCAL_TRAFFIC': 'true',
            'DD_DOGSTATSD_METRICS_STATS_ENABLE': 'true',
        },
    )


def test_mount_log(ddev, helpers, data_dir, write_result_file, mocker):
    config = {}
    metadata = {
        'e2e_env_vars': {
            'DDEV_E2E_ENV_docker_volumes': serialize_data(
                [
                    "/tmp/123456/apache_dd_log_1.log:/var/log/apache/dd_log_1",
                    "/tmp/123456/apache_dd_log_2.log:/var/log/apache/dd_log_2",
                ]
            )
        }
    }
    mocker.patch('subprocess.run', side_effect=write_result_file({'metadata': metadata, 'config': config}))
    start = mocker.patch('ddev.e2e.agent.docker.DockerAgent.start')

    integration = 'postgres'
    environment = 'py3.12'
    env_data = EnvDataStorage(data_dir).get(integration, environment)

    result = ddev('env', 'start', integration, environment)

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        ─────────────────────────────── Starting: py3.12 ───────────────────────────────

        Stop environment -> ddev env stop {integration} {environment}
        Execute tests -> ddev env test {integration} {environment}
        Check status -> ddev env agent {integration} {environment} status
        Trigger run -> ddev env agent {integration} {environment} check
        Reload config -> ddev env reload {integration} {environment}
        Manage config -> ddev env config
        Config file -> {env_data.config_file}
        """
    )

    assert env_data.read_config() == {'instances': [config]}

    expected_metadata = copy.deepcopy(metadata)
    expected_metadata['docker_volumes'] = [
        '/tmp/123456/apache_dd_log_1.log:/var/log/apache/dd_log_1',
        '/tmp/123456/apache_dd_log_2.log:/var/log/apache/dd_log_2',
    ]
    assert env_data.read_metadata() == expected_metadata

    start.assert_called_once_with(
        agent_build='datadog/agent-dev:master',
        local_packages={},
        env_vars={
            'DD_DD_URL': 'https://app.datadoghq.com',
            'DD_SITE': 'datadoghq.com',
        },
    )
