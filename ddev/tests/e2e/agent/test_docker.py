# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess

import pytest

from ddev.e2e.agent.docker import DockerAgent
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig
from ddev.utils.fs import Path


@pytest.fixture(scope='module')
def get_integration(local_repo):
    def _get_integration(name):
        return Integration(local_repo / name, local_repo, RepositoryConfig(local_repo / '.ddev' / 'config.toml'))

    return _get_integration


@pytest.fixture(autouse=True)
def free_port(mocker):
    port = 9000
    mocker.patch('ddev.e2e.agent.docker._find_free_port', return_value=port)
    return port


class TestStart:
    @pytest.mark.parametrize(
        'agent_build, agent_image, use_jmx',
        [
            pytest.param('', 'datadog/agent-dev:master-py3', False, id='default'),
            pytest.param('datadog/agent:7', 'datadog/agent:7', False, id='release'),
            pytest.param('datadog/agent-dev:master-py3', 'datadog/agent-dev:master-py3', False, id='exact'),
            pytest.param('datadog/agent-dev:master', 'datadog/agent-dev:master-py3-jmx', True, id='jmx'),
            pytest.param('datadog/agent-dev:master-py3-jmx', 'datadog/agent-dev:master-py3-jmx', True, id='jmx exact'),
            pytest.param(
                'my-custom-build-that-I-have-locally', 'my-custom-build-that-I-have-locally', False, id='custom build'
            ),
            pytest.param(
                'my-custom-build-that-I-have-locally',
                'my-custom-build-that-I-have-locally',
                True,
                id='custom build with jmx',
            ),
            pytest.param(
                'datadog/agent:7.46.0',
                'datadog/agent:7.46.0',
                False,
                id='Specific stable release',
            ),
            pytest.param(
                'datadog/agent:7.45.0',
                'datadog/agent:7.45.0-jmx',
                True,
                id='Specific stable release with jmx',
            ),
            pytest.param(
                'datadog/agent:6.44.0-jmx',
                'datadog/agent:6.44.0-jmx',
                True,
                id='Specific stable release with jmx exact',
            ),
        ],
    )
    def test_agent_build(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
        agent_build,
        agent_image,
        use_jmx,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'use_jmx': use_jmx}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build=agent_build, local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', agent_image], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    agent_image,
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_env_vars(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(
            agent_build='',
            local_packages={},
            env_vars={'DD_API_KEY': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb', 'DD_LOGS_ENABLED': 'true'},
        )

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_LOGS_ENABLED=true',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_no_config_file(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, temp_dir / 'config.yaml')
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_windows_container(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'docker_platform': 'windows'}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '-v',
                    f'{config_file.parent}:C:\\ProgramData\\Datadog\\conf.d\\{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    @pytest.mark.requires_linux
    def test_docker_volumes_linux(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'docker_volumes': ['/a/b/c:/d/e/f']}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-v',
                    '/a/b/c:/d/e/f',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    @pytest.mark.requires_windows
    def test_docker_volumes_windows_running_linux(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'docker_volumes': ['/a/b/c:/d/e/f', f'{config_file}:/mnt/{config_file.name}']}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-v',
                    '/a/b/c:/d/e/f',
                    '-v',
                    f'/{str(config_file).replace(":", "", 1).replace(os.sep, "/")}:/mnt/{config_file.name}',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    @pytest.mark.requires_windows
    def test_docker_volumes_windows_running_windows(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'docker_volumes': [f'{config_file.parent.parent}:C:\\mnt'], 'docker_platform': 'windows'}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '-v',
                    f'{config_file.parent}:C:\\ProgramData\\Datadog\\conf.d\\{integration}.d',
                    '-v',
                    f'{config_file.parent.parent}:C:\\mnt',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_retry_pull_image(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch(
            'subprocess.run',
            side_effect=[
                mocker.MagicMock(returncode=1),
                mocker.MagicMock(returncode=1),
                mocker.MagicMock(returncode=0),
                mocker.MagicMock(returncode=0),
            ],
        )

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, temp_dir / 'config.yaml')
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_custom_hosts(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'custom_hosts': [['host2', '127.0.0.1'], ['host1', '127.0.0.1']]}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    '--add-host',
                    'host2:127.0.0.1',
                    '--add-host',
                    'host1:127.0.0.1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_dogstatsd_port(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={'DD_DOGSTATSD_PORT': '9000'})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_DOGSTATSD_PORT=9000',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    '-p',
                    '9000:9000/udp',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_proxies(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'proxy': {'http': 'http://localhost:8080', 'https': 'https://localhost:4443'}}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_PROXY_HTTP=http://localhost:8080',
                    '-e',
                    'DD_PROXY_HTTPS=https://localhost:4443',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_start_commands(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'start_commands': ['echo "hello world"']}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call([docker_path, 'exec', f'dd_{integration}_{environment}', 'echo', 'hello world'], shell=False),
            mocker.call(
                [docker_path, 'restart', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_post_install_commands(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'post_install_commands': ['echo "hello world"']}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call([docker_path, 'exec', f'dd_{integration}_{environment}', 'echo', 'hello world'], shell=False),
            mocker.call(
                [docker_path, 'restart', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_local_packages_linux_container(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={temp_dir / 'foo': '[deps]'}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-v',
                    f'{temp_dir / "foo"}:/home/foo',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call(
                [
                    docker_path,
                    'exec',
                    f'dd_{integration}_{environment}',
                    '/opt/datadog-agent/embedded/bin/python3',
                    '-m',
                    'pip',
                    'install',
                    '--disable-pip-version-check',
                    '-e',
                    '/home/foo[deps]',
                ],
                shell=False,
            ),
            mocker.call(
                [docker_path, 'restart', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_local_packages_windows_container(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'docker_platform': 'windows'}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={temp_dir / 'foo': '[deps]'}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '-v',
                    f'{config_file.parent}:C:\\ProgramData\\Datadog\\conf.d\\{integration}.d',
                    '-v',
                    f'{temp_dir / "foo"}:C:\\Users\\ContainerAdministrator\\foo',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call(
                [
                    docker_path,
                    'exec',
                    f'dd_{integration}_{environment}',
                    'C:\\Program Files\\Datadog\\Datadog Agent\\embedded3\\python.exe',
                    '-m',
                    'pip',
                    'install',
                    '--disable-pip-version-check',
                    '-e',
                    'C:\\Users\\ContainerAdministrator\\foo[deps]',
                ],
                shell=False,
            ),
            mocker.call(
                [docker_path, 'restart', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_all_post_run_logic(
        self,
        platform,
        temp_dir,
        default_hostname,
        get_integration,
        docker_path,
        free_port,
        mocker,
    ):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'start_commands': ['echo "hello world1"'], 'post_install_commands': ['echo "hello world2"']}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={temp_dir / 'foo': '[deps]'}, env_vars={})

        assert run.call_args_list == [
            mocker.call([docker_path, 'pull', 'datadog/agent-dev:master-py3'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'run',
                    '-d',
                    '--name',
                    f'dd_{integration}_{environment}',
                    '--network',
                    'host',
                    '-v',
                    '/proc:/host/proc',
                    '-v',
                    f'{config_file.parent}:/etc/datadog-agent/conf.d/{integration}.d',
                    '-v',
                    f'{temp_dir / "foo"}:/home/foo',
                    '-e',
                    'DD_API_KEY=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    '-e',
                    'DD_APM_ENABLED=false',
                    '-e',
                    f'DD_CMD_PORT={free_port}',
                    '-e',
                    'DD_EXPVAR_PORT=5000',
                    '-e',
                    f'DD_HOSTNAME={default_hostname}',
                    '-e',
                    'DD_TELEMETRY_ENABLED=1',
                    '-e',
                    'PYTHONDONTWRITEBYTECODE=1',
                    'datadog/agent-dev:master-py3',
                ],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call([docker_path, 'exec', f'dd_{integration}_{environment}', 'echo', 'hello world1'], shell=False),
            mocker.call(
                [
                    docker_path,
                    'exec',
                    f'dd_{integration}_{environment}',
                    '/opt/datadog-agent/embedded/bin/python3',
                    '-m',
                    'pip',
                    'install',
                    '--disable-pip-version-check',
                    '-e',
                    '/home/foo[deps]',
                ],
                shell=False,
            ),
            mocker.call([docker_path, 'exec', f'dd_{integration}_{environment}', 'echo', 'hello world2'], shell=False),
            mocker.call(
                [docker_path, 'restart', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]


class TestStop:
    def test_basic(self, platform, get_integration, docker_path, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, Path('config.yaml'))
        agent.stop()

        assert run.call_args_list == [
            mocker.call(
                [docker_path, 'stop', '-t', '0', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call(
                [docker_path, 'rm', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]

    def test_stop_commands(self, platform, get_integration, docker_path, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'stop_commands': ['echo "hello world"']}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, Path('config.yaml'))
        agent.stop()

        assert run.call_args_list == [
            mocker.call([docker_path, 'exec', f'dd_{integration}_{environment}', 'echo', 'hello world'], shell=False),
            mocker.call(
                [docker_path, 'stop', '-t', '0', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
            mocker.call(
                [docker_path, 'rm', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]


class TestRestart:
    def test_basic(self, platform, get_integration, docker_path, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, Path('config.yaml'))
        agent.restart()

        assert run.call_args_list == [
            mocker.call(
                [docker_path, 'restart', f'dd_{integration}_{environment}'],
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            ),
        ]


class TestInvoke:
    def test_basic(self, platform, get_integration, docker_path, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, Path('config.yaml'))
        agent.invoke(['check', 'postgres'])

        assert run.call_args_list == [
            mocker.call(
                [docker_path, 'exec', f'dd_{integration}_{environment}', 'agent', 'check', 'postgres'],
                shell=False,
                check=True,
            ),
        ]


class TestEnterShell:
    def test_linux_container(self, platform, get_integration, docker_path, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))
        mocker.patch('sys.stdout', return_value=mocker.MagicMock(isatty=lambda: True))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, Path('config.yaml'))
        agent.enter_shell()

        assert run.call_args_list == [
            mocker.call(
                [docker_path, 'exec', '-it', f'dd_{integration}_{environment}', 'bash'],
                shell=False,
                check=True,
            ),
        ]

    def test_windows_container(self, platform, get_integration, docker_path, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))
        mocker.patch('sys.stdout', return_value=mocker.MagicMock(isatty=lambda: True))

        integration = 'postgres'
        environment = 'py3.12'
        metadata = {'docker_platform': 'windows'}

        agent = DockerAgent(platform, get_integration(integration), environment, metadata, Path('config.yaml'))
        agent.enter_shell()

        assert run.call_args_list == [
            mocker.call(
                [docker_path, 'exec', '-it', f'dd_{integration}_{environment}', 'cmd'],
                shell=False,
                check=True,
            ),
        ]
