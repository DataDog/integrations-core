# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPStatusError
from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.docker import get_docker_hostname
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.http import MockHTTPResponse
from datadog_checks.dev.utils import find_free_port

from .common import DEFAULT_GATEWAY_URL

USE_POWERFLEX_LAB = os.environ.get('USE_POWERFLEX_LAB')
POWERFLEX_GATEWAY_URL = os.environ.get('POWERFLEX_GATEWAY_URL')
POWERFLEX_USERNAME = os.environ.get('POWERFLEX_USERNAME')
POWERFLEX_PASSWORD = os.environ.get('POWERFLEX_PASSWORD')

COMPOSE_FILE = os.path.join(get_here(), 'docker', 'docker-compose.yaml')

LAB_INSTANCE = {
    'powerflex_gateway_url': POWERFLEX_GATEWAY_URL,
    'powerflex_username': POWERFLEX_USERNAME,
    'powerflex_password': POWERFLEX_PASSWORD,
    'collect_events': True,
    'collect_alerts': True,
    'resource_filters': [
        {'resource': 'device', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': True},
    ],
}


@pytest.fixture(scope='session')
def dd_environment():
    if USE_POWERFLEX_LAB:
        yield LAB_INSTANCE
    else:
        port = find_free_port(get_docker_hostname())
        caddy_instance = {
            'powerflex_gateway_url': f'http://{get_docker_hostname()}:{port}',
            'powerflex_username': 'admin',
            'powerflex_password': 'password',
            'collect_events': True,
            'collect_alerts': True,
            'resource_filters': [
                {'resource': 'device', 'property': 'name', 'patterns': ['.*'], 'collect_statistics': True},
            ],
        }
        conditions = [
            CheckDockerLogs(identifier='powerflex-api', patterns=['server running']),
            CheckEndpoints(f'http://{get_docker_hostname()}:{port}/api/version'),
        ]
        with docker_run(COMPOSE_FILE, conditions=conditions, env_vars={'POWERFLEX_PORT': str(port)}):
            yield caddy_instance


@pytest.fixture
def instance():
    return {
        'powerflex_gateway_url': DEFAULT_GATEWAY_URL,
        'powerflex_username': 'admin',
        'powerflex_password': 'password',
    }


def _get_url_path(url):
    parsed = urlparse(url)
    return parsed.path.replace('::', '__')


@pytest.fixture(scope='function')
def mock_responses():
    responses_map = {}

    def load_fixtures():
        root = os.path.join(get_here(), 'fixtures', 'GET')
        for file in Path(root).rglob('*'):
            if file.is_file():
                relative = file.relative_to(root)
                path = '/' + str(relative.parent) if str(relative.parent) != '.' else '/'
                responses_map.setdefault(path, {})[file.stem] = json.loads(file.read_text())

    def get(url, file='response', **kwargs):
        return responses_map.get(_get_url_path(url), {}).get(file)

    load_fixtures()
    yield get


@pytest.fixture
def mock_http_call(mock_responses):
    def call(url, file='response', **kwargs):
        data = mock_responses(url, file=file, **kwargs)
        if data is not None:
            return data
        raise HTTPStatusError('404 Not Found', response=MockHTTPResponse(status_code=404))

    yield call


@pytest.fixture
def mock_auth(mock_http):
    def post(url, *args, **kwargs):
        return MockHTTPResponse(json_data={'access_token': 'fake-token', 'expires_in': 300}, status_code=200)

    mock_http.post.side_effect = post


@pytest.fixture
def mock_http_get(mock_http, mock_http_call, mock_auth):
    def get(url, *args, **kwargs):
        return MockHTTPResponse(json_data=mock_http_call(url, **kwargs), status_code=200)

    mock_http.get.side_effect = get
    return mock_http
