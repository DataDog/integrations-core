# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from os import path

import pytest

from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import EXTRA_METRICS

NAMESPACE = "calico"
HERE = path.dirname(path.abspath(__file__))


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

    # Activate Felix
    run_command(
        """kubectl exec -i -n kube-system calicoctl -- /calicoctl patch felixConfiguration
        default --patch '{"spec":{"prometheusMetricsEnabled": true}}'"""
    )


@pytest.fixture(scope='session')
def dd_environment():

    with kind_run(
        conditions=[setup_calico], kind_config=path.join(HERE, 'kind', 'kind-calico.yaml'), sleep=10
    ) as kubeconfig, port_forward(kubeconfig, 'kube-system', 9091, 'service', 'felix-metrics-svc') as (
        calico_host,
        calico_port,
    ):
        endpoint = 'http://{}:{}/metrics'.format(calico_host, calico_port)

        # We can't add this to `kind_run` because we don't know the URL at this moment
        condition = CheckEndpoints(endpoint, wait=2, attempts=100)
        condition()

        yield {
            "openmetrics_endpoint": endpoint,
            "namespace": NAMESPACE,
            "extra_metrics": EXTRA_METRICS,
        }


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": 'http://localhost:9091/metrics',
        "namespace": NAMESPACE,
        "extra_metrics": EXTRA_METRICS,
    }
