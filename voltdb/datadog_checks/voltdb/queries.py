# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
#
# Each column declares a `source` field — the VoltDB column name to read from the
# `@Statistics` response. The check looks up these names against the VoltTable
# column metadata at runtime, so the integration tolerates VoltDB versions that
# add or remove columns. Columns missing on the server are submitted as None
# (tags drop out, numeric metrics are skipped).
#
# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcpu
# One row per server.
CPUMetrics = {
    'name': 'cpu',
    'query': '@Statistics:[CPU]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'PERCENT_USED', 'name': 'cpu.percent_used', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatmemory
# One row per server.
MemoryMetrics = {
    'name': 'memory',
    'query': '@Statistics:[MEMORY]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'RSS', 'name': 'memory.rss', 'type': 'gauge'},
        {'source': 'JAVAUSED', 'name': 'memory.java.used', 'type': 'gauge'},
        {'source': 'JAVAUNUSED', 'name': 'memory.java.unused', 'type': 'gauge'},
        {'source': 'TUPLEDATA', 'name': 'memory.tuple_data', 'type': 'gauge'},
        {'source': 'TUPLEALLOCATED', 'name': 'memory.tuple_allocated', 'type': 'gauge'},
        {'source': 'INDEXMEMORY', 'name': 'memory.index', 'type': 'gauge'},
        {'source': 'STRINGMEMORY', 'name': 'memory.string', 'type': 'gauge'},
        {'source': 'TUPLECOUNT', 'name': 'memory.tuple_count', 'type': 'gauge'},
        {'source': 'POOLEDMEMORY', 'name': 'memory.pooled', 'type': 'gauge'},
        {'source': 'PHYSICALMEMORY', 'name': 'memory.physical', 'type': 'gauge'},
        {'source': 'JAVAMAXHEAP', 'name': 'memory.java.max_heap', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatsnapshotstatus
# One row per snapshot file in the recent snapshots performed on the cluster.
SnapshotStatusMetrics = {
    'name': 'snapshot_status',
    'query': '@Statistics:[SNAPSHOTSTATUS]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'TABLE', 'name': 'table', 'type': 'tag'},
        {'source': 'FILENAME', 'name': 'filename', 'type': 'tag'},
        {'source': 'SIZE', 'name': 'snapshot_status.size', 'type': 'gauge'},
        {'source': 'DURATION', 'name': 'snapshot_status.duration', 'type': 'gauge'},
        {'source': 'THROUGHPUT', 'name': 'snapshot_status.throughput', 'type': 'gauge'},
        {'source': 'TYPE', 'name': 'type', 'type': 'tag'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcommandlog
# One row per server.
# (Enterprise edition only.)
CommandLogMetrics = {
    'name': 'commandlog',
    'query': '@Statistics:[COMMANDLOG, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {
            'source': 'OUTSTANDING_BYTES',
            'name': 'commandlog.outstanding_bytes',
            'type': 'gauge',
        },
        {
            'source': 'OUTSTANDING_TXNS',
            'name': 'commandlog.outstanding_transactions',
            'type': 'gauge',
        },
        {
            'source': 'IN_USE_SEGMENT_COUNT',
            'name': 'commandlog.in_use_segment_count',
            'type': 'gauge',
        },
        {
            'source': 'SEGMENT_COUNT',
            'name': 'commandlog.segment_count',
            'type': 'gauge',
        },
        {
            'source': 'FSYNC_INTERVAL',
            'name': 'commandlog.fsync_interval',
            'type': 'gauge',
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedure
# One row per (non-system) stored procedure that has been executed on the cluster, by execution site.
ProcedureMetrics = {
    'name': 'procedure',
    'query': '@Statistics:[PROCEDURE, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'PARTITION_ID', 'name': 'partition_id', 'type': 'tag'},
        {'source': 'PROCEDURE', 'name': 'procedure', 'type': 'tag'},
        {
            'source': 'INVOCATIONS',
            'name': 'procedure.invocations',
            'type': 'monotonic_count',
        },
        {
            'source': 'TIMED_INVOCATIONS',
            'name': 'procedure.timed_invocations',
            'type': 'monotonic_count',
        },
        {
            'source': 'MIN_EXECUTION_TIME',
            'name': 'procedure.min_execution_time',
            'type': 'gauge',
        },
        {
            'source': 'MAX_EXECUTION_TIME',
            'name': 'procedure.max_execution_time',
            'type': 'gauge',
        },
        {
            'source': 'AVG_EXECUTION_TIME',
            'name': 'procedure.avg_execution_time',
            'type': 'gauge',
        },
        {
            'source': 'MIN_RESULT_SIZE',
            'name': 'procedure.min_result_size',
            'type': 'gauge',
        },
        {
            'source': 'MAX_RESULT_SIZE',
            'name': 'procedure.max_result_size',
            'type': 'gauge',
        },
        {
            'source': 'AVG_RESULT_SIZE',
            'name': 'procedure.avg_result_size',
            'type': 'gauge',
        },
        {
            'source': 'MIN_PARAMETER_SET_SIZE',
            'name': 'procedure.min_parameter_set_size',
            'type': 'gauge',
        },
        {
            'source': 'MAX_PARAMETER_SET_SIZE',
            'name': 'procedure.max_parameter_set_size',
            'type': 'gauge',
        },
        {
            'source': 'AVG_PARAMETER_SET_SIZE',
            'name': 'procedure.avg_parameter_set_size',
            'type': 'gauge',
        },
        {'source': 'ABORTS', 'name': 'procedure.aborts', 'type': 'monotonic_count'},
        {'source': 'FAILURES', 'name': 'procedure.failures', 'type': 'monotonic_count'},
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
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'INTERVAL', 'name': 'latency.interval', 'type': 'gauge'},
        {'source': 'COUNT', 'name': 'latency.count', 'type': 'gauge'},
        {'source': 'TPS', 'name': 'latency.transactions_per_sec', 'type': 'gauge'},
        {'source': 'P50', 'name': 'latency.p50', 'type': 'gauge'},
        {'source': 'P95', 'name': 'latency.p95', 'type': 'gauge'},
        {'source': 'P99', 'name': 'latency.p99', 'type': 'gauge'},
        # VoltDB names these percentile columns with dots (P99.9, P99.99, P99.999).
        {'source': 'P99.9', 'name': 'latency.p999', 'type': 'gauge'},
        {'source': 'P99.99', 'name': 'latency.p9999', 'type': 'gauge'},
        {'source': 'P99.999', 'name': 'latency.p99999', 'type': 'gauge'},
        {'source': 'MAX', 'name': 'latency.max', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatgc
# One row per server.
GCMetrics = {
    'name': 'gc',
    'query': '@Statistics:[GC, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {
            'source': 'NEWGEN_GC_COUNT',
            'name': 'gc.newgen_gc_count',
            'type': 'monotonic_count',
        },
        {
            'source': 'NEWGEN_AVG_GC_TIME',
            'name': 'gc.newgen_avg_gc_time',
            'type': 'gauge',
        },
        {
            'source': 'OLDGEN_GC_COUNT',
            'name': 'gc.oldgen_gc_count',
            'type': 'monotonic_count',
        },
        {
            'source': 'OLDGEN_AVG_GC_TIME',
            'name': 'gc.oldgen_avg_gc_time',
            'type': 'gauge',
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatiostats
# One row per client connection on the cluster.
IOStatsMetrics = {
    'name': 'iostats',
    'query': '@Statistics:[IOSTATS, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'CONNECTION_HOSTNAME', 'name': 'connection_hostname', 'type': 'tag'},
        {'source': 'BYTES_READ', 'name': 'io.bytes_read', 'type': 'monotonic_count'},
        {
            'source': 'MESSAGES_READ',
            'name': 'io.messages_read',
            'type': 'monotonic_count',
        },
        {
            'source': 'BYTES_WRITTEN',
            'name': 'io.bytes_written',
            'type': 'monotonic_count',
        },
        {
            'source': 'MESSAGES_WRITTEN',
            'name': 'io.messages_written',
            'type': 'monotonic_count',
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstattable
# One row per partition of each table (num_partitions = num_sites_per_node * num_nodes).
TableMetrics = {
    'name': 'table',
    'query': '@Statistics:[TABLE, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'PARTITION_ID', 'name': 'partition_id', 'type': 'tag'},
        {'source': 'TABLE_NAME', 'name': 'table', 'type': 'tag'},
        {'source': 'TABLE_TYPE', 'name': 'table_type', 'type': 'tag'},
        {'source': 'TUPLE_COUNT', 'name': 'table.tuple_count', 'type': 'gauge'},
        {
            'source': 'TUPLE_ALLOCATED_MEMORY',
            'name': 'table.tuple_allocated_memory',
            'type': 'gauge',
        },
        {
            'source': 'TUPLE_DATA_MEMORY',
            'name': 'table.tuple_data_memory',
            'type': 'gauge',
        },
        {
            'source': 'STRING_DATA_MEMORY',
            'name': 'table.string_data_memory',
            'type': 'gauge',
        },
        {
            'source': 'TUPLE_LIMIT',
            'name': 'table.tuple_limit',
            'type': 'gauge',
        },  # May be null.
        {'source': 'PERCENT_FULL', 'name': 'table.percent_full', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatindex
# One row per index.
IndexMetrics = {
    'name': 'index',
    'query': '@Statistics:[INDEX, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'PARTITION_ID', 'name': 'partition_id', 'type': 'tag'},
        {'source': 'INDEX_NAME', 'name': 'index', 'type': 'tag'},
        {'source': 'TABLE_NAME', 'name': 'table', 'type': 'tag'},
        {'source': 'INDEX_TYPE', 'name': 'index_type', 'type': 'tag'},
        {'source': 'IS_UNIQUE', 'name': 'is_unique', 'type': 'tag', 'boolean': True},
        {
            'source': 'IS_COUNTABLE',
            'name': 'is_countable',
            'type': 'tag',
            'boolean': True,
        },
        {'source': 'ENTRY_COUNT', 'name': 'index.entry_count', 'type': 'gauge'},
        {'source': 'MEMORY_ESTIMATE', 'name': 'index.memory_estimate', 'type': 'gauge'},
    ],
}


# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatexport
# One row per export stream per partition.
ExportMetrics = {
    'name': 'export',
    'query': '@Statistics:[EXPORT, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'PARTITION_ID', 'name': 'partition_id', 'type': 'tag'},
        {'source': 'SOURCE', 'name': 'export_source', 'type': 'tag'},
        {'source': 'TARGET', 'name': 'export_target', 'type': 'tag'},
        {'source': 'ACTIVE', 'name': 'active', 'type': 'tag'},
        {
            'source': 'TUPLE_COUNT',
            'name': 'export.records_queued',
            'type': 'monotonic_count',
        },
        {'source': 'TUPLE_PENDING', 'name': 'export.records_pending', 'type': 'gauge'},
        {
            'source': 'LAST_QUEUED_TIMESTAMP',
            'name': '_source.last_queued_ms',
            'type': 'source',
        },
        {
            'source': 'LAST_ACKED_TIMESTAMP',
            'name': '_source.last_acked_ms',
            'type': 'source',
        },
        {'source': 'AVERAGE_LATENCY', 'name': 'export.latency.avg', 'type': 'gauge'},
        {'source': 'MAX_LATENCY', 'name': 'export.latency.max', 'type': 'gauge'},
        {'source': 'QUEUE_GAP', 'name': 'export.queue_gap', 'type': 'gauge'},
        {'source': 'STATUS', 'name': 'export_status', 'type': 'tag'},
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
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'IMPORTER_NAME', 'name': 'importer_name', 'type': 'tag'},
        {'source': 'PROCEDURE_NAME', 'name': 'procedure_name', 'type': 'tag'},
        {'source': 'SUCCESSES', 'name': 'import.successes', 'type': 'monotonic_gauge'},
        {'source': 'FAILURES', 'name': 'import.failures', 'type': 'monotonic_gauge'},
        {
            'source': 'OUTSTANDING_REQUESTS',
            'name': 'import.outstanding_requests',
            'type': 'gauge',
        },
        {'source': 'RETRIES', 'name': 'import.retries', 'type': 'monotonic_gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatqueue
# One row per partition and host listing the current state of the process queue.
QueueMetrics = {
    'name': 'queue',
    'query': '@Statistics:[QUEUE, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'CURRENT_DEPTH', 'name': 'queue.current_depth', 'type': 'gauge'},
        # The next metric is the number of tasks that left the queue in the past 5 seconds.
        # We compute a rate by dividing this value by 5.
        {'source': 'POLL_COUNT', 'name': '_source.poll_count', 'type': 'source'},
        {'source': 'AVG_WAIT', 'name': 'queue.avg_wait', 'type': 'gauge'},
        {'source': 'MAX_WAIT', 'name': 'queue.max_wait', 'type': 'gauge'},
    ],
    'extras': [
        {
            'name': 'queue.poll_count_per_sec',
            'expression': '_source.poll_count / 5.0',
            'submit_type': 'gauge',
        }
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatidletime
# One row per execution site and host.
IdleTimeMetrics = {
    'name': 'idletime',
    'query': '@Statistics:[IDLETIME, 1]',
    'columns': [
        {'source': 'HOST_ID', 'name': 'host_id', 'type': 'tag'},
        {'source': 'HOSTNAME', 'name': 'voltdb_hostname', 'type': 'tag'},
        {'source': 'SITE_ID', 'name': 'site_id', 'type': 'tag'},
        {'source': 'COUNT', 'name': 'idletime.wait', 'type': 'monotonic_gauge'},
        {'source': 'PERCENT', 'name': 'idletime.wait.pct', 'type': 'gauge'},
        {'source': 'AVG', 'name': 'idletime.avg_wait', 'type': 'gauge'},
        {'source': 'MIN', 'name': 'idletime.min_wait', 'type': 'gauge'},
        {'source': 'MAX', 'name': 'idletime.max_wait', 'type': 'gauge'},
        {'source': 'STDDEV', 'name': 'idletime.stddev', 'type': 'gauge'},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureoutput
# One row per procedure, summarized across the cluster.
ProcedureOutputMetrics = {
    'name': 'procedureoutput',
    'query': '@Statistics:[PROCEDUREOUTPUT]',
    'columns': [
        {'source': 'PROCEDURE', 'name': 'procedure', 'type': 'tag'},
        {
            'source': 'WEIGHTED_PERC',
            'name': 'procedureoutput.weighted_perc',
            'type': 'gauge',
        },
        {
            'source': 'INVOCATIONS',
            'name': 'procedureoutput.invocations',
            'type': 'monotonic_gauge',
        },
        {
            'source': 'MIN_RESULT_SIZE',
            'name': 'procedureoutput.min_result_size',
            'type': 'gauge',
        },
        {
            'source': 'MAX_RESULT_SIZE',
            'name': 'procedureoutput.max_result_size',
            'type': 'gauge',
        },
        {
            'source': 'AVG_RESULT_SIZE',
            'name': 'procedureoutput.avg_result_size',
            'type': 'gauge',
        },
        {
            'source': 'TOTAL_RESULT_SIZE_MB',
            'name': 'procedureoutput.total_result_size',
            'type': 'gauge',
        },
    ],
}


# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureprofile
# One row per procedure, summarized across the cluster.
ProcedureProfileMetrics = {
    'name': 'procedureprofile',
    'query': '@Statistics:[PROCEDUREPROFILE]',
    'columns': [
        {'source': 'PROCEDURE', 'name': 'procedure', 'type': 'tag'},
        {
            'source': 'WEIGHTED_PERC',
            'name': 'procedureprofile.weighted_perc',
            'type': 'gauge',
        },
        {
            'source': 'INVOCATIONS',
            'name': 'procedureprofile.invocations',
            'type': 'monotonic_gauge',
        },
        {'source': 'AVG', 'name': 'procedureprofile.avg_time', 'type': 'gauge'},
        {'source': 'MIN', 'name': 'procedureprofile.min_time', 'type': 'gauge'},
        {'source': 'MAX', 'name': 'procedureprofile.max_time', 'type': 'gauge'},
        {
            'source': 'ABORTS',
            'name': 'procedureprofile.aborts',
            'type': 'monotonic_gauge',
        },
        {
            'source': 'FAILURES',
            'name': 'procedureprofile.failures',
            'type': 'monotonic_gauge',
        },
    ],
}
