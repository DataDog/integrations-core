# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from contextlib import nullcontext

import mock
import pytest
import yaml

from datadog_checks.dev.kube_discovery import (
    AGENT_POD_NAME,
    DISCOVERY_NAMESPACE,
    assert_all_discovery_candidates_stable_kubernetes,
    assert_pod_stable,
    build_check_archive,
    build_service_from_pod,
    find_local_base_root,
    run_discovery_check_kubernetes,
    save_state,
    setup_discovery_agent,
)


def result(stdout='', stderr='', code=0):
    return mock.Mock(stdout=stdout, stderr=stderr, code=code)


def pod_state(
    *, uid='pod-uid', phase='Running', restart_count=0, ready=True, terminated_reason=None, pod_ip='10.0.0.5'
):
    last_state = {}
    if terminated_reason is not None:
        last_state = {'terminated': {'reason': terminated_reason}}

    return {
        'metadata': {'uid': uid, 'name': 'workload'},
        'spec': {'containers': [{'name': 'workload', 'ports': [{'containerPort': 8080, 'name': 'metrics'}]}]},
        'status': {
            'phase': phase,
            'podIP': pod_ip,
            'containerStatuses': [
                {'name': 'workload', 'restartCount': restart_count, 'ready': ready, 'lastState': last_state}
            ],
        },
    }


def write_auto_conf(check_root):
    check_name = os.path.basename(check_root)
    data_dir = os.path.join(check_root, 'datadog_checks', check_name, 'data')
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, 'auto_conf.yaml'), 'w', encoding='utf-8') as f:
        f.write('ad_identifiers:\n  - test\ndiscovery: {}\ninit_config:\ninstances: []\n')


def seed_kube_discovery_state(kubeconfig_path, *, namespace=DISCOVERY_NAMESPACE):
    save_state('kube_discovery', {'kubeconfig_path': kubeconfig_path, 'namespace': namespace})


@pytest.fixture(autouse=True)
def clear_kube_discovery_state(monkeypatch):
    monkeypatch.delenv('DDEV_E2E_ENV_kube_discovery', raising=False)


@pytest.fixture
def e2e_mode(monkeypatch):
    monkeypatch.setenv('DDEV_E2E_PARENT_PYTHON', '/usr/bin/python3')


def test_get_kube_discovery_state_missing_raises():
    from datadog_checks.dev.kube_discovery import get_kube_discovery_state

    with pytest.raises(AssertionError, match='No kube_discovery state found'):
        get_kube_discovery_state()


class TestSetupDiscoveryAgent:
    def test_is_noop_when_setup_disabled(self, monkeypatch):
        monkeypatch.setenv('DDEV_E2E_UP', 'false')

        with mock.patch('datadog_checks.dev.kube_discovery.run_command') as run_command:
            # env test/env stop re-run this fixture body to reach kind_run's teardown, but must not
            # re-apply manifests against a KUBECONFIG that isn't guaranteed to point at a live cluster.
            setup_discovery_agent('/tmp/kubeconfig')

        run_command.assert_not_called()

        from datadog_checks.dev.kube_discovery import get_kube_discovery_state

        with pytest.raises(AssertionError, match='No kube_discovery state found'):
            get_kube_discovery_state()

    def test_persists_kube_discovery_state(self, tmp_path):
        check_root = tmp_path / 'test_check'
        write_auto_conf(check_root)

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', return_value=result()):
            setup_discovery_agent('/tmp/kubeconfig', check_root=str(check_root))

        from datadog_checks.dev.kube_discovery import get_kube_discovery_state

        assert get_kube_discovery_state() == {'kubeconfig_path': '/tmp/kubeconfig', 'namespace': DISCOVERY_NAMESPACE}

    def test_applies_manifests_and_installs_package(self, tmp_path):
        check_root = tmp_path / 'test_check'
        write_auto_conf(check_root)

        applied_docs = []
        commands = []

        def fake_run_command(command, **kwargs):
            commands.append(command)
            if command[:2] == ['kubectl', 'apply']:
                manifest_path = command[3]
                with open(manifest_path, encoding='utf-8') as f:
                    applied_docs.append(list(yaml.safe_load_all(f)))
                return result()
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            setup_discovery_agent('/tmp/kubeconfig', check_root=str(check_root))

        # Wiring invariant: everything the pod mounts (RBAC, secret, configmap) is applied before the pod
        # itself. The field-level contents of each manifest are static data validated by the E2E run, not here.
        kinds = [[doc['kind'] for doc in docs] for docs in applied_docs]
        assert kinds == [
            ['Namespace', 'ServiceAccount', 'ClusterRole', 'ClusterRoleBinding'],
            ['Secret'],
            ['ConfigMap'],
            ['Pod'],
        ]

        # The check's own auto_conf.yaml must be read from disk and embedded, not hardcoded.
        configmap = applied_docs[2][0]
        assert 'ad_identifiers' in configmap['data']['auto_conf.yaml']

        assert [
            'kubectl',
            'wait',
            'pod',
            AGENT_POD_NAME,
            '-n',
            DISCOVERY_NAMESPACE,
            '--for=condition=Ready',
            '--timeout=120s',
        ] in commands

        cp_commands = [c for c in commands if c[:2] == ['kubectl', 'cp']]
        assert len(cp_commands) == 1
        assert cp_commands[0][3] == f'{DISCOVERY_NAMESPACE}/{AGENT_POD_NAME}:/tmp/test_check.tar.gz'

        exec_commands = [c for c in commands if c[:2] == ['kubectl', 'exec']]
        assert exec_commands[0][-1].startswith('mkdir -p /home/test_check')
        assert exec_commands[1][-6:] == [
            '-m',
            'pip',
            'install',
            '--disable-pip-version-check',
            '-e',
            '/home/test_check[deps]',
        ]

    def test_installs_local_base_before_package_when_available(self, tmp_path):
        check_root = tmp_path / 'test_check'
        base_root = tmp_path / 'datadog_checks_base'
        write_auto_conf(check_root)
        (base_root / 'datadog_checks' / 'base').mkdir(parents=True)
        (base_root / 'datadog_checks' / 'base' / '__init__.py').write_text('')

        commands = []

        def fake_run_command(command, **kwargs):
            commands.append(command)
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            setup_discovery_agent('/tmp/kubeconfig', check_root=str(check_root))

        cp_commands = [c for c in commands if c[:2] == ['kubectl', 'cp']]
        assert cp_commands[0][3] == f'{DISCOVERY_NAMESPACE}/{AGENT_POD_NAME}:/tmp/datadog_checks_base.tar.gz'
        assert cp_commands[1][3] == f'{DISCOVERY_NAMESPACE}/{AGENT_POD_NAME}:/tmp/test_check.tar.gz'

        pip_commands = [c for c in commands if c[:3] == ['kubectl', 'exec', AGENT_POD_NAME] and '-m' in c]
        assert pip_commands[0][-7:] == [
            '-m',
            'pip',
            'install',
            '--disable-pip-version-check',
            '--no-deps',
            '-e',
            '/home/datadog_checks_base',
        ]
        assert pip_commands[1][-6:] == [
            '-m',
            'pip',
            'install',
            '--disable-pip-version-check',
            '-e',
            '/home/test_check[deps]',
        ]

    def test_kubectl_calls_use_explicit_kubeconfig_env(self, tmp_path, monkeypatch):
        check_root = tmp_path / 'test_check'
        write_auto_conf(check_root)
        monkeypatch.setenv('KUBECONFIG', '/some/ambient/config')

        seen_envs = []

        def fake_run_command(command, **kwargs):
            seen_envs.append(kwargs.get('env'))
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            setup_discovery_agent('/tmp/kubeconfig', check_root=str(check_root))

        assert all(env['KUBECONFIG'] == '/tmp/kubeconfig' for env in seen_envs)


def test_find_local_base_root_returns_sibling_checkout(tmp_path):
    check_root = tmp_path / 'test_check'
    base_root = tmp_path / 'datadog_checks_base'
    base_root.mkdir()

    assert find_local_base_root(str(check_root)) == str(base_root)


def test_find_local_base_root_returns_none_without_sibling_checkout(tmp_path):
    assert find_local_base_root(str(tmp_path / 'test_check')) is None


class TestBuildCheckArchive:
    def test_excludes_vcs_and_cache_dirs(self, tmp_path):
        check_root = tmp_path / 'test_check'
        (check_root / '.git').mkdir(parents=True)
        (check_root / '.git' / 'config').write_text('data')
        (check_root / '.tox').mkdir()
        (check_root / '.tox' / 'thing').write_text('data')
        (check_root / 'datadog_checks').mkdir()
        (check_root / 'datadog_checks' / 'test_check.py').write_text('data')

        archive_path = tmp_path / 'archive.tar.gz'
        build_check_archive(str(check_root), str(archive_path))

        import tarfile

        with tarfile.open(archive_path) as tar:
            names = tar.getnames()

        assert any('datadog_checks/test_check.py' in name for name in names)
        assert not any('.git' in name for name in names)
        assert not any('.tox' in name for name in names)


class TestBuildServiceFromPod:
    def test_collapses_duplicate_ports_across_containers(self):
        pod = {
            'status': {'podIP': '10.0.0.9'},
            'spec': {
                'containers': [
                    {'name': 'a', 'ports': [{'containerPort': 8080, 'name': 'metrics'}, {'containerPort': 9090}]},
                    {'name': 'b', 'ports': [{'containerPort': 8080, 'name': 'dup'}]},
                ]
            },
        }

        service = build_service_from_pod(pod, 'svc')

        assert service.id == 'svc'
        assert service.host == '10.0.0.9'
        # 8080 collapses to its first occurrence; the unnamed 9090 keeps an empty name.
        assert [(port.number, port.name) for port in service.ports] == [(8080, 'metrics'), (9090, '')]

    def test_container_without_ports(self):
        pod = {'status': {'podIP': '10.0.0.9'}, 'spec': {'containers': [{'name': 'a'}]}}

        service = build_service_from_pod(pod, 'svc')

        assert service.ports == ()


class TestRunDiscoveryCheckKubernetes:
    def test_skips_outside_e2e(self, monkeypatch):
        monkeypatch.delenv('DDEV_E2E_PARENT_PYTHON', raising=False)

        with pytest.raises(pytest.skip.Exception, match='Not running E2E tests'):
            run_discovery_check_kubernetes(mock.Mock(), mock.Mock())

    def test_missing_state_raises(self, e2e_mode):
        with pytest.raises(AssertionError, match='No kube_discovery state found'):
            run_discovery_check_kubernetes(mock.Mock(), mock.Mock())

    def test_replays_collector_output(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig', namespace='dd-agent-discovery')

        collector = {
            'aggregator': {'metrics': [], 'service_checks': []},
            'runner': {'CheckID': 'test:1', 'CheckName': 'test'},
        }
        stdout = 'preamble\n[ {}\n{}\n]\n'.format('', json.dumps(collector))

        commands = []

        def fake_run_command(command, **kwargs):
            commands.append(command)
            return result(stdout=stdout)

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            with mock.patch('datadog_checks.dev.kube_discovery.find_check_root', return_value='/root/test_check'):
                run_discovery_check_kubernetes(mock.Mock(), mock.Mock())

        exec_command = commands[0]
        assert exec_command[:6] == ['kubectl', 'exec', AGENT_POD_NAME, '-n', 'dd-agent-discovery', '--']
        assert exec_command[6:] == [
            'agent',
            'check',
            'test_check',
            '--discovery-min-instances',
            '1',
            '--discovery-timeout',
            '30',
            '--json',
        ]

    def test_no_json_output_raises(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', return_value=result(stdout='no json here')):
            with mock.patch('datadog_checks.dev.kube_discovery.find_check_root', return_value='/root/test_check'):
                with pytest.raises(ValueError, match='Could not find valid check output'):
                    run_discovery_check_kubernetes(mock.Mock(), mock.Mock())

    def test_malformed_json_output_raises(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        stdout = 'preamble\n[ not valid json\n]\n'

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', return_value=result(stdout=stdout)):
            with mock.patch('datadog_checks.dev.kube_discovery.find_check_root', return_value='/root/test_check'):
                with pytest.raises(ValueError, match='Error loading json'):
                    run_discovery_check_kubernetes(mock.Mock(), mock.Mock())


class TestAssertAllDiscoveryCandidatesStableKubernetes:
    def test_skips_outside_e2e(self, monkeypatch):
        monkeypatch.delenv('DDEV_E2E_PARENT_PYTHON', raising=False)

        with pytest.raises(pytest.skip.Exception, match='Not running E2E tests'):
            assert_all_discovery_candidates_stable_kubernetes(
                mock.Mock(), mock.Mock(), mock.Mock(), namespace='keda', pod_name='workload'
            )

    def test_requires_pod_name_or_selector(self):
        seed_kube_discovery_state('/tmp/kubeconfig')

        with pytest.raises(TypeError, match='pod_name or pod_selector'):
            assert_all_discovery_candidates_stable_kubernetes(mock.Mock(), mock.Mock(), mock.Mock(), namespace='keda')

    def test_probes_generated_candidates_and_detects_restart(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        class DiscoveryCheck:
            service = None

            @classmethod
            def generate_configs(cls, service):
                cls.service = service
                for port in service.ports:
                    yield {'instances': [{'openmetrics_endpoint': f'http://{service.host}:{port.number}/metrics'}]}

        pod_states = iter([pod_state(restart_count=0), pod_state(restart_count=1)])

        def fake_run_command(command, **kwargs):
            if command[:3] == ['kubectl', 'get', 'pod']:
                return result(stdout=json.dumps(next(pod_states)))
            if command[:2] == ['kubectl', 'logs']:
                return result(stdout='ready\n')
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            with mock.patch('datadog_checks.dev.kube_discovery.find_check_root', return_value='/root/keda'):
                with pytest.raises(AssertionError, match='restart count changed'):
                    assert_all_discovery_candidates_stable_kubernetes(
                        DiscoveryCheck,
                        mock.Mock(),
                        mock.Mock(),
                        namespace='keda',
                        pod_name='workload',
                    )

        assert DiscoveryCheck.service.host == '10.0.0.5'
        assert [port.number for port in DiscoveryCheck.service.ports] == [8080]

    def test_no_candidates_raises(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        class DiscoveryCheck:
            @classmethod
            def generate_configs(cls, service):
                return iter(())

        def fake_run_command(command, **kwargs):
            if command[:3] == ['kubectl', 'get', 'pod']:
                return result(stdout=json.dumps(pod_state()))
            if command[:2] == ['kubectl', 'logs']:
                return result(stdout='ready\n')
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            with pytest.raises(AssertionError, match='No discovery candidates generated'):
                assert_all_discovery_candidates_stable_kubernetes(
                    DiscoveryCheck, mock.Mock(), mock.Mock(), namespace='keda', pod_name='workload'
                )

    def test_resolves_pod_via_selector(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        class DiscoveryCheck:
            @classmethod
            def generate_configs(cls, service):
                return iter(())

        commands = []

        def fake_run_command(command, **kwargs):
            commands.append(command)
            if command[:3] == ['kubectl', 'get', 'pods']:
                return result(stdout='workload-abc123')
            if command[:3] == ['kubectl', 'get', 'pod']:
                return result(stdout=json.dumps(pod_state()))
            if command[:2] == ['kubectl', 'logs']:
                return result(stdout='ready\n')
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            with pytest.raises(AssertionError, match='No discovery candidates generated'):
                assert_all_discovery_candidates_stable_kubernetes(
                    DiscoveryCheck, mock.Mock(), mock.Mock(), namespace='keda', pod_selector='app=workload'
                )

        selector_command = commands[0]
        assert selector_command[:6] == ['kubectl', 'get', 'pods', '-n', 'keda', '-l']
        assert selector_command[6] == 'app=workload'

    def test_detects_dangerous_log_output(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        class DiscoveryCheck:
            @classmethod
            def generate_configs(cls, service):
                yield {'instances': [{'openmetrics_endpoint': f'http://{service.host}:8080/metrics'}]}

        # A dangerous pattern appears only in the logs emitted after the baseline was captured.
        logs = iter(['ready\n', 'ready\npanic: something exploded\n'])

        def fake_run_command(command, **kwargs):
            if command[:3] == ['kubectl', 'get', 'pod']:
                return result(stdout=json.dumps(pod_state()))
            if command[:2] == ['kubectl', 'logs']:
                return result(stdout=next(logs))
            return result()

        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            with mock.patch('datadog_checks.dev.kube_discovery.find_check_root', return_value='/root/keda'):
                with pytest.raises(AssertionError, match=r"matched 'panic'"):
                    assert_all_discovery_candidates_stable_kubernetes(
                        DiscoveryCheck,
                        mock.Mock(),
                        mock.Mock(),
                        namespace='keda',
                        pod_name='workload',
                    )

    def test_probe_failure_still_checks_stability(self, e2e_mode):
        seed_kube_discovery_state('/tmp/kubeconfig')

        class DiscoveryCheck:
            @classmethod
            def generate_configs(cls, service):
                yield {'instances': [{'openmetrics_endpoint': f'http://{service.host}:8080/metrics'}]}

        pod_states = iter([pod_state(restart_count=0), pod_state(restart_count=1)])

        def fake_run_command(command, **kwargs):
            if command[:3] == ['kubectl', 'get', 'pod']:
                return result(stdout=json.dumps(next(pod_states)))
            if command[:2] == ['kubectl', 'logs']:
                return result(stdout='ready\n')
            return result()

        # A probe that raises must not abort the sweep: the pod restart is still caught afterwards. If the
        # except branch were gone, this would surface the RuntimeError instead of the restart AssertionError.
        with mock.patch('datadog_checks.dev.kube_discovery.run_command', side_effect=fake_run_command):
            with mock.patch('datadog_checks.dev.kube_discovery.find_check_root', return_value='/root/keda'):
                with mock.patch(
                    'datadog_checks.dev.kube_discovery.probe_candidate',
                    side_effect=RuntimeError('probe blew up'),
                ):
                    with pytest.raises(AssertionError, match='restart count changed'):
                        assert_all_discovery_candidates_stable_kubernetes(
                            DiscoveryCheck,
                            mock.Mock(),
                            mock.Mock(),
                            namespace='keda',
                            pod_name='workload',
                        )


class TestAssertPodStable:
    @pytest.mark.parametrize(
        ('initial', 'current', 'expectation'),
        [
            pytest.param(
                pod_state(uid='a'),
                pod_state(uid='b'),
                pytest.raises(AssertionError, match='Pod changed'),
                id='uid_change',
            ),
            pytest.param(
                pod_state(),
                pod_state(phase='Pending'),
                pytest.raises(AssertionError, match="Pod phase is 'Pending'"),
                id='not_running',
            ),
            pytest.param(
                pod_state(restart_count=0),
                pod_state(restart_count=1),
                pytest.raises(AssertionError, match='restart count changed'),
                id='restart',
            ),
            pytest.param(
                pod_state(),
                pod_state(ready=False),
                pytest.raises(AssertionError, match='is not ready'),
                id='not_ready',
            ),
            pytest.param(
                pod_state(),
                pod_state(terminated_reason='OOMKilled'),
                pytest.raises(AssertionError, match='OOMKilled'),
                id='oom_killed',
            ),
            pytest.param(
                pod_state(restart_count=1, terminated_reason='OOMKilled'),
                pod_state(restart_count=1, terminated_reason='OOMKilled'),
                nullcontext(),
                id='pre_existing_oom_killed',
            ),
            pytest.param(pod_state(), pod_state(), nullcontext(), id='stable'),
        ],
    )
    def test_assert_pod_stable(self, initial, current, expectation):
        with expectation:
            assert_pod_stable(initial, current, 1)
