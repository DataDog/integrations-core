# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Any, AnyStr
from unittest.mock import MagicMock
from urllib.parse import urlparse

import pytest

from datadog_checks.base.utils.http_testing import MockHTTPResponse
from datadog_checks.dev import docker_run, get_docker_hostname, get_here
from datadog_checks.dev.conditions import CheckDockerLogs

HERE = get_here()

NO_TENANT_METRICS_FOLDER = 'no_tenant'
ADMIN_TENANT_METRICS_FOLDER = 'admin_tenant'
MULTIPLE_TENANTS_METRICS_FOLDER = 'multiple_tenants'


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
    def _get_metrics(metrics_folder=NO_TENANT_METRICS_FOLDER, endpoint=None):
        with open(os.path.join(HERE, 'compose', 'fixtures', metrics_folder, 'metrics.json')) as f:
            expected_metrics = json.load(f)

        if endpoint is None:
            return expected_metrics

        transformed_expected_metrics = []
        for metric in expected_metrics:
            tags = [t.replace('https://34.123.32.255/', endpoint) for t in metric['tags']]
            transformed_expected_metrics.append(
                {'name': metric['name'], 'type': metric['type'], 'value': metric['value'], 'tags': tags}
            )

        return transformed_expected_metrics

    return _get_metrics


@pytest.fixture
def mock_client(mock_http):
    def mock_get(url: AnyStr, *__: Any, **___: Any):
        parsed = urlparse(url)
        resource = [part for part in parsed.path.split('/') if len(part) > 0][-1]
        query_params = parsed.query

        path = {}

        path['tenant=admin'] = ADMIN_TENANT_METRICS_FOLDER
        path['tenant=admin%2Ctenant_a%2Ctenant_b'] = MULTIPLE_TENANTS_METRICS_FOLDER

        if query_params:
            return MockHTTPResponse(
                file_path=os.path.join(HERE, 'compose', 'fixtures', path[query_params], f'{resource}_metrics')
            )

        return MockHTTPResponse(
            file_path=os.path.join(HERE, 'compose', 'fixtures', NO_TENANT_METRICS_FOLDER, f'{resource}_metrics')
        )

    def mock_post(url: AnyStr, *__: Any, **___: Any):
        return MockHTTPResponse(json_data={"results": []})

    mock_http.session = MagicMock(cookies={})
    mock_http.get.side_effect = mock_get
    mock_http.post.side_effect = mock_post
    yield


@pytest.fixture(scope='session')
def unit_instance():
    return {
        'avi_controller_url': 'https://34.123.32.255/',
        'tls_verify': False,
        'username': 'admin',
    }


@pytest.fixture(scope='session')
def integration_instance():
    return {'avi_controller_url': f'http://{get_docker_hostname()}:5000/', 'username': 'user1', 'password': 'dummyPass'}
