# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest

from .common import AGENT_METRICS, OPERATOR_METRICS
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
AGENT_PORT = '9090'
OPERATOR_PORT = '6942'
AGENT_URL = "http://{}:{}/metrics".format(HOST, AGENT_PORT)
OPERATOR_URL = "http://{}:{}/metrics".format(HOST, OPERATOR_PORT)


@pytest.fixture(scope='session')
def dd_environment():
    with terraform_run(os.path.join(HERE, 'terraform')) as outputs:
        kubeconfig = outputs['kubeconfig']['value']

        with port_forward(kubeconfig, 'cilium', 'cilium', 9090) as (ip, port):
            agent_instance = {
                'agent_endpoint': 'http://{}:{}/metrics'.format(ip, port),
                'metrics': AGENT_METRICS,
            }
        with port_forward(kubeconfig, 'cilium', 'cilium', 6942) as (ip, port):
            operator_instance = {
                'operator_endpoint': 'http://{}:{}/metrics'.format(ip, port),
                'metrics': OPERATOR_METRICS,
            }
            yield {'instances': [agent_instance, operator_instance]}
    # yield {'instances': [agent_instance, operator_instance]}


@pytest.fixture(scope="session")
def agent_instance():
    return {'agent_endpoint': AGENT_URL, 'tags': ['pod_test']}


@pytest.fixture
def operator_instance():
    return {'operator_endpoint': OPERATOR_URL, 'tags': ['operator_test']}


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
