# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Helpers for testing Agent Autodiscovery against Kubernetes pods.

Docker E2E tests can start a container and run a check from the host. Kubernetes
Autodiscovery has to be tested from inside the cluster instead: the Agent needs a Kubernetes service
account, pod networking, and access to the kubelet on the node where it is running.

This module creates a minimal Agent pod in a ``kind`` cluster. The container only sleeps during
setup; tests later run one-shot ``agent check`` commands inside it with ``kubectl exec``. That keeps
the environment small while still using the Agent's real Kubernetes discovery code.

Unlike the Docker helpers, this module cannot share a host log directory with the workload. The
tests read Kubernetes pod logs with ``kubectl logs`` instead.

Kubelet Autodiscovery is node-local. A node Agent asks the kubelet on its own node which pods are
running there, then resolves integration templates for those pods. These helpers therefore assume a
single-node ``kind`` cluster, or a test workload scheduled on the same node as the helper Agent pod.
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
    replay_collector_blobs,
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


def setup_discovery_agent(
    kubeconfig_path: str | os.PathLike[str],
    *,
    check_root: str | os.PathLike[str] | None = None,
    namespace: str = DISCOVERY_NAMESPACE,
    agent_image: str = DEFAULT_AGENT_IMAGE,
) -> None:
    """Create the helper Agent pod used by Kubernetes Autodiscovery E2E tests.

    Call this from the integration's ``kind_run(...)`` block while ``KUBECONFIG`` points at the
    newly created test cluster. The setup pass stores that kubeconfig path and the helper namespace
    so later test helpers can find the pod again.

    ``ddev env`` executes environment fixtures in more than one phase. The setup phase creates the
    cluster, while later test and stop phases re-enter the same fixture body to run tests or tear the
    cluster down. During those later phases, ``KUBECONFIG`` may no longer point at a usable cluster,
    so this function returns immediately unless the current phase is allowed to create resources.
    """
    if not set_up_env():
        return

    check_root = os.fspath(check_root or find_check_root(depth=1))
    check_name = os.path.basename(check_root)

    # The pod is only a place to run commands. It does not start the long-running Agent daemon.
    with tempfile.TemporaryDirectory() as manifest_dir:
        # Apply manifests in dependency order so the pod can mount its config and use its service account.
        apply_manifests(kubeconfig_path, build_rbac_manifests(namespace), manifest_dir, 'rbac.yaml')
        # `agent check` initializes the Agent's local inter-process communication client. That client
        # expects an auth token and TLS certificate on disk. A normal Agent daemon creates those files
        # on startup, but this container only sleeps, so provide them through a Secret.
        apply_manifests(kubeconfig_path, [build_ipc_secret_manifest(namespace)], manifest_dir, 'secret.yaml')
        # Mount the check's bundled Autodiscovery template where the Agent's file provider expects it.
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

    # Install local shared code before the check so generated discovery can use helpers added in
    # the same PR, even when the Agent image has an older datadog-checks-base package.
    local_base_root = find_local_base_root(check_root)
    if local_base_root is not None:
        install_local_package(
            kubeconfig_path, namespace, local_base_root, 'datadog_checks_base', pip_options=('--no-deps',)
        )

    # Install the checkout under test, not the version already baked into the Agent image. Request
    # the `deps` extra so runtime libraries declared in the integration's pyproject.toml are installed
    # too, matching what `ddev env start` does for the non-Kubernetes E2E path.
    install_local_package(kubeconfig_path, namespace, check_root, check_name, extras=('deps',))

    save_state('kube_discovery', {'kubeconfig_path': os.fspath(kubeconfig_path), 'namespace': namespace})


def run_discovery_check_kubernetes(
    aggregator: Any,
    datadog_agent: Any,
    *,
    check_name: str | None = None,
    discovery_min_instances: int = 1,
    discovery_timeout: int = 30,
    **flags: Any,
) -> Any:
    """Run ``agent check`` in the helper pod and replay its JSON output into the test aggregator.

    The command runs inside Kubernetes so the Agent discovers pods through the kubelet just as it
    would in a real DaemonSet. ``discovery_min_instances`` and ``discovery_timeout`` control how long
    the command waits for Autodiscovery to resolve the check template into runnable instances.
    """
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
        raise ValueError(f'Could not find valid check output:\n{result.stdout}\n{result.stderr}')

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
    """Check that generated configs can probe a Kubernetes workload without disturbing it.

    ``namespace``, ``pod_name``, and ``pod_selector`` identify the workload pod being monitored, not
    the helper Agent pod. The function builds the same service shape that Autodiscovery gives to
    ``check_cls.generate_configs``: pod IP plus declared container ports.

    Each generated config is copied into the helper Agent pod and run with ``agent check
    --config-file``. That deliberately bypasses template resolution so this test focuses on the
    generated config itself: whether it can reach the workload from inside the cluster, and whether
    trying it causes the workload pod to restart or log dangerous errors.
    """
    if not pod_name and not pod_selector:
        raise TypeError('Either pod_name or pod_selector must be provided.')

    if not e2e_testing():
        pytest.skip('Not running E2E tests')

    state = get_kube_discovery_state()
    kubeconfig_path = state['kubeconfig_path']
    check_name = os.path.basename(find_check_root(depth=1))

    pod_name = pod_name or resolve_pod_name(kubeconfig_path, namespace, pod_selector)
    # Capture the workload state before any probe so each candidate can be checked for side effects.
    initial_state = get_pod(kubeconfig_path, namespace, pod_name)
    previous_logs = get_pod_logs(kubeconfig_path, namespace, pod_name)

    service = build_service_from_pod(initial_state, service_id or pod_name)
    candidates = tuple(check_cls.generate_configs(service))
    if not candidates:
        raise AssertionError(f'No discovery candidates generated for service {service.id!r}')

    for index, candidate in enumerate(candidates, 1):
        logging.debug('Probing candidate #%d: %r', index, candidate)
        try:
            # Run the generated config directly; discovery already happened when generate_configs ran.
            probe_candidate(state, check_name, candidate, aggregator, datadog_agent)
        except Exception:
            # The failed check may still have contacted the workload before erroring.
            # Verify that the workload pod stayed healthy before trying the next config.
            logging.debug('Error probing candidate #%d: %r', index, candidate, exc_info=True)

        current_state = get_pod(kubeconfig_path, namespace, pod_name)
        assert_pod_stable(initial_state, current_state, index)

        current_logs = get_pod_logs(kubeconfig_path, namespace, pod_name)
        previous_logs = assert_no_new_log_patterns(previous_logs, current_logs, log_patterns, index)


def get_kube_discovery_state() -> dict[str, Any]:
    """Return the helper pod location saved by ``setup_discovery_agent``."""
    state = get_state('kube_discovery')
    if not state:
        raise AssertionError('No kube_discovery state found. Call setup_discovery_agent() during setup.')

    return state


def replay_collector_output(output: str, aggregator: Any, datadog_agent: Any) -> int:
    """Replay collector JSON blobs from ``agent check --json`` output."""
    matches = find_collector_blobs(output)
    replay_collector_blobs(matches, aggregator, datadog_agent)

    return len(matches)


def run_kubectl(kubeconfig_path: str | os.PathLike[str], args: list[str], **kwargs: Any) -> Any:
    """Run ``kubectl`` against the cluster created during the setup phase."""
    env = os.environ.copy()
    env['KUBECONFIG'] = os.fspath(kubeconfig_path)
    kwargs.setdefault('check', True)
    return run_command(['kubectl', *args], env=env, **kwargs)


def exec_agent_pod(kubeconfig_path: str | os.PathLike[str], namespace: str, command: list[str], **kwargs: Any) -> Any:
    """Run a command inside the sleeping helper Agent container."""
    return run_kubectl(kubeconfig_path, ['exec', AGENT_POD_NAME, '-n', namespace, '--', *command], **kwargs)


def apply_manifests(
    kubeconfig_path: str | os.PathLike[str], manifests: list[dict[str, Any]], manifest_dir: str, filename: str
) -> None:
    """Write Kubernetes objects to a temporary YAML file and apply them."""
    manifest_path = os.path.join(manifest_dir, filename)
    with open(manifest_path, 'w', encoding='utf-8') as f:
        yaml.dump_all(manifests, f)

    run_kubectl(kubeconfig_path, ['apply', '-f', manifest_path])


def build_rbac_manifests(namespace: str) -> list[dict[str, Any]]:
    """Build the namespace, service account, and Kubernetes permissions for the helper Agent."""
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
            # The Agent lists pods, endpoints, and services to find targets. It also reads kubelet
            # data through Kubernetes node resources, which is how it discovers pods on its own node.
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


def build_ipc_secret_manifest(namespace: str) -> dict[str, Any]:
    """Build the Secret that provides the Agent's local communication auth files."""
    # The sleeping pod never runs the Agent daemon, so it cannot create these files itself.
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
    """Generate the certificate and private key format expected by the Agent IPC loader."""
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

    # The Agent expects the certificate followed immediately by an `EC PRIVATE KEY` block.
    # If the PEM includes a separate `EC PARAMETERS` block, the Agent fails to decode it.
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return (cert_pem + key_pem).decode('ascii')


def build_auto_conf_configmap_manifest(namespace: str, check_root: str, check_name: str) -> dict[str, Any]:
    """Build the ConfigMap containing the check's bundled Kubernetes Autodiscovery template."""
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
    """Build the sleeping Agent pod that later receives ``kubectl exec`` commands."""
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
                    # These settings give one-shot `agent check` enough of a normal Agent
                    # environment to load Kubernetes templates and talk to the local kubelet.
                    'env': [
                        {'name': 'DD_API_KEY', 'value': FAKE_API_KEY},
                        {'name': 'DD_HOSTNAME', 'value': AGENT_POD_NAME},
                        {'name': 'DD_APM_ENABLED', 'value': 'false'},
                        # Let the Agent enable Kubernetes Autodiscovery from its pod environment.
                        {'name': 'DD_AUTOCONFIG_FROM_ENVIRONMENT', 'value': 'true'},
                        {'name': 'DD_AUTH_TOKEN_FILE_PATH', 'value': AGENT_AUTH_TOKEN_PATH},
                        {'name': 'DD_IPC_CERT_FILE_PATH', 'value': AGENT_IPC_CERT_PATH},
                        # In kind, status.hostIP reaches the local kubelet, but the kubelet
                        # certificate is issued for the node name instead of that IP address.
                        {'name': 'DD_KUBELET_TLS_VERIFY', 'value': 'false'},
                        # The Downward API fills these from the node running this helper pod.
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


def find_local_base_root(check_root: str) -> str | None:
    """Return the sibling datadog_checks_base checkout when this is an integrations-core worktree."""
    candidate = os.path.join(os.path.dirname(check_root), 'datadog_checks_base')
    if os.path.isdir(candidate):
        return candidate

    return None


def install_local_package(
    kubeconfig_path: str | os.PathLike[str],
    namespace: str,
    package_root: str,
    package_name: str,
    *,
    pip_options: Sequence[str] = (),
    extras: Sequence[str] = (),
) -> None:
    """Copy a local package into the helper pod and install it editable."""
    remote_dir = f'{AGENT_PACKAGE_MOUNT_DIR}/{package_name}'
    install_target = f'{remote_dir}[{",".join(extras)}]' if extras else remote_dir

    with tempfile.TemporaryDirectory() as tmp_dir:
        archive_path = os.path.join(tmp_dir, f'{package_name}.tar.gz')
        build_check_archive(package_root, archive_path)

        remote_archive_path = f'/tmp/{package_name}.tar.gz'
        run_kubectl(kubeconfig_path, ['cp', archive_path, f'{namespace}/{AGENT_POD_NAME}:{remote_archive_path}'])

    exec_agent_pod(
        kubeconfig_path,
        namespace,
        ['sh', '-c', f'mkdir -p {remote_dir} && tar -xzf {remote_archive_path} -C {remote_dir} --strip-components=1'],
    )
    exec_agent_pod(
        kubeconfig_path,
        namespace,
        [
            AGENT_PYTHON_PATH,
            '-m',
            'pip',
            'install',
            '--disable-pip-version-check',
            *pip_options,
            '-e',
            install_target,
        ],
    )


def build_check_archive(check_root: str, archive_path: str) -> None:
    """Create a small archive of the integration checkout for ``kubectl cp``."""

    def exclude_filter(tarinfo: tarfile.TarInfo) -> tarfile.TarInfo | None:
        # Keep the upload small and avoid copying host-only cache state into the Agent pod.
        if any(part in EXCLUDED_ARCHIVE_DIR_NAMES for part in tarinfo.name.split('/')):
            return None
        return tarinfo

    with tarfile.open(archive_path, 'w:gz') as tar:
        tar.add(check_root, arcname=os.path.basename(check_root), filter=exclude_filter)


def resolve_pod_name(kubeconfig_path: str | os.PathLike[str], namespace: str, pod_selector: str) -> str:
    """Resolve a pod selector to the first matching pod name."""
    result = run_kubectl(
        kubeconfig_path,
        ['get', 'pods', '-n', namespace, '-l', pod_selector, '-o', 'jsonpath={.items[0].metadata.name}'],
        capture='out',
        # jsonpath errors with a non-zero exit on an empty `.items` list, which we want to
        # turn into the friendlier AssertionError below rather than a raw subprocess error.
        check=False,
    )
    pod_name = result.stdout.strip() if result.code == 0 else ''
    if not pod_name:
        raise AssertionError(f'No pod found in namespace {namespace!r} matching selector {pod_selector!r}')

    return pod_name


def get_pod(kubeconfig_path: str | os.PathLike[str], namespace: str, pod_name: str) -> dict[str, Any]:
    """Fetch the current Kubernetes Pod object."""
    result = run_kubectl(kubeconfig_path, ['get', 'pod', pod_name, '-n', namespace, '-o', 'json'], capture='out')
    return json.loads(result.stdout)


def get_pod_logs(kubeconfig_path: str | os.PathLike[str], namespace: str, pod_name: str) -> str:
    """Fetch pod logs without failing when the pod is already unhealthy."""
    result = run_kubectl(kubeconfig_path, ['logs', pod_name, '-n', namespace], capture=True, check=False)
    return result.stdout + result.stderr


def build_service_from_pod(pod_state: dict[str, Any], service_id: str) -> Any:
    """Convert a Pod object into the service shape expected by ``generate_configs``."""
    host = pod_state['status']['podIP']
    ports = []
    seen_numbers = set()
    for container in pod_state['spec']['containers']:
        for port_spec in container.get('ports', []):
            number = port_spec['containerPort']
            # The Agent connects to a pod IP and port number, so the same port on two containers is one endpoint.
            if number in seen_numbers:
                continue
            seen_numbers.add(number)
            ports.append(SimpleNamespace(number=number, name=port_spec.get('name', '')))

    return SimpleNamespace(id=service_id, host=host, ports=tuple(ports))


def probe_candidate(
    state: dict[str, Any], check_name: str, candidate: dict[str, Any], aggregator: Any, datadog_agent: Any
) -> None:
    """Run one generated config from inside the helper Agent pod."""
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
    """Fail if probing a candidate changed the workload pod's health."""
    initial_uid = initial_state['metadata']['uid']
    current_uid = current_state['metadata']['uid']
    if current_uid != initial_uid:
        raise AssertionError(f'Pod changed while probing candidate #{candidate_index}: {initial_uid} -> {current_uid}')

    phase = current_state.get('status', {}).get('phase')
    if phase != 'Running':
        raise AssertionError(f'Pod phase is {phase!r} after probing candidate #{candidate_index}')

    initial_statuses = initial_state.get('status', {}).get('containerStatuses', [])
    current_statuses = current_state.get('status', {}).get('containerStatuses', [])
    initial_terminated_reasons = {
        status['name']: status.get('lastState', {}).get('terminated', {}).get('reason') for status in initial_statuses
    }

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
        if terminated_reason in ('Error', 'OOMKilled') and terminated_reason != initial_terminated_reasons.get(
            status['name']
        ):
            raise AssertionError(
                f"Container {status['name']!r} last terminated with reason {terminated_reason!r} "
                f'after probing candidate #{candidate_index}'
            )
