# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 9090


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [
    'katib.controller.reconcile.count',
    'katib.controller.reconcile.duration.seconds',
    'katib.experiment.created.total',
    'katib.experiment.duration.seconds',
    'katib.experiment.failed.total',
    'katib.experiment.running.total',
    'katib.experiment.succeeded.total',
    'katib.suggestion.created.total',
    'katib.suggestion.duration.seconds',
    'katib.suggestion.failed.total',
    'katib.suggestion.running.total',
    'katib.suggestion.succeeded.total',
    'katib.trial.created.total',
    'katib.trial.duration.seconds',
    'katib.trial.failed.total',
    'katib.trial.running.total',
    'katib.trial.succeeded.total',
    'kserve.inference.duration.seconds',
    'kserve.inference.errors',
    'kserve.inference.request.bytes',
    'kserve.inference.response.bytes',
    'kserve.inferences.total',
    'notebook.server.created.total',
    'notebook.server.failed.total',
    'notebook.server.reconcile.count',
    'notebook.server.reconcile.duration.seconds',
    'notebook.server.running.total',
    'notebook.server.succeeded.total',
    'pipeline.run.duration.seconds',
    'pipeline.run.status',
]

METRICS_MOCK = [f'kubeflow.{m}' for m in METRICS_MOCK]
