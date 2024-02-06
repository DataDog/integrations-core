# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from contextlib import ExitStack

import pytest

from datadog_checks.dev import get_here, run_command
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward

HERE = get_here()


def setup_tekton():
    run_command(["kubectl", "create", "namespace", "tekton-operator"])
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, "kind", "tekton-operator.yaml"), "-n", "tekton-operator"])
    run_command(
        ["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s", "-n", "tekton-operator"]
    )
    time.sleep(60)
    run_command(
        [
            "kubectl",
            "wait",
            "pods",
            "-l",
            "run=tekton-dashboard",
            "--for=condition=Ready",
            "--timeout=300s",
            "-n",
            "tekton-pipelines",
        ]
    )


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    # https://github.com/tektoncd/dashboard/blob/main/docs/walkthrough/walkthrough-kind.md
    with kind_run(conditions=[setup_tekton], sleep=30) as kubeconfig, ExitStack() as stack:
        instances = []

        pipeline_host, pipeline_port = stack.enter_context(
            port_forward(kubeconfig, 'tekton-pipelines', 9090, 'service', 'tekton-pipelines-controller')
        )
        instances.append({'openmetrics_endpoint': f'http://{pipeline_host}:{pipeline_port}/metrics'})

        trigger_host, trigger_port = stack.enter_context(
            port_forward(kubeconfig, 'tekton-pipelines', 9000, 'service', 'tekton-triggers-controller')
        )
        instances.append({'openmetrics_endpoint': f'http://{trigger_host}:{trigger_port}/metrics'})

        # We can't add this to `kind_run` because we don't know the URL at this moment
        for instance in instances:
            condition = CheckEndpoints(instance['openmetrics_endpoint'])
            condition()

        yield {'instances': instances}


@pytest.fixture
def instance():
    return {}
