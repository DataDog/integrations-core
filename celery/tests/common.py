# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 5555


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    'openmetrics_endpoint': f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:tag'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS = [
    'celery.flower.events.count',
    'celery.flower.events.created',
    'celery.flower.task.prefetch_time.seconds',
    'celery.flower.task.runtime.created',
    'celery.flower.task.runtime.seconds.bucket',
    'celery.flower.task.runtime.seconds.count',
    'celery.flower.task.runtime.seconds.sum',
    'celery.flower.worker.executing_tasks',
    'celery.flower.worker.online',
    'celery.flower.worker.prefetched_tasks',
]


E2E_METADATA = {
    'env_vars': {
        'DD_LOGS_ENABLED': 'true',
        'DD_LOGS_CONFIG_CONTAINER_COLLECT_ALL': 'true',
    },
    'docker_volumes': ['/var/run/docker.sock:/var/run/docker.sock:ro'],
}
