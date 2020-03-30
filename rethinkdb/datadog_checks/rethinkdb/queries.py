# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from . import operations
from .document_db import DocumentQuery, transformers

# System configuration.

# See: https://rethinkdb.com/docs/system-tables/#configuration-tables
config_summary = DocumentQuery(
    source=operations.get_config_summary,
    name='config_summary',
    prefix='rethinkdb.config',
    metrics=[{'type': 'gauge', 'path': 'servers'}, {'type': 'gauge', 'path': 'databases'}],
    groups=[
        {'type': 'gauge', 'path': 'tables_per_database', 'key_tag': 'database'},
        {'type': 'gauge', 'path': 'secondary_indexes_per_table', 'key_tag': 'table'},
    ],
)


# System statistics.

# See: https://rethinkdb.com/docs/system-stats#cluster
cluster_statistics = DocumentQuery(
    source=operations.get_cluster_statistics,
    name='cluster_statistics',
    prefix='rethinkdb.stats.cluster',
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
    prefix='rethinkdb.stats.server',
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
    prefix='rethinkdb.stats.table',
    metrics=[
        {'type': 'gauge', 'path': 'query_engine.read_docs_per_sec'},
        {'type': 'gauge', 'path': 'query_engine.written_docs_per_sec'},
    ],
)

# See: https://rethinkdb.com/docs/system-stats#replica
replica_statistics = DocumentQuery(
    source=operations.get_replicas_statistics,
    name='replica_statistics',
    prefix='rethinkdb.stats.table_server',
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
    prefix='rethinkdb.table_status',
    metrics=[
        {'type': 'service_check', 'path': 'status.ready_for_outdated_reads', 'transformer': transformers.ok_warning},
        {'type': 'service_check', 'path': 'status.ready_for_reads', 'transformer': transformers.ok_warning},
        {'type': 'service_check', 'path': 'status.ready_for_writes', 'transformer': transformers.ok_warning},
        {'type': 'service_check', 'path': 'status.all_replicas_ready', 'transformer': transformers.ok_warning},
        {'type': 'gauge', 'path': 'shards', 'transformer': transformers.length},
    ],
    enumerations=[
        {
            'path': 'shards',
            'index_tag': 'shard',
            'metrics': [
                {'type': 'gauge', 'path': 'replicas', 'transformer': transformers.length},
                {'type': 'gauge', 'path': 'primary_replicas', 'transformer': transformers.length},
            ],
        }
    ],
)

# See: https://rethinkdb.com/docs/system-tables/#server_status
server_statuses = DocumentQuery(
    source=operations.get_server_statuses,
    name='server_status',
    prefix='rethinkdb.server_status',
    metrics=[
        {'type': 'gauge', 'path': 'network.time_connected', 'transformer': transformers.to_time_elapsed},
        {'type': 'gauge', 'path': 'network.connected_to', 'transformer': transformers.length},
        {'type': 'gauge', 'path': 'process.time_started', 'transformer': transformers.to_time_elapsed},
    ],
)


# System jobs.

# See: https://rethinkdb.com/docs/system-jobs/
jobs_summary = DocumentQuery(
    source=operations.get_jobs_summary,
    name='jobs',
    prefix='rethinkdb.system_jobs',
    groups=[{'type': 'gauge', 'path': 'jobs', 'key_tag': 'job_type'}],
)


# System current issues.

# See: https://rethinkdb.com/docs/system-issues/
current_issues_summary = DocumentQuery(
    source=operations.get_current_issues_summary,
    name='current_issues',
    prefix='rethinkdb.current_issues',
    groups=[
        {'type': 'gauge', 'path': 'issues', 'key_tag': 'issue_type'},
        {'type': 'gauge', 'path': 'critical_issues', 'key_tag': 'issue_type'},
    ],
)
