from os import path

import pytest

from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.subprocess import run_command

from .common import EXTRA_METRICS

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

NAMESPACE = "calico"
HERE = path.dirname(path.abspath(__file__))


def setup_calico():
    # Deploy calico
    run_command(["kubectl", "apply", "-f", "https://docs.projectcalico.org/manifests/calico.yaml"])

    # Install calicoctl as a pod
    run_command(["kubectl", "apply", "-f", "https://docs.projectcalico.org/manifests/calicoctl.yaml"])

    # Create felix metrics service
    run_command(["kubectl", "apply", "-f", path.join(HERE, 'felix-service.yaml')])

    # Wait for pods
    run_command(["kubectl", "wait", "--for=condition=Ready", "pods", "--all", "--all-namespaces", "--timeout=300s"])

    # Activate Felix
    run_command(
        """kubectl exec -i -n kube-system calicoctl -- /calicoctl patch felixConfiguration
        default --patch '{"spec":{"prometheusMetricsEnabled": true}}'"""
    )


@pytest.fixture(scope='session')
def dd_environment():

    with kind_run(conditions=[setup_calico], kind_config=path.join(HERE, 'kind-calico.yaml')) as kubeconfig:
        with ExitStack() as stack:
            calico_host, calico_port = stack.enter_context(
                port_forward(kubeconfig, 'kube-system', 9091, 'service', 'felix-metrics-svc')
            )
            instance = {
                "openmetrics_endpoint": 'http://{}:{}/metrics'.format(calico_host, calico_port),
                "namespace": NAMESPACE,
                "extra_metrics": EXTRA_METRICS,
            }
            yield instance


@pytest.fixture
def instance():
    return {
        "openmetrics_endpoint": 'http://localhost:9091/metrics',
        "namespace": NAMESPACE,
        "extra_metrics": EXTRA_METRICS,
    }
