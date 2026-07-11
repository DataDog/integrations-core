# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_discovery import save_kube_discovery_state, setup_discovery_agent
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


def wait_for_linkerd_control_plane_ready(kubeconfig):
    # `linkerd check` (run by the install script) validates the control plane once, but does not
    # block until every control-plane pod's containers (including their self-mesh linkerd-proxy
    # sidecar) have stopped restarting. Autodiscovery only matches containers in Ready pods, so an
    # explicit wait here avoids a race where discovery finds nothing because the control plane is
    # still settling from its own bootstrap restarts.
    env = os.environ.copy()
    env['KUBECONFIG'] = kubeconfig
    run_command(
        ['kubectl', 'wait', 'pods', '-n', 'linkerd', '--all', '--for=condition=Ready', '--timeout=180s'],
        env=env,
        check=True,
    )


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_linkerd_cluster]) as kubeconfig:
        setup_discovery_agent(kubeconfig)
        save_kube_discovery_state(kubeconfig)

        compose_file = os.path.join(HERE, "compose", "docker-compose.yaml")
        with docker_run(
            compose_file=compose_file,
            conditions=[CheckDockerLogs(compose_file, 'LINKERD DEPLOY COMPLETE', wait=5, attempts=120)],
            attempts=2,
        ):
            wait_for_linkerd_control_plane_ready(kubeconfig)

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
