# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname, get_here

from . import advanced_metrics, metrics

HERE = get_here()
SERVER_CERT_PATH = os.path.join(HERE, 'docker', 'certs', 'server.crt')

HOST = get_docker_hostname()
HTTP_START_PORT = 8128
TCP_START_PORT = 9001
HTTPS_PORT = 8134

CLICKHOUSE_VERSION = os.environ['CLICKHOUSE_VERSION']

COMPOSE_FILE = os.path.join(HERE, 'docker', 'compose.yaml')
COMPOSE_LOGS_FILE = os.path.join(HERE, 'docker', 'compose-logs.yaml')
COMPOSE_LEGACY_FILE = os.path.join(HERE, 'docker', 'compose-legacy.yaml')

CONFIG = {
    'server': get_docker_hostname(),
    'port': 8123,
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


def get_compose_file() -> tuple[str, bool]:
    if is_legacy(CLICKHOUSE_VERSION):
        return COMPOSE_LEGACY_FILE, False

    if is_affirmative(os.getenv('MOUNT_LOGS', False)):
        return COMPOSE_LOGS_FILE, True

    return COMPOSE_FILE, False


def get_metrics(version: str) -> list[str]:
    if is_legacy(version):
        return metrics.get_metrics(version)

    return advanced_metrics.get_metrics(version)


def get_optional_metrics(version: str) -> list[str]:
    if is_legacy(version):
        return metrics.OPTIONAL_METRICS

    return advanced_metrics.get_optional_metrics(version)


def is_legacy(version: str) -> bool:
    return version in ["18", "19", "20", "21.8", "22.7"]
