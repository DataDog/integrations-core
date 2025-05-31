# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack
from copy import deepcopy

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

HERE = get_here()
opj = os.path.join


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('kuma_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def setup_kuma():
    run_command(["kubectl", "create", "namespace", "kuma-system"])
    run_command(["helm", "repo", "add", "kuma", "https://kumahq.github.io/charts"])
    run_command(["helm", "repo", "update"])
    run_command(["helm", "upgrade", "--install", "--create-namespace", "kuma", "kuma/kuma", "-n", "kuma-system"])
    run_command(
        ["kubectl", "rollout", "status", "deployment/kuma-control-plane", "-n", "kuma-system", "--timeout=90s"]
    )
    run_command(["kubectl", "apply", "-R", "-f", opj(HERE, "manifests", "mesh")])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_kuma]) as kubeconfig:
        with ExitStack() as stack:
            # Setup port forwards based on the ports defined in the justfile
            kuma_metrics_url, kuma_metrics_port = stack.enter_context(
                port_forward(kubeconfig, 'kuma-system', 5680, 'service', 'kuma-control-plane')
            )

            kuma_api_url, kuma_api_port = stack.enter_context(
                port_forward(kubeconfig, 'kuma-system', 5681, 'service', 'kuma-control-plane')
            )

            metrics_endpoint = f'http://{kuma_metrics_url}:{kuma_metrics_port}/metrics'
            api_endpoint = f'http://{kuma_api_url}:{kuma_api_port}'

            instance = {
                'openmetrics_endpoint': metrics_endpoint,
                # 'kuma_api_endpoint': api_endpoint,
            }

            dd_save_state("kuma_instance", instance)

            yield instance


@pytest.fixture
def instance():
    return {
        'openmetrics_endpoint': 'http://localhost:5680/metrics',
        'kuma_api_endpoint': 'http://localhost:5681',
    }
