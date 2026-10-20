# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from datadog_checks.dell_powerflex.api import TOKEN_PATH
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


FIXED_NOW = datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)
FIXED_SINCE = FIXED_NOW.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
# Events and alerts are queried since a timestamp embedded in the URL, so the clock is frozen to keep it exact.
QUERY_SUFFIXES = {
    '/rest/v1/alerts': f'?filter=last_updated ge {FIXED_SINCE}',
    '/rest/v1/events': f'?filter=timestamp ge {FIXED_SINCE}',
}


class FrozenDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return FIXED_NOW.astimezone(tz)


@pytest.fixture(scope='function')
def mock_responses():
    """Map each API path, with `::` stored as `__`, to its fixture JSON."""
    root = Path(get_here(), 'fixtures', 'GET')
    return {'/' + str(file.parent.relative_to(root)): json.loads(file.read_text()) for file in root.rglob('*.json')}


@pytest.fixture
def register_api_responses(fake_http_response, mock_responses, mocker):
    """Return a function that registers one check run worth of GET responses from the fixtures."""
    mocker.patch('datadog_checks.dell_powerflex.check.datetime', FrozenDatetime)

    def register():
        for path, data in mock_responses.items():
            url = f"{DEFAULT_GATEWAY_URL}{path.replace('__', '::')}{QUERY_SUFFIXES.get(path, '')}"
            fake_http_response(url, json_data=data)

    return register


@pytest.fixture
def mock_auth(fake_http_response):
    def register():
        fake_http_response(
            f'{DEFAULT_GATEWAY_URL}{TOKEN_PATH}',
            method='POST',
            json_data={'access_token': 'fake-token', 'expires_in': 300},
        )

    register()
    return register


@pytest.fixture
def mock_http_get(register_api_responses, mock_auth):
    """Register one authenticated check run, and return a function that registers another."""

    def register_run():
        mock_auth()
        register_api_responses()

    register_api_responses()
    return register_run
