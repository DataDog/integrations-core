# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
opj = os.path.join


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('argocd_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def setup_argocd():
    run_command(["kubectl", "create", "ns", "argocd"])
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "argocd_install.yaml"), "-n", "argocd"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "argocd", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_argocd]) as kubeconfig:
        instance = {
            'app_controller_endpoint': 'http://argocd-metrics.argocd.svc.cluster.local:8082/metrics',
            'appset_controller_endpoint': (
                'http://argocd-applicationset-controller.argocd.svc.cluster.local:8080/metrics'
            ),
            'api_server_endpoint': 'http://argocd-server-metrics.argocd.svc.cluster.local:8083/metrics',
            'repo_server_endpoint': 'http://argocd-repo-server.argocd.svc.cluster.local:8084/metrics',
            'notifications_controller_endpoint': (
                'http://argocd-notifications-controller-metrics.argocd.svc.cluster.local:9001/metrics'
            ),
        }
        metadata = {
            'agent_type': 'kubernetes',
            'kubernetes': {
                'kubeconfig': kubeconfig,
            },
        }

        # Save this instance to use for the openmetrics_v2 instance.
        dd_save_state("argocd_instance", instance)

        yield instance, metadata
