# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests
from requests.exceptions import HTTPError

from datadog_checks.base.utils.common import ensure_unicode
from datadog_checks.dev import get_here
from datadog_checks.dev.conditions import CheckEndpoints
from datadog_checks.dev.kube_port_forward import port_forward
from datadog_checks.dev.terraform import terraform_run

try:
    from contextlib import ExitStack
except ImportError:
    from contextlib2 import ExitStack


HERE = get_here()

DEPLOYMENTS_LEGACY = [
    ('istio-citadel', 15014),
    ('istio-galley', 15014),
    ('istio-pilot', 15014),
    ('istio-telemetry', 15014),
    ('istio-telemetry', 42422),
    ('istio-ingressgateway', 80),
]


@pytest.fixture(scope='session')
def dd_environment():
    version = os.environ.get("ISTIO_VERSION")

    with terraform_run(os.path.join(HERE, 'terraform', version)) as outputs:
        kubeconfig = outputs['kubeconfig']['value']
        with ExitStack() as stack:
            if version == '1.5.1':
                istiod_host, istiod_port = stack.enter_context(port_forward(kubeconfig, 'istio-system', 'istiod', 8080))
                instance = {'istiod_endpoint': 'http://{}:{}/metrics'.format(istiod_host, istiod_port)}

                yield instance
            else:
                ip_ports = [
                    stack.enter_context(port_forward(kubeconfig, 'istio-system', deployment, port))
                    for (deployment, port) in DEPLOYMENTS_LEGACY
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
def istio_proxy_mesh_fixture():
    mesh_file_path = os.path.join(HERE, 'fixtures', '1.5', 'istio-proxy.txt')
    responses = []
    with open(mesh_file_path, 'r') as f:
        responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def istiod_mixture_fixture():
    mesh_file_path = os.path.join(HERE, 'fixtures', '1.5', 'istiod.txt')
    responses = []
    with open(mesh_file_path, 'r') as f:
        responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def mesh_fixture():
    mesh_file_path = os.path.join(HERE, 'fixtures', '0.5', 'mesh.txt')
    responses = []
    with open(mesh_file_path, 'r') as f:
        responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def mixture_fixture():
    mixer_file_path = os.path.join(HERE, 'fixtures', '0.5', 'mixer.txt')
    responses = []
    with open(mixer_file_path, 'r') as f:
        responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_mesh_mixture_fixture():
    files = ['mesh.txt', 'mixer.txt', 'pilot.txt', 'galley.txt', 'citadel.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(HERE, 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_pilot_fixture():
    files = ['pilot.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(HERE, 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield


@pytest.fixture
def new_galley_fixture():
    files = ['galley.txt']
    responses = []
    for filename in files:
        file_path = os.path.join(HERE, 'fixtures', '1.1', filename)
        with open(file_path, 'r') as f:
            responses.append(f.read())

    with mock.patch('requests.get', return_value=MockResponse(responses, 'text/plain'), __name__="get"):
        yield
