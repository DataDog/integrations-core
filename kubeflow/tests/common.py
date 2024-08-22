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
    'katib.controller.reconcile.duration.seconds.bucket',
    'katib.controller.reconcile.duration.seconds.count',
    'katib.controller.reconcile.duration.seconds.sum',
    'katib.experiment.created.count',
    'katib.experiment.duration.seconds.bucket',
    'katib.experiment.duration.seconds.count',
    'katib.experiment.duration.seconds.sum',
    'katib.experiment.failed.count',
    'katib.experiment.running.total',
    'katib.experiment.succeeded.count',
    'katib.suggestion.created.count',
    'katib.suggestion.duration.seconds.bucket',
    'katib.suggestion.duration.seconds.count',
    'katib.suggestion.duration.seconds.sum',
    'katib.suggestion.failed.count',
    'katib.suggestion.running.total',
    'katib.suggestion.succeeded.count',
    'katib.trial.created.count',
    'katib.trial.duration.seconds.bucket',
    'katib.trial.duration.seconds.count',
    'katib.trial.duration.seconds.sum',
    'katib.trial.failed.count',
    'katib.trial.running.total',
    'katib.trial.succeeded.count',
    'kserve.inference.duration.seconds.bucket',
    'kserve.inference.duration.seconds.count',
    'kserve.inference.duration.seconds.sum',
    'kserve.inference.errors.count',
    'kserve.inference.request.bytes.bucket',
    'kserve.inference.request.bytes.count',
    'kserve.inference.request.bytes.sum',
    'kserve.inference.response.bytes.bucket',
    'kserve.inference.response.bytes.count',
    'kserve.inference.response.bytes.sum',
    'kserve.inferences.count',
    'notebook.server.created.count',
    'notebook.server.failed.count',
    'notebook.server.reconcile.count',
    'notebook.server.reconcile.duration.seconds.bucket',
    'notebook.server.reconcile.duration.seconds.count',
    'notebook.server.reconcile.duration.seconds.sum',
    'notebook.server.running.total',
    'notebook.server.succeeded.count',
    'pipeline.run.duration.seconds.bucket',
    'pipeline.run.duration.seconds.count',
    'pipeline.run.duration.seconds.sum',
    'pipeline.run.status',
]

METRICS_MOCK = [f'kubeflow.{m}' for m in METRICS_MOCK]
