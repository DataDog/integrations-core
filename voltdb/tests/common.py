# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

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

TLS_ENABLED = is_affirmative(os.environ.get('TLS_ENABLED'))
TLS_OUTPUT_DIR = os.path.join(HERE, 'tlsoutput')
TLS_CLIENT_CERT = os.path.join(TLS_OUTPUT_DIR, 'client.pem')  # type: str
TLS_PASSWORD = 'tlspass'

VOLTDB_SCHEME = 'https' if TLS_ENABLED else 'http'
VOLTDB_CLIENT_PORT = 8080
VOLTDB_URL = '{}://{}:{}'.format(VOLTDB_SCHEME, HOST, VOLTDB_CLIENT_PORT)
