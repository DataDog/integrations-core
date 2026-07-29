# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
import os
import tempfile
import time
from contextlib import ExitStack

import pytest
import yaml

from datadog_checks.base.stubs import tagger
from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import MOCKED_INSTANCE

HERE = get_here()
KUEUE_VERSION = os.environ.get('KUEUE_VERSION', 'v0.18.0')
KUEUE_NAMESPACE = 'kueue-system'  # hardcoded in the Kueue manifests
# Candidate /16 blocks for the kind service and pod networks. Kueue's controller and webhook
# bootstrap over in-cluster Service IPs, so a subnet overlapping a host route (for example a VPN)
# breaks cert bootstrap and crashloops the controller. We pick two that avoid the host routes.
SUBNET_CANDIDATES = [f'10.{octet}.0.0/16' for octet in (250, 251, 252, 253, 199, 198, 60, 61)] + [
    f'172.{octet}.0.0/16' for octet in (28, 29, 30, 31)
]


def parse_route_networks(output: str) -> list[ipaddress.IPv4Network]:
    """Parse route destinations from `ip route` or `netstat -rn` output into networks."""
    networks = []
    skip = {'default', 'destination', 'internet:', 'routing'}
    for line in output.splitlines():
        parts = line.split()
        if not parts:
            continue
        dest = parts[0].split('%')[0]
        if dest.lower() in skip:
            continue
        prefix = '32'
        if '/' in dest:
            dest, prefix = dest.split('/', 1)
        octets = dest.split('.')
        if not (1 <= len(octets) <= 4) or not all(octet.isdigit() for octet in octets):
            continue
        octets += ['0'] * (4 - len(octets))
        try:
            networks.append(ipaddress.ip_network(f'{".".join(octets)}/{prefix}', strict=False))
        except ValueError:
            continue
    return networks


def host_routed_networks() -> list[ipaddress.IPv4Network]:
    """Return the IPv4 networks currently present in the host routing table."""
    for command in (['ip', '-4', 'route', 'show'], ['netstat', '-rn', '-f', 'inet']):
        try:
            output = run_command(command, capture=True).stdout
        except Exception:
            continue
        if output.strip():
            return parse_route_networks(output)
    return []


def choose_free_subnets() -> tuple[str, str] | None:
    """Pick two non-overlapping /16 subnets that avoid host routes, for the kind service and pod networks."""
    routed = host_routed_networks()
    free = []
    for candidate in SUBNET_CANDIDATES:
        network = ipaddress.ip_network(candidate)
        if any(network.overlaps(route) for route in routed):
            continue
        if any(network.overlaps(ipaddress.ip_network(chosen)) for chosen in free):
            continue
        free.append(candidate)
        if len(free) == 2:
            return free[0], free[1]
    return None


def build_kind_config() -> str:
    """Render a kind config whose subnets avoid host-route collisions, falling back to the committed file."""
    base_config = os.path.join(HERE, 'kind', 'kind-config.yaml')
    subnets = choose_free_subnets()
    if subnets is None:
        return base_config

    with open(base_config) as f:
        config = yaml.safe_load(f)
    config.setdefault('networking', {})
    config['networking']['serviceSubnet'], config['networking']['podSubnet'] = subnets

    fd, path = tempfile.mkstemp(prefix='kueue-kind-', suffix='.yaml')
    with os.fdopen(fd, 'w') as f:
        yaml.safe_dump(config, f)
    return path


@pytest.fixture(autouse=True)
def reset_tagger():
    tagger.reset()
    yield
    tagger.reset()


def wait_for_controller():
    run_command(
        [
            'kubectl',
            'rollout',
            'status',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            '--timeout=300s',
        ]
    )
    run_command(
        [
            'kubectl',
            'wait',
            'deployment/kueue-controller-manager',
            '--for=condition=Available',
            '-n',
            KUEUE_NAMESPACE,
            '--timeout=300s',
        ]
    )


def disable_visibility_server():
    """Disable Kueue's visibility server, whose cert bootstrap crashloops the controller in some clusters."""
    run_command(
        [
            'kubectl',
            'patch',
            'deployment/kueue-controller-manager',
            '-n',
            KUEUE_NAMESPACE,
            '--type=json',
            '-p',
            '[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", '
            '"value": "--feature-gates=VisibilityOnDemand=false"}]',
        ]
    )
    # Left in place, the endpoint-less visibility APIServices can stall namespace deletion.
    run_command(
        [
            'kubectl',
            'delete',
            'apiservice',
            'v1beta1.visibility.kueue.x-k8s.io',
            'v1beta2.visibility.kueue.x-k8s.io',
            '--ignore-not-found',
        ]
    )


def setup_kueue():
    run_command(
        [
            'kubectl',
            'apply',
            '--server-side',
            '-f',
            f'https://github.com/kubernetes-sigs/kueue/releases/download/{KUEUE_VERSION}/manifests.yaml',
        ]
    )

    disable_visibility_server()

    # Ensure the controller is ready
    wait_for_controller()

    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'kueue-config.yaml')])
    # Restart the controller to pick up the new config
    run_command(['kubectl', 'rollout', 'restart', 'deployment/kueue-controller-manager', '-n', KUEUE_NAMESPACE])
    wait_for_controller()

    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'metrics-reader.yaml')])
    # The deployment can be `Available` before the webhook server is actually serving, so wait until the
    # webhook service has ready endpoints before applying resources that go through the mutating webhooks.
    run_command(
        [
            'kubectl',
            'wait',
            '--for=jsonpath={.subsets[*].addresses[*].ip}',
            'endpoints/kueue-webhook-service',
            '-n',
            KUEUE_NAMESPACE,
            '--timeout=300s',
        ]
    )
    apply_queue_manifests()
    run_command(['kubectl', 'wait', 'clusterqueue/cluster-queue', '--for=condition=Active', '--timeout=300s'])
    run_command(['kubectl', 'wait', 'clusterqueue/preempt-queue', '--for=condition=Active', '--timeout=300s'])
    run_command(
        ['kubectl', 'wait', 'localqueue/user-queue', '-n', 'default', '--for=condition=Active', '--timeout=300s']
    )
    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'workloads.yaml')])
    wait_for_job_workload_condition('scheduled-workload', 'Admitted=True')
    wait_for_job_workload_condition('unschedulable-workload', 'QuotaReserved=False')
    wait_for_job_workload_condition('gpu-workload', 'Admitted=True')
    wait_for_job_workload_condition('finished-workload', 'Finished=True')
    trigger_preemption()


def trigger_preemption():
    """Admit a low-priority workload, then a higher-priority one that preempts it, for preemption/eviction metrics."""
    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'preempt-low-workload.yaml')])
    wait_for_job_workload_condition('preempt-low-workload', 'Admitted=True')
    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'preempt-high-workload.yaml')])
    # Once the high-priority workload is admitted, the low-priority one has been preempted and evicted.
    wait_for_job_workload_condition('preempt-high-workload', 'Admitted=True')


def apply_queue_manifests():
    # The webhook can still reject calls for a short window after its endpoints become ready (cert
    # propagation), so retry the apply a few times before giving up.
    queue_manifest = os.path.join(HERE, 'kind', 'queue.yaml')
    last_error = None
    for _ in range(10):
        try:
            run_command(['kubectl', 'apply', '-f', queue_manifest], check=True)
            return
        except Exception as e:
            last_error = e
            time.sleep(5)
    raise RuntimeError(f'Failed to apply queue manifests after retries: {last_error}')


def wait_for_job_workload_condition(job_name: str, condition: str) -> None:
    job_uid = run_command(
        ['kubectl', 'get', 'job', job_name, '-n', 'default', '-o', 'jsonpath={.metadata.uid}'], capture=True
    ).stdout.strip()
    workload_name = ''
    for _ in range(10):
        workload_name = run_command(
            [
                'kubectl',
                'get',
                'workloads.kueue.x-k8s.io',
                '-n',
                'default',
                '-l',
                f'kueue.x-k8s.io/job-uid={job_uid}',
                '-o',
                'jsonpath={.items[0].metadata.name}',
            ],
            capture=True,
        ).stdout.strip()
        if workload_name:
            break
        time.sleep(1)
    if not workload_name:
        raise RuntimeError(f'Failed to find Kueue Workload for Job {job_name}')
    run_command(
        [
            'kubectl',
            'wait',
            f'workload/{workload_name}',
            '-n',
            'default',
            f'--for=condition={condition}',
            '--timeout=300s',
        ]
    )


def get_service_account_token():
    # The token is minted once and baked into the instance config, so it has to outlive a
    # `ddev env start --dev` session. Without `--duration` the apiserver default is one hour,
    # after which the scrape 401s and the failure looks like missing metrics.
    result = run_command(
        ['kubectl', 'create', 'token', 'kueue-metrics-reader', '-n', 'default', '--duration=24h'],
        capture=True,
    )
    return result.stdout.strip()


@pytest.fixture(scope='session')
def dd_environment():
    kind_config = build_kind_config()
    with kind_run(conditions=[setup_kueue], kind_config=kind_config, sleep=10) as kubeconfig, ExitStack() as stack:
        with open(kubeconfig) as f:
            kubeconfig_content = yaml.safe_load(f)

        kueue_host, kueue_port = stack.enter_context(
            port_forward(kubeconfig, 'kueue-system', 8443, 'service', 'kueue-controller-manager-metrics-service')
        )
        instances = [
            {
                'openmetrics_endpoint': f'https://{kueue_host}:{kueue_port}/metrics',
                'tls_verify': False,
                'extra_headers': {'Authorization': f'Bearer {get_service_account_token()}'},
                'collect_workload_events': True,
                'kube_config_dict': kubeconfig_content,
                'min_collection_interval': 30,
            }
        ]

        yield {'instances': instances}


@pytest.fixture
def instance():
    return MOCKED_INSTANCE.copy()
