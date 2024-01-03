# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.cilium import CiliumCheck
from datadog_checks.dev import run_command
from datadog_checks.dev.kind import kind_run
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.utils import get_active_env

from .common import CILIUM_VERSION

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from datadog_checks.dev import TempDir
from datadog_checks.dev.fs import path_join

from .common import CILIUM_LEGACY

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
AGENT_PORT = 9090
OPERATOR_PORT = 6942
AGENT_URL = "http://{}:{}/metrics".format(HOST, AGENT_PORT)
OPERATOR_URL = "http://{}:{}/metrics".format(HOST, OPERATOR_PORT)

IMAGE_NAME = "quay.io/cilium/cilium:v{}".format(CILIUM_VERSION)
PORTS = [AGENT_PORT, OPERATOR_PORT]
CLUSTER_NAME = 'cluster-{}-{}'.format('cilium', get_active_env())


def setup_cilium():
    run_command(["helm", "repo", "add", "cilium", "https://helm.cilium.io/"])
    run_command(["docker", "pull", IMAGE_NAME])
    run_command(
        [
            "kind",
            "load",
            "docker-image",
            IMAGE_NAME,
            "--name",
            CLUSTER_NAME,
        ]
    )
    run_command(["kubectl", "create", "ns", "cilium"])
    run_command(
        [
            "helm",
            "install",
            "cilium",
            "cilium/cilium",
            "--version",
            CILIUM_VERSION,
            "--namespace",
            "cilium",
            "--set",
            "kubeProxyReplacement=partial",
            "--set",
            "hostServices.enabled=false",
            "--set",
            "externalIPs.enabled=true",
            "--set",
            "nodePort.enabled=true",
            "--set",
            "hostPort.enabled=true",
            "--set",
            "bpf.masquerade=false",
            "--set",
            "image.pullPolicy=IfNotPresent",
            "--set",
            "ipam.mode=kubernetes",
            "--set",
            "prometheus.enabled=true",
            "--set",
            "operator.prometheus.enabled=true",
            "--set",
            "prometheus.metrics[0]=+cilium_bpf_map_pressure",
        ]
    )
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "cilium", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "-n", "cilium", "--all", "--for=condition=Ready", "--timeout=300s"])

    # Hack below...
    # Some metrics like cilium_api_limiter_adjustment_factor are not emitted until there are at least
    # one call to rate limited api. So we need to go through all our cilium pods and do at least one
    # call to list endpoint (which is rate limited) to be able to collect api_limiter metrics
    result = run_command(
        [
            "kubectl",
            "get",
            "pods",
            "-n",
            "cilium",
            "-l",
            "k8s-app=cilium",
            "-o",
            "jsonpath={.items[*].metadata.name}",
        ],
        capture=True,
    )
    if result.stderr:
        raise Exception(result.stderr)
    pods = result.stdout.split(' ')

    for pod in pods:
        result = run_command(
            [
                "kubectl",
                "exec",
                "-n",
                "cilium",
                "-c",
                "cilium-agent",
                pod.strip(),
                "--",
                "cilium",
                "endpoint",
                "list",
            ],
            capture=True,
        )
        if result.stderr:
            raise Exception(result.stderr)


def get_instances(agent_host, agent_port, operator_host, operator_port, use_openmetrics):
    return {
        'instances': [
            {
                'agent_endpoint': 'http://{}:{}/metrics'.format(agent_host, agent_port),
                'use_openmetrics': use_openmetrics,
            },
            {
                'operator_endpoint': 'http://{}:{}/metrics'.format(operator_host, operator_port),
                'use_openmetrics': use_openmetrics,
            },
        ]
    }


@pytest.fixture(scope='session')
def dd_environment():
    use_openmetrics = CILIUM_LEGACY == 'false'
    kind_config = os.path.join(HERE, 'kind', 'kind-config.yaml')
    with TempDir('helm_dir') as helm_dir:
        with kind_run(
            conditions=[setup_cilium],
            kind_config=kind_config,
            env_vars={
                "HELM_CACHE_HOME": path_join(helm_dir, 'Caches'),
                "HELM_CONFIG_HOME": path_join(helm_dir, 'Preferences'),
            },
        ) as kubeconfig:
            with ExitStack() as stack:
                ip_ports = [
                    stack.enter_context(port_forward(kubeconfig, 'cilium', port, 'deployment', 'cilium-operator'))
                    for port in PORTS
                ]

                instances = get_instances(
                    ip_ports[0][0], ip_ports[0][1], ip_ports[1][0], ip_ports[1][1], use_openmetrics
                )

            yield instances


@pytest.fixture(scope="session")
def check():
    return lambda instance: CiliumCheck('cilium', {}, [instance])


@pytest.fixture(scope="session")
def agent_instance_use_openmetrics():
    return lambda use_openmetrics: {
        'agent_endpoint': AGENT_URL,
        'tags': ['pod_test'],
        'use_openmetrics': use_openmetrics,
    }


@pytest.fixture
def operator_instance_use_openmetrics():
    return lambda use_openmetrics: {
        'operator_endpoint': OPERATOR_URL,
        'tags': ['operator_test'],
        'use_openmetrics': use_openmetrics,
    }


@pytest.fixture()
def mock_agent_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'agent_metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield


@pytest.fixture()
def mock_operator_data():
    f_name = os.path.join(os.path.dirname(__file__), 'fixtures', 'operator_metrics.txt')
    with open(f_name, 'r') as f:
        text_data = f.read()
    with mock.patch(
        'requests.get',
        return_value=mock.MagicMock(
            status_code=200, iter_lines=lambda **kwargs: text_data.split("\n"), headers={'Content-Type': "text/plain"}
        ),
    ):
        yield
