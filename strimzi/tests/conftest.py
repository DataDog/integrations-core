# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os.path

import pytest

from datadog_checks.dev import get_docker_hostname, get_here, run_command
from datadog_checks.dev.kind import kind_run
from datadog_checks.strimzi import StrimziCheck

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
def dd_environment():
    with kind_run(conditions=[setup_strimzi]):
        # TODO forward the ports
        # with ExitStack() as stack:
        # app_controller_host, app_controller_port = stack.enter_context(
        #     port_forward(kubeconfig, 'kafka', 8082, 'service', 'my-service')
        # )

        yield {
            "openmetrics_endpoint": f"http://{get_docker_hostname()}:1234/metrics",
        }


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": f"http://{get_docker_hostname()}:1234/metrics",
    }


@pytest.fixture()
def check():
    return lambda instance: StrimziCheck('strimzi', {}, [instance])
