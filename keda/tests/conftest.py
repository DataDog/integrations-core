# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
from contextlib import ExitStack

import pytest

from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from . import common

HERE = common.HERE


def setup_ked():
    run_command(['kubectl', 'create', 'ns', 'keda'])
    run_command(['kubectl', 'apply', '-f', os.path.join(HERE, 'kind', 'keda_install.yaml')])

    # Tries to ensure that the Kubernetes resources are deployed and ready before we do anything else
    run_command(['kubectl', 'rollout', 'status', 'deployment/keda-operator-metrics-apiserver', '-n', 'keda'])
    run_command(['kubectl', 'wait', 'pods', '--all', '-n', 'keda', '--for=condition=Ready', '--timeout=600s'])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_ked], sleep=30) as kubeconfig, ExitStack() as stack:
        keda_host, keda_port = stack.enter_context(
            port_forward(kubeconfig, 'keda', 8080, 'deployment', 'keda-operator-metrics-apiserver')
        )
        instances = [{'openmetrics_endpoint': f'http://{keda_host}:{keda_port}/metrics'}]

        yield {'instances': instances}


@pytest.fixture
def instance():
    return copy.deepcopy(common.MOCKED_INSTANCE)
