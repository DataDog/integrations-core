# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from unittest import mock

import pytest

from datadog_checks.dev import get_here
from datadog_checks.dev._env import get_state, save_state
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command
from datadog_checks.fluxcd import FluxcdCheck

HERE = get_here()
opj = os.path.join

# The Services in flux-system (source-controller, notification-controller) only expose the
# controllers' API port (9090) as port 80, not the Prometheus metrics port (8080), so Service DNS
# cannot reach /metrics for any controller. All four controllers are single-replica Deployments, so
# their pod IP is fetched directly and used to reach the metrics port. The `allow-scraping`
# NetworkPolicy shipped in install.yaml explicitly permits cross-namespace ingress on port 8080,
# confirming this is the intended scrape path.
CONTROLLERS = ('source-controller', 'helm-controller', 'kustomize-controller', 'notification-controller')
METRICS_PORT = 8080
POD_IP_STATE_PREFIX = 'fluxcd_pod_ip_'


def setup_fluxcd():
    run_command(["kubectl", "apply", "--filename", opj(HERE, 'kind', "install.yaml")])
    run_command(
        [
            "kubectl",
            "wait",
            "deployments",
            "--all",
            "--for=condition=Available",
            "--namespace",
            "flux-system",
            "--timeout=300s",
        ]
    )
    # Save each controller's pod IP now, while the cluster is guaranteed to be up. `dd_environment`
    # runs again (without `conditions`, so without this function) on every `ddev env` invocation,
    # including `stop`, when the cluster may already be gone.
    for controller in CONTROLLERS:
        save_state(POD_IP_STATE_PREFIX + controller, get_controller_pod_ip(controller))


def get_controller_pod_ip(controller):
    result = run_command(
        [
            "kubectl",
            "get",
            "pods",
            "--namespace",
            "flux-system",
            "--selector",
            f"app={controller}",
            "--output",
            "json",
        ],
        capture='out',
        check=True,
    )
    pods = json.loads(result.stdout)['items']
    if len(pods) != 1 or not pods[0].get('status', {}).get('podIP'):
        raise RuntimeError(f'Expected exactly one ready {controller} pod, found {len(pods)}')
    return pods[0]['status']['podIP']


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_fluxcd]) as kubeconfig:
        instances = [
            {
                'openmetrics_endpoint': f'http://{get_state(POD_IP_STATE_PREFIX + controller)}:{METRICS_PORT}/metrics',
            }
            for controller in CONTROLLERS
        ]

        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield {'instances': instances}, metadata


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": "http://localhost:3000/metrics",
    }


@pytest.fixture
def check(instance):
    return FluxcdCheck("fluxcd", {}, [instance])


@pytest.fixture()
def mock_metrics_v1():
    fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "metrics-v1.txt")

    with open(fixture_file, "r") as f:
        content = f.read()

    with mock.patch(
        "requests.Session.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: content.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield


@pytest.fixture()
def mock_metrics_v2():
    fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "metrics-v2.txt")

    with open(fixture_file, "r") as f:
        content = f.read()

    with mock.patch(
        "requests.Session.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: content.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield


@pytest.fixture()
def mock_metrics_ksm():
    fixture_file = os.path.join(os.path.dirname(__file__), "fixtures", "metrics-ksm.txt")

    with open(fixture_file, "r") as f:
        content = f.read()

    with mock.patch(
        "requests.Session.get",
        return_value=mock.MagicMock(
            status_code=200,
            iter_lines=lambda **kwargs: content.split("\n"),
            headers={"Content-Type": "text/plain"},
        ),
    ):
        yield
