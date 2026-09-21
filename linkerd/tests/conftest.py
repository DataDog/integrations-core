# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import os

import pytest

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.kind import kind_run

from .common import HERE, LINKERD_FIXTURE_METRICS, LINKERD_FIXTURE_TYPES

LINKERD_CONTROLLER_POD_IP_STATE = 'linkerd_controller_pod_ip'


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


def save_linkerd_controller_pod_ip() -> None:
    result = run_command(
        [
            'kubectl',
            'get',
            'pods',
            '--namespace',
            'linkerd',
            '--selector',
            'linkerd.io/control-plane-component=controller',
            '--output',
            'json',
        ],
        capture='out',
        check=True,
    )
    pods = json.loads(result.stdout)['items']
    if len(pods) != 1 or not pods[0].get('status', {}).get('podIP'):
        raise RuntimeError(f'Expected one Linkerd controller pod with an IP, found {len(pods)}')
    save_state(LINKERD_CONTROLLER_POD_IP_STATE, pods[0]['status']['podIP'])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_linkerd_cluster]) as kubeconfig:
        compose_file = os.path.join(HERE, "compose", "docker-compose.yaml")
        with docker_run(
            compose_file=compose_file,
            conditions=[
                CheckDockerLogs(compose_file, 'LINKERD DEPLOY COMPLETE', wait=5, attempts=120),
                save_linkerd_controller_pod_ip,
            ],
            attempts=2,
        ):
            controller_ip = get_state(LINKERD_CONTROLLER_POD_IP_STATE)
            instance = {
                'prometheus_url': f'http://{controller_ip}:4191/metrics',
                'metrics': [LINKERD_FIXTURE_METRICS],
                'type_overrides': LINKERD_FIXTURE_TYPES,
            }
            metadata = {
                'agent_type': 'kubernetes',
                'kubernetes': {
                    'kubeconfig': kubeconfig,
                },
            }
            yield instance, metadata
