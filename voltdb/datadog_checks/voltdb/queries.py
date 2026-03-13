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
        {'name': 'memory.tuple_data', 'type': 'gauge'},
        {'name': 'memory.tuple_allocated', 'type': 'gauge'},
        {'name': 'memory.index', 'type': 'gauge'},
        {'name': 'memory.string', 'type': 'gauge'},
        {'name': 'memory.tuple_count', 'type': 'gauge'},
        {'name': 'memory.pooled', 'type': 'gauge'},
        {'name': 'memory.physical', 'type': 'gauge'},
        {'name': 'memory.java.max_heap', 'type': 'gauge'},
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
    'query': '@Statistics:[COMMANDLOG, 1]',
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
    'query': '@Statistics:[PROCEDURE, 1]',
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
        None, # COMPOUND PROC
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

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatgc
# One row per server.
GCMetrics = {
    'name': 'gc',
    'query': '@Statistics:[GC, 1]',
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
    'query': '@Statistics:[IOSTATS, 1]',
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
    'query': '@Statistics:[TABLE, 1]',
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
        {'name': 'distributed_replication', 'type': 'tag', 'boolean': True},
        None,  # EXPORT
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatindex
# One row per index.
IndexMetrics = {
    'name': 'index',
    'query': '@Statistics:[INDEX, 1]',
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


# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatexport
# One row per export stream per partition.
ExportMetrics = {
    'name': 'export',
    'query': '@Statistics:[EXPORT, 1]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'partition_id', 'type': 'tag'},
        {'name': 'export_source', 'type': 'tag'},
        {'name': 'export_target', 'type': 'tag'},
        {'name': 'active', 'type': 'tag'},
        {'name': 'export.records_queued', 'type': 'monotonic_count'},
        {'name': 'export.records_pending', 'type': 'gauge'},
        {'name': '_source.last_queued_ms', 'type': 'source'},
        {'name': '_source.last_acked_ms', 'type': 'source'},
        {'name': 'export.latency.avg', 'type': 'gauge'},
        {'name': 'export.latency.max', 'type': 'gauge'},
        {'name': 'export.queue_gap', 'type': 'gauge'},
        {'name': 'export_status', 'type': 'tag'},
    ],
    'extras': [
        {
            'name': '_source.last_queued_s',
            'expression': '_source.last_queued_ms / 1000',
        },
        {
            'name': 'export.time_since_last_queued',
            'type': 'time_elapsed',
            'format': 'unix_time',
            'source': '_source.last_queued_s',
        },
        {
            'name': '_source.last_acked_s',
            'expression': '_source.last_acked_ms / 1000',
        },
        {
            'name': 'export.time_since_last_acked',
            'type': 'time_elapsed',
            'format': 'unix_time',
            'source': '_source.last_acked_s',
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatimport
# One row per import stream per server.
ImportMetrics = {
    'name': 'import',
    'query': '@Statistics:[IMPORT, 1]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'importer_name', 'type': 'tag'},
        {'name': 'procedure_name', 'type': 'tag'},
        {'name': 'import.successes', 'type': 'monotonic_gauge'},
        {'name': 'import.failures', 'type': 'monotonic_gauge'},
        {'name': 'import.outstanding_requests', 'type': 'gauge'},
        {'name': 'import.retries', 'type': 'monotonic_gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatqueue
# One row per partition and host listing the current state of the process queue.
QueueMetrics = {
    'name': 'queue',
    'query': '@Statistics:[QUEUE, 1]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'queue.current_depth', 'type': 'gauge'},
        # The next metric is the number of tasks that left the queue in the past 5 seconds.
        # We compute a rate by dividing this value by 5.
        {'name': '_source.poll_count', 'type': 'source'},
        {'name': 'queue.avg_wait', 'type': 'gauge'},
        {'name': 'queue.max_wait', 'type': 'gauge'},
    ],
    'extras': [{'name': 'queue.poll_count_per_sec', 'expression': '_source.poll_count / 5.0', 'submit_type': 'gauge'}],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatidletime
# One row per execution site and host.
IdleTimeMetrics = {
    'name': 'idletime',
    'query': '@Statistics:[IDLETIME, 1]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'host_id', 'type': 'tag'},
        {'name': 'voltdb_hostname', 'type': 'tag'},
        {'name': 'site_id', 'type': 'tag'},
        {'name': 'idletime.wait', 'type': 'monotonic_gauge'},
        {'name': 'idletime.wait.pct', 'type': 'gauge'},
        {'name': 'idletime.avg_wait', 'type': 'gauge'},
        {'name': 'idletime.min_wait', 'type': 'gauge'},
        {'name': 'idletime.max_wait', 'type': 'gauge'},
        {'name': 'idletime.stddev', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureoutput
# One row per procedure, summarized across the cluster.
ProcedureOutputMetrics = {
    'name': 'procedureoutput',
    'query': '@Statistics:[PROCEDUREOUTPUT]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'procedure', 'type': 'tag'},
        {'name': 'procedureoutput.weighted_perc', 'type': 'gauge'},
        {'name': 'procedureoutput.invocations', 'type': 'monotonic_gauge'},
        {'name': 'procedureoutput.min_result_size', 'type': 'gauge'},
        {'name': 'procedureoutput.max_result_size', 'type': 'gauge'},
        {'name': 'procedureoutput.avg_result_size', 'type': 'gauge'},
        {'name': 'procedureoutput.total_result_size', 'type': 'gauge'},
    ],
}


# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureprofile
# One row per procedure, summarized across the cluster.
ProcedureProfileMetrics = {
    'name': 'procedureprofile',
    'query': '@Statistics:[PROCEDUREPROFILE]',
    'columns': [
        None,  # TIMESTAMP
        {'name': 'procedure', 'type': 'tag'},
        {'name': 'procedureprofile.weighted_perc', 'type': 'gauge'},
        {'name': 'procedureprofile.invocations', 'type': 'monotonic_gauge'},
        {'name': 'procedureprofile.avg_time', 'type': 'gauge'},
        {'name': 'procedureprofile.min_time', 'type': 'gauge'},
        {'name': 'procedureprofile.max_time', 'type': 'gauge'},
        {'name': 'procedureprofile.aborts', 'type': 'monotonic_gauge'},
        {'name': 'procedureprofile.failures', 'type': 'monotonic_gauge'},
    ],
}
