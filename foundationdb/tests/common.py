# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_here

dirname = os.path.dirname(__file__)
HERE = get_here()

PROTOCOL = os.environ.get("PROTOCOL")

CLUSTER_FILE = os.path.join(dirname, 'fdb.cluster')
TLS_CLUSTER_FILE = os.path.join(dirname, 'fdb-tls.cluster')
TLS_CERT_FILE = os.path.join(dirname, 'docker/tls/fdb.pem')
TLS_KEY_FILE = os.path.join(dirname, 'docker/tls/private.key')

INSTANCE = {
    'cluster_file': CLUSTER_FILE,
    'tls_certificate_file': TLS_CERT_FILE,
    'tls_key_file': TLS_KEY_FILE,
    'tls_verify_peers': 'Check.Valid=0',
}

TLS_INSTANCE = {
    'cluster_file': TLS_CLUSTER_FILE,
    'tls_certificate_file': TLS_CERT_FILE,
    'tls_key_file': TLS_KEY_FILE,
    'tls_verify_peers': 'Check.Valid=0',
}

E2E_INSTANCE = {
    'cluster_file': '/fdb/fdb.cluster',
    'tls_certificate_file': '/fdb/tls/fdb.pem',
    'tls_key_file': '/fdb/tls/private.key',
    'tls_verify_peers': 'Check.Valid=0',
}

E2E_TLS_INSTANCE = {
    'cluster_file': '/fdb/fdb-tls.cluster',
    'tls_certificate_file': '/fdb/tls/fdb.pem',
    'tls_key_file': '/fdb/tls/private.key',
    'tls_verify_peers': 'Check.Valid=0',
}


E2E_CONFIG = {'init_config': {}, 'instances': [E2E_INSTANCE]}

E2E_TLS_CONFIG = {'init_config': {}, 'instances': [E2E_TLS_INSTANCE]}

E2E_METADATA = {
    'start_commands': [
        'curl -o foundationdb-clients_6.3.23-1_amd64.deb '
        '-L https://github.com/apple/foundationdb/releases/download/6.3.23/foundationdb-clients_6.3.23-1_amd64.deb',
        'dpkg -i foundationdb-clients_6.3.23-1_amd64.deb',
    ],
    'docker_volumes': [
        '{}:/fdb/fdb.cluster'.format(CLUSTER_FILE),
        '{}:/fdb/fdb-tls.cluster'.format(TLS_CLUSTER_FILE),
        '{}:/fdb/tls/fdb.pem'.format(TLS_CERT_FILE),
        '{}:/fdb/tls/private.key'.format(TLS_KEY_FILE),
    ],
}

METRICS = [
    "foundationdb.latency_probe.batch_priority_transaction_start_seconds",
    "foundationdb.latency_probe.commit_seconds",
    "foundationdb.latency_probe.immediate_priority_transaction_start_seconds",
    "foundationdb.latency_probe.read_seconds",
    "foundationdb.latency_probe.transaction_start_seconds",
    "foundationdb.machines",
    "foundationdb.processes",
    "foundationdb.degraded_processes",
    "foundationdb.workload.transactions.committed.counter",
    "foundationdb.workload.transactions.committed.hz",
    "foundationdb.workload.transactions.conflicted.counter",
    "foundationdb.workload.transactions.conflicted.hz",
    "foundationdb.workload.transactions.rejected_for_queued_too_long.counter",
    "foundationdb.workload.transactions.rejected_for_queued_too_long.hz",
    "foundationdb.workload.transactions.started.counter",
    "foundationdb.workload.transactions.started.hz",
    "foundationdb.workload.transactions.started_batch_priority.counter",
    "foundationdb.workload.transactions.started_batch_priority.hz",
    "foundationdb.workload.transactions.started_default_priority.counter",
    "foundationdb.workload.transactions.started_default_priority.hz",
    "foundationdb.workload.transactions.started_immediate_priority.counter",
    "foundationdb.workload.transactions.started_immediate_priority.hz",
    "foundationdb.workload.operations.location_requests.counter",
    "foundationdb.workload.operations.location_requests.hz",
    "foundationdb.workload.operations.low_priority_reads.counter",
    "foundationdb.workload.operations.low_priority_reads.hz",
    "foundationdb.workload.operations.memory_errors.counter",
    "foundationdb.workload.operations.memory_errors.hz",
    "foundationdb.workload.operations.read_requests.counter",
    "foundationdb.workload.operations.read_requests.hz",
    "foundationdb.workload.operations.reads.counter",
    "foundationdb.workload.operations.reads.hz",
    "foundationdb.workload.operations.writes.counter",
    "foundationdb.workload.operations.writes.hz",
    "foundationdb.data.system_kv_size_bytes",
    "foundationdb.data.total_disk_used_bytes",
    "foundationdb.data.total_kv_size_bytes",
    "foundationdb.data.least_operating_space_bytes_log_server",
    "foundationdb.data.moving_data.in_flight_bytes",
    "foundationdb.data.moving_data.in_queue_bytes",
    "foundationdb.data.moving_data.total_written_bytes",
    "foundationdb.datacenter_lag.seconds",
    "foundationdb.instances",
    "foundationdb.process.role.input_bytes.hz",
    "foundationdb.process.role.input_bytes.counter",
    "foundationdb.process.role.durable_bytes.hz",
    "foundationdb.process.role.durable_bytes.counter",
    "foundationdb.process.role.total_queries.hz",
    "foundationdb.process.role.total_queries.counter",
    "foundationdb.process.role.bytes_queried.hz",
    "foundationdb.process.role.bytes_queried.counter",
    "foundationdb.process.role.finished_queries.hz",
    "foundationdb.process.role.finished_queries.counter",
    "foundationdb.process.role.keys_queried.hz",
    "foundationdb.process.role.keys_queried.counter",
    "foundationdb.process.role.low_priority_queries.hz",
    "foundationdb.process.role.low_priority_queries.counter",
    "foundationdb.process.role.mutation_bytes.hz",
    "foundationdb.process.role.mutation_bytes.counter",
    "foundationdb.process.role.mutations.hz",
    "foundationdb.process.role.mutations.counter",
    "foundationdb.process.role.stored_bytes",
    "foundationdb.process.role.query_queue_max",
    "foundationdb.process.role.local_rate",
    "foundationdb.process.role.kvstore_available_bytes",
    "foundationdb.process.role.kvstore_free_bytes",
    "foundationdb.process.role.kvstore_inline_keys",
    "foundationdb.process.role.kvstore_total_bytes",
    "foundationdb.process.role.kvstore_total_nodes",
    "foundationdb.process.role.kvstore_total_size",
    "foundationdb.process.role.kvstore_used_bytes",
    "foundationdb.process.cpu.usage_cores",
    "foundationdb.process.disk.free_bytes",
    "foundationdb.process.disk.reads.hz",
    "foundationdb.process.disk.total_bytes",
    "foundationdb.process.disk.writes.hz",
    "foundationdb.process.memory.available_bytes",
    "foundationdb.process.memory.limit_bytes",
    "foundationdb.process.memory.unused_allocated_memory",
    "foundationdb.process.memory.used_bytes",
    "foundationdb.process.network.connection_errors.hz",
    "foundationdb.process.network.connections_closed.hz",
    "foundationdb.process.network.connections_established.hz",
    "foundationdb.process.network.current_connections",
    "foundationdb.process.network.megabits_received.hz",
    "foundationdb.process.network.megabits_sent.hz",
    "foundationdb.process.network.tls_policy_failures.hz",
    "foundationdb.process.role.commit_latency_statistics.count",
    "foundationdb.process.role.commit_latency_statistics.max",
    "foundationdb.process.role.commit_latency_statistics.min",
    "foundationdb.process.role.commit_latency_statistics.p25",
    "foundationdb.process.role.commit_latency_statistics.p90",
    "foundationdb.process.role.commit_latency_statistics.p99",
    "foundationdb.process.role.data_lag.seconds",
    "foundationdb.process.role.durability_lag.seconds",
    "foundationdb.process.role.grv_latency_statistics.default.count",
    "foundationdb.process.role.grv_latency_statistics.default.max",
    "foundationdb.process.role.grv_latency_statistics.default.min",
    "foundationdb.process.role.grv_latency_statistics.default.p25",
    "foundationdb.process.role.grv_latency_statistics.default.p90",
    "foundationdb.process.role.grv_latency_statistics.default.p99",
    "foundationdb.process.role.read_latency_statistics.count",
    "foundationdb.process.role.read_latency_statistics.max",
    "foundationdb.process.role.read_latency_statistics.min",
    "foundationdb.process.role.read_latency_statistics.p25",
    "foundationdb.process.role.read_latency_statistics.p90",
    "foundationdb.process.role.read_latency_statistics.p99",
    "foundationdb.process.role.queue_length",
    "foundationdb.processes_per_role.cluster_controller",
    "foundationdb.processes_per_role.coordinator",
    "foundationdb.processes_per_role.data_distributor",
    "foundationdb.processes_per_role.log",
    "foundationdb.processes_per_role.master",
    "foundationdb.processes_per_role.proxy",
    "foundationdb.processes_per_role.ratekeeper",
    "foundationdb.processes_per_role.resolver",
    "foundationdb.processes_per_role.storage",
]
