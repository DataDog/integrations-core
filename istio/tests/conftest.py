# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

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
VERSION = os.environ.get("ISTIO_VERSION")
opj = os.path.join


def setup_istio():
    run_command(
        [
            "curl",
            "-o",
            "istio.tar.gz",
            "-L",
            "https://github.com/istio/istio/releases/download/{version}/istio-{version}-linux.tar.gz".format(
                version=VERSION
            ),
        ]
    )
    run_command(["tar", "xf", "istio.tar.gz"])
    run_command(["kubectl", "create", "ns", "istio-system"])
    # Istio directory name
    istio = "istio-{}".format(VERSION)
    # Install demo profile
    run_command(["kubectl", "apply", "-f", opj(HERE, 'kind', "demo_profile.yaml")])
    # Wait for istio deployments
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "istio-system", "--timeout=300s"]
    )
    # Enable sidecar injection
    run_command(["kubectl", "label", "namespace", "default", "istio-injection=enabled"])
    # run_command(["kubectl", "label", "namespace", "istio-system", "istio-injection=enabled"])
    # Install sample application
    run_command(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "platform", "kube", "bookinfo.yaml")])
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])

    run_command(["kubectl", "apply", "-f", opj(istio, "samples", "bookinfo", "networking", "bookinfo-gateway.yaml")])
    run_command(["kubectl", "wait", "pods", "--all", "--for=condition=Ready", "--timeout=300s"])


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(conditions=[setup_istio]) as kubeconfig:
        with ExitStack() as stack:
            if VERSION == '1.5.1':
                istiod_host, istiod_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', 8080, 'deployment', 'istiod')
                )

                istio_mesh_host, istio_mesh_port = stack.enter_context(
                    port_forward(kubeconfig, 'istio-system', 8080, 'deployment', 'istio-proxy')
                )

                instance = {'istiod_endpoint': 'http://{}:{}/metrics'.format(istiod_host, istiod_port),
                            'istio_mesh_endpoint': 'http://{}:{}/metrics'.format(istio_mesh_host, istio_mesh_port)
                            }

                yield instance
