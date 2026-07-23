# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from os import path

import pytest

from datadog_checks.dev.conditions import WaitFor
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.subprocess import run_command

from .common import EXTRA_METRICS

NAMESPACE = "calico"
HERE = path.dirname(path.abspath(__file__))
FELIX_METRICS_ENDPOINT = 'http://felix-metrics-svc.kube-system.svc.cluster.local:9091/metrics'


def _felix_config_default_exists():
    result = run_command(["kubectl", "get", "felixconfiguration", "default"], capture='both')
    return result.code == 0


def felix_metrics_available() -> bool:
    result = run_command(
        [
            "kubectl",
            "run",
            "felix-metrics-readiness",
            "--namespace",
            "kube-system",
            "--image=busybox:1.36.1",
            "--restart=Never",
            "--attach",
            "--rm",
            "--quiet",
            "--",
            "wget",
            "-q",
            "-T",
            "2",
            "-O",
            "/dev/null",
            FELIX_METRICS_ENDPOINT,
        ],
        capture='both',
    )
    return result.code == 0


def setup_calico():
    # Deploy calico
    run_command(["kubectl", "apply", "-f", path.join(HERE, 'kind', 'calico.yaml')])

    # Install calicoctl as a pod
    run_command(["kubectl", "apply", "-f", path.join(HERE, 'kind', 'calicoctl.yaml')])

    # Create felix metrics service
    run_command(["kubectl", "apply", "-f", path.join(HERE, 'kind', 'felix-service.yaml')])

    # Create a network policy to populate metrics
    run_command(["kubectl", "apply", "-f", path.join(HERE, 'kind', 'network-policy.yaml')])

    # Wait for pods
    run_command(["kubectl", "wait", "--for=condition=Ready", "pods", "--all", "--all-namespaces", "--timeout=300s"])

    # calico-node creates the default FelixConfiguration asynchronously after pods report Ready.
    WaitFor(_felix_config_default_exists, attempts=60, wait=2)()

    # check=True so a missed patch fails loudly here instead of as a connection-refused timeout later.
    run_command(
        [
            "kubectl",
            "exec",
            "-i",
            "-n",
            "kube-system",
            "calicoctl",
            "--",
            "/calicoctl",
            "patch",
            "felixConfiguration",
            "default",
            "--patch",
            '{"spec":{"prometheusMetricsEnabled": true}}',
        ],
        check=True,
    )

    # Check from a temporary pod because the host cannot resolve Kubernetes Service DNS.
    WaitFor(felix_metrics_available, wait=2, attempts=100)()


@pytest.fixture(scope='session')
def dd_environment():
    with kind_run(
        conditions=[setup_calico], kind_config=path.join(HERE, 'kind', 'kind-calico.yaml'), sleep=10
    ) as kubeconfig:
        instance = {
            "openmetrics_endpoint": FELIX_METRICS_ENDPOINT,
            "namespace": NAMESPACE,
            "extra_metrics": EXTRA_METRICS,
        }
        metadata = {'agent_type': 'kubernetes', 'kubernetes': {'kubeconfig': kubeconfig}}

        yield instance, metadata


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": 'http://localhost:9091/metrics',
        "namespace": NAMESPACE,
        "extra_metrics": EXTRA_METRICS,
    }
