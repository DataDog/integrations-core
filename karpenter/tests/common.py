# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
PORT = 8000


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


MOCKED_INSTANCE = {
    "openmetrics_endpoint": f"http://{HOST}:{PORT}/metrics",
    'tags': ['test:tag'],
}

COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')

TEST_METRICS = [
    'karpenter.certwatcher.read.certificate.count',
    'karpenter.certwatcher.read.certificate.errors.count',
    'karpenter.controller.runtime.active_workers',
    'karpenter.controller.runtime.max.concurrent_reconciles',
    'karpenter.controller.runtime.reconcile.count',
    'karpenter.controller.runtime.reconcile_errors.count',
    'karpenter.deprovisioning.replacement.machine.initialized_seconds.bucket',
    'karpenter.deprovisioning.replacement.machine.initialized_seconds.count',
    'karpenter.deprovisioning.replacement.machine.initialized_seconds.sum',
    'karpenter.go.gc.duration_seconds.count',
    'karpenter.go.gc.duration_seconds.quantile',
    'karpenter.go.gc.duration_seconds.sum',
    'karpenter.go.memstats.alloc_bytes',
    'karpenter.go.memstats.buck.hash.sys_bytes',
    'karpenter.go.memstats.frees.count',
    'karpenter.go.memstats.gc.sys_bytes',
    'karpenter.go.memstats.heap.alloc_bytes',
    'karpenter.go.memstats.heap.idle_bytes',
    'karpenter.go.memstats.heap.inuse_bytes',
    'karpenter.go.memstats.heap.released_bytes',
    'karpenter.go.memstats.heap.sys_bytes',
    'karpenter.go.memstats.heap_objects',
    'karpenter.go.memstats.last.gc.time_seconds',
    'karpenter.go.memstats.lookups.count',
    'karpenter.go.memstats.mallocs.count',
    'karpenter.go.memstats.mcache.inuse_bytes',
    'karpenter.go.memstats.mcache.sys_bytes',
    'karpenter.go.memstats.mspan.inuse_bytes',
    'karpenter.go.memstats.mspan.sys_bytes',
    'karpenter.go.memstats.next.gc_bytes',
    'karpenter.go.memstats.other.sys_bytes',
    'karpenter.go.memstats.stack.inuse_bytes',
    'karpenter.go.memstats.stack.sys_bytes',
    'karpenter.go.memstats.sys_bytes',
    'karpenter.go_goroutines',
    'karpenter.go_info',
    'karpenter.go_threads',
    'karpenter.interruption.deleted_messages.count',
    'karpenter.interruption.message.latency.time_seconds.bucket',
    'karpenter.interruption.message.latency.time_seconds.count',
    'karpenter.interruption.message.latency.time_seconds.sum',
    'karpenter.pods.startup.time_seconds.count',
    'karpenter.pods.startup.time_seconds.sum',
    'karpenter.process.cpu_seconds.count',
    'karpenter.process.max_fds',
    'karpenter.process.open_fds',
    'karpenter.process.resident.memory_bytes',
    'karpenter.process.start.time_seconds',
    'karpenter.process.virtual.memory.max_bytes',
    'karpenter.process.virtual.memory_bytes',
    'karpenter.provisioner.scheduling.duration_seconds.bucket',
    'karpenter.provisioner.scheduling.duration_seconds.count',
    'karpenter.provisioner.scheduling.duration_seconds.sum',
    'karpenter.rest.client_requests.count',
    'karpenter.workqueue.longest.running.processor_seconds',
    'karpenter.workqueue.queue.duration_seconds.bucket',
    'karpenter.workqueue.queue.duration_seconds.count',
    'karpenter.workqueue.queue.duration_seconds.sum',
    'karpenter.workqueue.unfinished.work_seconds',
    'karpenter.workqueue.work.duration_seconds.bucket',
    'karpenter.workqueue.work.duration_seconds.count',
    'karpenter.workqueue.work.duration_seconds.sum',
    'karpenter.workqueue_adds.count',
    'karpenter.workqueue_depth',
    'karpenter.workqueue_retries.count',
]
