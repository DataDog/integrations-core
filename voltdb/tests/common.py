# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
VOLTDB_API_PORT = 8080

METRICS = [
    'voltdb.io.bytes_read',
    'voltdb.io.bytes_written',
    'voltdb.io.messages_read',
    'voltdb.io.messages_written',
    'voltdb.commandlog.fsync_interval',
    'voltdb.commandlog.in_use_segment_count',
    'voltdb.commandlog.outstanding_bytes',
    'voltdb.commandlog.outstanding_transactions',
    'voltdb.commandlog.segment_count',
    'voltdb.cpu.percent_used',
    'voltdb.gc.newgen_avg_gc_time',
    'voltdb.gc.newgen_gc_count',
    'voltdb.gc.oldgen_avg_gc_time',
    'voltdb.gc.oldgen_gc_count',
    'voltdb.latency.count',
    'voltdb.latency.interval',
    'voltdb.latency.max',
    'voltdb.latency.p50',
    'voltdb.latency.p95',
    'voltdb.latency.p99',
    'voltdb.latency.p999',
    'voltdb.latency.p9999',
    'voltdb.latency.p99999',
    'voltdb.latency.transactions_per_sec',
    'voltdb.memory.index',
    'voltdb.memory.java.max_heap',
    'voltdb.memory.java.unused',
    'voltdb.memory.java.used',
    'voltdb.memory.physical',
    'voltdb.memory.pooled',
    'voltdb.memory.rss',
    'voltdb.memory.string',
    'voltdb.memory.tuple_allocated',
    'voltdb.memory.tuple_count',
    'voltdb.memory.tuple_data',
]
