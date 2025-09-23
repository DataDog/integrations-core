# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

HERE = get_here()


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
def dd_environment():
    with kind_run(conditions=[setup_kyverno], sleep=30) as kubeconfig, ExitStack() as stack:
        kyverno_host1, kyverno_port1 = stack.enter_context(
            port_forward(kubeconfig, 'kyverno', 8000, 'deployment', 'kyverno-admission-controller'),
        )
        kyverno_host2, kyverno_port2 = stack.enter_context(
            port_forward(kubeconfig, 'kyverno', 8000, 'deployment', 'kyverno-background-controller'),
        )
        kyverno_host3, kyverno_port3 = stack.enter_context(
            port_forward(kubeconfig, 'kyverno', 8000, 'deployment', 'kyverno-cleanup-controller'),
        )
        kyverno_host4, kyverno_port4 = stack.enter_context(
            port_forward(kubeconfig, 'kyverno', 8000, 'deployment', 'kyverno-reports-controller'),
        )
        instances = [
            {'openmetrics_endpoint': f'http://{kyverno_host1}:{kyverno_port1}/metrics'},
            {'openmetrics_endpoint': f'http://{kyverno_host2}:{kyverno_port2}/metrics'},
            {'openmetrics_endpoint': f'http://{kyverno_host3}:{kyverno_port3}/metrics'},
            {'openmetrics_endpoint': f'http://{kyverno_host4}:{kyverno_port4}/metrics'},
        ]

        yield {'instances': instances}
