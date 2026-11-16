# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack

import pytest

from datadog_checks.dev import TempDir, get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import MOCKED_INSTANCE

HERE = get_here()
CROSSPLANE_NAMESPACE = 'crossplane-system'
CROSSPLANE_CHART_REPO = 'https://charts.crossplane.io/stable'
CROSSPLANE_VERSION_ENV = 'CROSSPLANE_VERSION'
METRICS_PORT = 8080
WAIT_TIMEOUT = '300s'
# Each endpoint is a separate instance: core reconciles composites, the provider owns managed resources.
METRICS_SERVICES = {'core': 'crossplane-metrics', 'provider': 'provider-nop-metrics'}


def crossplane_version() -> str:
    version = os.environ.get(CROSSPLANE_VERSION_ENV)
    if not version:
        raise RuntimeError(
            f'{CROSSPLANE_VERSION_ENV} is not set; run the suite through `ddev test` or `ddev env start`'
        )
    return version


def kubectl(*args: str) -> None:
    run_command(['kubectl', *args], check=True)


def manifest(name: str) -> str:
    return os.path.join(HERE, 'kind', name)


def setup_crossplane():
    run_command(
        [
            'helm',
            'upgrade',
            '--install',
            'crossplane',
            'crossplane',
            '--repo',
            CROSSPLANE_CHART_REPO,
            '--version',
            crossplane_version(),
            '--namespace',
            CROSSPLANE_NAMESPACE,
            '--create-namespace',
            '--set',
            'metrics.enabled=true',
            '--wait',
            f'--timeout={WAIT_TIMEOUT}',
        ],
        check=True,
    )
    kubectl('apply', '-f', manifest('packages.yaml'))
    kubectl(
        'wait',
        'provider.pkg/provider-nop',
        'function.pkg/function-patch-and-transform',
        '--for=condition=Healthy',
        f'--timeout={WAIT_TIMEOUT}',
    )
    kubectl('apply', '-f', manifest('metrics-services.yaml'))
    kubectl('apply', '-f', manifest('xrd.yaml'))
    kubectl('wait', 'xrd/xnopapps.example.crossplane.io', '--for=condition=Established', f'--timeout={WAIT_TIMEOUT}')
    # Composites exercise the function pipeline and create managed resources, which is what
    # populates the function_run, circuit_breaker, and managed_resource metric families.
    kubectl('apply', '-f', manifest('xr.yaml'))
    kubectl('wait', 'xnopapps', '--all', '-n', 'default', '--for=condition=Ready', f'--timeout={WAIT_TIMEOUT}')


@pytest.fixture(scope='session')
def dd_environment():
    with (
        TempDir('helm_dir') as helm_dir,
        kind_run(
            conditions=[setup_crossplane],
            env_vars={
                'HELM_CACHE_HOME': os.path.join(helm_dir, 'Caches'),
                'HELM_CONFIG_HOME': os.path.join(helm_dir, 'Preferences'),
            },
            sleep=10,
        ) as kubeconfig,
        ExitStack() as stack,
    ):
        instances = []
        for endpoint, service in METRICS_SERVICES.items():
            host, port = stack.enter_context(
                port_forward(kubeconfig, CROSSPLANE_NAMESPACE, METRICS_PORT, 'service', service)
            )
            instances.append(
                {'openmetrics_endpoint': f'http://{host}:{port}/metrics', 'tags': [f'crossplane_endpoint:{endpoint}']}
            )
        yield {'instances': instances}


@pytest.fixture
def instance():
    return MOCKED_INSTANCE.copy()
