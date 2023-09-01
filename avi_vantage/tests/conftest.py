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
from datadog_checks.dev.http import MockResponse

HERE = get_here()


@pytest.fixture(scope='session')
def dd_environment(integration_instance):
    compose_file = os.path.join(HERE, 'compose', 'docker-compose.yaml')
    # We need a custom condition to wait a bit longer
    with docker_run(
        compose_file=compose_file,
        build=True,
        conditions=[
            CheckDockerLogs(compose_file, 'Running on ', wait=5),
        ],
        attempts=2,
    ):
        yield integration_instance


@pytest.fixture
def get_expected_metrics():
    def _get_metrics(endpoint=None):
        with open(os.path.join(HERE, 'compose', 'fixtures', "metrics.json")) as f:
            expected_metrics = json.load(f)

        if endpoint is None:
            return expected_metrics

        transformed_expected_metrics = []
        for metric in expected_metrics:
            tags = [t.replace('https://34.123.32.255/', endpoint) for t in metric['tags']]
            transformed_expected_metrics.append(
                {"name": metric['name'], "type": metric['type'], "value": metric['value'], "tags": tags}
            )

        return transformed_expected_metrics

    return _get_metrics


@pytest.fixture
def mock_client():
    with mock.patch('datadog_checks.base.utils.http.requests') as req:

        def get(url: AnyStr, *_: Any, **__: Any):
            resource = url.split('/')[-1]
            return MockResponse(file_path=os.path.join(HERE, 'compose', 'fixtures', f'{resource}_metrics'))

        req.Session = mock.MagicMock(return_value=mock.MagicMock(get=get))
        yield


@pytest.fixture(scope='session')
def unit_instance():
    return {
        "avi_controller_url": "https://34.123.32.255/",
        "tls_verify": False,
        "username": "admin",
    }


@pytest.fixture(scope='session')
def integration_instance():
    return {"avi_controller_url": f"http://{get_docker_hostname()}:5000/", "username": "user1", "password": "dummyPass"}
