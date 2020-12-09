# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcpu
# One row per server.
CPUMetrics = {
    'name': 'cpu',
    'query': '@Statistics:[CPU]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'cpu.percent_used', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatmemory
# One row per server.
MemoryMetrics = {
    'name': 'memory',
    'query': '@Statistics:[MEMORY]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'memory.rss', 'type': 'gauge'},
        {'name': 'memory.java.used', 'type': 'gauge'},
        {'name': 'memory.java.unused', 'type': 'gauge'},
        {'name': 'memory.java.max_heap', 'type': 'gauge'},
        {'name': 'memory.tuple_data', 'type': 'gauge'},
        {'name': 'memory.tuple_allocated', 'type': 'gauge'},
        {'name': 'memory.tuple_count', 'type': 'gauge'},
        {'name': 'memory.index', 'type': 'gauge'},
        {'name': 'memory.string', 'type': 'gauge'},
        {'name': 'memory.pooled', 'type': 'gauge'},
        {'name': 'memory.physical', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatsnapshotstatus
# One row per snapshot file in the recent snapshots performed on the cluster.
SnapshotStatusMetrics = {
    'name': 'snapshot_status',
    'query': '@Statistics:[SNAPSHOTSTATUS]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        None,  # PATH
        {'name': 'filename', 'type': 'tag'},
        None,  # NONCE
        None,  # TXNID (Transaction ID)
        None,  # START_TIME
        None,  # END_TIME
        {'name': 'snapshot_status.size', 'type': 'gauge'},
        {'name': 'snapshot_status.duration', 'type': 'gauge'},
        {'name': 'snapshot_status.throughput', 'type': 'gauge'},
        None,  # RESULT (Can't translate string to int yet)
        {'name': 'type', 'type': 'tag'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcommandlog
# One row per server.
# (Enterprise edition only.)
CommandLogMetrics = {
    'name': 'commandlog',
    'query': '@Statistics:[COMMANDLOG]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'commandlog.outstanding_bytes', 'type': 'gauge'},
        {'name': 'commandlog.outstanding_transactions', 'type': 'gauge'},
        {'name': 'commandlog.in_use_segment_count', 'type': 'gauge'},
        {'name': 'commandlog.segment_count', 'type': 'gauge'},
        {'name': 'commandlog.fsync_interval', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedure
# One row per (non-system) stored procedure that has been executed on the cluster, by execution site.
ProcedureMetrics = {
    'name': 'procedure',
    'query': '@Statistics:[PROCEDURE]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'partition_id', 'type': 'tag'},
        {'name': 'procedure', 'type': 'tag'},
        {'name': 'procedure.invocations', 'type': 'monotonic_count'},
        {'name': 'procedure.timed_invocations', 'type': 'monotonic_count'},
        {'name': 'procedure.min_execution_time', 'type': 'gauge'},
        {'name': 'procedure.max_execution_time', 'type': 'gauge'},
        {'name': 'procedure.avg_execution_time', 'type': 'gauge'},
        {'name': 'procedure.min_result_size', 'type': 'gauge'},
        {'name': 'procedure.max_result_size', 'type': 'gauge'},
        {'name': 'procedure.avg_result_size', 'type': 'gauge'},
        {'name': 'procedure.min_parameter_set_size', 'type': 'gauge'},
        {'name': 'procedure.max_parameter_set_size', 'type': 'gauge'},
        {'name': 'procedure.avg_parameter_set_size', 'type': 'gauge'},
        {'name': 'procedure.aborts', 'type': 'monotonic_count'},
        {'name': 'procedure.failures', 'type': 'monotonic_count'},
        None,  # TRANSACTIONAL
    ],
    'extras': [
        {
            'name': 'procedure.successes',
            'expression': 'procedure.invocations - procedure.aborts - procedure.failures',
            'submit_type': 'monotonic_count',
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatlatency
# One row per server.
LatencyMetrics = {
    'name': 'latency',
    'query': '@Statistics:[LATENCY]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'latency.interval', 'type': 'gauge'},
        {'name': 'latency.count', 'type': 'gauge'},
        {'name': 'latency.transactions_per_sec', 'type': 'gauge'},
        {'name': 'latency.p50', 'type': 'gauge'},
        {'name': 'latency.p95', 'type': 'gauge'},
        {'name': 'latency.p99', 'type': 'gauge'},
        {'name': 'latency.p999', 'type': 'gauge'},
        {'name': 'latency.p9999', 'type': 'gauge'},
        {'name': 'latency.p99999', 'type': 'gauge'},
        {'name': 'latency.max', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatproceduredetail
# One row per statement for each (non-system) procedure that has been executed on the cluster, by execution site.
StatementMetrics = {
    'name': 'statement',
    'query': '@Statistics:[PROCEDUREDETAIL]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'partition_id', 'type': 'tag'},
        {'name': 'procedure', 'type': 'tag'},
        {'name': 'statement', 'type': 'tag'},
        {'name': 'statement.invocations', 'type': 'monotonic_count'},
        {'name': 'statement.timed_invocations', 'type': 'monotonic_count'},
        {'name': 'statement.min_execution_time', 'type': 'gauge'},
        {'name': 'statement.max_execution_time', 'type': 'gauge'},
        {'name': 'statement.avg_execution_time', 'type': 'gauge'},
        {'name': 'statement.min_result_size', 'type': 'gauge'},
        {'name': 'statement.max_result_size', 'type': 'gauge'},
        {'name': 'statement.avg_result_size', 'type': 'gauge'},
        {'name': 'statement.min_parameter_set_size', 'type': 'gauge'},
        {'name': 'statement.max_parameter_set_size', 'type': 'gauge'},
        {'name': 'statement.avg_parameter_set_size', 'type': 'gauge'},
        {'name': 'statement.aborts', 'type': 'monotonic_count'},
        {'name': 'statement.failures', 'type': 'monotonic_count'},
    ],
    'extras': [
        {
            'name': 'statement.successes',
            'expression': 'statement.invocations - statement.aborts - statement.failures',
            'submit_type': 'monotonic_count',
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatgc
# One row per server.
GCMetrics = {
    'name': 'gc',
    'query': '@Statistics:[GC]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'gc.newgen_gc_count', 'type': 'monotonic_count'},
        {'name': 'gc.newgen_avg_gc_time', 'type': 'gauge'},
        {'name': 'gc.oldgen_gc_count', 'type': 'monotonic_count'},
        {'name': 'gc.oldgen_avg_gc_time', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatiostats
# One row per client connection on the cluster.
IOStatsMetrics = {
    'name': 'iostats',
    'query': '@Statistics:[IOSTATS]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        None,  # CONNECTION_ID
        {'name': 'connection_hostname', 'type': 'tag'},
        {'name': 'io.bytes_read', 'type': 'monotonic_count'},
        {'name': 'io.messages_read', 'type': 'monotonic_count'},
        {'name': 'io.bytes_written', 'type': 'monotonic_count'},
        {'name': 'io.messages_written', 'type': 'monotonic_count'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstattable
# One row per partition of each table (num_partitions = num_sites_per_node * num_nodes).
TableMetrics = {
    'name': 'table',
    'query': '@Statistics:[TABLE]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'partition_id', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'table_type', 'type': 'tag'},
        {'name': 'table.tuple_count', 'type': 'gauge'},
        {'name': 'table.tuple_allocated_memory', 'type': 'gauge'},
        {'name': 'table.tuple_data_memory', 'type': 'gauge'},
        {'name': 'table.string_data_memory', 'type': 'gauge'},
        {'name': 'table.tuple_limit', 'type': 'gauge'},  # May be null.
        {'name': 'table.percent_full', 'type': 'gauge'},
        # The following two columns were added in V10 only. Leave them out for now, as we target v8.4.
        # See: https://docs.voltdb.com/ReleaseNotes/index.php
        # {'name': 'distributed_replication', 'type': 'tag', 'boolean': True},
        # None,  # EXPORT
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatindex
# One row per index.
IndexMetrics = {
    'name': 'index',
    'query': '@Statistics:[INDEX]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'partition_id', 'type': 'tag'},
        {'name': 'index', 'type': 'tag'},
        {'name': 'table', 'type': 'tag'},
        {'name': 'index_type', 'type': 'tag'},
        {'name': 'is_unique', 'type': 'tag', 'boolean': True},
        {'name': 'is_countable', 'type': 'tag', 'boolean': True},
        {'name': 'index.entry_count', 'type': 'gauge'},
        {'name': 'index.memory_estimate', 'type': 'gauge'},
    ],
}
