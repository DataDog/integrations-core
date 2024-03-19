# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://argo_rollouts:8090/metrics',
    'tags': ['test:tag'],
}

OM_METRICS = [
    # 'argo_rollouts.conroller.info',
    'argo_rollouts.controller.clientset.k8s.request.count',
    'argo_rollouts.go.gc.duration.seconds.count',
    'argo_rollouts.go.gc.duration.seconds.quantile',
    'argo_rollouts.go.gc.duration.seconds.sum',
    'argo_rollouts.go.goroutines',
    'argo_rollouts.go.info',
    'argo_rollouts.go.memstats.alloc_bytes',
    'argo_rollouts.go.memstats.alloc_bytes.count',
    'argo_rollouts.go.memstats.buck_hash.sys_bytes',
    'argo_rollouts.go.memstats.frees.count',
    'argo_rollouts.go.memstats.gc.sys_bytes',
    'argo_rollouts.go.memstats.heap.alloc_bytes',
    'argo_rollouts.go.memstats.heap.idle_bytes',
    'argo_rollouts.go.memstats.heap.inuse_bytes',
    'argo_rollouts.go.memstats.heap.objects',
    'argo_rollouts.go.memstats.heap.released_bytes',
    'argo_rollouts.go.memstats.heap.sys_bytes',
    'argo_rollouts.go.memstats.lookups.count',
    'argo_rollouts.go.memstats.mallocs.count',
    'argo_rollouts.go.memstats.mcache.inuse_bytes',
    'argo_rollouts.go.memstats.mcache.sys_bytes',
    'argo_rollouts.go.memstats.mspan.inuse_bytes',
    'argo_rollouts.go.memstats.mspan.sys_bytes',
    'argo_rollouts.go.memstats.next.gc_bytes',
    'argo_rollouts.go.memstats.other.sys_bytes',
    'argo_rollouts.go.memstats.stack.inuse_bytes',
    'argo_rollouts.go.memstats.stack.sys_bytes',
    'argo_rollouts.go.memstats.sys_bytes',
    'argo_rollouts.go.threads',
    'argo_rollouts.notification.send.bucket',
    'argo_rollouts.notification.send.count',
    'argo_rollouts.notification.send.sum',
    'argo_rollouts.process.cpu.seconds.count',
    'argo_rollouts.process.max_fds',
    'argo_rollouts.process.open_fds',
    'argo_rollouts.process.resident_memory.bytes',
    'argo_rollouts.process.start_time.seconds',
    'argo_rollouts.process.virtual_memory.bytes',
    'argo_rollouts.process.virtual_memory.max_bytes',
    'argo_rollouts.rollout.events.count',
    'argo_rollouts.rollout.info',
    'argo_rollouts.rollout.info.replicas.available',
    'argo_rollouts.rollout.info.replicas.desired',
    'argo_rollouts.rollout.info.replicas.unavailable',
    'argo_rollouts.rollout.info.replicas.updated',
    'argo_rollouts.rollout.phase',
    'argo_rollouts.rollout.reconcile.bucket',
    'argo_rollouts.rollout.reconcile.count',
    'argo_rollouts.rollout.reconcile.error.count',
    'argo_rollouts.rollout.reconcile.sum',
    'argo_rollouts.workqueue.adds.count',
    'argo_rollouts.workqueue.depth',
    'argo_rollouts.workqueue.longest.running_processor.seconds',
    'argo_rollouts.workqueue.queue.duration.seconds.bucket',
    'argo_rollouts.workqueue.queue.duration.seconds.count',
    'argo_rollouts.workqueue.queue.duration.seconds.sum',
    'argo_rollouts.workqueue.retries.count',
    'argo_rollouts.workqueue.unfinished_work.seconds',
    'argo_rollouts.workqueue.work.duration.seconds.bucket',
    'argo_rollouts.workqueue.work.duration.seconds.count',
    'argo_rollouts.workqueue.work.duration.seconds.sum',
]


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
