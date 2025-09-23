# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_here

HERE = get_here()
USE_AUTH = is_affirmative(os.environ.get('USE_AUTH'))

MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://weaviate:2112/metrics',
    'weaviate_api_endpoint': 'http://weaviate:8080',
    'tags': ['test:tag'],
}

OM_MOCKED_INSTANCE = {
    'openmetrics_endpoint': 'http://weaviate:2112/metrics',
    'tags': ['test:tag'],
}

BATCH_OBJECTS = {
    'objects': [
        {'class': 'Example', 'vector': [0.1, 0.3], 'properties': {'text': 'This is the first object'}},
        {'class': 'Example', 'vector': [0.01, 0.7], 'properties': {'text': 'This is another object'}},
    ]
}

OM_METRICS = [
    'weaviate.go.gc.duration.seconds.count',
    'weaviate.go.gc.duration.seconds.quantile',
    'weaviate.go.gc.duration.seconds.sum',
    'weaviate.go.goroutines',
    'weaviate.go.info',
    'weaviate.go.memstats.alloc_bytes',
    'weaviate.go.memstats.alloc_bytes.count',
    'weaviate.go.memstats.buck_hash.sys_bytes',
    'weaviate.go.memstats.frees.count',
    'weaviate.go.memstats.lookups.count',
    'weaviate.go.memstats.gc.cpu_fraction',
    'weaviate.go.memstats.gc.sys_bytes',
    'weaviate.go.memstats.heap.alloc_bytes',
    'weaviate.go.memstats.heap.idle_bytes',
    'weaviate.go.memstats.heap.inuse_bytes',
    'weaviate.go.memstats.heap.objects',
    'weaviate.go.memstats.heap.released_bytes',
    'weaviate.go.memstats.heap.sys_bytes',
    'weaviate.go.memstats.mallocs.count',
    'weaviate.go.memstats.mcache.inuse_bytes',
    'weaviate.go.memstats.mcache.sys_bytes',
    'weaviate.go.memstats.mspan.inuse_bytes',
    'weaviate.go.memstats.mspan.sys_bytes',
    'weaviate.go.memstats.next.gc_bytes',
    'weaviate.go.memstats.other.sys_bytes',
    'weaviate.go.memstats.stack.inuse_bytes',
    'weaviate.go.memstats.stack.sys_bytes',
    'weaviate.go.memstats.sys_bytes',
    'weaviate.go.threads',
    'weaviate.process.cpu.seconds.count',
    'weaviate.process.max_fds',
    'weaviate.process.open_fds',
    'weaviate.process.resident_memory.bytes',
    'weaviate.process.start_time.seconds',
    'weaviate.process.virtual_memory.bytes',
    'weaviate.process.virtual_memory.max_bytes',
    'weaviate.promhttp.metric_handler.requests.count',
    'weaviate.promhttp.metric_handler.requests_in_flight',
    'weaviate.batch.durations_ms.bucket',
    'weaviate.batch.durations_ms.count',
    'weaviate.batch.durations_ms.sum',
    'weaviate.lsm.active.segments',
    'weaviate.lsm.segment.size',
    'weaviate.lsm.segments',
    'weaviate.objects',
    'weaviate.objects.durations_ms.count',
    'weaviate.objects.durations_ms.sum',
    'weaviate.queries.filtered.vector.durations_ms.count',
    'weaviate.queries.filtered.vector.durations_ms.sum',
    'weaviate.startup.durations_ms.count',
    'weaviate.startup.durations_ms.sum',
    'weaviate.startup.progress',
    'weaviate.vector.index.durations_ms.count',
    'weaviate.vector.index.durations_ms.sum',
    'weaviate.vector.index.maintenance.durations_ms.count',
    'weaviate.vector.index.maintenance.durations_ms.sum',
    'weaviate.vector.index.operations',
    'weaviate.vector.index.size',
    'weaviate.vector.index.tombstone.cleaned.count',
    'weaviate.vector.index.tombstone.cleanup.threads',
    'weaviate.vector.index.tombstones',
    'weaviate.lsm.memtable.durations_ms.count',
    'weaviate.lsm.memtable.durations_ms.sum',
    'weaviate.concurrent.queries',
    'weaviate.lsm.bloom.filters.duration_ms.count',
    'weaviate.lsm.bloom.filters.duration_ms.sum',
    'weaviate.lsm.memtable.size',
    "weaviate.queries.durations_ms.bucket",
    "weaviate.queries.durations_ms.count",
    "weaviate.queries.durations_ms.sum",
    "weaviate.query.dimensions.count",
    "weaviate.requests",
]

API_METRICS = [
    'weaviate.node.status',
    'weaviate.node.shard.objects',
    'weaviate.node.stats.objects',
    'weaviate.node.stats.shards',
]

latency_metric = ['weaviate.http.latency_ms']

FLAKY_E2E_METRICS = [
    'weaviate.lsm.segment.size',
    'weaviate.lsm.segments',
    'weaviate.lsm.bloom.filters.duration_ms.count',
    'weaviate.lsm.bloom.filters.duration_ms.sum',
    "weaviate.queries.durations_ms.bucket",
    "weaviate.queries.durations_ms.count",
    "weaviate.queries.durations_ms.sum",
    "weaviate.query.dimensions.count",
]

E2E_METRICS = OM_METRICS + API_METRICS + latency_metric


def get_fixture_path(filename):
    return os.path.join(HERE, 'fixtures', filename)
