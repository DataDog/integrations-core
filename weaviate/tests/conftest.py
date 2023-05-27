# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = get_here()
opj = os.path.join


def setup_weaviate():
    run_command(["kubectl", "create", "ns", "weaviate"])
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "weaviate_install.yaml"), "-n", "weaviate"])
    run_command(
        ["kubectl", "wait", "statefulset", "--all", "--for=condition=Available", "-n", "weaviate", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_weaviate]) as kubeconfig:
        with ExitStack() as stack:
            weaviate_host, weaviate_port = stack.enter_context(
                port_forward(kubeconfig, 'weaviate', 2112, 'statefulset', 'weaviate')
            )
            instance = {
                "openmetrics_endpoint": 'http://{}:{}/metrics'.format(weaviate_host, weaviate_port)
            }
            yield instance

@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": 'http://localhost:2112/metrics',
    }