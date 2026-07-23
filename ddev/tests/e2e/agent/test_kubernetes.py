# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import subprocess

import pytest

from ddev.e2e.agent.kubernetes import KubernetesAgent
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig

RESTART_COMMAND = (
    'old_pid=$(pidof agent) || exit 1; '
    'set -- $old_pid; old_pid=$1; '
    'rm -f /var/run/s6/services/agent/finish; '
    'kill "$old_pid" || exit 1; '
    'elapsed=0; '
    'while kill -0 "$old_pid" 2>/dev/null; do '
    '[ "$elapsed" -ge 120 ] && exit 1; '
    'sleep 1; elapsed=$((elapsed + 1)); '
    'done'
)


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
            'kubeconfig': '/tmp/kubeconfig',
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
        if command[-4:] == ['get', 'nodes', '-o', 'json']:
            nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}
            return successful_process(command, stdout=json.dumps(nodes).encode())
        return successful_process(command)

    return mocker.patch.object(app.platform, 'run_command', side_effect=run)


def command_calls(run_command):
    return [call.args[0] for call in run_command.call_args_list]


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
    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    assert calls[0] == [*prefix, 'get', 'nodes', '-o', 'json']

    create_calls = [call for call in run_command.call_args_list if call.args[0] == [*prefix, 'create', '-f', '-']]
    assert len(create_calls) == 1
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

    start_command = [
        *prefix,
        'exec',
        '--namespace',
        'ddev-agent',
        'pod/ddev-agent',
        '--container',
        'agent',
        '--',
        'echo',
        'start',
    ]
    post_install_command = [
        *prefix,
        'exec',
        '--namespace',
        'ddev-agent',
        'pod/ddev-agent',
        '--container',
        'agent',
        '--',
        'echo',
        'post-install',
    ]
    assert start_command in calls
    assert post_install_command in calls

    assert [
        *prefix,
        'cp',
        '--container',
        'agent',
        local_base.name,
        f'{agent._namespace}/ddev-agent:/home/datadog_checks_base',
    ] in calls
    assert [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        'pod/ddev-agent',
        '--container',
        'agent',
        '--',
        '/opt/datadog-agent/embedded/bin/python3',
        '-m',
        'pip',
        'install',
        '--disable-pip-version-check',
        '-e',
        '/home/datadog_checks_base[kube]',
    ] in calls
    assert [
        *prefix,
        'cp',
        '--container',
        'agent',
        config_file.name,
        f'{agent._namespace}/ddev-agent:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    ] in calls
    assert [
        *prefix,
        'cp',
        '--container',
        'agent',
        auto_conf.name,
        f'{agent._namespace}/ddev-agent:/etc/datadog-agent/conf.d/velero.d/auto_conf.yaml',
    ] in calls
    restart_command = [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        'pod/ddev-agent',
        '--container',
        'agent',
        '--',
        'sh',
        '-c',
        RESTART_COMMAND,
    ]
    assert restart_command in calls
    assert calls.index(start_command) < calls.index(post_install_command) < calls.index(restart_command)
    assert metadata['kubernetes']['local_packages'] == [
        {'path': str(local_base), 'name': 'datadog_checks_base', 'features': '[kube]'},
        {'path': str(integration), 'name': 'velero', 'features': '[deps]'},
    ]
    local_base_copy = next(call for call in run_command.call_args_list if call.args[0][-2] == local_base.name)
    assert local_base_copy.kwargs['cwd'] == local_base.resolve().parent


@pytest.mark.parametrize('wait_timeout', [0, True])
def test_rejects_invalid_wait_timeout_before_creating_resources(agent, metadata, run_command, wait_timeout):
    metadata['kubernetes']['wait_timeout'] = wait_timeout

    with pytest.raises(ValueError, match='wait_timeout'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    run_command.assert_not_called()


def test_rejects_multi_node_clusters(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'one'}, 'spec': {}}, {'metadata': {'name': 'two'}, 'spec': {}}]}
    run_command = mocker.patch.object(
        app.platform,
        'run_command',
        return_value=successful_process([], stdout=json.dumps(nodes).encode()),
    )

    with pytest.raises(NotImplementedError, match='exactly one schedulable node'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    run_command.assert_called_once()


def test_partial_manifest_creation_failure_is_propagated(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}

    def run(command, **kwargs):
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


def test_invoke_synchronizes_config_and_environment(agent, metadata, config_file, auto_conf, run_command):
    config_file.write_text('instances:\n  - openmetrics_endpoint: http://velero:8085/metrics\n')

    agent.invoke(['check', 'velero', '--json'], env_vars={'ZED': 'last', 'ALPHA': 'first'})

    calls = command_calls(run_command)
    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    assert calls == [
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            'pod/ddev-agent',
            '--container',
            'agent',
            '--',
            'mkdir',
            '-p',
            '/etc/datadog-agent/conf.d/velero.d',
        ],
        [
            *prefix,
            'cp',
            '--container',
            'agent',
            config_file.name,
            f'{agent._namespace}/ddev-agent:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
        ],
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            'pod/ddev-agent',
            '--container',
            'agent',
            '--',
            'mkdir',
            '-p',
            '/etc/datadog-agent/conf.d/velero.d',
        ],
        [
            *prefix,
            'cp',
            '--container',
            'agent',
            auto_conf.name,
            f'{agent._namespace}/ddev-agent:/etc/datadog-agent/conf.d/velero.d/auto_conf.yaml',
        ],
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            'pod/ddev-agent',
            '--container',
            'agent',
            '--',
            'env',
            'ALPHA=first',
            'ZED=last',
            'agent',
            'check',
            'velero',
            '--json',
        ],
    ]


def test_invoke_removes_pod_config_when_host_config_is_absent(agent, config_file, run_command):
    config_file.remove()

    agent.invoke(['status'])

    calls = command_calls(run_command)
    assert [
        'kubectl',
        '--kubeconfig',
        '/tmp/kubeconfig',
        'exec',
        '--namespace',
        agent._namespace,
        'pod/ddev-agent',
        '--container',
        'agent',
        '--',
        'rm',
        '-f',
        '/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    ] in calls


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
    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    package_copy = [
        *prefix,
        'cp',
        '--container',
        'agent',
        local_package.name,
        f'{agent._namespace}/ddev-agent:/home/velero-source',
    ]
    config_copy = [
        *prefix,
        'cp',
        '--container',
        'agent',
        config_file.name,
        f'{agent._namespace}/ddev-agent:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    ]
    restart = [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        'pod/ddev-agent',
        '--container',
        'agent',
        '--',
        'sh',
        '-c',
        RESTART_COMMAND,
    ]
    assert package_copy in calls
    assert config_copy in calls
    assert calls.index(package_copy) < calls.index(config_copy) < calls.index(restart)
    assert not any('pip' in command for command in calls)


def test_shell_and_logs_use_backend_commands(agent, run_command):
    agent.enter_shell()
    agent.show_logs()

    calls = command_calls(run_command)
    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    assert calls == [
        [
            *prefix,
            'exec',
            '-it',
            '--namespace',
            agent._namespace,
            'pod/ddev-agent',
            '--container',
            'agent',
            '--',
            'bash',
        ],
        [*prefix, 'logs', '--namespace', agent._namespace, 'pod/ddev-agent', '--container', 'agent'],
    ]
    assert run_command.call_args_list[-1].kwargs['check'] is True


def test_kubeconfig_validation(app, get_integration, config_file):
    agent = KubernetesAgent(app, get_integration('velero'), 'py3.12', {'kubernetes': {}}, config_file)
    with pytest.raises(ValueError, match='non-empty `kubeconfig`'):
        _ = agent._kubeconfig
