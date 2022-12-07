import os

import pytest

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward

from .common import HERE, LINKERD_FIXTURE_METRICS, LINKERD_FIXTURE_TYPES

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


def setup_linkerd_cluster():
    clusters = run_command(["kind", "get", "clusters"], capture='out')
    cluster = [c for c in clusters.stdout.split() if 'linkerd' in c][0]
    result = run_command(
        ["kind", "get", "kubeconfig", "--internal", "--name", cluster],
        capture='out',
        check=True,
    )
    with open('/tmp/kubeconfig.yaml', 'w') as f:
        f.write(result.stdout)
    run_command(['cat', '/tmp/kubeconfig.yaml'], check=True, shell=True)


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_linkerd_cluster]) as kubeconfig:
        compose_file = os.path.join(HERE, "compose", "docker-compose.yaml")
        with docker_run(
            compose_file=compose_file,
            conditions=[CheckDockerLogs(compose_file, 'LINKERD DEPLOY COMPLETE', wait=5, attempts=120)],
            attempts=2,
        ):
            with ExitStack() as stack:
                ip, port = stack.enter_context(
                    port_forward(kubeconfig, 'linkerd', 4191, 'deployment', 'linkerd-controller')
                )

            instance = {
                'prometheus_url': 'http://{ip}:{port}/metrics'.format(ip=ip, port=port),
                'metrics': [LINKERD_FIXTURE_METRICS],
                'type_overrides': LINKERD_FIXTURE_TYPES,
            }
            yield instance
