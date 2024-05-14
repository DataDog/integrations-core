# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8085


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:test'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

METRICS_MOCK = [
    'cluster.cpu.current.cores',
    'cluster.memory.current.bytes',
    'cluster.safe.to.autoscale',
    'cpu.limits.cores',
    'created.node.groups.count',
    'deleted.node.groups.count',
    'errors.count',
    'evicted.pods.count',
    'failed.scale.ups.count',
    'function.duration.seconds.bucket',
    'function.duration.seconds.count',
    'function.duration.seconds.sum',
    'last.activity',
    'max.nodes.count',
    'memory.limits.bytes',
    'nap.enabled',
    'nodes.count',
    'node.groups.count',
    'old.unregistered.nodes.removed.count',
    'scaled.down.gpu.nodes.count',
    'scaled.down.nodes.count',
    'scaled.up.gpu.nodes.count',
    'scaled.up.nodes.count',
    'skipped.scale.events.count',
    'unneeded.nodes.count',
    'unschedulable.pods.count',
]

METRICS_MOCK = [f'kubernetes_cluster_autoscaler.{m}' for m in METRICS_MOCK]
