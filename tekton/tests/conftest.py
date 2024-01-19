# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time

import pytest

from datadog_checks.dev import get_here, run_command
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward

HERE = get_here()


def setup_tekton():
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, 'kind', "ingress-nginx.yaml")])
    time.sleep(30)
    run_command(
        [
            "kubectl",
            "wait",
            "-n",
            "ingress-nginx",
            "--for=condition=ready",
            "pod",
            "--selector=app.kubernetes.io/component=controller",
            "--timeout=120s",
        ]
    )

    run_command(["kubectl", "apply", "-f", os.path.join(HERE, 'kind', "tekton-pipelines.yaml")])
    time.sleep(30)
    run_command(
        [
            "kubectl",
            "wait",
            "-n",
            "tekton-pipelines",
            "--for=condition=ready",
            "pod",
            "--selector=app.kubernetes.io/part-of=tekton-pipelines,app.kubernetes.io/component=controller",
            "--timeout=120s",
        ]
    )

    run_command(
        [
            "curl",
            "-sL",
            "https://raw.githubusercontent.com/tektoncd/dashboard/main/scripts/release-installer",
            "-o",
            "/tmp/release-installer.bash",
        ]
    )
    run_command(
        [
            "bash",
            "/tmp/release-installer.bash",
            "install",
            "latest",
            "--read-write",
            "--ingress-url",
            "tekton-dashboard.127.0.0.1.nip.io",
        ]
    )
    time.sleep(5)
    run_command(
        [
            "kubectl",
            "wait",
            "-n",
            "tekton-pipelines",
            "--for=condition=ready",
            "pod",
            "--selector=app.kubernetes.io/part-of=tekton-dashboard,app.kubernetes.io/component=dashboard",
            "--timeout=120s",
        ]
    )

    run_command(["kubectl", "create", "ns", "test"])
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, 'kind', "service-account.yaml")])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    # https://github.com/tektoncd/dashboard/blob/main/docs/walkthrough/walkthrough-kind.md
    with kind_run(kind_config=os.path.join(HERE, 'kind', "cluster.yaml"), conditions=[setup_tekton]) as kubeconfig:
        with port_forward(kubeconfig, 'tekton-pipelines', 9090, 'service', 'tekton-pipelines-controller') as (
            controller_host,
            controller_port,
        ):
            endpoint = f'http://{controller_host}:{controller_port}/metrics'
            instance = {'openmetrics_endpoint': endpoint}

            # We can't add this to `kind_run` because we don't know the URL at this moment
            condition = CheckEndpoints(endpoint)
            condition()

            # save this instance to use for openmetrics_v2 instance, since the endpoint is different each run
            dd_save_state("tekton_instance", instance)

            yield instance


@pytest.fixture
def instance():
    return {}
