# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5000


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

NAMESPACE = 'datadog.csi_driver'

METRICS = [
    'node_publish_volume_attempts.count',
    'node_unpublish_volume_attempts.count',
]

METRICS_MOCK = [f'{NAMESPACE}.{m}' for m in METRICS]
