# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import shlex

import pytest

from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

KUMA_NAMESPACE = 'kuma-system'
KUMA_SERVICE = 'kuma-control-plane'
KUMA_STARTUP_TIMEOUT = 600
KUMA_METRICS_ENDPOINT = f'http://{KUMA_SERVICE}.{KUMA_NAMESPACE}.svc.cluster.local:5680/metrics'
KUMA_SOURCE_COMMAND = shlex.join(
    [
        '/opt/datadog-agent/embedded/bin/python3',
        '-c',
        "import datadog_checks.kuma; print('Resolved Kuma module source:', datadog_checks.kuma.__file__)",
    ]
)


def setup_kuma():
    kuma_version = os.environ.get('KUMA_VERSION', '2.10.6')
    run_command(['kubectl', 'create', 'namespace', KUMA_NAMESPACE], check=True)
    run_command(['helm', 'repo', 'add', 'kuma', 'https://kumahq.github.io/charts'], check=True)
    run_command(['helm', 'repo', 'update'], check=True)
    run_command(
        [
            'helm',
            'upgrade',
            '--install',
            'kuma',
            'kuma/kuma',
            '--version',
            kuma_version,
            '--create-namespace',
            '-n',
            KUMA_NAMESPACE,
        ],
        check=True,
    )
    run_command(
        [
            'kubectl',
            'rollout',
            'status',
            f'deployment/{KUMA_SERVICE}',
            '-n',
            KUMA_NAMESPACE,
            # The Kuma deployment's readiness probe checks its in-cluster /ready endpoint.
            f'--timeout={KUMA_STARTUP_TIMEOUT}s',
        ],
        check=True,
    )


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_kuma]) as kubeconfig:
        instance = {'openmetrics_endpoint': KUMA_METRICS_ENDPOINT}
        metadata = {
            'agent_type': 'kubernetes',
            'kubernetes': {
                'kubeconfig': kubeconfig,
            },
            'post_install_commands': [KUMA_SOURCE_COMMAND],
        }

        dd_save_state('kuma_instance', instance)
        yield instance, metadata


@pytest.fixture(scope='session')
def instance(dd_get_state):
    return dd_get_state(
        'kuma_instance',
        default={
            'openmetrics_endpoint': 'http://localhost:5680/metrics',
        },
    )
