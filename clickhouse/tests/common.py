# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.getenv('COMPOSE_FILE', 'docker-compose.yaml')
IS_TLS = COMPOSE_FILE == 'docker-compose-tls.yaml'
COMPOSE_FILE_PATH = os.path.join(HERE, 'docker', COMPOSE_FILE)

tls = pytest.mark.skipif(not IS_TLS, reason='Test only valid for TLS flavor')

HOST = get_docker_hostname()
HTTP_START_PORT = 8128
TCP_START_PORT = 9001
HTTPS_PORT = 8134
CLICKHOUSE_VERSION = os.environ['CLICKHOUSE_VERSION']

CONFIG = {
    'server': HOST,
    'port': HTTP_START_PORT,
    'username': 'datadog',
    'password': 'Datadog123!',
    'tags': ['foo:bar'],
}

TLS_CONFIG = {
    'server': HOST,
    'port': HTTPS_PORT,
    'username': 'datadog',
    'password': 'Datadog123!',
    'tls_verify': True,
    'tags': ['foo:bar'],
}
