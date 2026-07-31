# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
import os
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from glob import glob

import pytest
import yaml

from datadog_checks.base.stubs import tagger
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command
from datadog_checks.dev.utils import get_active_env

from .common import CHECK_NAME, INSTANCE_STATE_KEY, MOCKED_INSTANCE
from .kube import (
    WAIT_TIMEOUT,
    kubectl,
    kubectl_output,
    manifest_path,
    retry_apply,
    wait_for_job_workload_condition,
)

KUEUE_VERSION_ENV = 'KUEUE_VERSION'
KUEUE_NAMESPACE = 'kueue-system'  # hardcoded in the Kueue manifests
MANAGER_CONTAINER = 'manager'
KIND_SUBNETS_ENV = 'KUEUE_KIND_SUBNETS'
SUBNET_CANDIDATES = [f'10.{octet}.0.0/16' for octet in range(255, -1, -1)]


def parse_route_networks(output: str) -> list[ipaddress.IPv4Network]:
    """Parse route destinations from `ip route` or `netstat -rn` output into networks."""
    networks = []
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        dest, _, prefix = parts[0].split('%')[0].partition('/')
        octets = dest.split('.')
        if len(octets) > 4 or not all(octet.isdigit() for octet in octets):
            continue
        prefix = prefix or str(8 * len(octets))
        octets += ['0'] * (4 - len(octets))
        try:
            networks.append(ipaddress.ip_network(f'{".".join(octets)}/{prefix}', strict=False))
        except ValueError:
            continue
    return networks


def host_routed_networks() -> list[ipaddress.IPv4Network]:
    """Return the IPv4 networks in the host routing table, raising if it could not be read.

    Raising matters because an empty table would make every candidate look free.
    """
    for command in (['ip', '-4', 'route', 'show'], ['netstat', '-rn', '-f', 'inet']):
        try:
            output = run_command(command, capture=True).stdout
        except Exception:
            continue
        if output.strip():
            return parse_route_networks(output)

    raise RuntimeError(
        'Could not read the host routing table with `ip -4 route show` or `netstat -rn -f inet`. '
        'Without it a colliding kind subnet cannot be detected, and the Kueue webhook would crashloop '
        f'instead. Pin the subnets with {KIND_SUBNETS_ENV}=<serviceSubnet>,<podSubnet>.'
    )


def free_subnets() -> tuple[str, str]:
    """Return the service and pod subnets to use, picking /16s that no host route claims."""
    routed = host_routed_networks()
    free = [
        candidate
        for candidate in SUBNET_CANDIDATES
        if not any(ipaddress.ip_network(candidate).overlaps(route) for route in routed)
    ]
    if len(free) < 2:
        raise RuntimeError(
            f'Fewer than two of the {len(SUBNET_CANDIDATES)} candidate /16s are free of a host route. '
            f'Disconnect the VPN, or pin the subnets with {KIND_SUBNETS_ENV}=<serviceSubnet>,<podSubnet>.'
        )
    return free[0], free[1]


def pinned_subnets() -> tuple[str, str] | None:
    """Return the subnets pinned through the environment, validating them so a typo fails loudly."""
    raw = os.environ.get(KIND_SUBNETS_ENV, '').strip()
    if not raw:
        return None

    parts = [part.strip() for part in raw.split(',')]
    if len(parts) != 2:
        raise RuntimeError(f'{KIND_SUBNETS_ENV} must be `<serviceSubnet>,<podSubnet>`, got {raw!r}')
    for part in parts:
        ipaddress.ip_network(part)
    return parts[0], parts[1]


@contextmanager
def build_kind_config() -> Iterator[str]:
    """Yield a kind config whose subnets are known not to collide with a host route."""
    with open(manifest_path('kind-config.yaml')) as f:
        config = yaml.safe_load(f)

    service_subnet, pod_subnet = pinned_subnets() or free_subnets()
    networking = config.setdefault('networking', {})
    networking['serviceSubnet'] = service_subnet
    networking['podSubnet'] = pod_subnet
    print(f'Using kind subnets {service_subnet} (service) and {pod_subnet} (pod)')

    fd, path = tempfile.mkstemp(prefix='kueue-kind-', suffix='.yaml')
    try:
        with os.fdopen(fd, 'w') as f:
            yaml.safe_dump(config, f)
        yield path
    finally:
        os.unlink(path)


@pytest.fixture(autouse=True)
def reset_tagger():
    tagger.reset()
    yield
    tagger.reset()


def wait_for_controller():
    kubectl(
        [
            'rollout',
            'status',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            f'--timeout={WAIT_TIMEOUT}',
        ]
    )
    kubectl(
        [
            'wait',
            'deployment/kueue-controller-manager',
            '--for=condition=Available',
            '-n',
            KUEUE_NAMESPACE,
            f'--timeout={WAIT_TIMEOUT}',
        ]
    )


def manager_container_index() -> int:
    """Return the index of the Kueue manager container in the controller deployment."""
    names = kubectl_output(
        [
            'get',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            '-o',
            'jsonpath={.spec.template.spec.containers[*].name}',
        ]
    ).split()
    if MANAGER_CONTAINER not in names:
        raise RuntimeError(f'No {MANAGER_CONTAINER!r} container in the Kueue controller deployment: {names}')
    return names.index(MANAGER_CONTAINER)


def disable_visibility_server():
    """Disable Kueue's visibility server, whose cert bootstrap crashloops the controller in some clusters.

    This is a separate failure from the subnet collision the kind config guards against, so both
    mitigations are required. The trade-off is that the env no longer represents a default install:
    `VisibilityOnDemand` is Beta and on by default since v0.9, and the check does not read it.

    This appends a second `--feature-gates` flag rather than editing any existing one, which relies on
    Kueue merging repeated occurrences. That holds for the versions this env pins.
    """
    index = manager_container_index()
    kubectl(
        [
            'patch',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            '--type=json',
            '-p',
            f'[{{"op": "add", "path": "/spec/template/spec/containers/{index}/args/-", '
            '"value": "--feature-gates=VisibilityOnDemand=false"}]',
        ]
    )
    kubectl(
        [
            'delete',
            'apiservice',
            'v1beta1.visibility.kueue.x-k8s.io',
            'v1beta2.visibility.kueue.x-k8s.io',
            '--ignore-not-found',
        ]
    )


def kueue_version():
    """Return the Kueue version under test, which the hatch.toml env matrix exports."""
    version = os.environ.get(KUEUE_VERSION_ENV)
    if not version:
        raise RuntimeError(
            f'{KUEUE_VERSION_ENV} is not set. The hatch.toml env matrix exports it, so run the suite through '
            '`ddev test` or `ddev env start` rather than invoking pytest directly.'
        )
    return version


def workload_images():
    """Return the images the test Jobs run, read from the manifests so no constant has to track them."""
    images = set()
    for manifest in sorted(glob(manifest_path('*.yaml'))):
        with open(manifest) as f:
            for document in yaml.safe_load_all(f):
                if not document or document.get('kind') != 'Job':
                    continue
                for container in document['spec']['template']['spec']['containers']:
                    images.add(container['image'])
    return images


def preload_workload_images():
    """Pull the workload images once and side-load them, instead of once per Job pod from Docker Hub."""
    cluster_name = f'cluster-{CHECK_NAME}-{get_active_env()}'
    for image in sorted(workload_images()):
        run_command(['docker', 'pull', image])
        run_command(['kind', 'load', 'docker-image', image, '--name', cluster_name])


def wait_for_queues_active():
    """Wait for every queue the tests assert on to become Active.

    `invalid-queue` is deliberately excluded: it references a missing flavor so that it never activates,
    which is what gives the tests coverage of the non-active side of `cluster_queue.status`.
    """
    for cluster_queue in ('cluster-queue', 'borrow-queue', 'preempt-queue'):
        kubectl(['wait', f'clusterqueue/{cluster_queue}', '--for=condition=Active', f'--timeout={WAIT_TIMEOUT}'])
    for local_queue in ('user-queue', 'preempt-queue'):
        kubectl(
            [
                'wait',
                f'localqueue/{local_queue}',
                '-n',
                'default',
                '--for=condition=Active',
                f'--timeout={WAIT_TIMEOUT}',
            ]
        )


def setup_kueue():
    preload_workload_images()
    kubectl(
        [
            'apply',
            '--server-side',
            '-f',
            f'https://github.com/kubernetes-sigs/kueue/releases/download/{kueue_version()}/manifests.yaml',
        ]
    )

    disable_visibility_server()

    # Ensure the controller is ready
    wait_for_controller()

    kubectl(['apply', '-f', manifest_path('kueue-config.yaml')])
    # Restart the controller to pick up the new config
    kubectl(['rollout', 'restart', 'deployment/kueue-controller-manager', '-n', KUEUE_NAMESPACE])
    wait_for_controller()

    kubectl(['apply', '-f', manifest_path('metrics-reader.yaml')])
    # The deployment can be `Available` before the webhook server is actually serving, so wait until the
    # webhook service has ready endpoints before applying resources that go through the mutating webhooks.
    kubectl(
        [
            'wait',
            '--for=jsonpath={.subsets[*].addresses[*].ip}',
            'endpoints/kueue-webhook-service',
            '-n',
            KUEUE_NAMESPACE,
            f'--timeout={WAIT_TIMEOUT}',
        ]
    )
    retry_apply('queue.yaml')
    wait_for_queues_active()
    retry_apply('workloads.yaml')
    wait_for_job_workload_condition('scheduled-workload', 'Admitted=True')
    wait_for_job_workload_condition('unschedulable-workload', 'QuotaReserved=False')
    wait_for_job_workload_condition('gpu-workload', 'Admitted=True')
    wait_for_job_workload_condition('finished-workload', 'Finished=True')
    trigger_preemption()


def trigger_preemption():
    """Admit a low-priority workload, then a higher-priority one that preempts it, for preemption/eviction metrics.

    This runs at env-start so the counters are already non-zero when the metrics test scrapes. It does
    not give the check an observable Evicted *transition*: Kueue clears that condition as soon as it
    requeues the preempted workload, well inside a collection interval.
    """
    retry_apply('preempt-low-workload.yaml')
    wait_for_job_workload_condition('preempt-low-workload', 'Admitted=True')
    retry_apply('preempt-high-workload.yaml')
    wait_for_job_workload_condition('preempt-high-workload', 'Admitted=True')


def get_service_account_token():
    return kubectl_output(['create', 'token', 'kueue-metrics-reader', '-n', 'default', '--duration=24h'])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with (
        build_kind_config() as kind_config,
        kind_run(conditions=[setup_kueue], kind_config=kind_config, sleep=10) as kubeconfig,
        ExitStack() as stack,
    ):
        with open(kubeconfig) as f:
            kubeconfig_content = yaml.safe_load(f)

        kueue_host, kueue_port = stack.enter_context(
            port_forward(kubeconfig, 'kueue-system', 8443, 'service', 'kueue-controller-manager-metrics-service')
        )
        instance = {
            'openmetrics_endpoint': f'https://{kueue_host}:{kueue_port}/metrics',
            'tls_verify': False,
            'extra_headers': {'Authorization': f'Bearer {get_service_account_token()}'},
            'collect_workload_events': True,
            'kube_config_dict': kubeconfig_content,
            'min_collection_interval': 30,
        }
        dd_save_state(INSTANCE_STATE_KEY, instance)

        yield {'instances': [instance]}


@pytest.fixture
def instance():
    return MOCKED_INSTANCE.copy()
