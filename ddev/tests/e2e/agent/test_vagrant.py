# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ddev.e2e.agent.vagrant import VagrantAgent, disable_integration_before_install
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig
from ddev.utils.fs import Path as DdevPath
from ddev.utils.structures import EnvVars


@pytest.fixture(scope='module')
def get_integration(local_repo):
    def _get_integration(name):
        return Integration(local_repo / name, local_repo, RepositoryConfig(local_repo / '.ddev' / 'config.toml'))

    return _get_integration


@pytest.fixture
def vagrant_env_cleanup():
    """Clean up VAGRANT_CWD environment variable after test."""
    original_value = os.environ.get('VAGRANT_CWD')
    yield
    if original_value is not None:
        os.environ['VAGRANT_CWD'] = original_value
    else:
        os.environ.pop('VAGRANT_CWD', None)


@pytest.fixture
def mock_env_data_storage(mocker, temp_dir):
    """Mock EnvDataStorage to provide a test storage directory."""
    storage_mock = mocker.MagicMock()
    storage_mock.get.return_value.storage_dir = temp_dir
    mocker.patch('ddev.e2e.agent.vagrant.EnvDataStorage', return_value=storage_mock)
    return storage_mock


@pytest.fixture
def mock_vagrantfile_template(mocker):
    """Mock the Vagrantfile template."""
    template_content = """
Vagrant.configure("2") do |config|
  config.vm.box = "{{ vagrant_box }}"
  config.vm.hostname = "{{ vm_hostname }}"
  {{ synced_folders_str }}
  {{ exported_env_vars_str }}
  config.vm.provision "shell", inline: <<-SHELL
    DD_API_KEY="{{ dd_api_key }}" {{ agent_install_env_vars_str }} bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"
  SHELL
end
"""
    mock_template = mocker.MagicMock()
    mock_template.render.return_value = template_content
    mocker.patch.object(VagrantAgent, '_get_vagrantfile_template', return_value=mock_template)
    return mock_template


@pytest.fixture
def mock_platform_run(app, mocker):
    """Mock platform.run_command method."""
    process_mock = mocker.MagicMock(returncode=0, stdout=b'', stderr=b'')
    run_mock = mocker.patch.object(app.platform, 'run_command', return_value=process_mock)
    return run_mock


class TestStart:
    @pytest.mark.parametrize(
        'agent_build, expected_env_vars',
        [
            pytest.param('', {}, id='default'),
            pytest.param(
                '12345-7-x86_64',
                {
                    'TESTING_APT_URL': 's3.amazonaws.com/apttesting.datad0g.com',
                    'TESTING_APT_REPO_VERSION': 'pipeline-12345-a7-x86_64 7',
                    'TESTING_YUM_URL': 's3.amazonaws.com/yumtesting.datad0g.com',
                    'TESTING_YUM_VERSION_PATH': 'testing/pipeline-12345-a7/7',
                },
                id='pipeline build',
            ),
            pytest.param(
                '67890-8-arm64',
                {
                    'TESTING_APT_URL': 's3.amazonaws.com/apttesting.datad0g.com',
                    'TESTING_APT_REPO_VERSION': 'pipeline-67890-a8-arm64 8',
                    'TESTING_YUM_URL': 's3.amazonaws.com/yumtesting.datad0g.com',
                    'TESTING_YUM_VERSION_PATH': 'testing/pipeline-67890-a8/8',
                },
                id='arm64 build',
            ),
        ],
    )
    def test_agent_build(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
        agent_build,
        expected_env_vars,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build=agent_build, local_packages={}, env_vars={})

        # Verify vagrant up command was called
        assert mock_platform_run.call_args_list[0] == mocker.call('vagrant up dd-vagrant-glusterfs-py3.12', shell=False)

        # Verify Vagrantfile was generated with correct env vars
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        agent_install_env_vars_str = render_kwargs['agent_install_env_vars_str']
        for key, value in expected_env_vars.items():
            assert f'{key}="{value}"' in agent_install_env_vars_str

    def test_env_vars(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(
            agent_build='',
            local_packages={},
            env_vars={'DD_API_KEY': 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa', 'DD_LOGS_ENABLED': 'true'},
        )

        # Verify Vagrantfile was generated with correct exported env vars
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        exported_env_vars_str = render_kwargs['exported_env_vars_str']
        assert 'export DD_API_KEY="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"' in exported_env_vars_str
        assert 'export DD_APM_ENABLED="false"' in exported_env_vars_str
        assert 'export DD_TELEMETRY_ENABLED="true"' in exported_env_vars_str

    def test_no_config_file(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, temp_dir / 'config.yaml')
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify no synced folder for config was added
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        # Since config file doesn't exist, synced_folders_str should be empty or not contain config mount
        synced_folders_str = render_kwargs['synced_folders_str']
        assert synced_folders_str == ""

    def test_windows_vm(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_guest_os': 'windows'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify config mount path is Windows-style
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        synced_folders_str = render_kwargs['synced_folders_str']
        # Check that the Windows config path is in the synced folders
        assert (
            'ProgramData' in synced_folders_str
            and 'Datadog' in synced_folders_str
            and 'glusterfs.d' in synced_folders_str
        )

    def test_synced_folders(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_synced_folders': ['/host/path:/guest/path', '/another/host:/another/guest']}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify synced folders were included
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        synced_folders_str = render_kwargs['synced_folders_str']
        assert 'config.vm.synced_folder "/host/path", "/guest/path"' in synced_folders_str
        assert 'config.vm.synced_folder "/another/host", "/another/guest"' in synced_folders_str

    def test_custom_hostname(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'dd_hostname': 'custom-hostname'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify custom hostname was set
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        exported_env_vars_str = render_kwargs['exported_env_vars_str']
        assert 'export DD_HOSTNAME="custom-hostname"' in exported_env_vars_str

    def test_proxies(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'proxy': {'http': 'http://localhost:8080', 'https': 'https://localhost:4443'}}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify proxy settings were added
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        exported_env_vars_str = render_kwargs['exported_env_vars_str']
        assert 'export DD_PROXY_HTTP="http://localhost:8080"' in exported_env_vars_str
        assert 'export DD_PROXY_HTTPS="https://localhost:4443"' in exported_env_vars_str

    def test_start_commands(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'start_commands': ['echo "hello world"']}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify start command was executed
        vm_name = 'dd-vagrant-glusterfs-py3.12'
        expected_calls = [
            mocker.call('vagrant up dd-vagrant-glusterfs-py3.12', shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'echo "hello world"'], shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sudo service datadog-agent restart'], shell=False),
        ]

        assert mock_platform_run.call_args_list == expected_calls

    def test_post_install_commands(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'post_install_commands': ['echo "post install"']}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify post install command was executed
        vm_name = 'dd-vagrant-glusterfs-py3.12'
        expected_calls = [
            mocker.call('vagrant up dd-vagrant-glusterfs-py3.12', shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'echo "post install"'], shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sudo service datadog-agent restart'], shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls

    def test_local_packages_linux(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        foo_package = temp_dir / 'foo'
        foo_package.mkdir()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={foo_package: '[deps]'}, env_vars={})

        # Verify package was mounted and installed
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        synced_folders_str = render_kwargs['synced_folders_str']
        # Check that the package mount is in the synced folders
        assert '/home/packages/foo' in synced_folders_str

        # Verify pip install command
        vm_name = 'dd-vagrant-glusterfs-py3.12'
        expected_calls = [
            mocker.call('vagrant up dd-vagrant-glusterfs-py3.12', shell=False),
            mocker.call(
                [
                    'vagrant',
                    'ssh',
                    vm_name,
                    '-c',
                    'sudo -u dd-agent /opt/datadog-agent/embedded/bin/python3 -m pip install --disable-pip-version-check -e /home/packages/foo[deps]',  # noqa: E501
                ],
                shell=False,
            ),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sudo service datadog-agent restart'], shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls

    def test_local_packages_windows(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        foo_package = temp_dir / 'foo'
        foo_package.mkdir()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_guest_os': 'windows'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={foo_package: '[deps]'}, env_vars={})

        # Verify package was mounted with Windows path
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        synced_folders_str = render_kwargs['synced_folders_str']
        # Check that the Windows package mount is in the synced folders
        # The path will have escaped backslashes and the foo directory
        assert any('foo"' in line and 'vagrant' in line for line in synced_folders_str.split('\n'))

    def test_sudoers_configuration(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        sudoers_content = 'dd-agent ALL=(ALL) NOPASSWD:ALL'
        metadata = {'vagrant_sudoers_config': sudoers_content}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify sudoers commands were executed
        sudoers_commands = [
            'sudo mkdir -p /etc/sudoers.d',
            'dd-agent ALL=(ALL) NOPASSWD:ALL',
            'sudo chmod 0440 /etc/sudoers.d/dd-agent',
            'sudo chown root:root /etc/sudoers.d/dd-agent',
            'sudo visudo -c -f /etc/sudoers.d/dd-agent',
        ]

        for cmd in sudoers_commands:
            assert any(cmd in str(call) for call in mock_platform_run.call_args_list), (
                f"Expected command '{cmd}' not found"
            )

    def test_template_variable_substitution(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {
            'start_commands': ['echo "Host IP is %HOST%"'],
            'env': {'TEST_HOST': '%HOST%'},
        }

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)
        agent.start(agent_build='', local_packages={}, env_vars={})

        # Verify %HOST% was replaced with actual IP in env vars
        mock_vagrantfile_template.render.assert_called_once()
        render_kwargs = mock_vagrantfile_template.render.call_args.kwargs
        exported_env_vars_str = render_kwargs['exported_env_vars_str']
        assert 'export TEST_HOST="172.30.1.5"' in exported_env_vars_str

        # Verify %HOST% was replaced in commands
        vm_name = 'dd-vagrant-glusterfs-py3.12'
        expected_calls = [
            mocker.call('vagrant up dd-vagrant-glusterfs-py3.12', shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'echo "Host IP is 172.30.1.5"'], shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sudo service datadog-agent restart'], shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls

    def test_invalid_agent_build_format(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_vagrantfile_template,
        vagrant_env_cleanup,
    ):
        config_file = temp_dir / 'config' / 'config.yaml'
        config_file.parent.mkdir()
        config_file.touch()

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, config_file)

        # Mock app.abort to verify it's called
        abort_mock = mocker.patch.object(app, 'abort', side_effect=SystemExit)

        with pytest.raises(SystemExit):
            agent.start(agent_build='invalid-format', local_packages={}, env_vars={})

        abort_mock.assert_called_once()
        assert "Invalid `agent_build` format" in abort_mock.call_args[1]['text']


class TestStop:
    def test_basic(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        rmtree = mocker.patch('shutil.rmtree')

        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.stop()

        # Verify halt and destroy commands
        expected_calls = [
            mocker.call('vagrant halt dd-vagrant-glusterfs-py3.12', shell=False),
            mocker.call('vagrant destroy dd-vagrant-glusterfs-py3.12 --force', shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls

        # Verify temp directory was removed
        rmtree.assert_called_once()

    def test_stop_commands(
        self,
        app,
        temp_dir,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'stop_commands': ['echo "stopping services"']}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.stop()

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Verify stop command was executed before halt
        expected_calls = [
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'echo "stopping services"'], shell=False),
            mocker.call('vagrant halt dd-vagrant-glusterfs-py3.12', shell=False),
            mocker.call('vagrant destroy dd-vagrant-glusterfs-py3.12 --force', shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls


class TestRestart:
    def test_linux_restart(
        self,
        app,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.restart()

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Verify restart command
        expected_calls = [
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sudo service datadog-agent restart'], shell=False)
        ]
        assert mock_platform_run.call_args_list == expected_calls

    def test_windows_restart(
        self,
        app,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_guest_os': 'windows'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.restart()

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Verify Windows service restart commands
        expected_calls = [
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sc stop DatadogAgent'], shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sc start DatadogAgent'], shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls

    def test_windows_custom_service_name(
        self,
        app,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_guest_os': 'windows', 'vagrant_windows_agent_service_name': 'CustomAgentService'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.restart()

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Verify custom service name is used
        expected_calls = [
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sc stop CustomAgentService'], shell=False),
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sc start CustomAgentService'], shell=False),
        ]
        assert mock_platform_run.call_args_list == expected_calls


class TestInvoke:
    def test_linux_invoke(
        self,
        app,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.invoke(['check', 'glusterfs'])

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Verify agent command invocation
        expected_calls = [
            mocker.call(['vagrant', 'ssh', vm_name, '-c', 'sudo /opt/datadog-agent/bin/agent/agent check glusterfs']),
        ]
        assert mock_platform_run.call_args_list == expected_calls

    def test_windows_invoke(
        self,
        app,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_guest_os': 'windows'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))
        agent.invoke(['check', 'glusterfs'])

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Verify Windows agent command invocation
        expected_calls = [
            mocker.call(
                [
                    'vagrant',
                    'ssh',
                    vm_name,
                    '-c',
                    'C:\\Program Files\\Datadog\\Datadog Agent\\bin\\agent.exe check glusterfs',
                ]
            ),
        ]
        assert mock_platform_run.call_args_list == expected_calls


class TestEnterShell:
    def test_enter_shell(
        self,
        app,
        get_integration,
        mocker,
        mock_env_data_storage,
        mock_platform_run,
        vagrant_env_cleanup,
    ):
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))

        vm_name = 'dd-vagrant-glusterfs-py3.12'

        # Mock platform.modules.subprocess.run for enter_shell
        subprocess_run = mocker.patch.object(app.platform.modules.subprocess, 'run')

        agent.enter_shell()

        # Verify interactive shell command
        subprocess_run.assert_called_with(['vagrant', 'ssh', vm_name], check=True)


class TestDisableIntegrationBeforeInstall:
    def test_context_manager(self, temp_dir):
        """Test the disable_integration_before_install context manager."""
        config_file = temp_dir / 'conf.yaml'
        config_file.write_text('test content')

        with disable_integration_before_install(config_file):
            # Inside context: file should be renamed
            assert not config_file.exists()
            assert (temp_dir / 'conf.yaml.example').exists()
            assert (temp_dir / 'conf.yaml.example').read_text() == 'test content'

        # After context: file should be renamed back
        assert config_file.exists()
        assert config_file.read_text() == 'test content'
        assert not (temp_dir / 'conf.yaml.example').exists()

    def test_context_manager_with_error(self, temp_dir):
        """Test the context manager properly restores the file even if an error occurs."""
        config_file = temp_dir / 'conf.yaml'
        config_file.write_text('test content')

        try:
            with disable_integration_before_install(config_file):
                # Inside context: file should be renamed
                assert not config_file.exists()
                assert (temp_dir / 'conf.yaml.example').exists()
                raise ValueError("Test error")
        except ValueError:
            pass

        # After context: file should still be renamed back
        assert config_file.exists()
        assert config_file.read_text() == 'test content'
        assert not (temp_dir / 'conf.yaml.example').exists()


class TestVagrantProperties:
    def test_vm_name_sanitization(
        self,
        app,
        get_integration,
        mock_env_data_storage,
    ):
        """Test that VM names are properly sanitized."""
        integration = 'test_integration'
        environment = 'py3.12_test'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))

        # VM name should have underscores replaced with hyphens
        assert agent._vm_name == 'dd-vagrant-test-integration-py3.12-test'

    def test_cached_properties(
        self,
        app,
        get_integration,
        mock_env_data_storage,
    ):
        """Test various cached properties."""
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))

        # Test Linux properties
        assert agent._is_windows_vm is False
        assert agent._package_mount_dir == '/home/packages/'
        assert agent._config_mount_dir == '/etc/datadog-agent/conf.d/glusterfs.d'
        assert agent._python_path == '/opt/datadog-agent/embedded/bin/python3'

    def test_windows_cached_properties(
        self,
        app,
        get_integration,
        mock_env_data_storage,
    ):
        """Test cached properties for Windows VMs."""
        integration = 'glusterfs'
        environment = 'py3.12'
        metadata = {'vagrant_guest_os': 'windows'}

        agent = VagrantAgent(app, get_integration(integration), environment, metadata, DdevPath('config.yaml'))

        # Test Windows properties
        assert agent._is_windows_vm is True
        assert agent._package_mount_dir == 'C:\\vagrant\\packages\\'
        assert agent._config_mount_dir == 'C:\\ProgramData\\Datadog\\conf.d\\glusterfs.d'
        assert agent._python_path == 'C:\\Program Files\\Datadog\\Datadog Agent\\embedded3\\python.exe'
