# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Kubernetes/Kubelet Autodiscovery e2e helpers, parallel to :mod:`.docker`.

Exercises real Kubelet Autodiscovery inside a ``kind`` cluster by running ``agent check`` through
``kubectl exec`` against a sleeping, RBAC-scoped Agent pod, rather than a normal long-running Agent.
There is no Kubernetes equivalent of ``mount_logs``/``shared_logs()`` here: there is no host
bind-mount channel into a cluster pod.

The agent pod is pinned to its own node (see the ``DD_KUBERNETES_KUBELET_HOST``/``NODENAME`` env
vars in ``build_agent_pod_manifest``), matching real Kubelet-AD semantics: it only sees pods
scheduled on that same node. This assumes a single-node ``kind`` cluster, or that discovery targets
are pinned to the same node as the agent pod.
"""

import json
import logging
import os
import secrets
import tarfile
import tempfile
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from ._env import (
    e2e_testing,
    find_collector_blobs,
    flags_to_argv,
    format_config,
    get_state,
    replay_check_run,
    save_state,
    set_up_env,
)
from .docker import CONTAINER_STABILITY_LOG_PATTERNS, assert_no_new_log_patterns
from .subprocess import run_command
from .utils import find_check_root

DISCOVERY_NAMESPACE = 'dd-agent-discovery'
AGENT_POD_NAME = 'dd-agent-discovery'
AGENT_SERVICE_ACCOUNT = 'dd-agent-discovery'
AGENT_CLUSTER_ROLE = 'dd-agent-discovery'
AGENT_CLUSTER_ROLE_BINDING = 'dd-agent-discovery'
AGENT_IPC_SECRET = 'dd-agent-discovery-ipc'
AGENT_AUTO_CONF_CONFIGMAP = 'dd-agent-discovery-auto-conf'
DEFAULT_AGENT_IMAGE = 'registry.datadoghq.com/agent-dev:master-py3'
AGENT_PYTHON_PATH = '/opt/datadog-agent/embedded/bin/python3'
AGENT_PACKAGE_MOUNT_DIR = '/home'
AGENT_AUTH_TOKEN_PATH = '/etc/datadog-agent/auth_token'
AGENT_IPC_CERT_PATH = '/etc/datadog-agent/ipc_cert.pem'
FAKE_API_KEY = 'a' * 32
EXCLUDED_ARCHIVE_DIR_NAMES = frozenset({'.git', '.tox', '__pycache__', '.cache', '.mypy_cache', '.pytest_cache'})


def save_kube_discovery_state(kubeconfig_path: str | os.PathLike[str], *, namespace: str = DISCOVERY_NAMESPACE) -> None:
    """Persist the kubeconfig path and agent namespace from the setup process to the test process.

    A no-op outside the actual environment setup pass (``env test``/``env stop`` re-run the fixture
    body to reach ``kind_run``'s teardown, but must not re-derive or overwrite this state).
    """
    if not set_up_env():
        return

    save_state('kube_discovery', {'kubeconfig_path': os.fspath(kubeconfig_path), 'namespace': namespace})


def setup_discovery_agent(
    kubeconfig_path: str | os.PathLike[str],
    *,
    check_root: str | os.PathLike[str] | None = None,
    namespace: str = DISCOVERY_NAMESPACE,
    agent_image: str = DEFAULT_AGENT_IMAGE,
    extra_cluster_roles: Sequence[str] = (),
) -> None:
    """Deploy a sleeping, RBAC-scoped Agent pod that ``run_discovery_check_kubernetes`` can exec into.

    Call this inside the integration's existing ``kind_run(...)`` block, while ``KUBECONFIG`` still
    points at the freshly created cluster. A no-op outside the actual environment setup pass, matching
    how ``KindUp``/``ComposeFileUp``/``PortForwardUp`` behave: ``env test``/``env stop`` re-run the
    fixture body to reach ``kind_run``'s teardown, but ``KUBECONFIG`` isn't guaranteed to resolve to a
    live cluster at that point.

    ``extra_cluster_roles`` binds additional, already-existing ``ClusterRole``\\ s (e.g. a
    CRD-provided ``view`` role like KubeVirt's ``kubevirt.io:view``) to the agent's service account,
    for checks whose production setup docs require binding such a role to the real ``datadog-agent``
    service account.
    """
    if not set_up_env():
        return

    check_root = os.fspath(check_root or find_check_root(depth=1))
    check_name = os.path.basename(check_root)

    # The pod stays asleep; tests exec one-shot Agent commands into it after setup.
    with tempfile.TemporaryDirectory() as manifest_dir:
        # RBAC mirrors the minimum resources Kubelet AD needs to resolve node and pod data.
        apply_manifests(kubeconfig_path, build_rbac_manifests(namespace), manifest_dir, 'rbac.yaml')
        if extra_cluster_roles:
            apply_manifests(
                kubeconfig_path,
                build_extra_cluster_role_binding_manifests(namespace, extra_cluster_roles),
                manifest_dir,
                'extra-rbac.yaml',
            )
        # `agent check` uses read-only IPC auth today, so mount the expected files up front.
        apply_manifests(kubeconfig_path, [build_ipc_secret_manifest(namespace)], manifest_dir, 'secret.yaml')
        # The real Agent file provider expects integration templates under conf.d/<check>.d.
        apply_manifests(
            kubeconfig_path,
            [build_auto_conf_configmap_manifest(namespace, check_root, check_name)],
            manifest_dir,
            'configmap.yaml',
        )
        apply_manifests(
            kubeconfig_path,
            [build_agent_pod_manifest(namespace, check_name, agent_image)],
            manifest_dir,
            'pod.yaml',
        )

    run_kubectl(
        kubeconfig_path, ['wait', 'pod', AGENT_POD_NAME, '-n', namespace, '--for=condition=Ready', '--timeout=120s']
    )

    # Install the local worktree into the Agent's embedded Python before running checks.
    install_local_package(kubeconfig_path, namespace, check_root, check_name)


def run_discovery_check_kubernetes(
    aggregator: Any,
    datadog_agent: Any,
    *,
    check_name: str | None = None,
    discovery_min_instances: int = 1,
    discovery_timeout: int = 30,
    **flags: Any,
) -> Any:
    """The Kubelet-AD analog of ``dd_agent_check_discovery``: run ``agent check`` inside the agent pod."""
    if not e2e_testing():
        pytest.skip('Not running E2E tests')

    state = get_kube_discovery_state()
    check_name = check_name or os.path.basename(find_check_root(depth=1))

    command = [
        'agent',
        'check',
        check_name,
        '--discovery-min-instances',
        str(discovery_min_instances),
        '--discovery-timeout',
        str(discovery_timeout),
        '--json',
    ]
    command.extend(flags_to_argv(flags))

    result = exec_agent_pod(state['kubeconfig_path'], state['namespace'], command, capture=True, check=False)
    if not replay_collector_output(result.stdout, aggregator, datadog_agent):
        agent_logs = get_pod_logs(state['kubeconfig_path'], state['namespace'], AGENT_POD_NAME)
        raise ValueError(
            f'Could not find valid check output:\n{result.stdout}\n{result.stderr}\n\nAgent pod logs:\n{agent_logs}'
        )

    return aggregator


def assert_all_discovery_candidates_stable_kubernetes(
    check_cls: type[Any],
    aggregator: Any,
    datadog_agent: Any,
    *,
    namespace: str,
    pod_name: str | None = None,
    pod_selector: str | None = None,
    service_id: str | None = None,
    log_patterns: Sequence[str] = CONTAINER_STABILITY_LOG_PATTERNS,
) -> None:
    """Structural mirror of ``docker.assert_all_discovery_candidates_stable`` for a Kubernetes workload pod.

    ``namespace``/``pod_name``/``pod_selector`` identify the workload pod being monitored, not the
    agent pod created by ``setup_discovery_agent``. Candidates are probed by copying each generated
    config into the agent pod and running ``agent check --config-file`` against it there, exercising
    real in-cluster reachability from the agent to the workload pod IP.
    """
    if not pod_name and not pod_selector:
        raise TypeError('Either pod_name or pod_selector must be provided.')

    if not e2e_testing():
        pytest.skip('Not running E2E tests')

    state = get_kube_discovery_state()
    kubeconfig_path = state['kubeconfig_path']
    check_name = os.path.basename(find_check_root(depth=1))

    pod_name = pod_name or resolve_pod_name(kubeconfig_path, namespace, pod_selector)
    # Capture a baseline before probing generated configs; candidates must not disturb the workload pod.
    initial_state = get_pod(kubeconfig_path, namespace, pod_name)
    previous_logs = get_pod_logs(kubeconfig_path, namespace, pod_name)

    service = build_service_from_pod(initial_state, service_id or pod_name)
    candidates = tuple(check_cls.generate_configs(service))
    if not candidates:
        raise AssertionError(f'No discovery candidates generated for service {service.id!r}')

    for index, candidate in enumerate(candidates, 1):
        logging.debug('Probing candidate #%d: %r', index, candidate)
        try:
            # Probe as a static config so this check validates generated candidates, not AD resolution.
            probe_candidate(state, check_name, candidate, aggregator, datadog_agent)
        except Exception:
            # Even a failing candidate should still be checked for restarts or dangerous log output.
            logging.debug('Error probing candidate #%d: %r', index, candidate, exc_info=True)

        current_state = get_pod(kubeconfig_path, namespace, pod_name)
        assert_pod_stable(initial_state, current_state, index)

        current_logs = get_pod_logs(kubeconfig_path, namespace, pod_name)
        previous_logs = assert_no_new_log_patterns(previous_logs, current_logs, log_patterns, index)


def get_kube_discovery_state() -> dict[str, Any]:
    state = get_state('kube_discovery')
    if not state:
        raise AssertionError('No kube_discovery state found. Call save_kube_discovery_state() during setup.')

    return state


def replay_collector_output(output: str, aggregator: Any, datadog_agent: Any) -> int:
    """Replay collector JSON blobs from ``agent check --json`` output."""
    matches = find_collector_blobs(output)
    for raw_json in matches:
        try:
            collector = json.loads(raw_json)
        except Exception as e:
            raise Exception(f'Error loading json: {e}\nCollector Json Output:\n{raw_json}')
        replay_check_run(collector, aggregator, datadog_agent)

    return len(matches)


def run_kubectl(kubeconfig_path: str | os.PathLike[str], args: list[str], **kwargs: Any) -> Any:
    env = os.environ.copy()
    env['KUBECONFIG'] = os.fspath(kubeconfig_path)
    kwargs.setdefault('check', True)
    return run_command(['kubectl', *args], env=env, **kwargs)


def exec_agent_pod(kubeconfig_path: str | os.PathLike[str], namespace: str, command: list[str], **kwargs: Any) -> Any:
    return run_kubectl(kubeconfig_path, ['exec', AGENT_POD_NAME, '-n', namespace, '--', *command], **kwargs)


def apply_manifests(
    kubeconfig_path: str | os.PathLike[str], manifests: list[dict[str, Any]], manifest_dir: str, filename: str
) -> None:
    manifest_path = os.path.join(manifest_dir, filename)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        yaml.dump_all(manifests, f)

    run_kubectl(kubeconfig_path, ['apply', '-f', manifest_path])


def build_rbac_manifests(namespace: str) -> list[dict[str, Any]]:
    return [
        {'apiVersion': 'v1', 'kind': 'Namespace', 'metadata': {'name': namespace}},
        {
            'apiVersion': 'v1',
            'kind': 'ServiceAccount',
            'metadata': {'name': AGENT_SERVICE_ACCOUNT, 'namespace': namespace},
        },
        {
            'apiVersion': 'rbac.authorization.k8s.io/v1',
            'kind': 'ClusterRole',
            'metadata': {'name': AGENT_CLUSTER_ROLE},
            'rules': [
                {'apiGroups': [''], 'resources': ['nodes'], 'verbs': ['get', 'list', 'watch']},
                {
                    'apiGroups': [''],
                    'resources': ['nodes/metrics', 'nodes/spec', 'nodes/stats', 'nodes/proxy'],
                    'verbs': ['get'],
                },
                {'apiGroups': [''], 'resources': ['pods', 'endpoints', 'services'], 'verbs': ['get', 'list', 'watch']},
            ],
        },
        {
            'apiVersion': 'rbac.authorization.k8s.io/v1',
            'kind': 'ClusterRoleBinding',
            'metadata': {'name': AGENT_CLUSTER_ROLE_BINDING},
            'roleRef': {
                'apiGroup': 'rbac.authorization.k8s.io',
                'kind': 'ClusterRole',
                'name': AGENT_CLUSTER_ROLE,
            },
            'subjects': [{'kind': 'ServiceAccount', 'name': AGENT_SERVICE_ACCOUNT, 'namespace': namespace}],
        },
    ]


def build_extra_cluster_role_binding_manifests(namespace: str, cluster_roles: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            'apiVersion': 'rbac.authorization.k8s.io/v1',
            'kind': 'ClusterRoleBinding',
            'metadata': {'name': '{}-extra-{}'.format(AGENT_CLUSTER_ROLE_BINDING, index)},
            'roleRef': {
                'apiGroup': 'rbac.authorization.k8s.io',
                'kind': 'ClusterRole',
                'name': cluster_role,
            },
            'subjects': [{'kind': 'ServiceAccount', 'name': AGENT_SERVICE_ACCOUNT, 'namespace': namespace}],
        }
        for index, cluster_role in enumerate(cluster_roles)
    ]


def build_ipc_secret_manifest(namespace: str) -> dict[str, Any]:
    # The sleeping pod never runs `agent run`, so it cannot create these auth artifacts itself.
    return {
        'apiVersion': 'v1',
        'kind': 'Secret',
        'metadata': {'name': AGENT_IPC_SECRET, 'namespace': namespace},
        'type': 'Opaque',
        'stringData': {
            'auth_token': generate_auth_token(),
            'ipc_cert.pem': generate_ipc_cert_pem(),
        },
    }


def generate_auth_token() -> str:
    return secrets.token_hex(32)


def generate_ipc_cert_pem() -> str:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, AGENT_POD_NAME)])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )

    # A certificate followed immediately by an SEC1 `EC PRIVATE KEY` (no `EC PARAMETERS` block):
    # an `EC PARAMETERS` block makes the Agent's IPC component fail with a PEM decode error.
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return (cert_pem + key_pem).decode('ascii')


def build_auto_conf_configmap_manifest(namespace: str, check_root: str, check_name: str) -> dict[str, Any]:
    auto_conf_path = os.path.join(check_root, 'datadog_checks', check_name, 'data', 'auto_conf.yaml')
    with open(auto_conf_path, encoding='utf-8') as f:
        auto_conf_contents = f.read()

    return {
        'apiVersion': 'v1',
        'kind': 'ConfigMap',
        'metadata': {'name': AGENT_AUTO_CONF_CONFIGMAP, 'namespace': namespace},
        'data': {'auto_conf.yaml': auto_conf_contents},
    }


def build_agent_pod_manifest(namespace: str, check_name: str, agent_image: str) -> dict[str, Any]:
    config_mount_path = f'/etc/datadog-agent/conf.d/{check_name}.d/auto_conf.yaml'

    return {
        'apiVersion': 'v1',
        'kind': 'Pod',
        'metadata': {'name': AGENT_POD_NAME, 'namespace': namespace, 'labels': {'app': AGENT_POD_NAME}},
        'spec': {
            'serviceAccountName': AGENT_SERVICE_ACCOUNT,
            'restartPolicy': 'Never',
            'containers': [
                {
                    'name': 'agent',
                    'image': agent_image,
                    'imagePullPolicy': 'Always',
                    'command': ['sleep', 'infinity'],
                    'env': [
                        {'name': 'DD_API_KEY', 'value': FAKE_API_KEY},
                        {'name': 'DD_HOSTNAME', 'value': AGENT_POD_NAME},
                        {'name': 'DD_APM_ENABLED', 'value': 'false'},
                        {'name': 'DD_AUTOCONFIG_FROM_ENVIRONMENT', 'value': 'true'},
                        {'name': 'DD_AUTH_TOKEN_FILE_PATH', 'value': AGENT_AUTH_TOKEN_PATH},
                        {'name': 'DD_IPC_CERT_FILE_PATH', 'value': AGENT_IPC_CERT_PATH},
                        # kind's kubelet certificate does not cover status.hostIP.
                        {'name': 'DD_KUBELET_TLS_VERIFY', 'value': 'false'},
                        {
                            'name': 'DD_KUBERNETES_KUBELET_HOST',
                            'valueFrom': {'fieldRef': {'fieldPath': 'status.hostIP'}},
                        },
                        {
                            'name': 'DD_KUBERNETES_KUBELET_NODENAME',
                            'valueFrom': {'fieldRef': {'fieldPath': 'spec.nodeName'}},
                        },
                    ],
                    'volumeMounts': [
                        {'name': 'ipc', 'mountPath': AGENT_AUTH_TOKEN_PATH, 'subPath': 'auth_token'},
                        {'name': 'ipc', 'mountPath': AGENT_IPC_CERT_PATH, 'subPath': 'ipc_cert.pem'},
                        {'name': 'auto-conf', 'mountPath': config_mount_path, 'subPath': 'auto_conf.yaml'},
                    ],
                }
            ],
            'volumes': [
                {'name': 'ipc', 'secret': {'secretName': AGENT_IPC_SECRET}},
                {'name': 'auto-conf', 'configMap': {'name': AGENT_AUTO_CONF_CONFIGMAP}},
            ],
        },
    }


def install_local_package(
    kubeconfig_path: str | os.PathLike[str], namespace: str, check_root: str, check_name: str
) -> None:
    remote_dir = f'{AGENT_PACKAGE_MOUNT_DIR}/{check_name}'

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = os.path.join(tmp_dir, f'{check_name}.tar.gz')
        build_check_archive(check_root, archive_path)

        remote_archive_path = f'/tmp/{check_name}.tar.gz'
        run_kubectl(kubeconfig_path, ['cp', archive_path, f'{namespace}/{AGENT_POD_NAME}:{remote_archive_path}'])

    exec_agent_pod(
        kubeconfig_path,
        namespace,
        ['sh', '-c', f'mkdir -p {remote_dir} && tar -xzf {remote_archive_path} -C {remote_dir} --strip-components=1'],
    )
    exec_agent_pod(
        kubeconfig_path,
        namespace,
        [AGENT_PYTHON_PATH, '-m', 'pip', 'install', '--disable-pip-version-check', '-e', remote_dir],
    )


def build_check_archive(check_root: str, archive_path: str) -> None:
    def exclude_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        # Keep the upload small and avoid copying host-local cache state into the Agent pod.
        if any(part in EXCLUDED_ARCHIVE_DIR_NAMES for part in tarinfo.name.split('/')):
            return None
        return tarinfo

    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(check_root, arcname=os.path.basename(check_root), filter=exclude_filter)


def resolve_pod_name(kubeconfig_path: str | os.PathLike[str], namespace: str, pod_selector: str) -> str:
    result = run_kubectl(
        kubeconfig_path,
        ['get', 'pods', '-n', namespace, '-l', pod_selector, '-o', 'jsonpath={.items[0].metadata.name}'],
        capture='out',
    )
    pod_name = result.stdout.strip()
    if not pod_name:
        raise AssertionError(f'No pod found in namespace {namespace!r} matching selector {pod_selector!r}')

    return pod_name


def get_pod(kubeconfig_path: str | os.PathLike[str], namespace: str, pod_name: str) -> dict[str, Any]:
    result = run_kubectl(kubeconfig_path, ['get', 'pod', pod_name, '-n', namespace, '-o', 'json'], capture='out')
    return json.loads(result.stdout)


def get_pod_logs(kubeconfig_path: str | os.PathLike[str], namespace: str, pod_name: str) -> str:
    result = run_kubectl(kubeconfig_path, ['logs', pod_name, '-n', namespace], capture=True, check=False)
    return result.stdout + result.stderr


def build_service_from_pod(pod_state: dict[str, Any], service_id: str) -> Any:
    host = pod_state['status']['podIP']
    ports = []
    seen_numbers = set()
    for container in pod_state['spec']['containers']:
        for port_spec in container.get('ports', []):
            number = port_spec['containerPort']
            # Discovery services model pod-level reachability, so duplicate container ports collapse.
            if number in seen_numbers:
                continue
            seen_numbers.add(number)
            ports.append(SimpleNamespace(number=number, name=port_spec.get('name', '')))

    return SimpleNamespace(id=service_id, host=host, ports=tuple(ports))


def probe_candidate(
    state: dict[str, Any], check_name: str, candidate: dict[str, Any], aggregator: Any, datadog_agent: Any
) -> None:
    kubeconfig_path = state['kubeconfig_path']
    namespace = state['namespace']
    remote_config_path = f'/tmp/{check_name}-candidate.json'

    with tempfile.TemporaryDirectory() as tmp_dir:
        config_path = os.path.join(tmp_dir, 'candidate.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(format_config(candidate), f)

        run_kubectl(kubeconfig_path, ['cp', config_path, f'{namespace}/{AGENT_POD_NAME}:{remote_config_path}'])

    result = exec_agent_pod(
        kubeconfig_path,
        namespace,
        ['agent', 'check', check_name, '--config-file', remote_config_path, '--json'],
        capture=True,
        check=False,
    )

    replay_collector_output(result.stdout, aggregator, datadog_agent)


def assert_pod_stable(initial_state: dict[str, Any], current_state: dict[str, Any], candidate_index: int) -> None:
    initial_uid = initial_state['metadata']['uid']
    current_uid = current_state['metadata']['uid']
    if current_uid != initial_uid:
        raise AssertionError(f'Pod changed while probing candidate #{candidate_index}: {initial_uid} -> {current_uid}')

    phase = current_state.get('status', {}).get('phase')
    if phase != 'Running':
        raise AssertionError(f'Pod phase is {phase!r} after probing candidate #{candidate_index}')

    initial_statuses = initial_state.get('status', {}).get('containerStatuses', [])
    current_statuses = current_state.get('status', {}).get('containerStatuses', [])

    initial_restarts = sum(status['restartCount'] for status in initial_statuses)
    current_restarts = sum(status['restartCount'] for status in current_statuses)
    if current_restarts != initial_restarts:
        raise AssertionError(
            f'Pod restart count changed while probing candidate #{candidate_index}: '
            f'{initial_restarts} -> {current_restarts}'
        )

    for status in current_statuses:
        if not status.get('ready', False):
            raise AssertionError(
                f"Container {status['name']!r} is not ready after probing candidate #{candidate_index}"
            )

        terminated_reason = status.get('lastState', {}).get('terminated', {}).get('reason')
        if terminated_reason in ('Error', 'OOMKilled'):
            raise AssertionError(
                f"Container {status['name']!r} last terminated with reason {terminated_reason!r} "
                f'after probing candidate #{candidate_index}'
            )
