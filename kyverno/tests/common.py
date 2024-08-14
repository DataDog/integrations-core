# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

HERE = get_here()

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://kyverno:8000/metrics',
    'tags': ['test:tag'],
}


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)


COMMON_METRICS = [
    'kyverno.client.queries.count',
    'kyverno.controller.reconcile.count',
    'kyverno.go.gc.duration.seconds.count',
    'kyverno.go.gc.duration.seconds.quantile',
    'kyverno.go.gc.duration.seconds.sum',
    'kyverno.go.goroutines',
    'kyverno.go.info',
    'kyverno.go.memstats.alloc_bytes',
    'kyverno.go.memstats.alloc_bytes.count',
    'kyverno.go.memstats.buck_hash.sys_bytes',
    'kyverno.go.memstats.frees.count',
    'kyverno.go.memstats.gc.sys_bytes',
    'kyverno.go.memstats.heap.alloc_bytes',
    'kyverno.go.memstats.heap.idle_bytes',
    'kyverno.go.memstats.heap.inuse_bytes',
    'kyverno.go.memstats.heap.objects',
    'kyverno.go.memstats.heap.released_bytes',
    'kyverno.go.memstats.heap.sys_bytes',
    'kyverno.go.memstats.lookups.count',
    'kyverno.go.memstats.mallocs.count',
    'kyverno.go.memstats.mcache.inuse_bytes',
    'kyverno.go.memstats.mcache.sys_bytes',
    'kyverno.go.memstats.mspan.inuse_bytes',
    'kyverno.go.memstats.mspan.sys_bytes',
    'kyverno.go.memstats.next.gc_bytes',
    'kyverno.go.memstats.other.sys_bytes',
    'kyverno.go.memstats.stack.inuse_bytes',
    'kyverno.go.memstats.stack.sys_bytes',
    'kyverno.go.memstats.sys_bytes',
    'kyverno.go.threads',
    'kyverno.process.cpu.seconds.count',
    'kyverno.process.max_fds',
    'kyverno.process.open_fds',
    'kyverno.process.resident_memory.bytes',
    'kyverno.process.start_time.seconds',
    'kyverno.process.virtual_memory.bytes',
    'kyverno.process.virtual_memory.max_bytes',
]


REPORTS_METRICS = [
    'kyverno.controller.requeue.count',
    'kyverno.policy.execution.duration.seconds.bucket',
    'kyverno.policy.execution.duration.seconds.count',
    'kyverno.policy.execution.duration.seconds.sum',
    'kyverno.policy.results.count',
]

BACKGROUND_METRICS = [
    'kyverno.policy.changes.count',
    'kyverno.policy.rule.info',
]

ADMISSION_METRICS = [
    'kyverno.http.requests.count',
    'kyverno.http.requests.duration.seconds.bucket',
    'kyverno.http.requests.duration.seconds.count',
    'kyverno.http.requests.duration.seconds.sum',
    'kyverno.policy.changes.count',
    'kyverno.policy.rule.info',
]

CLEANUP_METRICS = []
