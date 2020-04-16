# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests
from requests.exceptions import HTTPError

from datadog_checks.base.utils.common import ensure_unicode
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.terraform import terraform_run
from datadog_checks.dev.utils import get_here

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack

DEPLOYMENTS = [
    ('istio-citadel', 15014),
    ('istio-galley', 15014),
    ('istio-pilot', 15014),
    ('istio-telemetry', 15014),
    ('istio-telemetry', 42422),
    ('istio-ingressgateway', 80),
]


@pytest.fixture(scope='session')
def dd_environment():
    with terraform_run(os.path.join(get_here(), 'terraform')) as outputs:
        kubeconfig = outputs['kubeconfig']['value']
        with ExitStack() as stack:
            ip_ports = [
                stack.enter_context(port_forward(kubeconfig, 'istio-system', deployment, port))
                for (deployment, port) in DEPLOYMENTS
            ]
            instance = {
                'citadel_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[0]),
                'galley_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[1]),
                'pilot_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[2]),
                'mixer_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[3]),
                'istio_mesh_endpoint': 'http://{}:{}/metrics'.format(*ip_ports[4]),
            }
            page = 'http://{}:{}/productpage'.format(*ip_ports[5])
            # Check a bit to make sure it's available
            CheckEndpoints([page], wait=5)()
            for _ in range(5):
                # Generate some traffic
                requests.get(page)
            yield instance


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type, status=200):
        self.content = content if isinstance(content, list) else [content]
        self.headers = {'Content-Type': content_type}
        self.status = status
        self.encoding = 'utf-8'

    def iter_lines(self, **_):
        content = self.content.pop(0)
        for elt in content.split("\n"):
            yield ensure_unicode(elt)

    def raise_for_status(self):
        if self.status != 200:
            raise HTTPError('Not 200 Client Error')

    def close(self):
        pass


@pytest.fixture
def mesh_mixture_fixture():
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'istio', 'mesh.txt')
    mixer_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'istio', 'mixer.txt')
    responses = []
    with open(mesh_file_path, 'r') as f:
        responses.append(f.read())
    with open(mixer_file_path, 'r') as f:
        responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_mesh_mixture_fixture():
    files = ['mesh.txt', 'mixer.txt', 'pilot.txt', 'galley.txt', 'citadel.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(os.path.dirname(__file__), 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_pilot_fixture():
    files = ['pilot.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(os.path.dirname(__file__), 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_galley_fixture():
    files = ['galley.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(os.path.dirname(__file__), 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield
