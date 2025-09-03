# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

CLICKHOUSE_VERSION = os.environ['CLICKHOUSE_VERSION']

COMPOSE_FILE = os.path.join(HERE, 'docker', 'compose.yaml')

CLICKHOUSE_NODE_NUM = 2
HTTP_START_PORT = 8123
TCP_START_PORT = 9000

CONFIG = {
    'server': HOST,
    'port': TCP_START_PORT,
    'username': 'datadog',
    'password': 'Datadog123!',
    'tags': ['foo:bar'],
}
