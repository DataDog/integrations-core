# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

HOST = get_docker_hostname()
HTTP_START_PORT = 8128
TCP_START_PORT = 9001
CLICKHOUSE_VERSION = os.environ['CLICKHOUSE_VERSION']

CONFIG = {
    'server': HOST,
    'port': TCP_START_PORT,
    'username': 'datadog',
    'password': 'Datadog123!',
    'tags': ['foo:bar'],
}
