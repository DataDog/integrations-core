# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from datadog_checks.dev import docker_run
from datadog_checks.dev.conditions import CheckDockerLogs, CheckEndpoints
from datadog_checks.dev.docker import get_docker_hostname
from datadog_checks.dev.fs import get_here
from datadog_checks.dev.utils import find_free_port

from .common import DEFAULT_GATEWAY_URL, TOKEN_URL

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


FROZEN_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
FROZEN_SINCE = FROZEN_NOW.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
# The fake matches exact URLs, and the alert and event queries embed the collection time.
QUERY_SUFFIXES = {
    '/rest/v1/alerts': f'?filter=last_updated ge {FROZEN_SINCE}',
    '/rest/v1/events': f'?filter=timestamp ge {FROZEN_SINCE}',
}


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FROZEN_NOW.astimezone(tz) if tz is not None else FROZEN_NOW.replace(tzinfo=None)


@pytest.fixture
def frozen_now(monkeypatch):
    monkeypatch.setattr('datadog_checks.dell_powerflex.check.datetime', FrozenDatetime)
    return FROZEN_SINCE


@pytest.fixture(scope='function')
def mock_responses():
    """Map each fixture's request URL to its parsed JSON body."""
    responses_map = {}
    root = os.path.join(get_here(), 'fixtures', 'GET')
    for file in Path(root).rglob('*'):
        if file.is_file():
            relative = file.relative_to(root)
            path = '/' + str(relative.parent).replace('__', '::')
            url = f'{DEFAULT_GATEWAY_URL}{path}{QUERY_SUFFIXES.get(path, "")}'
            responses_map[url] = json.loads(file.read_text())
    return responses_map


@pytest.fixture
def mock_auth(fake_http_response):
    fake_http_response(TOKEN_URL, method='POST', json_data={'access_token': 'fake-token', 'expires_in': 300})


@pytest.fixture
def mock_get_responses(fake_http_response, mock_responses, frozen_now):
    for url, data in mock_responses.items():
        fake_http_response(url, json_data=data)


@pytest.fixture
def mock_http_get(mock_get_responses, mock_auth, fake_http):
    return fake_http
