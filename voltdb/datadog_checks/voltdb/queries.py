# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcpu
# One row per server.
CPUMetrics = {
    "name": "cpu",
    "query": "@Statistics:[CPU]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "cpu.percent_used", "type": "gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatmemory
# One row per server.
MemoryMetrics = {
    "name": "memory",
    "query": "@Statistics:[MEMORY]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "memory.rss", "type": "gauge"},
        {"name": "memory.java.used", "type": "gauge"},
        {"name": "memory.java.unused", "type": "gauge"},
        {"name": "memory.tuple_data", "type": "gauge"},
        {"name": "memory.tuple_allocated", "type": "gauge"},
        {"name": "memory.index", "type": "gauge"},
        {"name": "memory.string", "type": "gauge"},
        {"name": "memory.tuple_count", "type": "gauge"},
        {"name": "memory.pooled", "type": "gauge"},
        {"name": "memory.physical", "type": "gauge"},
        {"name": "memory.java.max_heap", "type": "gauge"},
        {"name": "memory.undo_pool_size", "type": "gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatsnapshotstatus
# One row per snapshot file in the recent snapshots performed on the cluster.
SnapshotStatusMetrics = {
    "name": "snapshot_status",
    "query": "@Statistics:[SNAPSHOTSTATUS]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "table", "type": "tag"},
        None,  # PATH
        {"name": "filename", "type": "tag"},
        None,  # NONCE
        None,  # TXNID (Transaction ID)
        None,  # START_TIME
        None,  # END_TIME
        {"name": "snapshot_status.size", "type": "gauge"},
        {"name": "snapshot_status.duration", "type": "gauge"},
        {"name": "snapshot_status.throughput", "type": "gauge"},
        None,  # RESULT (Can't translate string to int yet)
        {"name": "type", "type": "tag"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatcommandlog
# One row per server.
# (Enterprise edition only.)
CommandLogMetrics = {
    "name": "commandlog",
    "query": "@Statistics:[COMMANDLOG, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "commandlog.outstanding_bytes", "type": "gauge"},
        {"name": "commandlog.outstanding_transactions", "type": "gauge"},
        {"name": "commandlog.in_use_segment_count", "type": "gauge"},
        {"name": "commandlog.segment_count", "type": "gauge"},
        {"name": "commandlog.fsync_interval", "type": "gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedure
# One row per (non-system) stored procedure that has been executed on the cluster, by execution site.
ProcedureMetrics = {
    "name": "procedure",
    "query": "@Statistics:[PROCEDURE, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "partition_id", "type": "tag"},
        {"name": "procedure", "type": "tag"},
        {"name": "procedure.invocations", "type": "monotonic_count"},
        {"name": "procedure.timed_invocations", "type": "monotonic_count"},
        {"name": "procedure.min_execution_time", "type": "gauge"},
        {"name": "procedure.max_execution_time", "type": "gauge"},
        {"name": "procedure.avg_execution_time", "type": "gauge"},
        {"name": "procedure.min_result_size", "type": "gauge"},
        {"name": "procedure.max_result_size", "type": "gauge"},
        {"name": "procedure.avg_result_size", "type": "gauge"},
        {"name": "procedure.min_parameter_set_size", "type": "gauge"},
        {"name": "procedure.max_parameter_set_size", "type": "gauge"},
        {"name": "procedure.avg_parameter_set_size", "type": "gauge"},
        {"name": "procedure.aborts", "type": "monotonic_count"},
        {"name": "procedure.failures", "type": "monotonic_count"},
        None,  # TRANSACTIONAL
        None,  # COMPOUND PROC
    ],
    "extras": [
        {
            "name": "procedure.successes",
            "expression": "procedure.invocations - procedure.aborts - procedure.failures",
            "submit_type": "monotonic_count",
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatlatency
# One row per server.
LatencyMetrics = {
    "name": "latency",
    "query": "@Statistics:[LATENCY]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "latency.interval", "type": "gauge"},
        {"name": "latency.count", "type": "gauge"},
        {"name": "latency.transactions_per_sec", "type": "gauge"},
        {"name": "latency.p50", "type": "gauge"},
        {"name": "latency.p95", "type": "gauge"},
        {"name": "latency.p99", "type": "gauge"},
        {"name": "latency.p999", "type": "gauge"},
        {"name": "latency.p9999", "type": "gauge"},
        {"name": "latency.p99999", "type": "gauge"},
        {"name": "latency.max", "type": "gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatgc
# One row per server.
GCMetrics = {
    "name": "gc",
    "query": "@Statistics:[GC, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "gc.newgen_gc_count", "type": "monotonic_count"},
        {"name": "gc.newgen_avg_gc_time", "type": "gauge"},
        {"name": "gc.oldgen_gc_count", "type": "monotonic_count"},
        {"name": "gc.oldgen_avg_gc_time", "type": "gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatiostats
# One row per client connection on the cluster.
IOStatsMetrics = {
    "name": "iostats",
    "query": "@Statistics:[IOSTATS, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        None,  # CONNECTION_ID
        {"name": "connection_hostname", "type": "tag"},
        {"name": "io.bytes_read", "type": "monotonic_count"},
        {"name": "io.messages_read", "type": "monotonic_count"},
        {"name": "io.bytes_written", "type": "monotonic_count"},
        {"name": "io.messages_written", "type": "monotonic_count"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstattable
# One row per partition of each table (num_partitions = num_sites_per_node * num_nodes).
TableMetrics = {
    "name": "table",
    "query": "@Statistics:[TABLE, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "partition_id", "type": "tag"},
        {"name": "table", "type": "tag"},
        {"name": "table_type", "type": "tag"},
        {"name": "table.tuple_count", "type": "gauge"},
        {"name": "table.tuple_allocated_memory", "type": "gauge"},
        {"name": "table.tuple_data_memory", "type": "gauge"},
        {"name": "table.string_data_memory", "type": "gauge"},
        {"name": "table.tuple_limit", "type": "gauge"},  # May be null.
        {"name": "table.percent_full", "type": "gauge"},
        {"name": "distributed_replication", "type": "tag", "boolean": True},
        None,  # EXPORT
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatindex
# One row per index.
IndexMetrics = {
    "name": "index",
    "query": "@Statistics:[INDEX, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "partition_id", "type": "tag"},
        {"name": "index", "type": "tag"},
        {"name": "table", "type": "tag"},
        {"name": "index_type", "type": "tag"},
        {"name": "is_unique", "type": "tag", "boolean": True},
        {"name": "is_countable", "type": "tag", "boolean": True},
        {"name": "index.entry_count", "type": "gauge"},
        {"name": "index.memory_estimate", "type": "gauge"},
    ],
}


# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatexport
# One row per export stream per partition.
ExportMetrics = {
    "name": "export",
    "query": "@Statistics:[EXPORT, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "partition_id", "type": "tag"},
        {"name": "export_source", "type": "tag"},
        {"name": "export_target", "type": "tag"},
        {"name": "active", "type": "tag"},
        {"name": "export.records_queued", "type": "monotonic_count"},
        {"name": "export.records_pending", "type": "gauge"},
        {"name": "_source.last_queued_ms", "type": "source"},
        {"name": "_source.last_acked_ms", "type": "source"},
        {"name": "export.latency.avg", "type": "gauge"},
        {"name": "export.latency.max", "type": "gauge"},
        {"name": "export.queue_gap", "type": "gauge"},
        {"name": "export_status", "type": "tag"},
    ],
    "extras": [
        {
            "name": "_source.last_queued_s",
            "expression": "_source.last_queued_ms / 1000",
        },
        {
            "name": "export.time_since_last_queued",
            "type": "time_elapsed",
            "format": "unix_time",
            "source": "_source.last_queued_s",
        },
        {
            "name": "_source.last_acked_s",
            "expression": "_source.last_acked_ms / 1000",
        },
        {
            "name": "export.time_since_last_acked",
            "type": "time_elapsed",
            "format": "unix_time",
            "source": "_source.last_acked_s",
        },
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatimport
# One row per import stream per server.
ImportMetrics = {
    "name": "import",
    "query": "@Statistics:[IMPORT, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "importer_name", "type": "tag"},
        {"name": "procedure_name", "type": "tag"},
        {"name": "import.successes", "type": "monotonic_gauge"},
        {"name": "import.failures", "type": "monotonic_gauge"},
        {"name": "import.outstanding_requests", "type": "gauge"},
        {"name": "import.retries", "type": "monotonic_gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatqueue
# One row per partition and host listing the current state of the process queue.
QueueMetrics = {
    "name": "queue",
    "query": "@Statistics:[QUEUE, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "queue.current_depth", "type": "gauge"},
        # The next metric is the number of tasks that left the queue in the past 5 seconds.
        # We compute a rate by dividing this value by 5.
        {"name": "_source.poll_count", "type": "source"},
        {"name": "queue.avg_wait", "type": "gauge"},
        {"name": "queue.max_wait", "type": "gauge"},
    ],
    "extras": [
        {
            "name": "queue.poll_count_per_sec",
            "expression": "_source.poll_count / 5.0",
            "submit_type": "gauge",
        }
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatidletime
# One row per execution site and host.
IdleTimeMetrics = {
    "name": "idletime",
    "query": "@Statistics:[IDLETIME, 1]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "idletime.wait", "type": "monotonic_gauge"},
        {"name": "idletime.wait.pct", "type": "gauge"},
        {"name": "idletime.avg_wait", "type": "gauge"},
        {"name": "idletime.min_wait", "type": "gauge"},
        {"name": "idletime.max_wait", "type": "gauge"},
        {"name": "idletime.stddev", "type": "gauge"},
    ],
}

# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureoutput
# One row per procedure, summarized across the cluster.
ProcedureOutputMetrics = {
    "name": "procedureoutput",
    "query": "@Statistics:[PROCEDUREOUTPUT]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "procedure", "type": "tag"},
        {"name": "procedureoutput.weighted_perc", "type": "gauge"},
        {"name": "procedureoutput.invocations", "type": "monotonic_gauge"},
        {"name": "procedureoutput.min_result_size", "type": "gauge"},
        {"name": "procedureoutput.max_result_size", "type": "gauge"},
        {"name": "procedureoutput.avg_result_size", "type": "gauge"},
        {"name": "procedureoutput.total_result_size", "type": "gauge"},
    ],
}


# See: https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureprofile
# One row per procedure, summarized across the cluster.
ProcedureProfileMetrics = {
    "name": "procedureprofile",
    "query": "@Statistics:[PROCEDUREPROFILE]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "procedure", "type": "tag"},
        {"name": "procedureprofile.weighted_perc", "type": "gauge"},
        {"name": "procedureprofile.invocations", "type": "monotonic_gauge"},
        {"name": "procedureprofile.avg_time", "type": "gauge"},
        {"name": "procedureprofile.min_time", "type": "gauge"},
        {"name": "procedureprofile.max_time", "type": "gauge"},
        {"name": "procedureprofile.aborts", "type": "monotonic_gauge"},
        {"name": "procedureprofile.failures", "type": "monotonic_gauge"},
    ],
}
# https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatliveclients
# One row per procedure, summarized across the cluster.
LiveClientsMetrics = {
    "name": "liveclients",
    "query": "@Statistics:[LIVECLIENTS]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "liveclients.connection_id", "type": "gauge"},
        {"name": "liveclients.client_hostname", "type": "tag"},
        {"name": "liveclients.admin", "type": "gauge"},
        {"name": "liveclients.outstanding_request_bytes", "type": "monotonic_gauge"},
        {"name": "liveclients.outstanding_response_messages", "type": "gauge"},
        {"name": "liveclients.outstanding_transactions", "type": "monotonic_gauge"},
    ],
}

# https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatpartitioncount
# One row per procedure, summarized across the cluster.

InitiatorMetrics = {
    "name": "initiator",
    "query": "@Statistics:[INITIATOR]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "initiator.site_id", "type": "tag"},
        None,  # CONNECTION_ID
        {"name": "connection_hostname", "type": "tag"},
        {"name": "procedure_name", "type": "tag"},
        {"name": "initiator.invocations", "type": "monotonic_gauge"},
        {"name": "initiator.avg_execution_time", "type": "gauge"},
        {"name": "initiator.min_execution_time", "type": "gauge"},
        {"name": "initiator.max_execution_time", "type": "gauge"},
        {"name": "initiator.aborts", "type": "monotonic_count"},
        {"name": "initiator.failures", "type": "monotonic_count"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatpartitioncount
# One row per procedure, summarized across the cluster.

PartitionCountMetrics = {
    "name": "partitioncount",
    "query": "@Statistics:[PARTITIONCOUNT]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "partitioncount.partition_count", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatttl
# One row per procedure, summarized across the cluster.

TtlMetrics = {
    "name": "ttl",
    "query": "@Statistics:[TTL]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "ttl.table_name", "type": "tag"},
        {"name": "ttl.rows_deleted", "type": "tag"},
        {"name": "ttl.rows_deleted_last_round", "type": "gauge"},
        {"name": "ttl.rows_remaining", "type": "gauge"},
        {"name": "ttl.last_delete_timestamp", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatcompoundproc
# One row per procedure, summarized across the cluster.

CompoundProcCallsMetrics = {
    "name": "compoundproccalls",
    "query": "@Statistics:[COMPOUNDPROCCALLS]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "compoundproccalls.procedure", "type": "gauge"},
        {"name": "compoundproccalls.called_procedure", "type": "gauge"},
        {"name": "compoundproccalls.invocations", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatcompoundproccalls
# One row per procedure, summarized across the cluster.

CompoundProcSummaryMetrics = {
    "name": "compoundprocsummary",
    "query": "@Statistics:[COMPOUNDPROCSUMMARY]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "compoundprocsummary.procedure", "type": "gauge"},
        {"name": "compoundprocsummary.invocations", "type": "gauge"},
        {"name": "compoundprocsummary.min_elapsed_time", "type": "gauge"},
        {"name": "compoundprocsummary.max_elapsed_time", "type": "gauge"},
        {"name": "compoundprocsummary.avg_elapsed_time", "type": "gauge"},
        {"name": "compoundprocsummary.aborts", "type": "monotonic_count"},
        {"name": "compoundprocsummary.failure", "type": "monotonic_count"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatproceduredetail
# One row per procedure, summarized across the cluster.

ProcedureDetailMetrics = {
    "name": "proceduredetail",
    "query": "@Statistics:[PROCEDUREDETAIL]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "proceduredetail.site_id", "type": "tag"},
        {"name": "proceduredetail.partition_id", "type": "gauge"},
        {"name": "procedure", "type": "tag"},
        {"name": "proceduredetail.statement", "type": "source"},
        {"name": "proceduredetail.invocations", "type": "gauge"},
        {"name": "proceduredetail.timed_invocations", "type": "gauge"},
        {"name": "proceduredetail.min_execution_time", "type": "gauge"},
        {"name": "proceduredetail.max_execution_time", "type": "gauge"},
        {"name": "proceduredetail.avg_execution_time", "type": "gauge"},
        {"name": "proceduredetail.min_result_size", "type": "gauge"},
        {"name": "proceduredetail.max_result_size", "type": "gauge"},
        {"name": "proceduredetail.avg_result_size", "type": "gauge"},
        {"name": "proceduredetail.min_parameter_set_size", "type": "gauge"},
        {"name": "proceduredetail.max_parameter_set_size", "type": "gauge"},
        {"name": "proceduredetail.avg_parameter_set_size", "type": "gauge"},
        {"name": "proceduredetail.aborts", "type": "monotonic_count"},
        {"name": "proceduredetail.failures", "type": "monotonic_count"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatprocedureinput
# One row per procedure, summarized across the cluster.

ProcedureInputMetrics = {
    "name": "procedureinput",
    "query": "@Statistics:[PROCEDUREINPUT]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "procedure", "type": "tag"},
        {"name": "procedureinput.weighted_perc", "type": "gauge"},
        {"name": "procedureinput.invocations", "type": "gauge"},
        {"name": "procedureinput.min_parameter_set_size", "type": "gauge"},
        {"name": "procedureinput.max_parameter_set_size", "type": "gauge"},
        {"name": "procedureinput.avg_parameter_set_size", "type": "gauge"},
        {"name": "procedureinput.total_parameter_set_size_mb", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstattask
# One row per procedure, summarized across the cluster.

TaskMetrics = {
    "name": "task",
    "query": "@Statistics:[TASK]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "task.partition_id", "type": "tag"},
        {"name": "task.task_name", "type": "tag"},
        {"name": "task.state", "type": "tag"},
        {"name": "task.scope", "type": "tag"},
        {"name": "task.scheduler_invocations", "type": "gauge"},
        {"name": "task.scheduler_total_execution", "type": "gauge"},
        {"name": "task.scheduler_min_execution", "type": "gauge"},
        {"name": "task.scheduler_max_execution", "type": "gauge"},
        {"name": "task.scheduler_avg_execution", "type": "gauge"},
        {"name": "task.scheduler_total_wait_time", "type": "gauge"},
        {"name": "task.scheduler_min_wait_time", "type": "gauge"},
        {"name": "task.scheduler_max_wait_time", "type": "gauge"},
        {"name": "task.scheduler_avg_wait_time", "type": "gauge"},
        {"name": "task.scheduler_status", "type": "gauge"},
        {"name": "task.procedure_invocations", "type": "gauge"},
        {"name": "task.procedure_total_execution", "type": "gauge"},
        {"name": "task.procedure_min_execution", "type": "gauge"},
        {"name": "task.procedure_max_execution", "type": "gauge"},
        {"name": "task.procedure_avg_execution", "type": "gauge"},
        {"name": "task.procedure_total_wait_time", "type": "gauge"},
        {"name": "task.procedure_min_wait_time", "type": "gauge"},
        {"name": "task.procedure_max_wait_time", "type": "gauge"},
        {"name": "task.procedure_avg_wait_time", "type": "gauge"},
        {"name": "task.procedure_failures", "type": "monotonic_count"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstattopic
# One row per procedure, summarized across the cluster.

TopicMetrics = {
    "name": "topic",
    "query": "@Statistics:[TOPIC]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "topic.site_id", "type": "gauge"},
        {"name": "topic.topic", "type": "gauge"},
        {"name": "topic.partition_id", "type": "gauge"},
        {"name": "topic.first_offset", "type": "gauge"},
        {"name": "topic.last_offset", "type": "gauge"},
        {"name": "topic.first_offset_timestamp", "type": "gauge"},
        {"name": "topic.last_offset_timestamp", "type": "gauge"},
        {"name": "topic.bytes_on_disk", "type": "gauge"},
        {"name": "topic.bytes_fetched", "type": "gauge"},
        {"name": "topic.state", "type": "gauge"},
        {"name": "topic.master", "type": "gauge"},
        {"name": "topic.retention_policy", "type": "gauge"},
        {"name": "topic.rows_skipped", "type": "gauge"},
        {"name": "topic.error_offset", "type": "gauge"},
        {"name": "topic.error_message", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatrebalance
# One row per procedure, summarized across the cluster.

RebalanceMetrics = {
    "name": "rebalance",
    "query": "@Statistics:[REBALANCE]",
    "columns": [
        {"name": "rebalance.total_ranges", "type": "gauge"},
        {"name": "rebalance.percentage_moved", "type": "monotonic_gauge"},
        {"name": "relabance.moved_rows", "type": "gauge"},
        {"name": "rebalance.rows_per_second", "type": "monotonic_gauge"},
        {"name": "rebalance.estimated_remaining", "type": "gauge"},
        {"name": "rebalance.megabytes_per_second", "type": "gauge"},
        {"name": "rebalance.call_per_second", "type": "gauge"},
        {"name": "rebalance.call_latency", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatplanner
# One row per procedure, summarized across the cluster.
PlannerMetrics = {
    "name": "planner",
    "query": "@Statistics:[PLANNER]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "planner.site_id", "type": "tag"},
        {"name": "planner.partition_id", "type": "tag"},
        {"name": "planner.cache1_level", "type": "gauge"},
        {"name": "planner.cache2_level", "type": "gauge"},
        {"name": "planner.cache1_hits", "type": "monotonic_gauge"},
        {"name": "planner.cache2_hits", "type": "monotonic_gauge"},
        {"name": "planner.cache_misses", "type": "monotonic_gauge"},
        {"name": "planner.plan_time_min", "type": "gauge"},
        {"name": "planner.plan_time_max", "type": "gauge"},
        {"name": "planner.plan_time_avg", "type": "gauge"},
        {"name": "planner.failures", "type": "monotonic_count"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatclockskew
# One row per procedure, summarized across the cluster.

ClockSkewMetrics = {
    "name": "clockskew",
    "query": "@Statistics:[CLOCKSKEW]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "clockskew.skew_time", "type": "gauge"},
        {"name": "clockskew.remote_host_id", "type": "gauge"},
        {"name": "clockskew.remote_hostname", "type": "tag"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatlimits
# One row per procedure, summarized across the cluster.

LimitsMetrics = {
    "name": "limits",
    "query": "@Statistics:[LIMITS]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "limits.file_descriptors_limit", "type": "gauge"},
        {"name": "limits.file_descriptors_open", "type": "monotonic_gauge"},
        {"name": "limits.client_connections_limit", "type": "gauge"},
        {"name": "limits.client_connections_open", "type": "monotonic_gauge"},
        {"name": "limits.accepted_connections", "type": "gauge"},
        {"name": "limits.dropped_connections", "type": "gauge"},
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatsnapshotstatus
# One row per procedure, summarized across the cluster.

SnapshotsSummaryMetrics = {
    "name": "snapshotsummary",
    "query": "@Statistics:[SNAPSHOTSUMMARY]",
    "columns": [
        {"name": "snapshotsummary.nonce", "type": "gauge"},
        {"name": "snapshotsummary.txnid", "type": "gauge"},
        None,  # TYPE
        {"name": "snapshotsummary.path", "type": "source"},
        {"name": "snapshotsummary.start_time", "type": "gauge"},
        {"name": "snapshotsummary.end_time", "type": "gauge"},
        {"name": "snapshotsummary.duration", "type": "gauge"},
        {"name": "snapshotsummary.progress_pct", "type": "gauge"},
        None,  # RESULT
    ],
}

# https://docs.voltdb.com/v11docs/UsingVoltDB/sysprocstatistics.php#sysprocstatcompoundproc
# One row per procedure, summarized across the cluster.

CompoundProcMetrics = {
    "name": "compoundproc",
    "query": "@Statistics:[COMPOUNDPROC]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "procedure", "type": "tag"},
        {"name": "compoundproc.invocations", "type": "monotonic_gauge"},
        {"name": "compoundproc.min_elapsed_time", "type": "gauge"},
        {"name": "compoundproc.max_elapsed_time", "type": "gauge"},
        {"name": "compoundproc.avg_elapsed_time", "type": "gauge"},
        {"name": "compoundproc.aborts", "type": "monotonic_count"},
        {"name": "compoundproc.failures", "type": "monotonic_count"},
    ],
}
# https://docs.voltdb.com/UsingVoltDB/sysprocstatistics.php#sysprocstatqueueprio
# One row per procedure, summarized across the cluster.
QueuePriorityMetrics = {
    "name": "queuepriority",
    "query": "@Statistics:[QUEUEPRIORITY]",
    "columns": [
        None,  # TIMESTAMP
        {"name": "host_id", "type": "tag"},
        {"name": "voltdb_hostname", "type": "tag"},
        {"name": "site_id", "type": "tag"},
        {"name": "queuepriority.priority", "type": "gauge"},
        {"name": "queuepriority.current_depth", "type": "gauge"},
        {"name": "queuepriority.poll_count", "type": "gauge"},
        {"name": "queuepriority.avg_wait", "type": "gauge"},
        {"name": "queuepriority.max_wait", "type": "gauge"},
    ],
}
