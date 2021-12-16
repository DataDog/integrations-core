# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Constant for SQLServer cntr_type
PERF_LARGE_RAW_BASE = 1073939712
PERF_RAW_LARGE_FRACTION = 537003264
PERF_AVERAGE_BULK = 1073874176
PERF_COUNTER_BULK_COUNT = 272696576
PERF_COUNTER_LARGE_RAWCOUNT = 65792

# Metric discovery queries
COUNTER_TYPE_QUERY = """select distinct cntr_type
                        from sys.dm_os_performance_counters
                        where counter_name = ?;"""

BASE_NAME_QUERY = (
    """select distinct counter_name
       from sys.dm_os_performance_counters
       where (counter_name=? or counter_name=?
       or counter_name=?) and cntr_type=%s;"""
    % PERF_LARGE_RAW_BASE
)

DEFAULT_AUTODISCOVERY_INTERVAL = 3600
AUTODISCOVERY_QUERY = "select name from sys.databases"

VALID_METRIC_TYPES = ('gauge', 'rate', 'histogram')

SERVICE_CHECK_NAME = 'sqlserver.can_connect'
DATABASE_SERVICE_CHECK_NAME = 'sqlserver.database.can_connect'

DBM_MIGRATED_METRICS = [
    ('sqlserver.stats.connections', 'User Connections', ''),  # LARGE_RAWCOUNT
]

# Default performance table metrics - Database Instance level
# datadog metric name, counter name, instance name
INSTANCE_METRICS = [
    # SQLServer:General Statistics
    ('sqlserver.stats.procs_blocked', 'Processes blocked', ''),  # LARGE_RAWCOUNT
    # SQLServer:Access Methods
    ('sqlserver.access.page_splits', 'Page Splits/sec', ''),  # BULK_COUNT
    # SQLServer:Memory Manager
    ('sqlserver.memory.memory_grants_pending', 'Memory Grants Pending', ''),
    ('sqlserver.memory.total_server_memory', 'Total Server Memory (KB)', ''),
    # SQLServer:Buffer Manager
    ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio', ''),  # RAW_LARGE_FRACTION
    ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy', ''),  # LARGE_RAWCOUNT
    ('sqlserver.buffer.page_reads', 'Page reads/sec', ''),  # LARGE_RAWCOUNT
    ('sqlserver.buffer.page_writes', 'Page writes/sec', ''),  # LARGE_RAWCOUNT
    ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec', ''),  # BULK_COUNT
    # SQLServer:SQL Statistics
    ('sqlserver.stats.auto_param_attempts', 'Auto-Param Attempts/sec', ''),
    ('sqlserver.stats.failed_auto_param_attempts', 'Failed Auto-Params/sec', ''),
    ('sqlserver.stats.safe_auto_param_attempts', 'Safe Auto-Params/sec', ''),
    ('sqlserver.stats.batch_requests', 'Batch Requests/sec', ''),  # BULK_COUNT
    ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec', ''),  # BULK_COUNT
    ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec', ''),  # BULK_COUNT
]

# Performance table metrics, initially configured to track at instance-level only
# With auto-discovery enabled, these metrics will be extended accordingly
# datadog metric name, counter name, instance name
INSTANCE_METRICS_TOTAL = [
    # SQLServer:Locks
    ('sqlserver.stats.lock_waits', 'Lock Waits/sec', '_Total'),  # BULK_COUNT
    # SQLServer:Plan Cache
    ('sqlserver.cache.object_counts', 'Cache Object Counts', '_Total'),
    ('sqlserver.cache.pages', 'Cache Pages', '_Total'),
    # SQLServer:Databases
    ('sqlserver.database.backup_restore_throughput', 'Backup/Restore Throughput/sec', '_Total'),
    ('sqlserver.database.log_bytes_flushed', 'Log Bytes Flushed/sec', '_Total'),
    ('sqlserver.database.log_flushes', 'Log Flushes/sec', '_Total'),
    ('sqlserver.database.log_flush_wait', 'Log Flush Wait Time', '_Total'),
    ('sqlserver.database.transactions', 'Transactions/sec', '_Total'),  # BULK_COUNT
    ('sqlserver.database.write_transactions', 'Write Transactions/sec', '_Total'),  # BULK_COUNT
    ('sqlserver.database.active_transactions', 'Active Transactions', '_Total'),  # BULK_COUNT
]

# AlwaysOn metrics
# datadog metric name, sql table, column name, tag
AO_METRICS = [
    ('sqlserver.ao.ag_sync_health', 'sys.dm_hadr_availability_group_states', 'synchronization_health'),
    ('sqlserver.ao.replica_sync_state', 'sys.dm_hadr_database_replica_states', 'synchronization_state'),
    ('sqlserver.ao.replica_failover_mode', 'sys.availability_replicas', 'failover_mode'),
    ('sqlserver.ao.replica_failover_readiness', 'sys.availability_replicas', 'is_failover_ready'),
]

AO_METRICS_PRIMARY = [
    ('sqlserver.ao.primary_replica_health', 'sys.dm_hadr_availability_group_states', 'primary_recovery_health'),
]

AO_METRICS_SECONDARY = [
    ('sqlserver.ao.secondary_replica_health', 'sys.dm_hadr_availability_group_states', 'secondary_recovery_health'),
]

# AlwaysOn metrics for Failover Cluster Instances (FCI).
# This is in a separate category than other AlwaysOn metrics
# because FCI specifies a different SQLServer setup
# compared to Availability Groups (AG).
# datadog metric name, sql table, column name
# FCI status enum:
#   0 = Up, 1 = Down, 2 = Paused, 3 = Joining, -1 = Unknown
FCI_METRICS = [
    ('sqlserver.fci.status', 'sys.dm_os_cluster_nodes', 'status'),
    ('sqlserver.fci.is_current_owner', 'sys.dm_os_cluster_nodes', 'is_current_owner'),
]

# Non-performance table metrics - can be database specific
# datadog metric name, sql table, column name
TASK_SCHEDULER_METRICS = [
    ('sqlserver.scheduler.current_tasks_count', 'sys.dm_os_schedulers', 'current_tasks_count'),
    ('sqlserver.scheduler.current_workers_count', 'sys.dm_os_schedulers', 'current_workers_count'),
    ('sqlserver.scheduler.active_workers_count', 'sys.dm_os_schedulers', 'active_workers_count'),
    ('sqlserver.scheduler.runnable_tasks_count', 'sys.dm_os_schedulers', 'runnable_tasks_count'),
    ('sqlserver.scheduler.work_queue_count', 'sys.dm_os_schedulers', 'work_queue_count'),
    ('sqlserver.task.context_switches_count', 'sys.dm_os_tasks', 'context_switches_count'),
    ('sqlserver.task.pending_io_count', 'sys.dm_os_tasks', 'pending_io_count'),
    ('sqlserver.task.pending_io_byte_count', 'sys.dm_os_tasks', 'pending_io_byte_count'),
    ('sqlserver.task.pending_io_byte_average', 'sys.dm_os_tasks', 'pending_io_byte_average'),
]

# Non-performance table metrics
# datadog metric name, sql table, column name
# Files State enum:
#   0 = Online, 1 = Restoring, 2 = Recovering, 3 = Recovery_Pending,
#   4 = Suspect, 5 = Unknown, 6 = Offline, 7 = Defunct
# Database State enum:
#   0 = Online, 1 = Restoring, 2 = Recovering, 3 = Recovery_Pending,
#   4 = Suspect, 5 = Emergency, 6 = Offline, 7 = Copying, 10 = Offline_Secondary
# Is Sync with Backup enum:
#   0 = False, 1 = True
DATABASE_METRICS = [
    ('sqlserver.database.files.size', 'sys.database_files', 'size'),
    ('sqlserver.database.files.state', 'sys.database_files', 'state'),
    ('sqlserver.database.state', 'sys.databases', 'state'),
    ('sqlserver.database.is_sync_with_backup', 'sys.databases', 'is_sync_with_backup'),
    ('sqlserver.database.backup_count', 'msdb.dbo.backupset', 'backup_set_id_count'),
]

DATABASE_FRAGMENTATION_METRICS = [
    (
        'sqlserver.database.avg_fragmentation_in_percent',
        'sys.dm_db_index_physical_stats',
        'avg_fragmentation_in_percent',
    ),
    ('sqlserver.database.fragment_count', 'sys.dm_db_index_physical_stats', 'fragment_count'),
    (
        'sqlserver.database.avg_fragment_size_in_pages',
        'sys.dm_db_index_physical_stats',
        'avg_fragment_size_in_pages',
    ),
]

DATABASE_MASTER_FILES = [
    ('sqlserver.database.master_files.size', 'sys.master_files', 'size'),
    ('sqlserver.database.master_files.state', 'sys.master_files', 'state'),
]

DATABASE_FILES_IO = [
    ('sqlserver.files.reads', 'num_of_reads'),
    ('sqlserver.files.read_bytes', 'num_of_bytes_read'),
    ('sqlserver.files.read_io_stall', 'io_stall_read_ms'),
    ('sqlserver.files.read_io_stall_queued', 'io_stall_queued_read_ms'),
    ('sqlserver.files.writes', 'num_of_writes'),
    ('sqlserver.files.written_bytes', 'num_of_bytes_written'),
    ('sqlserver.files.write_io_stall', 'io_stall_write_ms'),
    ('sqlserver.files.write_io_stall_queued', 'io_stall_queued_write_ms'),
    ('sqlserver.files.io_stall', 'io_stall'),
    ('sqlserver.files.size_on_disk', 'size_on_disk_bytes'),
]
