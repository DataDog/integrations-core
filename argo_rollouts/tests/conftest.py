# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()


def setup_argo_rollouts():
    run_command(['kubectl', 'create', 'ns', 'argo-rollouts'])
    run_command(
        ['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'argo_rollouts_install.yaml'), '-n', 'argo-rollouts']
    )

    # Tries to ensure that the Kubernetes resources are deployed and ready before we do anything else
    run_command(['kubectl', 'rollout', 'status', 'deployment/argo-rollouts', '-n', 'argo-rollouts'])
    run_command(['kubectl', 'wait', 'pods', '--all', '-n', 'argo-rollouts', '--for=condition=Ready', '--timeout=600s'])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_argo_rollouts], sleep=30) as kubeconfig:
        instances = [
            {'openmetrics_endpoint': 'http://argo-rollouts-metrics.argo-rollouts.svc.cluster.local:8090/metrics'}
        ]

        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield {'instances': instances}, metadata
