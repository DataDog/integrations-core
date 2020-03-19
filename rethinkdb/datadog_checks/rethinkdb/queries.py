# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import operations
from .document_db import DocumentQuery

# System configuration.

# See: https://rethinkdb.com/docs/system-tables/#configuration-tables
config_summary = DocumentQuery(
    source=operations.get_config_summary,
    name='config_summary',
    prefix='config',
    metrics=[{'type': 'gauge', 'path': 'servers'}, {'type': 'gauge', 'path': 'databases'}],
    groups=[
        {'path': 'tables_per_database', 'key_tag': 'database', 'value_metric_type': 'gauge'},
        {'path': 'secondary_indexes_per_table', 'key_tag': 'table', 'value_metric_type': 'gauge'},
    ],
)


# System statistics.

# See: https://rethinkdb.com/docs/system-stats#cluster
cluster_statistics = DocumentQuery(
    source=operations.get_cluster_statistics,
    name='cluster_statistics',
    prefix='stats.cluster',
    metrics=[
        {'type': 'gauge', 'path': 'query_engine.queries_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
    ],
)

# See: https://rethinkdb.com/docs/system-stats#server
server_statistics = DocumentQuery(
    source=operations.get_servers_statistics,
    name='server_statistics',
    prefix='stats.server',
    metrics=[
        {'type': 'gauge', 'path': 'query_engine.client_connections'},
        {'type': 'gauge', 'path': 'query_engine.clients_active'},
        {'type': 'gauge', 'path': 'query_engine.queries_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.queries_total'},
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.read_docs_total'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.written_docs_total'},
    ],
)

# See: https://rethinkdb.com/docs/system-stats#table
table_statistics = DocumentQuery(
    source=operations.get_tables_statistics,
    name='table_statistics',
    prefix='stats.table',
    metrics=[
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
    ],
)

# See: https://rethinkdb.com/docs/system-stats#replica
replica_statistics = DocumentQuery(
    source=operations.get_replicas_statistics,
    name='replica_statistics',
    prefix='stats.table_server',
    metrics=[
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.read_docs_total'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
        {'type': 'monotonic_count', 'path': 'query_engine.written_docs_total'},
        {'type': 'gauge', 'path': 'storage_engine.cache.in_use_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.read_bytes_per_sec'},
        {'type': 'monotonic_count', 'path': 'storage_engine.disk.read_bytes_total'},
        {'type': 'gauge', 'path': 'storage_engine.disk.written_bytes_per_sec'},
        {'type': 'monotonic_count', 'path': 'storage_engine.disk.written_bytes_total'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.metadata_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.data_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.garbage_bytes'},
        {'type': 'gauge', 'path': 'storage_engine.disk.space_usage.preallocated_bytes'},
    ],
)


# System status.

# See: https://rethinkdb.com/docs/system-tables/#table_status
table_statuses = DocumentQuery(
    source=operations.get_table_statuses,
    name='table_status',
    prefix='table_status',
    metrics=[
        {'type': 'service_check', 'path': 'status.ready_for_outdated_reads', 'modifier': 'ok_warning'},
        {'type': 'service_check', 'path': 'status.ready_for_reads', 'modifier': 'ok_warning'},
        {'type': 'service_check', 'path': 'status.ready_for_writes', 'modifier': 'ok_warning'},
        {'type': 'service_check', 'path': 'status.all_replicas_ready', 'modifier': 'ok_warning'},
        {'type': 'gauge', 'path': 'shards', 'modifier': 'total'},
    ],
    enumerations=[
        {
            'path': 'shards',
            'index_tag': 'shard',
            'metrics': [
                {'type': 'gauge', 'path': 'replicas', 'modifier': 'total'},
                {'type': 'gauge', 'path': 'primary_replicas', 'modifier': 'total'},
            ],
        }
    ],
)

# See: https://rethinkdb.com/docs/system-tables/#server_status
server_statuses = DocumentQuery(
    source=operations.get_server_statuses,
    name='server_status',
    prefix='server_status',
    metrics=[
        {'type': 'gauge', 'path': 'network.time_connected', 'modifier': 'timestamp'},
        {'type': 'gauge', 'path': 'network.connected_to', 'modifier': 'total'},
        {'type': 'gauge', 'path': 'process.time_started', 'modifier': 'timestamp'},
    ],
)


# System jobs.

# See: https://rethinkdb.com/docs/system-jobs/
system_jobs = DocumentQuery(
    source=operations.get_system_jobs,
    name='system_jobs',
    prefix='jobs',
    metrics=[{'type': 'gauge', 'path': 'duration_sec'}],
)


# System current issues.

# See: https://rethinkdb.com/docs/system-issues/
current_issues_summary = DocumentQuery(
    source=operations.get_current_issues_summary,
    name='current_issues',
    prefix='current_issues',
    groups=[
        {'path': 'issues', 'key_tag': 'issue_type', 'value_metric_type': 'gauge'},
        {'path': 'critical_issues', 'key_tag': 'issue_type', 'value_metric_type': 'gauge'},
    ],
)
