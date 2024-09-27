# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import ExitStack

import pytest

from datadog_checks.dev import get_here, run_command
from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward

HERE = get_here()
KUBEVIRT_VERSION = "v1.2.2"


def setup_kubevirt():
    # deploy the KubeVirt operator
    run_command(["kubectl", "create", "-f", os.path.join(HERE, "kind", "kubevirt-operator.yaml")])

    # deploy the KubeVirt Custom Resource Definitions
    run_command(["kubectl", "create", "-f", os.path.join(HERE, "kind", "kubevirt-cr.yaml")])

    # enable nested virtualization
    run_command(
        [
            "kubectl",
            "-n",
            "kubevirt",
            "patch",
            "kubevirt",
            "kubevirt",
            "--type=merge",
            "--patch",
            '{"spec":{"configuration":{"developerConfiguration":{"useEmulation":true}}}}',
        ]
    )

    # wait for kubevirt deployment
    run_command(
        [
            "kubectl",
            "wait",
            "kubevirt.kubevirt.io/kubevirt",
            "-n",
            "kubevirt",
            "--for=jsonpath={.status.phase}=Deployed",
            "--timeout=2m",
        ]
    )


@pytest.fixture(scope="session")
def dd_environment():
    with kind_run(conditions=[setup_kubevirt], sleep=10) as kubeconfig, ExitStack() as stack:
        instance = {}

        host, port = stack.enter_context(port_forward(kubeconfig, "kubevirt", 8443, "daemonset", "virt-handler"))

        instance["kubevirt_handler_metrics_endpoint"] = f"https://{host}:{port}/metrics"
        instance["kubevirt_handler_healthz_endpoint"] = f"https://{host}:{port}/healthz"
        instance["kube_namespace"] = "kubevirt"
        instance["kube_pod_name"] = "virt-handler-98cf864cc-zkgcd"
        instance["tls_verify"] = "false"

        yield {"instances": [instance]}


@pytest.fixture
def instance():
    return {
        "kubevirt_handler_healthz_endpoint": "https://127.0.0.1:8443/healthz",
        "kubevirt_handler_metrics_endpoint": "https://127.0.0.1:8443/metrics",
        "kube_namespace": "kubevirt",
        "kube_pod_name": "virt-handler-some-id",
    }


def mock_http_responses(url, **_params):
    mapping = {
        "https://127.0.0.1:8443/healthz": "healthz.txt",
        "https://127.0.0.1:8443/metrics": "metrics.txt",
    }

    fixtures_file = mapping.get(url)

    if not fixtures_file:
        raise Exception(f"url `{url}` not registered")

    with open(os.path.join(HERE, "fixtures", fixtures_file)) as f:
        return MockResponse(content=f.read())
