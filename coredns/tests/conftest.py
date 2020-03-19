# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess

import mock
import pytest
import requests

from datadog_checks.base.utils.common import get_docker_hostname
from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.utils import ON_WINDOWS

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FOLDER = os.path.join(HERE, 'docker', 'coredns')
HOST = get_docker_hostname()
ATHOST = "@{}".format(HOST)
PORT = '9153'
URL = "http://{}:{}/metrics".format(HOST, PORT)

# One lookup each for the forward and proxy plugins
DIG_ARGS = ["dig", "google.com", ATHOST, "example.com", ATHOST, "-p", "54"]


def init_coredns():
    res = requests.get(URL)
    if not ON_WINDOWS:
        # create some metrics by using dig
        subprocess.check_call(DIG_ARGS)
    res.raise_for_status()


@pytest.fixture(scope="session")
def dd_environment(instance):
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yml')
    env = {'COREDNS_CONFIG_FOLDER': CONFIG_FOLDER}

    with docker_run(compose_file, conditions=[WaitFor(init_coredns)], env_vars=env):
        yield instance


@pytest.fixture
def dockerinstance():
    return {'prometheus_url': URL}


@pytest.fixture(scope="session")
def instance():
    return {'prometheus_url': URL}


@pytest.fixture
def mock_get():
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    with open(mesh_file_path, 'r') as f:
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
        self.encoding = 'utf-8'

    def iter_lines(self, **_):
        for elt in self.content.split("\n"):
            yield elt

    def raise_for_status(self):
        pass

    def close(self):
        pass
