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


@pytest.fixture(scope='session')
def dd_environment():
    kind_config = os.path.join(HERE, 'kind', 'kind-linkerd.yaml')
    with kind_run(conditions=[setup_linkerd_cluster], kind_config=kind_config) as kubeconfig:
        compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
        with docker_run(
            compose_file=compose_file,
            build=True,
            conditions=[CheckDockerLogs(compose_file, 'LINKERD DEPLOY COMPLETE', wait=5, attempts=120)],
            attempts=2,
        ):
            instance = {
                'prometheus_url': 'http://linkerd-controller-proxy-metrics.linkerd.svc.cluster.local:4191/metrics',
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
