# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest
import requests

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = '8200'
INSTANCES = {
    'main': {'api_url': 'http://{}:{}/v1'.format(HOST, PORT), 'tags': ['instance:foobar'], 'detect_leader': True},
    'unsupported_api': {
        'api_url': 'http://{}:{}/v0'.format(HOST, PORT),
        'tags': ['instance:foobar'],
        'detect_leader': True,
    },
    'bad_url': {'api_url': 'http://1.2.3.4:555/v1', 'tags': ['instance:foobar'], 'timeout': 1},
    'no_leader': {'api_url': 'http://{}:{}/v1'.format(HOST, PORT), 'tags': ['instance:foobar']},
    'invalid': {},
}
HEALTH_ENDPOINT = '{}/sys/health'.format(INSTANCES['main']['api_url'])

AUTH_TYPE = os.environ['AUTH_TYPE']


class MockResponse:
    def __init__(self, j, status_code=200):
        self.j = j
        self.status_code = status_code

    def json(self):
        return self.j

    def raise_for_status(self):
        if self.status_code >= 300:
            raise requests.exceptions.HTTPError


def get_vault_server_config_file():
    if AUTH_TYPE == 'no-auth':
        return './vault_server_config_noauth.json'
    else:
        return './vault_server_config.json'


auth_required = pytest.mark.skipif(AUTH_TYPE == 'no-auth', reason='Test only if auth is required to retrieve metrics')
noauth_required = pytest.mark.skipif(
    AUTH_TYPE != 'no-auth', reason='Test only if auth is NOT required to retrieve metrics'
)
