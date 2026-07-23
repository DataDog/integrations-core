# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import subprocess

import pytest

from ddev.e2e.agent.kubernetes import KubernetesAgent
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig

TEST_KUBECONFIG = '/tmp/kubeconfig'
TEST_NAMESPACE = 'ddev-agent'
TEST_POD = 'ddev-agent'
TEST_CONTAINER = 'agent'


@pytest.fixture(scope='module')
def get_integration(local_repo):
    def _get_integration(name):
        return Integration(local_repo / name, local_repo, RepositoryConfig(local_repo / '.ddev' / 'config.toml'))

    return _get_integration


@pytest.fixture
def config_file(temp_dir):
    path = temp_dir / 'config' / 'velero.yaml'
    path.parent.ensure_dir_exists()
    path.write_text('instances: []\n')
    return path


@pytest.fixture
def auto_conf(temp_dir):
    path = temp_dir / 'auto_conf.yaml'
    path.write_text('ad_identifiers:\n  - velero\n')
    return path


@pytest.fixture
def metadata(auto_conf):
    return {
        'kubernetes': {
            'kubeconfig': TEST_KUBECONFIG,
            'auto_conf': str(auto_conf),
        },
    }


@pytest.fixture
def agent(app, get_integration, metadata, config_file):
    return KubernetesAgent(app, get_integration('velero'), 'py3.12', metadata, config_file)


def successful_process(command, *, stdout=b''):
    return subprocess.CompletedProcess(command, 0, stdout=stdout)


@pytest.fixture
def run_command(app, mocker):
    def run(command, **kwargs):
        if command[-2:] == ['config', 'current-context']:
            return successful_process(command, stdout=b'kind-test\n')
        if command[-4:] == ['get', 'nodes', '-o', 'json']:
            nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}
            return successful_process(command, stdout=json.dumps(nodes).encode())
        return successful_process(command)

    return mocker.patch.object(app.platform, 'run_command', side_effect=run)


def command_calls(run_command):
    return [call.args[0] for call in run_command.call_args_list]


def option_value(command: list[str], option: str) -> str:
    return command[command.index(option) + 1]


def find_kubectl_command(calls: list[list[str]], expected: list[str]) -> int:
    matches = []
    for index, command in enumerate(calls):
        kubectl_args = command[: command.index('--')] if '--' in command else command
        contains_expected = any(
            kubectl_args[start : start + len(expected)] == expected
            for start in range(len(kubectl_args) - len(expected) + 1)
        )
        if not contains_expected:
            continue

        assert command[0] == 'kubectl'
        assert option_value(kubectl_args, '--kubeconfig') == TEST_KUBECONFIG
        matches.append(index)

    assert len(matches) == 1, f'Expected one kubectl command containing {expected!r}, found {len(matches)}'
    return matches[0]


def find_exec_command(calls: list[list[str]], expected: list[str], *, prefix: bool = False) -> int:
    matches = []
    for index, command in enumerate(calls):
        if 'exec' not in command or '--' not in command:
            continue

        separator = command.index('--')
        payload = command[separator + 1 :]
        matches_expected = payload[: len(expected)] == expected if prefix else payload == expected
        if not matches_expected:
            continue

        kubectl_args = command[:separator]
        assert command[0] == 'kubectl'
        assert option_value(kubectl_args, '--kubeconfig') == TEST_KUBECONFIG
        assert option_value(kubectl_args, '--namespace') == TEST_NAMESPACE
        assert f'pod/{TEST_POD}' in kubectl_args
        assert option_value(kubectl_args, '--container') == TEST_CONTAINER
        matches.append(index)

    assert len(matches) == 1, f'Expected one kubectl exec payload matching {expected!r}, found {len(matches)}'
    return matches[0]


def find_copy_command(calls: list[list[str]], source: str, destination: str) -> int:
    matches = []
    for index, command in enumerate(calls):
        if 'cp' not in command or source not in command or destination not in command:
            continue

        assert command[0] == 'kubectl'
        assert option_value(command, '--kubeconfig') == TEST_KUBECONFIG
        assert option_value(command, '--container') == TEST_CONTAINER
        assert command.index(source) < command.index(destination)
        matches.append(index)

    assert len(matches) == 1, f'Expected one kubectl cp from {source!r} to {destination!r}, found {len(matches)}'
    return matches[0]


def test_exec_builds_scoped_command_and_sorts_environment(agent, run_command):
    agent._exec(['agent', 'check', 'velero'], env_vars={'ZED': 'last', 'ALPHA': 'first'})

    run_command.assert_called_once_with(
        [
            'kubectl',
            '--kubeconfig',
            TEST_KUBECONFIG,
            'exec',
            '--namespace',
            TEST_NAMESPACE,
            f'pod/{TEST_POD}',
            '--container',
            TEST_CONTAINER,
            '--',
            'env',
            'ALPHA=first',
            'ZED=last',
            'agent',
            'check',
            'velero',
        ],
        check=True,
    )


def test_copy_file_builds_scoped_command(agent, config_file, run_command):
    destination = '/tmp/conf.yaml'

    agent._copy_file(str(config_file), destination)

    run_command.assert_called_once_with(
        [
            'kubectl',
            '--kubeconfig',
            TEST_KUBECONFIG,
            'cp',
            '--container',
            TEST_CONTAINER,
            config_file.name,
            f'{TEST_NAMESPACE}/{TEST_POD}:{destination}',
        ],
        check=True,
        cwd=config_file.resolve().parent,
    )


def test_restart_command_preserves_s6_and_timeout_contract(agent, metadata, mocker):
    metadata['kubernetes']['wait_timeout'] = 17
    operations = mocker.Mock()
    execute = mocker.patch.object(agent, '_exec')
    wait_for_agent = mocker.patch.object(agent, '_wait_for_agent')
    operations.attach_mock(execute, 'execute')
    operations.attach_mock(wait_for_agent, 'wait_for_agent')

    agent._restart_agent_process()

    operations.assert_has_calls([mocker.call.execute(mocker.ANY), mocker.call.wait_for_agent()])
    command = execute.call_args.args[0]
    assert command[:2] == ['sh', '-c']
    script = command[2]
    assert 'pidof agent' in script
    assert 'rm -f /var/run/s6/services/agent/finish' in script
    assert 'kill "$old_pid"' in script
    assert '[ "$elapsed" -ge 17 ]' in script


def test_start_uses_selected_image_rbac_config_and_local_packages(
    agent, metadata, config_file, auto_conf, temp_dir, run_command
):
    local_base = temp_dir / 'datadog_checks_base'
    local_base.ensure_dir_exists()
    integration = temp_dir / 'velero'
    integration.ensure_dir_exists()
    metadata['start_commands'] = ['echo start']
    metadata['post_install_commands'] = ['echo post-install']

    agent.start(
        agent_build='registry.example.com/datadog-agent:test',
        local_packages={local_base: '[kube]', integration: '[deps]'},
        env_vars={'DD_SITE': 'datadoghq.com'},
    )

    calls = command_calls(run_command)
    prefix = ['kubectl', '--kubeconfig', TEST_KUBECONFIG]
    context_index = find_kubectl_command(calls, ['config', 'current-context'])
    topology_index = find_kubectl_command(calls, ['get', 'nodes', '-o', 'json'])
    create_calls = [call for call in run_command.call_args_list if call.args[0] == [*prefix, 'create', '-f', '-']]
    assert len(create_calls) == 1
    create_index = run_command.call_args_list.index(create_calls[0])
    assert context_index < topology_index < create_index
    manifest = json.loads(create_calls[0].kwargs['input'])
    resources = {item['kind']: item for item in manifest['items']}
    assert resources['Namespace']['metadata']['name'] == 'ddev-agent'
    assert resources['ServiceAccount']['metadata']['namespace'] == 'ddev-agent'
    assert resources['ClusterRole']['metadata']['name'] == 'ddev-agent'
    assert resources['ClusterRoleBinding']['metadata']['name'] == 'ddev-agent'
    assert resources['ClusterRoleBinding']['roleRef']['name'] == 'ddev-agent'
    assert resources['ClusterRoleBinding']['subjects'][0]['namespace'] == 'ddev-agent'
    assert resources['Pod']['metadata']['namespace'] == 'ddev-agent'
    assert resources['Pod']['spec']['containers'][0]['name'] == 'agent'
    assert resources['Pod']['spec']['containers'][0]['image'] == 'registry.example.com/datadog-agent:test'
    assert resources['Pod']['spec']['containers'][0]['imagePullPolicy'] == 'Always'
    assert resources['Pod']['spec']['serviceAccountName'] == 'ddev-agent'
    resource_labels = {'app.kubernetes.io/managed-by': 'ddev'}
    for kind in ('Namespace', 'ServiceAccount', 'ClusterRole', 'ClusterRoleBinding'):
        assert resources[kind]['metadata']['labels'] == resource_labels
    assert resources['Pod']['metadata']['labels'] == {
        **resource_labels,
        'app.kubernetes.io/name': 'ddev-agent',
    }
    assert resources['ClusterRole']['rules'] == [
        {'apiGroups': [''], 'resources': ['nodes'], 'verbs': ['get', 'list', 'watch']},
        {
            'apiGroups': [''],
            'resources': ['nodes/metrics', 'nodes/spec', 'nodes/stats', 'nodes/proxy'],
            'verbs': ['get'],
        },
        {
            'apiGroups': [''],
            'resources': ['pods', 'endpoints', 'services'],
            'verbs': ['get', 'list', 'watch'],
        },
    ]
    env = {item['name']: item.get('value') for item in resources['Pod']['spec']['containers'][0]['env']}
    assert env['DD_API_KEY'] == 'a' * 32
    assert env['DD_SITE'] == 'datadoghq.com'
    assert env['DD_AUTOCONFIG_FROM_ENVIRONMENT'] == 'true'
    assert 'DD_KUBERNETES_KUBELET_HOST' in env
    assert 'DD_KUBERNETES_KUBELET_NODENAME' in env

    start_index = find_exec_command(calls, ['echo', 'start'])
    post_install_index = find_exec_command(calls, ['echo', 'post-install'])
    local_base_copy_index = find_copy_command(
        calls,
        local_base.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/home/datadog_checks_base',
    )
    find_exec_command(
        calls,
        [
            '/opt/datadog-agent/embedded/bin/python3',
            '-m',
            'pip',
            'install',
            '--disable-pip-version-check',
            '-e',
            '/home/datadog_checks_base[kube]',
        ],
    )
    find_copy_command(
        calls,
        config_file.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    )
    find_copy_command(
        calls,
        auto_conf.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/etc/datadog-agent/conf.d/velero.d/auto_conf.yaml',
    )
    restart_index = find_exec_command(calls, ['sh', '-c'], prefix=True)
    assert start_index < post_install_index < restart_index
    assert metadata['kubernetes']['local_packages'] == [
        {'path': str(local_base), 'name': 'datadog_checks_base', 'features': '[kube]'},
        {'path': str(integration), 'name': 'velero', 'features': '[deps]'},
    ]
    local_base_copy = run_command.call_args_list[local_base_copy_index]
    assert local_base_copy.kwargs['cwd'] == local_base.resolve().parent


@pytest.mark.parametrize('wait_timeout', [0, True])
def test_rejects_invalid_wait_timeout_before_creating_resources(agent, metadata, run_command, wait_timeout):
    metadata['kubernetes']['wait_timeout'] = wait_timeout

    with pytest.raises(ValueError, match='wait_timeout'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    run_command.assert_not_called()


def test_rejects_non_kind_context_before_inspecting_cluster(agent, app, mocker):
    run_command = mocker.patch.object(
        app.platform,
        'run_command',
        return_value=successful_process([], stdout=b'prod\n'),
    )

    with pytest.raises(RuntimeError, match='non-Kind Kubernetes context `prod`'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    run_command.assert_called_once_with(
        ['kubectl', '--kubeconfig', TEST_KUBECONFIG, 'config', 'current-context'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_rejects_multi_node_clusters(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'one'}, 'spec': {}}, {'metadata': {'name': 'two'}, 'spec': {}}]}

    def run(command, **kwargs):
        if command[-2:] == ['config', 'current-context']:
            return successful_process(command, stdout=b'kind-test\n')
        return successful_process(command, stdout=json.dumps(nodes).encode())

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(NotImplementedError, match='exactly one schedulable node'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    calls = command_calls(run_command)
    context_index = find_kubectl_command(calls, ['config', 'current-context'])
    topology_index = find_kubectl_command(calls, ['get', 'nodes', '-o', 'json'])
    assert context_index < topology_index
    assert not any('create' in command for command in calls)
    for index in (context_index, topology_index):
        assert run_command.call_args_list[index].kwargs['stdout'] is subprocess.PIPE
        assert run_command.call_args_list[index].kwargs['stderr'] is subprocess.STDOUT


def test_partial_manifest_creation_failure_is_propagated(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}

    def run(command, **kwargs):
        if command[-2:] == ['config', 'current-context']:
            return successful_process(command, stdout=b'kind-test\n')
        if command[-4:] == ['get', 'nodes', '-o', 'json']:
            return successful_process(command, stdout=json.dumps(nodes).encode())
        if command[-3:] == ['create', '-f', '-']:
            return subprocess.CompletedProcess(command, 1, stdout=b'', stderr=b'namespace already exists')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='Unable to create Kubernetes Agent resources'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    calls = command_calls(run_command)
    assert sum(command[-3:] == ['create', '-f', '-'] for command in calls) == 1
    assert not any('apply' in command or 'wait' in command for command in calls)


def test_invoke_synchronizes_config_and_environment(agent, config_file, auto_conf, run_command):
    config_file.write_text('instances:\n  - openmetrics_endpoint: http://velero:8085/metrics\n')

    agent.invoke(['check', 'velero', '--json'], env_vars={'ZED': 'last', 'ALPHA': 'first'})

    calls = command_calls(run_command)
    config_copy_index = find_copy_command(
        calls,
        config_file.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    )
    auto_conf_copy_index = find_copy_command(
        calls,
        auto_conf.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/etc/datadog-agent/conf.d/velero.d/auto_conf.yaml',
    )
    invoke_index = find_exec_command(
        calls,
        ['env', 'ALPHA=first', 'ZED=last', 'agent', 'check', 'velero', '--json'],
    )
    assert config_copy_index < auto_conf_copy_index < invoke_index


def test_invoke_removes_pod_config_when_host_config_is_absent(agent, config_file, run_command):
    config_file.remove()

    agent.invoke(['status'])

    calls = command_calls(run_command)
    find_exec_command(calls, ['rm', '-f', '/etc/datadog-agent/conf.d/velero.d/conf.yaml'])


def test_stop_is_no_op(agent, run_command):
    agent.stop()

    run_command.assert_not_called()


def test_restart_resynchronizes_config_auto_conf_and_editable_sources(
    agent, metadata, config_file, temp_dir, run_command
):
    local_package = temp_dir / 'velero-source'
    local_package.ensure_dir_exists()
    metadata['kubernetes']['local_packages'] = [
        {'path': str(local_package), 'name': 'velero-source', 'features': '[deps]'}
    ]

    agent.restart()

    calls = command_calls(run_command)
    package_copy_index = find_copy_command(
        calls,
        local_package.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/home/velero-source',
    )
    config_copy_index = find_copy_command(
        calls,
        config_file.name,
        f'{TEST_NAMESPACE}/{TEST_POD}:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    )
    restart_index = find_exec_command(calls, ['sh', '-c'], prefix=True)
    assert package_copy_index < config_copy_index < restart_index
    assert not any('pip' in command for command in calls)


def test_shell_and_logs_use_backend_commands(agent, run_command):
    agent.enter_shell()
    agent.show_logs()

    calls = command_calls(run_command)
    prefix = ['kubectl', '--kubeconfig', TEST_KUBECONFIG]
    assert calls == [
        [
            *prefix,
            'exec',
            '-it',
            '--namespace',
            TEST_NAMESPACE,
            f'pod/{TEST_POD}',
            '--container',
            TEST_CONTAINER,
            '--',
            'bash',
        ],
        [*prefix, 'logs', '--namespace', TEST_NAMESPACE, f'pod/{TEST_POD}', '--container', TEST_CONTAINER],
    ]
    assert run_command.call_args_list[-1].kwargs['check'] is True


def test_kubeconfig_validation(app, get_integration, config_file):
    agent = KubernetesAgent(app, get_integration('velero'), 'py3.12', {'kubernetes': {}}, config_file)
    with pytest.raises(ValueError, match='non-empty `kubeconfig`'):
        _ = agent._kubeconfig
