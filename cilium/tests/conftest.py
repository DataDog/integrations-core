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

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

from .common import CILIUM_LEGACY, ON_CI

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
AGENT_PORT = 9090
OPERATOR_PORT = 6942
AGENT_URL = "http://{}:{}/metrics".format(HOST, AGENT_PORT)
OPERATOR_URL = "http://{}:{}/metrics".format(HOST, OPERATOR_PORT)

PORTS = [AGENT_PORT, OPERATOR_PORT]


def setup_cilium():
    config = os.path.join(HERE, 'kind', 'cilium.yaml')
    run_command(["kubectl", "create", "ns", "cilium"])
    run_command(["kubectl", "create", "-f", config])
    run_command(
        ["kubectl", "wait", "deployments", "--all", "--for=condition=Available", "-n", "cilium", "--timeout=300s"]
    )
    run_command(["kubectl", "wait", "pods", "-n", "cilium", "--all", "--for=condition=Ready", "--timeout=300s"])


@pytest.fixture(scope='session')
def dd_environment():
    use_openmetrics = CILIUM_LEGACY == 'false'
    if ON_CI:
        yield [
            {
                'agent_endpoint': 'http://localhost:9090/metrics',
                'use_openmetrics': use_openmetrics,
            },
            {
                'operator_endpoint': 'http://localhost:6942/metrics',
                'use_openmetrics': use_openmetrics,
            },
        ]
    kind_config = os.path.join(HERE, 'kind', 'kind-config.yaml')
    with kind_run(conditions=[setup_cilium], kind_config=kind_config) as kubeconfig:
        with ExitStack() as stack:
            ip_ports = [
                stack.enter_context(port_forward(kubeconfig, 'cilium', port, 'deployment', 'cilium-operator'))
                for port in PORTS
            ]

            instances = {
                'instances': [
                    {
                        'agent_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[0]),
                        'use_openmetrics': use_openmetrics,
                    },
                    {
                        'operator_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[1]),
                        'use_openmetrics': use_openmetrics,
                    },
                ]
            }

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
