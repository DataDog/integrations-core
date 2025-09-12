# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack

import pytest

from datadog_checks.dev import get_here, run_command
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward

HERE = get_here()


def _wait_for_resource(*, kind, name, condition, namespace=None, timeout="300s"):
    """A helper function to run `kubectl wait` with a standard set of arguments."""
    command = ["kubectl", "wait", kind, name, f"--for=condition={condition}", f"--timeout={timeout}"]
    if namespace:
        command.extend(["-n", namespace])
    run_command(command)


def setup_tekton():
    run_command(["kubectl", "create", "namespace", "tekton-operator"])
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, "kind", "tekton-operator.yaml"), "-n", "tekton-operator"])

    print("Waiting for tekton-operator to be ready...")
    _wait_for_resource(kind="deployment", name="tekton-operator", condition="Available", namespace="tekton-operator")

    print("Applying TektonPipeline and TektonTrigger CRs to trigger installation...")
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, "kind", "tekton-pipeline-install.yaml")])
    run_command(["kubectl", "apply", "-f", os.path.join(HERE, "kind", "tekton-trigger-install.yaml")])

    print("Waiting for Tekton Pipelines to be ready...")
    _wait_for_resource(kind="tektonpipeline", name="pipeline", condition="Ready")

    print("Waiting for Tekton Triggers to be ready...")
    _wait_for_resource(kind="tektontrigger", name="trigger", condition="Ready")

    resource_definitions = ["pipeline", "task"]
    actions = ["hello", "bye"]

    # Apply all configurations: definitions (pipeline, task) and runs (pipelinerun, taskrun)
    for resource in resource_definitions + [f"{r}run" for r in resource_definitions]:
        for action in actions:
            run_command(
                [
                    "kubectl",
                    "apply",
                    "-f",
                    os.path.join(HERE, "kind", f"tekton-{resource}-{action}.yaml"),
                    "-n",
                    "tekton-pipelines",
                ]
            )

    for action in actions:
        for definition in resource_definitions:
            kind = f"{definition}run"
            name = f"{action}-{definition}-run"
            _wait_for_resource(kind=kind, name=name, condition="Succeeded", namespace="tekton-pipelines")


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_tekton], sleep=10) as kubeconfig, ExitStack() as stack:
        instances = {}

        pipeline_host, pipeline_port = stack.enter_context(
            port_forward(kubeconfig, 'tekton-pipelines', 9090, 'service', 'tekton-pipelines-controller')
        )
        instances['pipelines_controller_endpoint'] = f'http://{pipeline_host}:{pipeline_port}/metrics'

        trigger_host, trigger_port = stack.enter_context(
            port_forward(kubeconfig, 'tekton-pipelines', 9000, 'service', 'tekton-triggers-controller')
        )
        instances['triggers_controller_endpoint'] = f'http://{trigger_host}:{trigger_port}/metrics'

        yield {'instances': [instances]}


@pytest.fixture
def pipelines_instance():
    return {
        "pipelines_controller_endpoint": "http://tekton-pipelines:9090",
    }


@pytest.fixture
def triggers_instance():
    return {
        "triggers_controller_endpoint": "http://tekton-triggers:9000",
    }
