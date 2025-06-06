# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import time
from contextlib import ExitStack
from copy import deepcopy

import pytest
import requests

from datadog_checks.dev import get_here
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

HERE = get_here()


@pytest.fixture
def instance_openmetrics_v2(dd_get_state):
    openmetrics_v2 = deepcopy(dd_get_state('kuma_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def setup_kuma():
    kuma_version = os.environ.get("KUMA_VERSION", "2.10.1")
    run_command(["kubectl", "create", "namespace", "kuma-system"])
    run_command(["helm", "repo", "add", "kuma", "https://kumahq.github.io/charts"])
    run_command(["helm", "repo", "update"])
    run_command(
        [
            "helm",
            "upgrade",
            "--install",
            "kuma",
            "kuma/kuma",
            "--version",
            kuma_version,
            "--create-namespace",
            "-n",
            "kuma-system",
        ]
    )
    run_command(
        ["kubectl", "rollout", "status", "deployment/kuma-control-plane", "-n", "kuma-system", "--timeout=180s"]
    )


def wait_for_kuma_readiness(api_url, api_port, max_wait=120):
    """Wait for Kuma control plane to be ready by querying the /config endpoint."""
    config_url = f'http://{api_url}:{api_port}/config'
    start_time = time.monotonic()

    while time.monotonic() - start_time < max_wait:
        try:
            response = requests.get(config_url, timeout=5)
            if response.status_code == 200:
                print(f"Kuma control plane is ready at {config_url} (took {time.monotonic() - start_time} seconds)")
                return
        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            pass

        print(f"Waiting for Kuma control plane to be ready at {config_url}...")
        time.sleep(1)

    raise TimeoutError(f"Kuma control plane did not become ready within {max_wait} seconds")


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_kuma]) as kubeconfig:
        with ExitStack() as stack:
            kuma_metrics_url, kuma_metrics_port = stack.enter_context(
                port_forward(kubeconfig, 'kuma-system', 5680, 'service', 'kuma-control-plane')
            )
            kuma_api_url, kuma_api_port = stack.enter_context(
                port_forward(kubeconfig, 'kuma-system', 5681, 'service', 'kuma-control-plane')
            )

            # Wait for Kuma control plane to be ready
            wait_for_kuma_readiness(kuma_api_url, kuma_api_port)

            metrics_endpoint = f'http://{kuma_metrics_url}:{kuma_metrics_port}/metrics'

            instance = {
                'openmetrics_endpoint': metrics_endpoint,
            }

            dd_save_state("kuma_instance", instance)

            yield instance


@pytest.fixture
def instance():
    return {
        'openmetrics_endpoint': 'http://localhost:5680/metrics',
    }
