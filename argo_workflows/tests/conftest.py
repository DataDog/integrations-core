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


def setup_argo_wf():
    run_command(["kubectl", "create", "ns", "argo"])
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, 'kind', "quick-start-minimal.yaml"), "-n", "argo"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "argo", "--timeout=300s"]
    )
    # run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_argo_wf]) as kubeconfig:
        with ExitStack() as stack:
            controller_host, controller_port = stack.enter_context(
                # there is no service for workflow-controller
                port_forward(kubeconfig, 'argo', 9090, 'deployment', 'workflow-controller')
            )
            # save this instance to use for openmetrics_v2 instance, since the endpoint is different each run
            # dd_save_state("argocd_instance", instance)

            yield {'openmetrics_endpoint': f'http://{controller_host}:{controller_port}/metrics'}


@pytest.fixture
def instance():
    return {}
