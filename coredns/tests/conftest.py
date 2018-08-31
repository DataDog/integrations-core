# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import os
import mock
import pytest
import requests
import subprocess
import sys
import time

from datadog_checks.dev import docker_run, RetryError
from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FOLDER = os.path.join(HERE, 'docker', 'coredns')
HOST = get_docker_hostname()
PORT = '9153'
URL = "http://{}:{}/metrics".format(HOST, PORT)

DIG_ARGS = [
    "dig",
    "google.com",
    "@127.0.0.1",
    "-p",
    "54"
]


@pytest.fixture(scope="session")
def spin_up_coredns():
    def condition():

        sys.stderr.write("Waiting for CoreDNS to boot...")
        booted = False
        for _ in xrange(10):
            try:
                res = requests.get(URL)
                # create some metrics by using dig
                subprocess.check_call(DIG_ARGS, env=env)
                res.raise_for_status()
                booted = True
                break
            except Exception:
                time.sleep(1)

        if not booted:
            raise RetryError("CoreDNS failed to boot!")
        sys.stderr.write("CoreDNS boot complete.\n")

    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yml')
    env = {'COREDNS_CONFIG_FOLDER': CONFIG_FOLDER}
    with docker_run(compose_file, conditions=[condition], env_vars=env):
        yield


@pytest.fixture
def dockerinstance():
    return {
      'prometheus_url': URL,
    }


@pytest.fixture
def instance():
    return {
      'prometheus_url': 'http://localhost:9153/metrics',
    }


@pytest.fixture
def mock_get():
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    text_data = None
    with open(mesh_file_path, 'rb') as f:
        text_data = f.read()
    with mock.patch('requests.get', return_value=MockResponse(text_data, 'text/plain; version=0.0.4'), __name__='get'):
        yield


class MockResponse:
    """
    MockResponse is used to simulate the object requests.Response commonly returned by requests.get
    """

    def __init__(self, content, content_type):
        self.content = content
        self.headers = {'Content-Type': content_type}

    def iter_lines(self, **_):
        for elt in self.content.split("\n"):
            yield elt

    def raise_for_status(self):
        pass

    def close(self):
        pass
