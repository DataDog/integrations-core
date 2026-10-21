# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
import os
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager

import pytest
import yaml

from datadog_checks.dev import TempDir
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import INSTANCE_STATE_KEY, KUBECONFIG_STATE_KEY, MOCKED_INSTANCE
from .kube import (
    KAI_NAMESPACE,
    WAIT_TIMEOUT,
    manifest_path,
    retry_apply,
    trigger_preemption,
    wait_for_deployment,
    wait_for_pod,
)

KAI_VERSION_ENV = 'KAI_VERSION'
KAI_CHART = 'oci://ghcr.io/kai-scheduler/kai-scheduler/kai-scheduler'
KIND_SUBNETS_ENV = 'KAI_KIND_SUBNETS'
SUBNET_CANDIDATES = [f'10.{octet}.0.0/16' for octet in range(255, -1, -1)]
METRICS_PORT = 8080

# Services created by the KAI operator, keyed by the instance option that scrapes them.
METRICS_SERVICES = {
    'scheduler_endpoint': 'kai-scheduler-default',
    'queue_controller_endpoint': 'queue-controller',
    'binder_endpoint': 'binder',
}


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
            networks.append(ipaddress.IPv4Network(f'{".".join(octets)}/{prefix}', strict=False))
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
        networks = parse_route_networks(output)
        if networks:
            return networks

    raise RuntimeError(
        'Could not read the host routing table with `ip -4 route show` or `netstat -rn -f inet`. '
        'Without it a colliding kind subnet cannot be detected, and the KAI webhooks would be unreachable. '
        f'Pin the subnets with {KIND_SUBNETS_ENV}=<serviceSubnet>,<podSubnet>.'
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

    fd, path = tempfile.mkstemp(prefix='kai-kind-', suffix='.yaml')
    try:
        with os.fdopen(fd, 'w') as f:
            yaml.safe_dump(config, f)
        yield path
    finally:
        os.unlink(path)


def kai_version() -> str:
    """Return the KAI version under test, which the hatch.toml env matrix exports."""
    version = os.environ.get(KAI_VERSION_ENV)
    if not version:
        raise RuntimeError(
            f'{KAI_VERSION_ENV} is not set. The hatch.toml env matrix exports it, so run the suite through '
            '`ddev test` or `ddev env start` rather than invoking pytest directly.'
        )
    return version


def install_kai():
    run_command(
        [
            'helm',
            'upgrade',
            '--install',
            'kai-scheduler',
            KAI_CHART,
            '--namespace',
            KAI_NAMESPACE,
            '--create-namespace',
            '--version',
            kai_version(),
            '--wait',
            f'--timeout={WAIT_TIMEOUT}',
        ],
        check=True,
    )
    for service in METRICS_SERVICES.values():
        wait_for_deployment(service)


def setup_kai():
    install_kai()
    retry_apply('queues.yaml')
    retry_apply('workloads.yaml')
    wait_for_pod('running-pod', 'condition=Ready')
    # Preempt at env start so the preemption counters and the eviction series exist when the tests scrape.
    trigger_preemption()


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with (
        TempDir('helm_dir') as helm_dir,
        build_kind_config() as kind_config,
        kind_run(
            conditions=[setup_kai],
            kind_config=kind_config,
            env_vars={
                'HELM_CACHE_HOME': os.path.join(helm_dir, 'Caches'),
                'HELM_CONFIG_HOME': os.path.join(helm_dir, 'Preferences'),
            },
            sleep=10,
        ) as kubeconfig,
        ExitStack() as stack,
    ):
        instance = {'min_collection_interval': 30, 'tags': ['test:e2e']}
        for option, service in METRICS_SERVICES.items():
            host, port = stack.enter_context(port_forward(kubeconfig, KAI_NAMESPACE, METRICS_PORT, 'service', service))
            instance[option] = f'http://{host}:{port}/metrics'
        dd_save_state(INSTANCE_STATE_KEY, instance)
        with open(kubeconfig) as f:
            dd_save_state(KUBECONFIG_STATE_KEY, f.read())

        yield {'instances': [instance]}


@pytest.fixture
def instance():
    return MOCKED_INSTANCE.copy()
