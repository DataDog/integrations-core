# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.base import is_affirmative
from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()

METRICS = [
    # CPU
    'voltdb.cpu.percent_used',
    # MEMORY
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
    # SNAPSHOTSTATUS
    'voltdb.snapshot_status.size',
    'voltdb.snapshot_status.duration',
    'voltdb.snapshot_status.throughput',
    # COMMANDLOG
    'voltdb.commandlog.fsync_interval',
    'voltdb.commandlog.in_use_segment_count',
    'voltdb.commandlog.outstanding_bytes',
    'voltdb.commandlog.outstanding_transactions',
    'voltdb.commandlog.segment_count',
    # PROCEDURE
    'voltdb.procedure.invocations',
    'voltdb.procedure.timed_invocations',
    'voltdb.procedure.min_execution_time',
    'voltdb.procedure.max_execution_time',
    'voltdb.procedure.avg_execution_time',
    'voltdb.procedure.min_result_size',
    'voltdb.procedure.max_result_size',
    'voltdb.procedure.avg_result_size',
    'voltdb.procedure.min_parameter_set_size',
    'voltdb.procedure.max_parameter_set_size',
    'voltdb.procedure.avg_parameter_set_size',
    'voltdb.procedure.aborts',
    'voltdb.procedure.failures',
    'voltdb.procedure.successes',
    # LATENCY
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
    # PROCEDUREDETAIL
    'voltdb.statement.invocations',
    'voltdb.statement.timed_invocations',
    'voltdb.statement.min_execution_time',
    'voltdb.statement.max_execution_time',
    'voltdb.statement.avg_execution_time',
    'voltdb.statement.min_result_size',
    'voltdb.statement.max_result_size',
    'voltdb.statement.avg_result_size',
    'voltdb.statement.min_parameter_set_size',
    'voltdb.statement.max_parameter_set_size',
    'voltdb.statement.avg_parameter_set_size',
    'voltdb.statement.aborts',
    'voltdb.statement.failures',
    'voltdb.statement.successes',
    # GC
    'voltdb.gc.newgen_avg_gc_time',
    'voltdb.gc.newgen_gc_count',
    'voltdb.gc.oldgen_avg_gc_time',
    'voltdb.gc.oldgen_gc_count',
    # IO
    'voltdb.io.bytes_read',
    'voltdb.io.bytes_written',
    'voltdb.io.messages_read',
    'voltdb.io.messages_written',
    # TABLE
    # ('voltdb.table.tuple_limit' not submitted as it is null)
    'voltdb.table.tuple_count',
    'voltdb.table.tuple_allocated_memory',
    'voltdb.table.tuple_data_memory',
    'voltdb.table.string_data_memory',
    'voltdb.table.percent_full',
    # INDEX
    'voltdb.index.entry_count',
    'voltdb.index.memory_estimate',
    # Custom queries
    'voltdb.custom.heroes.count',
    'voltdb.custom.heroes.avg_name_length',
]

METADATA_EXCLUDE_METRICS = [
    # Custom queries
    'voltdb.custom.heroes.count',
    'voltdb.custom.heroes.avg_name_length',
]

TLS_ENABLED = is_affirmative(os.environ.get('TLS_ENABLED'))
TLS_OUTPUT_DIR = os.path.join(HERE, 'tlsoutput')
TLS_CLIENT_CERT = os.path.join(TLS_OUTPUT_DIR, 'client.pem')  # type: str
TLS_PASSWORD = 'tlspass'
TLS_CONTAINER_LOCALCERT_PATH = '/tmp/localcert.properties'

VOLTDB_DEPLOYMENT = os.path.join(HERE, 'compose', 'deployment-tls.xml' if TLS_ENABLED else 'deployment.xml')
VOLTDB_SCHEME = 'https' if TLS_ENABLED else 'http'
VOLTDB_CLIENT_PORT = 8443 if TLS_ENABLED else 8080
VOLTDB_URL = '{}://{}:{}'.format(VOLTDB_SCHEME, HOST, VOLTDB_CLIENT_PORT)

VOLTDB_VERSION = os.environ['VOLTDB_VERSION']
VOLTDB_IMAGE = os.environ['VOLTDB_IMAGE']
