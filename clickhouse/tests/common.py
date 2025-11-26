# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()

CLICKHOUSE_VERSION = os.environ['CLICKHOUSE_VERSION']

COMPOSE_FILE = os.path.join(HERE, 'docker', 'compose.yaml')
COMPOSE_LOGS_FILE = os.path.join(HERE, 'docker', 'compose-logs.yaml')

CONFIG = {
    'server': get_docker_hostname(),
    'port': 8123,
    'username': 'datadog',
    'password': 'Datadog123!',
    'tags': ['foo:bar'],
}


def get_compose_file() -> tuple[str, bool]:
    if is_affirmative(os.getenv('MOUNT_LOGS', False)):
        return COMPOSE_LOGS_FILE, True

    return COMPOSE_FILE, False
