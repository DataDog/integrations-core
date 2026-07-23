# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import subprocess

import pytest

from ddev.e2e.agent.kubernetes_helm import AgentImage, HelmDaemonSetDeployment, parse_agent_image


def successful_process(command, *, stdout=b'', stderr=None):
    return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=stderr)


@pytest.fixture
def metadata():
    return {'pod_labels': {'purpose': 'discovery-e2e'}}


@pytest.fixture
def deployment(app, temp_dir, metadata):
    return HelmDaemonSetDeployment(
        platform=app.platform,
        kubeconfig='/tmp/kubeconfig',
        namespace='ddev-agent-velero-12345678',
        owner_id='test-owner',
        kubernetes_metadata=metadata,
        state_dir=temp_dir,
        wait_timeout=90,
    )


@pytest.mark.parametrize(
    'reference, expected',
    [
        (
            'registry.datadoghq.com/agent-dev:master-py3',
            AgentImage(repository='registry.datadoghq.com/agent-dev', tag='master-py3'),
        ),
        ('datadog/agent:7.81.1', AgentImage(repository='datadog/agent', tag='7.81.1')),
        (
            'localhost:5000/datadog-agent:test',
            AgentImage(repository='localhost:5000/datadog-agent', tag='test'),
        ),
        (
            f'registry.example.com/agent@sha256:{"a" * 64}',
            AgentImage(repository='registry.example.com/agent', digest=f'sha256:{"a" * 64}'),
        ),
    ],
)
def test_parse_agent_image(reference, expected):
    assert parse_agent_image(reference) == expected


@pytest.mark.parametrize(
    'reference',
    [
        '',
        'registry.example.com/agent',
        'registry.example.com/agent:',
        'registry.example.com/agent@sha256:not-hex',
        f'registry.example.com/agent@sha256:{"a" * 63}',
        'registry.example.com/agent:bad tag',
    ],
)
def test_parse_agent_image_rejects_invalid_references(reference):
    with pytest.raises(ValueError, match='image'):
        parse_agent_image(reference)


def test_values_disable_auxiliary_workloads_and_map_image_environment_and_labels(deployment, metadata):
    metadata['pod_labels']['ddev.datadoghq.com/environment'] = 'another-owner'
    metadata['pod_labels']['app.kubernetes.io/component'] = 'broken-selector'
    metadata['pod_labels']['app'] = 'broken-selector'
    metadata['image_pull_policy'] = 'Never'

    values = deployment.values(
        'localhost:5000/datadog-agent:test',
        {
            'DD_API_KEY': 'secret',
            'DD_SITE': 'datadoghq.eu',
            'DD_KUBELET_TLS_VERIFY': 'true',
            'DD_LOG_LEVEL': 'debug',
        },
        node_name='kind-control-plane',
    )

    assert values['fullnameOverride'] == deployment.namespace
    assert values['targetSystem'] == 'linux'
    assert values['commonLabels'] == {'ddev.datadoghq.com/environment': 'test-owner'}
    assert values['clusterAgent'] == {
        'enabled': False,
        'admissionController': {'enabled': False},
    }
    assert values['agents']['enabled'] is True
    assert values['agents']['instanceLabelOverride'] == 'test-owner'
    assert values['agents']['image'] == {
        'repository': 'localhost:5000/datadog-agent',
        'tag': 'test',
        'doNotCheckTag': True,
        'pullPolicy': 'Never',
    }
    assert values['agents']['podLabels'] == {
        'purpose': 'discovery-e2e',
        'ddev.datadoghq.com/environment': 'test-owner',
        'app.kubernetes.io/component': 'agent',
        'app': deployment.namespace,
    }
    assert values['agents']['tolerations'] == [{'operator': 'Exists'}]
    assert values['agents']['affinity'] == {
        'nodeAffinity': {
            'requiredDuringSchedulingIgnoredDuringExecution': {
                'nodeSelectorTerms': [
                    {
                        'matchFields': [
                            {
                                'key': 'metadata.name',
                                'operator': 'In',
                                'values': ['kind-control-plane'],
                            }
                        ]
                    }
                ]
            }
        }
    }

    datadog = values['datadog']
    assert datadog['apiKey'] == 'secret'
    assert datadog['site'] == 'datadoghq.eu'
    assert datadog['logLevel'] == 'debug'
    assert datadog['kubelet']['tlsVerify'] is True
    for feature in (
        datadog['clusterChecks'],
        datadog['kubeStateMetricsCore'],
        datadog['logs'],
        datadog['orchestratorExplorer'],
        datadog['operator'],
        datadog['remoteConfiguration'],
    ):
        assert feature['enabled'] is False
    assert datadog['collectEvents'] is False
    assert datadog['leaderElection'] is False
    assert datadog['useHostPID'] is False
    assert datadog['apm'] == {'socketEnabled': False, 'portEnabled': False}
    assert datadog['processAgent'] == {
        'enabled': False,
        'processCollection': False,
        'processDiscovery': False,
        'containerCollection': False,
    }
    assert datadog['dogstatsd'] == {
        'port': 8125,
        'useSocketVolume': False,
        'nonLocalTraffic': True,
        'originDetection': False,
        'tagCardinality': 'low',
    }
    assert datadog['expvarPort'] == 5000
    assert datadog['containerLifecycle']['enabled'] is False
    assert datadog['discovery'] == {'enabled': False, 'networkStats': {'enabled': False}}

    assert values['agents']['containers']['agent']['command'] == ['/bin/entrypoint.sh']
    agent_container = values['agents']['containers']['agent']
    assert agent_container['securityContext'] == {'readOnlyRootFilesystem': False}
    local_probe = {
        'exec': {'command': ['/bin/true']},
        'initialDelaySeconds': 0,
        'periodSeconds': 1,
        'timeoutSeconds': 1,
        'successThreshold': 1,
        'failureThreshold': 3,
    }
    for probe in ('livenessProbe', 'readinessProbe', 'startupProbe'):
        assert agent_container[probe] == local_probe
    env = {item['name']: item['value'] for item in agent_container['env']}
    assert env == {'DD_AUTOCONFIG_FROM_ENVIRONMENT': 'true'}
    for chart_mapped_name in ('DD_API_KEY', 'DD_SITE', 'DD_KUBELET_TLS_VERIFY', 'DD_APM_ENABLED', 'DD_LOG_LEVEL'):
        assert chart_mapped_name not in env
    for chart_generated_name in ('DD_HOSTNAME', 'DD_KUBERNETES_KUBELET_HOST', 'DD_KUBERNETES_KUBELET_NODENAME'):
        assert chart_generated_name not in env


def test_values_map_digest_reference(deployment):
    digest = f'sha256:{"b" * 64}'

    values = deployment.values(f'registry.example.com/agent@{digest}', {}, node_name='kind-control-plane')

    assert values['agents']['image'] == {
        'repository': 'registry.example.com/agent',
        'digest': digest,
        'doNotCheckTag': True,
        'pullPolicy': 'Always',
    }


@pytest.mark.parametrize(
    'metadata_update, env_vars, match',
    [
        ({'pod_labels': []}, {}, 'pod_labels'),
        ({'image_pull_policy': 'Sometimes'}, {}, 'image_pull_policy'),
        ({}, {'DD_KUBELET_TLS_VERIFY': 'maybe'}, 'DD_KUBELET_TLS_VERIFY'),
        ({}, {'DD_APM_ENABLED': 'true'}, 'must remain false'),
        ({}, {'DD_LOGS_ENABLED': 'true'}, 'log collection'),
        ({}, {'DD_APM_RECEIVER_PORT': '8127'}, 'managed by the Helm chart'),
    ],
)
def test_values_validate_metadata_before_install(deployment, metadata, metadata_update, env_vars, match):
    metadata.update(metadata_update)

    with pytest.raises(ValueError, match=match):
        deployment.values('registry.example.com/agent:test', env_vars, node_name='kind-control-plane')


def test_helm_environment_is_isolated_under_environment_state(deployment, temp_dir):
    environment = deployment.helm_environment

    assert environment['HELM_CACHE_HOME'] == str(temp_dir / 'helm' / 'cache')
    assert environment['HELM_CONFIG_HOME'] == str(temp_dir / 'helm' / 'config')
    assert environment['HELM_DATA_HOME'] == str(temp_dir / 'helm' / 'data')
    assert all((temp_dir / 'helm' / directory).is_dir() for directory in ('cache', 'config', 'data'))


def test_check_helm_reports_missing_executable(deployment, app, mocker):
    mocker.patch.object(app.platform, 'run_command', side_effect=FileNotFoundError('helm'))

    with pytest.raises(RuntimeError, match='requires the `helm` executable'):
        deployment.check_helm()


def test_agent_pod_selects_ready_owned_agent_and_ignores_terminating_pod(deployment, app, mocker):
    pods = {
        'items': [
            {
                'metadata': {'name': 'old-agent', 'uid': 'old', 'deletionTimestamp': 'now'},
                'spec': {'nodeName': 'kind-control-plane', 'containers': [{'name': 'agent'}]},
                'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]},
            },
            {
                'metadata': {'name': 'new-agent', 'uid': 'new'},
                'spec': {'nodeName': 'kind-control-plane', 'containers': [{'name': 'agent'}]},
                'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]},
            },
        ]
    }
    run_command = mocker.patch.object(
        app.platform,
        'run_command',
        return_value=successful_process([], stdout=json.dumps(pods).encode()),
    )

    pod = deployment.agent_pod()

    assert pod.name == 'new-agent'
    assert pod.uid == 'new'
    assert pod.node_name == 'kind-control-plane'
    command = run_command.call_args.args[0]
    assert command == [
        'kubectl',
        '--kubeconfig',
        '/tmp/kubeconfig',
        'get',
        'pods',
        '--namespace',
        deployment.namespace,
        '--selector',
        'app.kubernetes.io/component=agent,ddev.datadoghq.com/environment=test-owner',
        '-o',
        'json',
    ]


@pytest.mark.parametrize(
    'items, ready, expected_count',
    [
        ([], True, 0),
        (
            [
                {
                    'metadata': {'name': 'unready', 'uid': 'one'},
                    'spec': {'nodeName': 'kind-control-plane', 'containers': [{'name': 'agent'}]},
                    'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'False'}]},
                }
            ],
            True,
            0,
        ),
        (
            [
                {
                    'metadata': {'name': name, 'uid': name},
                    'spec': {'nodeName': 'kind-control-plane', 'containers': [{'name': 'agent'}]},
                    'status': {'phase': 'Running', 'conditions': [{'type': 'Ready', 'status': 'True'}]},
                }
                for name in ('one', 'two')
            ],
            True,
            2,
        ),
    ],
)
def test_agent_pod_rejects_zero_or_multiple_candidates(deployment, app, mocker, items, ready, expected_count):
    mocker.patch.object(
        app.platform,
        'run_command',
        return_value=successful_process([], stdout=json.dumps({'items': items}).encode()),
    )

    with pytest.raises(RuntimeError, match=rf'found {expected_count}'):
        deployment.agent_pod(ready=ready)


def test_uninstall_skips_missing_release_without_status_preflight(deployment, app, mocker):
    namespace = {'metadata': {'uid': 'namespace-uid', 'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if (
            'clusterrole,clusterrolebinding' in command
            or 'all,secret,configmap,serviceaccount,role,rolebinding' in command
        ):
            return successful_process(command)
        if command[0] == 'kubectl':
            return successful_process(command, stdout=json.dumps(namespace).encode())
        return subprocess.CompletedProcess(command, 1, stdout=b'Error: release: not found')

    run_command = mocker.patch.object(app.platform, 'run_command', side_effect=run)

    deployment.uninstall()

    assert len(run_command.call_args_list) == 4
    assert any(call.args[0][:2] == ['helm', 'uninstall'] for call in run_command.call_args_list)


def test_uninstall_preserves_state_when_release_metadata_is_missing_but_cluster_resources_remain(
    deployment, app, mocker
):
    namespace = {'metadata': {'uid': 'namespace-uid', 'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if 'clusterrole,clusterrolebinding' in command:
            return successful_process(command, stdout=b'clusterrole.rbac.authorization.k8s.io/ddev-agent')
        if command[0] == 'kubectl':
            return successful_process(command, stdout=json.dumps(namespace).encode())
        return subprocess.CompletedProcess(command, 1, stdout=b'Error: release: not found')

    mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='release metadata is missing'):
        deployment.uninstall()


def test_uninstall_preserves_state_when_release_metadata_is_missing_but_namespaced_resources_remain(
    deployment, app, mocker
):
    namespace = {'metadata': {'uid': 'namespace-uid', 'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if 'clusterrole,clusterrolebinding' in command:
            return successful_process(command)
        if 'all,secret,configmap,serviceaccount,role,rolebinding' in command:
            return successful_process(command, stdout=b'service/ddev-agent')
        if command[0] == 'kubectl':
            return successful_process(command, stdout=json.dumps(namespace).encode())
        return subprocess.CompletedProcess(command, 1, stdout=b'Error: release: not found')

    mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='release metadata is missing'):
        deployment.uninstall()


def test_uninstall_reports_non_missing_release_error(deployment, app, mocker):
    namespace = {'metadata': {'uid': 'namespace-uid', 'labels': {'ddev.datadoghq.com/environment': 'test-owner'}}}

    def run(command, **kwargs):
        if command[0] == 'kubectl':
            return successful_process(command, stdout=json.dumps(namespace).encode())
        return subprocess.CompletedProcess(command, 1, stdout=b'Kubernetes API unavailable')

    mocker.patch.object(app.platform, 'run_command', side_effect=run)

    with pytest.raises(RuntimeError, match='Unable to uninstall Kubernetes Agent Helm release'):
        deployment.uninstall()
