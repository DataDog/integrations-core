# (C) Datadog, Inc. 2024-present
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
    openmetrics_v2 = deepcopy(dd_get_state('traefik_instance', default={}))
    openmetrics_v2['use_openmetrics'] = 'true'
    return openmetrics_v2


def setup_traefik_mesh():
    run_command(["kubectl", "create", "namespace", "traefik-mesh"])
    # SMI CRDs are not installed by the Helm chart, so we need to install them manually
    run_command(
        [
            "kubectl",
            "apply",
            "--server-side",
            "--force-conflicts",
            "-k",
            "https://github.com/traefik/mesh-helm-chart/mesh/crds/",
            "-n",
            "traefik-mesh",
        ]
    )
    run_command(["kubectl", "apply", "-f", opj(HERE, "kind", "traefik_mesh.yaml"), "-n", "traefik-mesh"])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "traefik-mesh", "--timeout=90s"]
    )
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=90s"])


@pytest.fixture(scope='session')
def dd_environment(dd_save_state):
    with kind_run(conditions=[setup_traefik_mesh]) as kubeconfig:
        with ExitStack() as stack:

            traefik_controller_api_url, traefik_controller_api_port = stack.enter_context(
                port_forward(kubeconfig, 'traefik-mesh', 9000, 'service', 'traefik-mesh-controller')
            )

            traefik_proxy_url, traefik_proxy_port = stack.enter_context(
                port_forward(kubeconfig, 'traefik-mesh', 8080, 'daemonset', 'traefik-mesh-proxy')
            )

            traefik_proxy_endpoint = f'http://{traefik_proxy_url}:{traefik_proxy_port}/metrics'
            traefik_controller_api_endpoint = f'http://{traefik_controller_api_url}:{traefik_controller_api_port}'

            instance = {
                'openmetrics_endpoint': traefik_proxy_endpoint,
                'traefik_proxy_api_endpoint': traefik_proxy_endpoint,
                'traefik_controller_api_endpoint': traefik_controller_api_endpoint,
            }

            dd_save_state("traefik_instance", instance)

        yield instance
