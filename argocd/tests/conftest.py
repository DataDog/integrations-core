# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

# from json.encoder import py_encode_basestring


try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = get_here()
opj = os.path.join


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('argocd_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def setup_argocd():
    run_command(["kubectl", "create", "ns", "argocd"])
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "argocd_install.yaml"), "-n", "argocd"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "argocd", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_argocd]) as kubeconfig:
        with ExitStack() as stack:
            argocd_host, argocd_port = stack.enter_context(
                port_forward(kubeconfig, 'argocd', 8082, 'service', 'argocd-metrics')
            )

            argocd_endpoint = 'http://{}:{}/metrics'.format(argocd_host, argocd_port)
            instance = {'argocd_endpoint': argocd_endpoint, 'use_openmetrics': 'false'}

            # save this instance to use for openmetrics_v2 instance, since the endpoint is different each run
            dd_save_state("argocd_instance", instance)

            yield instance
