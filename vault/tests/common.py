# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests

from datadog_checks.dev import get_docker_hostname

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


class MockResponse:
    def __init__(self, j, status_code=200):
        self.j = j
        self.status_code = status_code

    def json(self):
        return self.j

    def raise_for_status(self):
        if self.status_code >= 300:
            raise requests.exceptions.HTTPError
