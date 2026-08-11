# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

HERE = get_here()


def setup_argo_wf():
    run_command(["kubectl", "create", "ns", "argo"])
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, 'kind', "quick-start-minimal.yaml"), "-n", "argo"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "argo", "--timeout=300s"]
    )
    # run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])


def get_workflow_controller_pod_ip() -> str:
    # There is no Service for workflow-controller, so the pod IP is fetched directly.
    result = run_command(
        ["kubectl", "get", "pods", "--namespace", "argo", "--selector", "app=workflow-controller", "--output", "json"],
        capture='out',
        check=True,
    )
    pods = json.loads(result.stdout)['items']
    if len(pods) != 1 or not pods[0].get('status', {}).get('podIP'):
        raise RuntimeError(f'Expected exactly one ready workflow-controller pod, found {len(pods)}')
    return pods[0]['status']['podIP']


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_argo_wf]) as kubeconfig:
        controller_ip = get_workflow_controller_pod_ip()
        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield {'openmetrics_endpoint': f'http://{controller_ip}:9090/metrics'}, metadata


@pytest.fixture
def instance():
    return {}
