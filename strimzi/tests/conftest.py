# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os.path
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here, run_command
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
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
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_strimzi]) as kubeconfig:
        with port_forward(kubeconfig, 'kafka', 8080, 'deployment', 'strimzi-cluster-operator') as (host, port):
            instance = {
                "openmetrics_endpoint": f"http://{host}:{port}/metrics",
            }

            # save this instance since the endpoint is different each run
            dd_save_state("strimzi_instance", instance)

            yield instance


@pytest.fixture
def instance(dd_get_state):
    # We define a default value for unit tests, which are using a mock
    return deepcopy(dd_get_state('strimzi_instance', default={"openmetrics_endpoint": "http://strimzi:8080/metrics"}))


@pytest.fixture
def tags(instance):
    return [f'endpoint:{instance["openmetrics_endpoint"]}']


@pytest.fixture()
def check():
    return lambda instance: StrimziCheck('strimzi', {}, [instance])
