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

COREDNS_VERSION = [int(i) for i in os.environ['COREDNS_VERSION'].split(".")]


def init_coredns():
    res = requests.get(URL)
    if not ON_WINDOWS:
        # create some metrics by using dig
        subprocess.check_call(DIG_ARGS)
    res.raise_for_status()


@pytest.fixture(scope="session")
def dd_environment(omv2_instance):
    compose_file = os.path.join(HERE, 'docker', 'docker-compose.yml')
    env = {'COREDNS_CONFIG_FILE': CONFIG_FILE}

    with docker_run(compose_file, conditions=[WaitFor(init_coredns)], env_vars=env):
        yield omv2_instance


@pytest.fixture
def dockerinstance():
    return {'prometheus_url': URL}


@pytest.fixture
def docker_omv2_instance():
    return {'openmetrics_endpoint': URL}


@pytest.fixture(scope="session")
def instance():
    return {'prometheus_url': URL}


@pytest.fixture(scope="session")
def omv2_instance():
    return {'openmetrics_endpoint': URL}


@pytest.fixture
def mock_get(mock_http_response):
    if COREDNS_VERSION[:2] == [1, 8]:
        metric_file = 'metrics_18.txt'
    elif COREDNS_VERSION[:2] == [1, 2]:
        metric_file = 'metrics_12.txt'
    metric_file_path = os.path.join(os.path.dirname(__file__), 'fixtures', metric_file)
    yield mock_http_response(file_path=metric_file_path)
