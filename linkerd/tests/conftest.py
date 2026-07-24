# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import pytest

from datadog_checks.dev import docker_run, run_command
from datadog_checks.dev.conditions import CheckDockerLogs
from datadog_checks.dev.kind import kind_run

from .common import HERE, LINKERD_FIXTURE_METRICS, LINKERD_FIXTURE_TYPES


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


def get_linkerd_container_ip(compose_file: str) -> str:
    result = run_command(['docker', 'compose', '-f', compose_file, 'ps', '-q', 'linkerd'], capture='out', check=True)
    container_id = result.stdout.strip()
    docker_network_template = (
        '{{range $name, $network := .NetworkSettings.Networks}}'
        '{{if eq $name "kind"}}{{$network.IPAddress}}{{end}}'
        '{{end}}'
    )
    result = run_command(
        [
            'docker',
            'inspect',
            '-f',
            docker_network_template,
            container_id,
        ],
        capture='out',
        check=True,
    )
    return result.stdout.strip()


@pytest.fixture(scope='session')
def dd_environment():
    kind_config = os.path.join(HERE, 'kind', 'kind-linkerd.yaml')
    with kind_run(conditions=[setup_linkerd_cluster], kind_config=kind_config):
        compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
        with docker_run(
            compose_file=compose_file,
            build=True,
            conditions=[CheckDockerLogs(compose_file, 'LINKERD DEPLOY COMPLETE', wait=5, attempts=120)],
            attempts=2,
        ):
            ip = get_linkerd_container_ip(compose_file)
            instance = {
                'prometheus_url': 'http://{}:4191/metrics'.format(ip),
                'metrics': [LINKERD_FIXTURE_METRICS],
                'type_overrides': LINKERD_FIXTURE_TYPES,
            }
            yield instance
