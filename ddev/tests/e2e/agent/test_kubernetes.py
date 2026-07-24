# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import subprocess
from pathlib import Path

import pytest

from ddev.e2e.agent.kubernetes import KubernetesAgent
from ddev.e2e.agent.kubernetes_helm import CHART_REPOSITORY, CHART_VERSION
from ddev.integration.core import Integration
from ddev.repo.config import RepositoryConfig

POD_NAME = 'ddev-agent-abcde'
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


def pod_data(*, ready=True, terminating=False, name=POD_NAME, node='kind-control-plane'):
    metadata = {'name': name, 'uid': f'{name}-uid'}
    if terminating:
        metadata['deletionTimestamp'] = '2026-07-22T00:00:00Z'
    return {
        'metadata': metadata,
        'spec': {'nodeName': node, 'containers': [{'name': 'agent'}]},
        'status': {
            'phase': 'Running',
            'conditions': [{'type': 'Ready', 'status': 'True' if ready else 'False'}],
        },
    }


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
        '_kubernetes_owner_id': 'test-owner',
        'kubernetes': {
            'kubeconfig': '/tmp/kubeconfig',
            'auto_conf': str(auto_conf),
            'wait_timeout': 120,
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
        if 'get' in command and 'pods' in command and command[-2:] == ['-o', 'json']:
            return successful_process(command, stdout=json.dumps({'items': [pod_data()]}).encode())
        if command[:3] == ['helm', 'version', '--short']:
            return successful_process(command, stdout=b'v3.19.0\n')
        if 'create' in command and command[-4:] == ['-f', '-', '-o', 'json']:
            return successful_process(command, stdout=b'{"metadata":{"uid":"namespace-uid"}}')
        if command[:2] == ['helm', 'list']:
            return successful_process(command, stdout=b'[]')
        return successful_process(command)

    return mocker.patch.object(app.platform, 'run_command', side_effect=run)


def command_calls(run_command):
    return [call.args[0] for call in run_command.call_args_list]


def operational_calls(run_command):
    return [
        call.args[0] for call in run_command.call_args_list if not ('get' in call.args[0] and 'pods' in call.args[0])
    ]


def test_start_installs_pinned_helm_chart_and_prepares_selected_agent(
    agent, metadata, config_file, auto_conf, temp_dir, run_command
):
    local_base = temp_dir / 'datadog_checks_base'
    local_base.ensure_dir_exists()
    integration = temp_dir / 'velero'
    integration.ensure_dir_exists()

    agent.start(
        agent_build='registry.example.com/datadog-agent:test',
        local_packages={local_base: '[kube]', integration: '[deps]'},
        env_vars={'DD_SITE': 'datadoghq.com'},
    )

    calls = command_calls(run_command)
    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    assert calls[0] == ['helm', 'version', '--short']
    assert calls[1] == [*prefix, 'get', 'nodes', '-o', 'json']
    assert calls[2] == [*prefix, 'get', 'namespace', agent._namespace, '--ignore-not-found=true', '-o', 'name']

    create_calls = [
        call for call in run_command.call_args_list if call.args[0] == [*prefix, 'create', '-f', '-', '-o', 'json']
    ]
    assert len(create_calls) == 1
    namespace = json.loads(create_calls[0].kwargs['input'])
    assert namespace == {
        'apiVersion': 'v1',
        'kind': 'Namespace',
        'metadata': {
            'name': agent._namespace,
            'labels': {
                'app.kubernetes.io/managed-by': 'ddev',
                'ddev.datadoghq.com/environment': 'test-owner',
            },
        },
    }

    helm_call = next(call for call in run_command.call_args_list if call.args[0][:2] == ['helm', 'install'])
    assert helm_call.args[0] == [
        'helm',
        'install',
        'ddev-agent',
        'datadog',
        '--repo',
        CHART_REPOSITORY,
        '--version',
        CHART_VERSION,
        '--namespace',
        agent._namespace,
        '--kubeconfig',
        '/tmp/kubeconfig',
        '--atomic',
        '--wait',
        '--timeout',
        '120s',
        '-f',
        '-',
    ]
    values = json.loads(helm_call.kwargs['input'])
    assert values['fullnameOverride'] == agent._namespace
    assert values['commonLabels'] == {'ddev.datadoghq.com/environment': 'test-owner'}
    assert values['agents']['instanceLabelOverride'] == 'test-owner'
    assert values['agents']['image'] == {
        'repository': 'registry.example.com/datadog-agent',
        'tag': 'test',
        'doNotCheckTag': True,
        'pullPolicy': 'Always',
    }
    assert values['agents']['podLabels']['ddev.datadoghq.com/environment'] == 'test-owner'
    assert values['agents']['podLabels']['app.kubernetes.io/component'] == 'agent'
    assert values['agents']['podLabels']['app'] == agent._namespace
    assert values['agents']['affinity']['nodeAffinity']['requiredDuringSchedulingIgnoredDuringExecution'][
        'nodeSelectorTerms'
    ] == [{'matchFields': [{'key': 'metadata.name', 'operator': 'In', 'values': ['kind-control-plane']}]}]
    assert values['datadog']['site'] == 'datadoghq.com'
    assert values['datadog']['dogstatsd']['useSocketVolume'] is False
    assert values['datadog']['operator']['enabled'] is False
    assert values['clusterAgent']['enabled'] is False
    assert Path(helm_call.kwargs['env']['HELM_CACHE_HOME']).parts[-2:] == ('helm', 'cache')

    assert [
        *prefix,
        'rollout',
        'status',
        f'daemonset/{agent._namespace}',
        '--namespace',
        agent._namespace,
        '--timeout=120s',
    ] in calls
    assert [
        *prefix,
        'cp',
        '--container',
        'agent',
        local_base.name,
        f'{agent._namespace}/{POD_NAME}:/home/datadog_checks_base',
    ] in calls
    pip_command = [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        f'pod/{POD_NAME}',
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
    ]
    assert pip_command in calls
    pip_call = next(call for call in run_command.call_args_list if call.args[0] == pip_command)
    assert pip_call.kwargs['stdout'] == subprocess.PIPE
    assert pip_call.kwargs['stderr'] == subprocess.STDOUT
    assert [
        *prefix,
        'cp',
        '--container',
        'agent',
        config_file.name,
        f'{agent._namespace}/{POD_NAME}:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    ] in calls
    assert [
        *prefix,
        'cp',
        '--container',
        'agent',
        auto_conf.name,
        f'{agent._namespace}/{POD_NAME}:/etc/datadog-agent/conf.d/velero.d/auto_conf.yaml',
    ] in calls
    assert [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        f'pod/{POD_NAME}',
        '--container',
        'agent',
        '--',
        'sh',
        '-c',
        RESTART_COMMAND,
    ] in calls
    assert [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        f'pod/{POD_NAME}',
        '--container',
        'agent',
        '--',
        'touch',
        '/home/.ddev-agent-prepared',
    ] in calls
    assert metadata['kubernetes']['_namespace_uid'] == 'namespace-uid'
    assert metadata['kubernetes']['local_packages'] == [
        {'path': str(local_base), 'name': 'datadog_checks_base', 'features': '[kube]'},
        {'path': str(integration), 'name': 'velero', 'features': '[deps]'},
    ]
    assert not any('clusterrole' in command or 'clusterrolebinding' in command for command in calls)
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

    def run(command, **kwargs):
        if command[:3] == ['helm', 'version', '--short']:
            return successful_process(command)
        return successful_process(command, stdout=json.dumps(nodes).encode())

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(NotImplementedError, match='exactly one schedulable node'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    assert command_calls(run_command) == [
        ['helm', 'version', '--short'],
        ['kubectl', '--kubeconfig', '/tmp/kubeconfig', 'get', 'nodes', '-o', 'json'],
    ]


def test_rejects_preexisting_namespace(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}

    def run(command, **kwargs):
        if command[:3] == ['helm', 'version', '--short']:
            return successful_process(command)
        if command[-4:] == ['get', 'nodes', '-o', 'json']:
            return successful_process(command, stdout=json.dumps(nodes).encode())
        if 'namespace' in command and '--ignore-not-found=true' in command:
            return successful_process(command, stdout=f'namespace/{agent._namespace}\n'.encode())
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='Refusing to overwrite Kubernetes resources'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    assert not any('create' in call.args[0] for call in run_command.call_args_list)


def test_rejects_stale_cluster_resources_before_creating_namespace(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}

    def run(command, **kwargs):
        if command[:3] == ['helm', 'version', '--short']:
            return successful_process(command)
        if command[-4:] == ['get', 'nodes', '-o', 'json']:
            return successful_process(command, stdout=json.dumps(nodes).encode())
        if f'clusterrole/{agent._namespace}' in command:
            return successful_process(
                command, stdout=f'clusterrole.rbac.authorization.k8s.io/{agent._namespace}\n'.encode()
            )
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='stale Kubernetes Agent cluster-scoped resources'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    assert not any('create' in call.args[0] for call in run_command.call_args_list)


def test_namespace_creation_remains_atomic(agent, app, mocker):
    nodes = {'items': [{'metadata': {'name': 'kind-control-plane'}, 'spec': {}}]}

    def run(command, **kwargs):
        if command[:3] == ['helm', 'version', '--short']:
            return successful_process(command)
        if command[-4:] == ['get', 'nodes', '-o', 'json']:
            return successful_process(command, stdout=json.dumps(nodes).encode())
        if command[-4:] == ['-f', '-', '-o', 'json']:
            return subprocess.CompletedProcess(command, 1, stdout=b'namespace already exists')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='Unable to create Kubernetes Agent namespace'):
        agent.start(agent_build='', local_packages={}, env_vars={})

    calls = command_calls(run_command)
    assert sum(command[-4:] == ['-f', '-', '-o', 'json'] for command in calls) == 1
    assert not any(command[:2] == ['helm', 'install'] for command in calls)


def test_invoke_synchronizes_config_and_environment(agent, config_file, auto_conf, run_command):
    config_file.write_text('instances:\n  - openmetrics_endpoint: http://velero:8085/metrics\n')

    agent.invoke(['check', 'velero', '--json'], env_vars={'ZED': 'last', 'ALPHA': 'first'})

    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    assert operational_calls(run_command) == [
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
            '--container',
            'agent',
            '--',
            'test',
            '-f',
            '/home/.ddev-agent-prepared',
        ],
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
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
            f'{agent._namespace}/{POD_NAME}:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
        ],
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
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
            f'{agent._namespace}/{POD_NAME}:/etc/datadog-agent/conf.d/velero.d/auto_conf.yaml',
        ],
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
            '--container',
            'agent',
            '--',
            'test',
            '-f',
            '/home/.ddev-agent-prepared',
        ],
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
            '--container',
            'agent',
            '--',
            'env',
            'ALPHA=first',
            'DD_LOG_LEVEL=off',
            'ZED=last',
            'agent',
            'check',
            'velero',
            '--json',
        ],
    ]


def test_invoke_reinstalls_after_daemonset_replaces_container(agent, metadata, temp_dir, app, mocker):
    local_package = temp_dir / 'velero-source'
    local_package.ensure_dir_exists()
    metadata['kubernetes']['local_packages'] = [
        {'path': str(local_package), 'name': 'velero-source', 'features': '[deps]'}
    ]
    metadata['start_commands'] = ['echo recovery-start']
    prepared = False

    def run(command, **kwargs):
        nonlocal prepared
        if 'get' in command and 'pods' in command:
            return successful_process(
                command, stdout=json.dumps({'items': [pod_data(name='replacement-agent')]}).encode()
            )
        if command[-3:] == ['test', '-f', '/home/.ddev-agent-prepared']:
            return successful_process(command) if prepared else subprocess.CompletedProcess(command, 1)
        if command[-2:] == ['touch', '/home/.ddev-agent-prepared']:
            prepared = True
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    agent.invoke(['status'])

    calls = command_calls(run_command)
    assert any('pip' in command and '/home/velero-source[deps]' in command for command in calls)
    marker_probes = [
        call for call in run_command.call_args_list if call.args[0][-3:] == ['test', '-f', '/home/.ddev-agent-prepared']
    ]
    assert marker_probes
    assert all(call.kwargs['stdout'] == subprocess.PIPE for call in marker_probes)
    recovery_start = next(
        call for call in run_command.call_args_list if call.args[0][-2:] == ['echo', 'recovery-start']
    )
    assert recovery_start.kwargs['stdout'] == subprocess.PIPE
    assert recovery_start.kwargs['stderr'] == subprocess.STDOUT
    assert any(command[-2:] == ['touch', '/home/.ddev-agent-prepared'] for command in calls)
    invoke = next(command for command in reversed(calls) if command[-2:] == ['agent', 'status'])
    assert 'pod/replacement-agent' in invoke


def test_invoke_retries_preparation_when_pod_changes_during_synchronization(agent, app, mocker):
    state = {'pod_queries': 0, 'replacement_prepared': False}

    def run(command, **kwargs):
        if 'get' in command and 'pods' in command:
            state['pod_queries'] += 1
            name = 'old-agent' if state['pod_queries'] == 1 else 'replacement-agent'
            return successful_process(command, stdout=json.dumps({'items': [pod_data(name=name)]}).encode())
        if command[-3:] == ['test', '-f', '/home/.ddev-agent-prepared']:
            if 'pod/old-agent' in command or state['replacement_prepared']:
                return successful_process(command)
            return subprocess.CompletedProcess(command, 1)
        if command[-2:] == ['touch', '/home/.ddev-agent-prepared']:
            state['replacement_prepared'] = True
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    agent.invoke(['status'])

    calls = command_calls(run_command)
    assert state['pod_queries'] == 5
    assert any(
        'pod/replacement-agent' in command and command[-2:] == ['touch', '/home/.ddev-agent-prepared']
        for command in calls
    )
    invoke = next(command for command in reversed(calls) if command[-2:] == ['agent', 'status'])
    assert 'pod/replacement-agent' in invoke


def test_invoke_waits_for_replacement_when_no_agent_pod_is_ready(agent, app, mocker):
    mocker.patch('ddev.e2e.agent.kubernetes_helm.time.sleep')
    pod_queries = 0

    def run(command, **kwargs):
        nonlocal pod_queries
        if 'get' in command and 'pods' in command:
            pod_queries += 1
            items = [] if pod_queries == 1 else [pod_data(name='replacement-agent')]
            return successful_process(command, stdout=json.dumps({'items': items}).encode())
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    agent.invoke(['status'])

    calls = command_calls(run_command)
    assert pod_queries == 3
    invoke = next(command for command in reversed(calls) if command[-2:] == ['agent', 'status'])
    assert 'pod/replacement-agent' in invoke


def test_invoke_removes_pod_config_when_host_config_is_absent(agent, config_file, run_command):
    config_file.remove()

    agent.invoke(['status'])

    assert [
        'kubectl',
        '--kubeconfig',
        '/tmp/kubeconfig',
        'exec',
        '--namespace',
        agent._namespace,
        f'pod/{POD_NAME}',
        '--container',
        'agent',
        '--',
        'rm',
        '-f',
        '/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    ] in command_calls(run_command)


def test_stop_is_idempotent_when_namespace_is_absent(agent, run_command):
    agent.stop()

    assert command_calls(run_command) == [
        [
            'kubectl',
            '--kubeconfig',
            '/tmp/kubeconfig',
            'get',
            'namespace',
            agent._namespace,
            '--ignore-not-found=true',
            '-o',
            'json',
        ],
        [
            'kubectl',
            '--kubeconfig',
            '/tmp/kubeconfig',
            'get',
            'clusterrole,clusterrolebinding',
            '--selector',
            'ddev.datadoghq.com/environment=test-owner',
            '-o',
            'name',
        ],
    ]


def test_stop_does_not_touch_another_environment_namespace(agent, app, mocker):
    namespace = {'metadata': {'labels': {'ddev.datadoghq.com/environment': 'another-owner'}}}

    def run(command, **kwargs):
        if 'namespace' in command:
            return successful_process(command, stdout=json.dumps(namespace).encode())
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    agent.stop()

    calls = command_calls(run_command)
    assert len(calls) == 2
    assert calls[0][-5:-3] == ['namespace', agent._namespace]
    assert not any(command[0] == 'helm' or 'delete' in command for command in calls)


def test_stop_preserves_state_when_namespace_is_missing_but_cluster_resources_remain(agent, app, mocker):
    def run(command, **kwargs):
        if 'clusterrole,clusterrolebinding' in command:
            return successful_process(
                command, stdout=f'clusterrole.rbac.authorization.k8s.io/{agent._namespace}\n'.encode()
            )
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='cluster-scoped resources remain'):
        agent.stop()

    calls = command_calls(run_command)
    assert not any(command[0] == 'helm' or 'delete' in command for command in calls)


def test_stop_revalidates_namespace_uid_before_helm_uninstall(agent, metadata, app, mocker):
    metadata['kubernetes']['_namespace_uid'] = 'owned-uid'
    namespace_queries = 0

    def run(command, **kwargs):
        nonlocal namespace_queries
        if command[-2:] == ['-o', 'json'] and 'namespace' in command:
            namespace_queries += 1
            uid = 'owned-uid' if namespace_queries == 1 else 'replacement-uid'
            namespace = {
                'metadata': {
                    'uid': uid,
                    'labels': {'ddev.datadoghq.com/environment': 'test-owner'},
                }
            }
            return successful_process(command, stdout=json.dumps(namespace).encode())
        if 'get' in command and 'pods' in command:
            return successful_process(command, stdout=b'{"items":[]}')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='ownership changed'):
        agent.stop()

    assert namespace_queries == 2
    assert not any(command[0] == 'helm' or 'delete' in command for command in command_calls(run_command))


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
        f'{agent._namespace}/{POD_NAME}:/home/velero-source',
    ]
    config_copy = [
        *prefix,
        'cp',
        '--container',
        'agent',
        config_file.name,
        f'{agent._namespace}/{POD_NAME}:/etc/datadog-agent/conf.d/velero.d/conf.yaml',
    ]
    restart = [
        *prefix,
        'exec',
        '--namespace',
        agent._namespace,
        f'pod/{POD_NAME}',
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


def test_stop_uninstalls_release_before_namespace(agent, app, mocker):
    namespace = {'metadata': {'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if command[-2:] == ['-o', 'json'] and 'namespace' in command:
            return successful_process(command, stdout=json.dumps(namespace).encode())
        if 'get' in command and 'pods' in command:
            return successful_process(command, stdout=json.dumps({'items': [pod_data()]}).encode())
        if command[:2] == ['helm', 'list']:
            return successful_process(command, stdout=b'[{"name":"ddev-agent"}]')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    agent.stop()

    calls = command_calls(run_command)
    uninstall = next(command for command in calls if command[:2] == ['helm', 'uninstall'])
    delete = next(command for command in calls if 'delete' in command)
    assert calls.index(uninstall) < calls.index(delete)
    assert not any('clusterrole' in command for command in calls)


def test_stop_runs_hook_in_selected_non_ready_pod(agent, app, mocker):
    agent.metadata['stop_commands'] = ['echo stopping']
    namespace = {'metadata': {'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if command[-2:] == ['-o', 'json'] and 'namespace' in command:
            return successful_process(command, stdout=json.dumps(namespace).encode())
        if 'get' in command and 'pods' in command:
            return successful_process(command, stdout=json.dumps({'items': [pod_data(ready=False)]}).encode())
        if command[:2] == ['helm', 'list']:
            return successful_process(command, stdout=b'[]')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    agent.stop()

    stop_hook = next(command for command in command_calls(run_command) if command[-2:] == ['echo', 'stopping'])
    assert f'pod/{POD_NAME}' in stop_hook


def test_stop_preserves_namespace_when_helm_uninstall_fails(agent, app, mocker):
    namespace = {'metadata': {'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if command[-2:] == ['-o', 'json'] and 'namespace' in command:
            return successful_process(command, stdout=json.dumps(namespace).encode())
        if 'get' in command and 'pods' in command:
            return successful_process(command, stdout=json.dumps({'items': []}).encode())
        if command[:2] == ['helm', 'list']:
            return successful_process(command, stdout=b'[{"name":"ddev-agent"}]')
        if command[:2] == ['helm', 'uninstall']:
            return subprocess.CompletedProcess(command, 1, stdout=b'helm failed')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='preserving the Helm release namespace'):
        agent.stop()

    calls = command_calls(run_command)
    assert any(command[:2] == ['helm', 'uninstall'] for command in calls)
    assert not any('delete' in command for command in calls)


def test_stop_cleans_resources_after_stop_command_failure(agent, app, mocker):
    agent.metadata['stop_commands'] = ['false']
    namespace = {'metadata': {'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if command[-2:] == ['-o', 'json'] and 'namespace' in command:
            return successful_process(command, stdout=json.dumps(namespace).encode())
        if 'get' in command and 'pods' in command:
            return successful_process(command, stdout=json.dumps({'items': [pod_data()]}).encode())
        if command[-1:] == ['false']:
            raise subprocess.CalledProcessError(1, command)
        if command[:2] == ['helm', 'list']:
            return successful_process(command, stdout=b'[]')
        return successful_process(command)

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='Errors while stopping Kubernetes Agent'):
        agent.stop()

    calls = command_calls(run_command)
    assert any('namespace' in command and 'delete' in command for command in calls)


def test_shell_and_logs_use_dynamically_selected_pod(agent, run_command):
    agent.enter_shell()
    agent.show_logs()

    calls = operational_calls(run_command)
    prefix = ['kubectl', '--kubeconfig', '/tmp/kubeconfig']
    assert calls == [
        [
            *prefix,
            'exec',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
            '--container',
            'agent',
            '--',
            'test',
            '-f',
            '/home/.ddev-agent-prepared',
        ],
        [
            *prefix,
            'exec',
            '-it',
            '--namespace',
            agent._namespace,
            f'pod/{POD_NAME}',
            '--container',
            'agent',
            '--',
            'bash',
        ],
        [*prefix, 'logs', '--namespace', agent._namespace, f'pod/{POD_NAME}', '--container', 'agent'],
    ]
    assert run_command.call_args_list[-1].kwargs['check'] is True


@pytest.mark.parametrize(
    'metadata, match',
    [
        ({}, 'must contain a `kubernetes` mapping'),
        ({'kubernetes': {}}, 'non-empty `kubeconfig`'),
        ({'kubernetes': {'kubeconfig': '/tmp/config', 'namespace': 'INVALID'}}, 'Invalid Kubernetes Agent namespace'),
        (
            {'kubernetes': {'kubeconfig': '/tmp/config', 'namespace': '1-invalid-service-name'}},
            'Invalid Kubernetes Agent namespace',
        ),
    ],
)
def test_metadata_validation(app, get_integration, config_file, metadata, match):
    agent = KubernetesAgent(app, get_integration('velero'), 'py3.12', metadata, config_file)
    with pytest.raises(ValueError, match=match):
        _ = agent._namespace if 'namespace' in metadata.get('kubernetes', {}) else agent._kubeconfig
