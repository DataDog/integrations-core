# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import subprocess

import pytest
import requests

from datadog_checks.dev import WaitFor, docker_run
from datadog_checks.dev.utils import ON_WINDOWS

from .common import ATHOST, CONFIG_FILE, HERE, URL

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
    env = {'COREDNS_CONFIG_FILE': CONFIG_FILE}

    with docker_run(compose_file, conditions=[WaitFor(init_coredns)], env_vars=env):
        yield instance


@pytest.fixture
def dockerinstance():
    return {'prometheus_url': URL}


@pytest.fixture(scope="session")
def instance():
    return {'prometheus_url': URL}


@pytest.fixture
def mock_get(mock_http_response):
    mesh_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', 'metrics.txt')
    yield mock_http_response(file_path=mesh_file_path)
