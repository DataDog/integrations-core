# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# NOTE: these metrics don't map 1:1 with what RethinkDB exposes via system tables -- often times
# it's a combination of parts of multiple tables.

ClusterMetrics = {
    'name': 'cluster',
    'query': '.queries_impl:get_cluster_metrics',
    'columns': [
        # https://rethinkdb.com/docs/system-tables/#server_config
        {'name': 'config.servers', 'type': 'gauge'},
        # https://rethinkdb.com/docs/system-tables/#db_config
        {'name': 'config.databases', 'type': 'gauge'},
        # https://rethinkdb.com/docs/system-stats#cluster
        {'name': 'stats.cluster.query_engine.queries_per_sec', 'type': 'gauge'},
        {'name': 'stats.cluster.query_engine.read_docs_per_sec', 'type': 'gauge'},
        {'name': 'stats.cluster.query_engine.written_docs_per_sec', 'type': 'gauge'},
    ],
}

ServerMetrics = {
    'name': 'server',
    'query': '.queries_impl:get_server_metrics',
    'columns': [
        {'name': 'server', 'type': 'tag'},
        {'name': 'server_tag', 'type': 'tag_list'},
        # https://rethinkdb.com/docs/system-tables/#server_config
        {'name': 'stats.server.query_engine.client_connections', 'type': 'gauge'},
        {'name': 'stats.server.query_engine.clients_active', 'type': 'gauge'},
        {'name': 'stats.server.query_engine.queries_per_sec', 'type': 'gauge'},
        {'name': 'stats.server.query_engine.queries_total', 'type': 'monotonic_count'},
        {'name': 'stats.server.query_engine.read_docs_per_sec', 'type': 'gauge'},
        {'name': 'stats.server.query_engine.read_docs_total', 'type': 'monotonic_count'},
        {'name': 'stats.server.query_engine.written_docs_per_sec', 'type': 'gauge'},
        {'name': 'stats.server.query_engine.written_docs_total', 'type': 'monotonic_count'},
        # https://rethinkdb.com/docs/system-tables/#server_status
        {'name': 'server_status.network.time_connected', 'type': 'gauge'},
        {'name': 'server_status.network.connected_to', 'type': 'gauge'},
        {'name': 'server_status.process.time_started', 'type': 'gauge'},
    ],
}

DatabaseConfigMetrics = {
    'name': 'database',
    'query': '.queries_impl:get_database_config_metrics',
    'columns': [
        {'name': 'database', 'type': 'tag'},
        # Group on https://rethinkdb.com/docs/system-tables/#table_config
        {'name': 'config.tables_per_database', 'type': 'gauge'},
    ],
}

DatabaseTableMetrics = {
    'name': 'database_table',
    'query': '.queries_impl:get_database_table_metrics',
    'columns': [
        {'name': 'database', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        # https://rethinkdb.com/docs/system-stats/#table
        {'name': 'stats.table.query_engine.read_docs_per_sec', 'type': 'gauge'},
        {'name': 'stats.table.query_engine.written_docs_per_sec', 'type': 'gauge'},
        # https://rethinkdb.com/docs/system-tables/#table_status
        {'name': 'table_status.shards', 'type': 'gauge'},
        {
            'name': 'table_status.status.ready_for_outdated_reads',
            'type': 'service_check',
            'status_map': {True: 'OK', False: 'WARNING'},
        },
        {
            'name': 'table_status.status.ready_for_reads',
            'type': 'service_check',
            'status_map': {True: 'OK', False: 'WARNING'},
        },
        {
            'name': 'table_status.status.ready_for_writes',
            'type': 'service_check',
            'status_map': {True: 'OK', False: 'WARNING'},
        },
        {
            'name': 'table_status.status.all_replicas_ready',
            'type': 'service_check',
            'status_map': {True: 'OK', False: 'WARNING'},
        },
    ],
}

TableConfigMetrics = {
    'name': 'table',
    'query': '.queries_impl:get_table_config_metrics',
    'columns': [
        {'name': 'table', 'type': 'tag'},
        # Obtained from https://rethinkdb.com/docs/system-tables/#table_config
        {'name': 'config.secondary_indexes_per_table', 'type': 'gauge'},
    ],
}

ReplicaMetrics = {
    'name': 'replica',
    'query': '.queries_impl:get_replica_metrics',
    'columns': [
        {'name': 'table', 'type': 'tag'},
        {'name': 'database', 'type': 'tag'},
        {'name': 'server', 'type': 'tag'},
        {'name': 'server_tag', 'type': 'tag_list'},
        {'name': 'state', 'type': 'tag'},
        # https://rethinkdb.com/docs/system-stats/#replica-tableserver-pair
        {'name': 'stats.table_server.query_engine.read_docs_per_sec', 'type': 'gauge'},
        {'name': 'stats.table_server.query_engine.read_docs_total', 'type': 'monotonic_count'},
        {'name': 'stats.table_server.query_engine.written_docs_per_sec', 'type': 'gauge'},
        {'name': 'stats.table_server.query_engine.written_docs_total', 'type': 'monotonic_count'},
        {'name': 'stats.table_server.storage_engine.cache.in_use_bytes', 'type': 'gauge'},
        {'name': 'stats.table_server.storage_engine.disk.read_bytes_per_sec', 'type': 'gauge'},
        {'name': 'stats.table_server.storage_engine.disk.read_bytes_total', 'type': 'monotonic_count'},
        {'name': 'stats.table_server.storage_engine.disk.written_bytes_per_sec', 'type': 'gauge'},
        {'name': 'stats.table_server.storage_engine.disk.written_bytes_total', 'type': 'monotonic_count'},
        {'name': 'stats.table_server.storage_engine.disk.space_usage.metadata_bytes', 'type': 'gauge'},
        {'name': 'stats.table_server.storage_engine.disk.space_usage.data_bytes', 'type': 'gauge'},
        {'name': 'stats.table_server.storage_engine.disk.space_usage.garbage_bytes', 'type': 'gauge'},
        {'name': 'stats.table_server.storage_engine.disk.space_usage.preallocated_bytes', 'type': 'gauge'},
    ],
}

ShardMetrics = {
    'name': 'shard',
    'query': '.queries_impl:get_shard_metrics',
    'columns': [
        {'name': 'shard', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'database', 'type': 'tag'},
        # Combination of https://rethinkdb.com/docs/system-tables/#table_status
        # and https://rethinkdb.com/docs/system-tables/#table_config
        {'name': 'table_status.shards.replicas', 'type': 'gauge'},
        {'name': 'table_status.shards.primary_replicas', 'type': 'gauge'},
    ],
}

JobMetrics = {
    'name': 'job',
    'query': '.queries_impl:get_job_metrics',
    'columns': [
        {'name': 'job_type', 'type': 'tag'},
        # https://rethinkdb.com/docs/system-tables/#jobs
        {'name': 'system_jobs.jobs', 'type': 'gauge'},
    ],
}

CurrentIssuesMetrics = {
    'name': 'current_issues',
    'query': '.queries_impl:get_current_issues_metrics',
    'columns': [
        {'name': 'issue_type', 'type': 'tag'},
        # https://rethinkdb.com/docs/system-issues/
        {'name': 'current_issues.issues', 'type': 'gauge'},
        {'name': 'current_issues.critical_issues', 'type': 'gauge'},
    ],
}

VersionMetadata = {
    'name': 'version_metadata',
    'query': '.queries_impl:get_version_metadata',
    'columns': [
        {'name': 'version', 'type': 'metadata'},
    ],
}
