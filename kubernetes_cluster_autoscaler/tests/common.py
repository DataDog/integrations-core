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
    'go.gc.duration.seconds.count',
    'go.gc.duration.seconds.sum',
    'go.gc.duration.seconds.quantile',
    'go.goroutines',
    'go.info',
    'go.memstats.alloc_bytes',
    'go.memstats.alloc_bytes.count',
    'go.memstats.buck_hash.sys_bytes',
    'go.memstats.frees.count',
    'go.memstats.gc.sys_bytes',
    'go.memstats.heap.alloc_bytes',
    'go.memstats.heap.idle_bytes',
    'go.memstats.heap.inuse_bytes',
    'go.memstats.heap.objects',
    'go.memstats.heap.released_bytes',
    'go.memstats.heap.sys_bytes',
    'go.memstats.lookups.count',
    'go.memstats.mallocs.count',
    'go.memstats.mcache.inuse_bytes',
    'go.memstats.mcache.sys_bytes',
    'go.memstats.mspan.inuse_bytes',
    'go.memstats.mspan.sys_bytes',
    'go.memstats.next.gc_bytes',
    'go.memstats.other.sys_bytes',
    'go.memstats.stack.inuse_bytes',
    'go.memstats.stack.sys_bytes',
    'go.memstats.sys_bytes',
    'go.threads',
]

METRICS_MOCK = [f'kubernetes_cluster_autoscaler.{m}' for m in METRICS_MOCK]
