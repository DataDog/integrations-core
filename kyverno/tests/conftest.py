# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
CHECK_ROOT = os.path.dirname(HERE)


def setup_kyverno():
    run_command(['kubectl', 'create', 'ns', 'kyverno'])
    run_command(['kubectl', 'create', '-f', os.path.join(HERE, 'kind', 'kyverno_install.yaml')])
    run_command(['kubectl', 'create', '-f', os.path.join(HERE, 'kind', 'kyverno-policies_install.yaml')])

    # Tries to ensure that the Kubernetes resources are deployed and ready before we do anything else
    deployments = [
        'kyverno-admission-controller',
        'kyverno-background-controller',
        'kyverno-cleanup-controller',
        'kyverno-reports-controller',
    ]
    for deployment in deployments:
        run_command(['kubectl', 'rollout', 'status', f'deployment/{deployment}', '-n', 'kyverno'])

    run_command(['kubectl', 'wait', 'pods', '--all', '-n', 'kyverno', '--for=condition=Ready', '--timeout=600s'])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_kyverno], sleep=30) as kubeconfig:
        dd_save_state('kyverno_kubeconfig', kubeconfig)
        instances = [
            {'openmetrics_endpoint': 'http://kyverno-svc-metrics.kyverno.svc.cluster.local:8000/metrics'},
            {
                'openmetrics_endpoint': (
                    'http://kyverno-background-controller-metrics.kyverno.svc.cluster.local:8000/metrics'
                )
            },
            {
                'openmetrics_endpoint': (
                    'http://kyverno-cleanup-controller-metrics.kyverno.svc.cluster.local:8000/metrics'
                )
            },
            {
                'openmetrics_endpoint': (
                    'http://kyverno-reports-controller-metrics.kyverno.svc.cluster.local:8000/metrics'
                )
            },
        ]
        metadata = {
            'agent_type': 'kubernetes',
            'kubernetes': {
                'kubeconfig': kubeconfig,
                'auto_conf': os.path.join(CHECK_ROOT, 'datadog_checks', 'kyverno', 'data', 'auto_conf.yaml'),
            },
        }

        yield {'instances': instances}, metadata


@pytest.fixture(scope='session')
def kyverno_kubeconfig(dd_get_state):
    return dd_get_state('kyverno_kubeconfig')
