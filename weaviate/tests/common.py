# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

MOCKED_INSTANCE = {'openmetrics_endpoint': 'http://weaviate:2112/metrics', 'weaviate_api': 'http://weaviate:8080'}

E2E_METRICS = [
    "weaviate.go.gc.duration.seconds.count",
    "weaviate.go.gc.duration.seconds.quantile",
    "weaviate.go.gc.duration.seconds.sum",
    "weaviate.go.goroutines",
    "weaviate.go.memstats.alloc_bytes",
    "weaviate.go.memstats.alloc_bytes.count",
    "weaviate.go.memstats.buck_hash.sys_bytes",
    "weaviate.go.memstats.frees.count",
    "weaviate.go.memstats.lookups.count",
    "weaviate.go.memstats.gc.cpu_fraction",
    "weaviate.go.memstats.gc.sys_bytes",
    "weaviate.go.memstats.heap.alloc_bytes",
    "weaviate.go.memstats.heap.idle_bytes",
    "weaviate.go.memstats.heap.inuse_bytes",
    "weaviate.go.memstats.heap.objects",
    "weaviate.go.memstats.heap.released_bytes",
    "weaviate.go.memstats.heap.sys_bytes",
    "weaviate.go.memstats.mallocs.count",
    "weaviate.go.memstats.mcache.inuse_bytes",
    "weaviate.go.memstats.mcache.sys_bytes",
    "weaviate.go.memstats.mspan.inuse_use",
    "weaviate.go.memstats.mspan.sys_bytes",
    "weaviate.go.memstats.next.gc_bytes",
    "weaviate.go.memstats.other.sys_bytes",
    "weaviate.go.memstats.stack.inuse_bytes",
    "weaviate.go.memstats.stack.sys_bytes",
    "weaviate.go.memstats.sys_bytes",
    "weaviate.go.threads",
    "weaviate.process.cpu.seconds.count",
    "weaviate.process.max_fds",
    "weaviate.process.open_fds",
    "weaviate.process.resident_memory.bytes",
    "weaviate.process.start_time.seconds",
    "weaviate.process.virtual_memory.bytes",
    "weaviate.process.virtual_memory.max_bytes",
    "weaviate.promhttp.metric_handler.requests.count",
    "weaviate.promhttp.metric_handler.requests_in_flight",
    "weaviate.http.latency_ms",
]

fixture_metrics = [
    "weaviate.batch.durations_ms.bucket",
    "weaviate.batch.durations_ms.count",
    "weaviate.batch.durations_ms.sum",
    "weaviate.lsm.active.segments",
    "weaviate.lsm.segment.count",
    "weaviate.lsm.segment.size",
    "weaviate.object_count",
    "weaviate.objects.durations_ms.count",
    "weaviate.objects.durations_ms.sum",
    "weaviate.queries.filtered_vector.durations_ms.count",
    "weaviate.queries.filtered_vector.durations_ms.sum",
    "weaviate.startup.durations_ms.count",
    "weaviate.startup.durations_ms.sum",
    "weaviate.startup.progress",
    "weaviate.vector.index.durations_ms.count",
    "weaviate.vector.index.durations_ms.sum",
    "weaviate.vector.index.maintenance.durations_ms.count",
    "weaviate.vector.index.maintenance.durations_ms.sum",
    "weaviate.vector.index.operations",
    "weaviate.vector.index.size",
    "weaviate.vector.index.tombstone.cleaned.count",
    "weaviate.vector.index.tombstone.cleanup.threads",
    "weaviate.vector.index.tombstones",
]

API_METRICS = [
    "weaviate.node.status",
    "weaviate.node.shard.objects",
    "weaviate.node.stats.objects",
    "weaviate.node.stats.shards",
    "weaviate.http.latency_ms",
]

TEST_METRICS = E2E_METRICS + fixture_metrics
