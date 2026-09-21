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


@pytest.fixture(scope='function')
def powerflex_responses():
    responses = {}
    root = Path(get_here()) / 'fixtures' / 'GET'
    for file in root.rglob('*.json'):
        path = '/' + str(file.relative_to(root).parent).replace('__', '::')
        responses[f'{DEFAULT_GATEWAY_URL}{path}'] = json.loads(file.read_text())
    return responses


@pytest.fixture
def powerflex_http(mocker, fake_http, fake_http_response, powerflex_responses):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            value = cls(2026, 3, 18, 4, 0, tzinfo=timezone.utc)
            return value if tz is None else value.astimezone(tz)

    mocker.patch('datadog_checks.dell_powerflex.check.datetime', FrozenDateTime)
    token_url = f'{DEFAULT_GATEWAY_URL}/auth/realms/powerflex/protocol/openid-connect/token'
    for _ in range(10):
        fake_http_response(
            token_url,
            method='POST',
            json_data={'access_token': 'fake-token', 'expires_in': 300},
        )
    for url, payload in powerflex_responses.items():
        for _ in range(10):
            fake_http_response(url, json_data=payload)
    timestamp = '2026-03-18T04:00:00.000000Z'
    for endpoint, timestamp_field in (('events', 'timestamp'), ('alerts', 'last_updated')):
        payload = powerflex_responses[f'{DEFAULT_GATEWAY_URL}/rest/v1/{endpoint}']
        url = f'{DEFAULT_GATEWAY_URL}/rest/v1/{endpoint}?filter={timestamp_field} ge {timestamp}'
        for _ in range(10):
            fake_http_response(url, json_data=payload)
    return fake_http
