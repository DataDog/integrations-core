# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Any, AnyStr

import mock
import pytest

from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

HERE = get_here()


@pytest.fixture(scope='session')
def dd_environment():
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    # We need a custom condition to wait a bit longer
    with docker_run(
        compose_file=compose_file,
        conditions=[
            CheckDockerLogs(compose_file, 'Running on ', wait=5),
        ],
    ):
        yield


@pytest.fixture
def expected_metrics():
    with open(os.path.join(HERE, 'compose', 'fixtures', "metrics.json")) as f:
        return json.load(f)


@pytest.fixture
def mock_client():
    with mock.patch('datadog_checks.base.utils.http.requests') as req:

        def get(url: AnyStr, *_: Any, **__: Any):
            response = mock.MagicMock()
            resource = url.split('/')[-1]
            with open(os.path.join(HERE, 'compose', 'fixtures', f"{resource}_metrics")) as f:
                content = f.read()
                response.iter_lines = lambda *_, **__: content.splitlines()
                return mock.MagicMock(__enter__=mock.MagicMock(return_value=response))

        req.Session = mock.MagicMock(return_value=mock.MagicMock(get=get))
        yield


@pytest.fixture
def unit_instance():
    return {
        "avi_controller_url": "https://34.123.32.255/",
        "tls_verify": False,
        "username": "admin",
        # "password": os.environ['DOCKER_AVI_PASS']
    }


@pytest.fixture
def integration_instance():
    return {"avi_controller_url": f"http://{get_docker_hostname()}:5000/", "username": "user1", "password": "dummyPass"}
