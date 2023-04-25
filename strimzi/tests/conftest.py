# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os.path
from contextlib import ExitStack
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here, run_command
from datadog_checks.dev.kind import kind_run
from datadog_checks.strimzi import StrimziCheck

from datadog_checks.dev.kube_port_forward import port_forward
from .common import STRIMZI_VERSION

HERE = get_here()


def setup_strimzi():
    run_command(["kubectl", "create", "namespace", "kafka"])
    run_command(
        ["kubectl", "create", "-f", os.path.join(HERE, "kind", STRIMZI_VERSION, "strimzi_install.yaml"), "-n", "kafka"]
    )
    run_command(
        [
            "kubectl",
            "apply",
            "-f",
            os.path.join(HERE, "kind", STRIMZI_VERSION, "kafka.yaml"),
            "-n",
            "kafka",
        ]
    )
    run_command(["kubectl", "wait", "kafka/my-cluster", "--for=condition=Ready", "--timeout=300s", "-n", "kafka"])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_strimzi]) as kubeconfig:
        with ExitStack() as stack:
            host, port = stack.enter_context(
                port_forward(kubeconfig, 'kafka', 8080, 'deployment', 'strimzi-cluster-operator')
            )

            instance = {
                "openmetrics_endpoint": f"http://{host}:{port}/metrics",
            }

            # save this instance since the endpoint is different each run
            dd_save_state("strimzi_instance", instance)

            yield instance


@pytest.fixture
def instance(dd_get_state):
    return deepcopy(dd_get_state('strimzi_instance', default={}))


@pytest.fixture()
def check():
    return lambda instance: StrimziCheck('strimzi', {}, [instance])
