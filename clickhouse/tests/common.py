# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE_PATH = os.path.join(HERE, 'docker', 'docker-compose.yaml')
SERVER_CERT_PATH = os.path.join(HERE, 'docker', 'certs', 'server.crt')

TLS_ENABLED = 'tls' in os.getenv('COMPOSE_PROFILES', '').split(',')

tls = pytest.mark.skipif(
    not TLS_ENABLED,
    reason='TLS tests require a ClickHouse version that supports modern TLS (22.7+)',
)

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
