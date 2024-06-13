# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Constant for SQLServer cntr_type
PERF_LARGE_RAW_BASE = 1073939712
PERF_RAW_LARGE_FRACTION = 537003264
PERF_AVERAGE_BULK = 1073874176
PERF_COUNTER_BULK_COUNT = 272696576
PERF_COUNTER_LARGE_RAWCOUNT = 65792

# Engine Editions; see:
# https://docs.microsoft.com/en-us/sql/t-sql/functions/serverproperty-transact-sql
ENGINE_EDITION_PERSONAL = 1
ENGINE_EDITION_STANDARD = 2
ENGINE_EDITION_ENTERPRISE = 3
ENGINE_EDITION_EXPRESS = 4
ENGINE_EDITION_SQL_DATABASE = 5
ENGINE_EDITION_AZURE_SYNAPSE_ANALYTICS = 6
ENGINE_EDITION_AZURE_MANAGED_INSTANCE = 8
ENGINE_EDITION_AZURE_SQL_EDGE = 9
ENGINE_EDITION_AZURE_SYNAPSE_SERVERLESS_POOL = 11

# Keys of the static info cache, used to cache server info which does not change
STATIC_INFO_VERSION = 'version'
STATIC_INFO_MAJOR_VERSION = 'major_version'
STATIC_INFO_ENGINE_EDITION = 'engine_edition'
AWS_RDS_HOSTNAME_SUFFIX = ".rds.amazonaws.com"
AZURE_DEPLOYMENT_TYPE_TO_RESOURCE_TYPES = {
    # azure sql database has a special case, where we should emit
    # a resource for both the server and the database because
    # azure treats these as two separate entities, and both can have
    # related tags and metrics
    "sql_database": "azure_sql_server_database,azure_sql_server",
    "managed_instance": "azure_sql_server_managed_instance",
    "virtual_machine": "azure_virtual_machine_instance",
}

# Metric discovery queries
COUNTER_TYPE_QUERY = """select distinct cntr_type
                        from sys.dm_os_performance_counters
                        where counter_name = ?;"""

BASE_NAME_QUERY = (
    """select distinct counter_name
       from sys.dm_os_performance_counters
       where lower(counter_name) IN (?, ?, ?) and cntr_type=%s;"""
    % PERF_LARGE_RAW_BASE
)

DEFAULT_AUTODISCOVERY_INTERVAL = 3600
AUTODISCOVERY_QUERY = """select {columns} from sys.databases"""
expected_sys_databases_columns = [
    'name',
    'physical_database_name',
]

DATABASE_SERVICE_CHECK_QUERY = """SELECT 1;"""
SWITCH_DB_STATEMENT = """USE {};"""

VALID_METRIC_TYPES = ('gauge', 'rate', 'histogram')

SERVICE_CHECK_NAME = 'sqlserver.can_connect'
DATABASE_SERVICE_CHECK_NAME = 'sqlserver.database.can_connect'

DBM_MIGRATED_METRICS = [
    ('sqlserver.stats.connections', 'User Connections', '', ''),  # LARGE_RAWCOUNT
]

# Default performance table metrics - Database Instance level
# datadog metric name, counter name, instance name, object name
INSTANCE_METRICS = [
    # SQLServer:General Statistics
    ('sqlserver.stats.procs_blocked', 'Processes blocked', '', ''),  # LARGE_RAWCOUNT
    # SQLServer:Access Methods
    ('sqlserver.access.page_splits', 'Page Splits/sec', '', ''),  # BULK_COUNT
    ('sqlserver.access.full_scans', 'Full Scans/sec', '', ''),  # BULK_COUNT
    ('sqlserver.access.range_scans', 'Range Scans/sec', '', ''),  # BULK_COUNT
    ('sqlserver.access.probe_scans', 'Probe Scans/sec', '', ''),  # BULK_COUNT
    ('sqlserver.access.index_searches', 'Index Searches/sec', '', ''),  # BULK_COUNT
    # SQLServer:Memory Manager
    ('sqlserver.memory.memory_grants_pending', 'Memory Grants Pending', '', ''),
    ('sqlserver.memory.total_server_memory', 'Total Server Memory (KB)', '', ''),
    ('sqlserver.memory.sql_cache', 'SQL Cache Memory (KB)', '', ''),
    ('sqlserver.memory.grants_outstanding', 'Memory Grants Outstanding', '', ''),
    ('sqlserver.memory.database_cache', 'Database Cache Memory (KB)', '', ''),
    ('sqlserver.memory.connection', 'Connection Memory (KB)', '', ''),
    ('sqlserver.memory.optimizer', 'Optimizer Memory (KB)', '', ''),
    ('sqlserver.memory.granted_workspace', 'Granted Workspace Memory (KB)', '', ''),
    ('sqlserver.memory.lock', 'Lock Memory (KB)', '', ''),
    ('sqlserver.memory.stolen', 'Stolen Server Memory (KB)', '', ''),
    ('sqlserver.memory.log_pool_memory', 'Log Pool Memory (KB)', '', ''),
    # SQLServer:Buffer Manager
    ('sqlserver.buffer.cache_hit_ratio', 'Buffer cache hit ratio', '', ''),  # RAW_LARGE_FRACTION
    ('sqlserver.buffer.page_life_expectancy', 'Page life expectancy', '', ''),  # LARGE_RAWCOUNT
    ('sqlserver.buffer.page_reads', 'Page reads/sec', '', ''),  # LARGE_RAWCOUNT
    ('sqlserver.buffer.page_writes', 'Page writes/sec', '', ''),  # LARGE_RAWCOUNT
    ('sqlserver.buffer.checkpoint_pages', 'Checkpoint pages/sec', '', ''),  # BULK_COUNT
    # SQLServer:SQL Statistics
    ('sqlserver.stats.auto_param_attempts', 'Auto-Param Attempts/sec', '', ''),
    ('sqlserver.stats.failed_auto_param_attempts', 'Failed Auto-Params/sec', '', ''),
    ('sqlserver.stats.safe_auto_param_attempts', 'Safe Auto-Params/sec', '', ''),
    ('sqlserver.stats.batch_requests', 'Batch Requests/sec', '', ''),  # BULK_COUNT
    ('sqlserver.stats.sql_compilations', 'SQL Compilations/sec', '', ''),  # BULK_COUNT
    ('sqlserver.stats.sql_recompilations', 'SQL Re-Compilations/sec', '', ''),  # BULK_COUNT
    # SQLServer:Locks
    ('sqlserver.stats.lock_waits', 'Lock Waits/sec', '_Total', ''),  # BULK_COUNT
    ('sqlserver.latches.latch_waits', 'Latch Waits/sec', '', ''),  # BULK_COUNT
    ('sqlserver.locks.deadlocks', 'Number of Deadlocks/sec', '_Total', ''),  # BULK_COUNT
    # SQLServer:Plan Cache
    ('sqlserver.cache.object_counts', 'Cache Object Counts', '_Total', ''),
    ('sqlserver.cache.pages', 'Cache Pages', '_Total', ''),
    # SQLServer:Database Replica
    ('sqlserver.replica.transaction_delay', 'Transaction Delay', '_Total', 'SQLServer:Database Replica'),
    ('sqlserver.replica.flow_control_sec', 'Flow Control/sec', '_Total', ''),
    # SQLServer:Transactions
    ('sqlserver.transactions.version_store_size', 'Version Store Size (KB)', '', ''),
    ('sqlserver.transactions.version_cleanup_rate', 'Version Cleanup rate (KB/s)', '', ''),
    ('sqlserver.transactions.version_generation_rate', 'Version Generation rate (KB/s)', '', ''),
    ('sqlserver.transactions.longest_transaction_running_time', 'Longest Transaction Running Time', '', ''),
]

# SQLServer version >= 2016
# Default performance table metrics - Database Instance level
# datadog metric name, counter name, instance name
INSTANCE_METRICS_NEWER_2016 = [
    # SQLServer:Locks
    # base counter Average Latch Wait Time Base is available starting with SQL Server 2016
    ('sqlserver.latches.latch_wait_time', 'Average Latch Wait Time (ms)', '', ''),  # BULK_COUNT
]

# Performance table metrics, initially configured to track at instance-level only
# With auto-discovery enabled, these metrics will be extended accordingly
# datadog metric name, counter name, instance name, object name
INSTANCE_METRICS_DATABASE_SINGLE = [
    # SQLServer:Databases
    ('sqlserver.database.backup_restore_throughput', 'Backup/Restore Throughput/sec', '_Total', ''),
    ('sqlserver.database.log_bytes_flushed', 'Log Bytes Flushed/sec', '_Total', ''),
    ('sqlserver.database.log_flushes', 'Log Flushes/sec', '_Total', ''),
    ('sqlserver.database.log_flush_wait', 'Log Flush Wait Time', '_Total', ''),
    ('sqlserver.database.transactions', 'Transactions/sec', '_Total', ''),  # BULK_COUNT
    ('sqlserver.database.write_transactions', 'Write Transactions/sec', '_Total', ''),  # BULK_COUNT
    ('sqlserver.database.active_transactions', 'Active Transactions', '_Total', ''),  # BULK_COUNT
]

# Performance table metrics when AlwaysOn is enabled
# datadog metric name, counter name, instance name, object name
INSTANCE_METRICS_DATABASE_AO = [
    ('sqlserver.database.replica.transaction_delay', 'Transaction Delay', '', 'SQLServer:Database Replica'),
]

INSTANCE_METRICS_DATABASE = INSTANCE_METRICS_DATABASE_SINGLE + INSTANCE_METRICS_DATABASE_AO

# AlwaysOn metrics
# datadog metric name, sql table, column name, tag
AO_AG_SYNC_METRICS = [
    ('sqlserver.ao.ag_sync_health', 'sys.dm_hadr_availability_group_states', 'synchronization_health'),
]
AO_REPLICA_SYNC_METRICS = [
    ('sqlserver.ao.replica_sync_state', 'sys.dm_hadr_database_replica_states', 'synchronization_state'),
]
AO_REPLICA_FAILOVER_METRICS = [
    ('sqlserver.ao.replica_failover_mode', 'sys.availability_replicas', 'failover_mode'),
    ('sqlserver.ao.replica_failover_readiness', 'sys.availability_replicas', 'is_failover_ready'),
]
AO_METRICS = AO_AG_SYNC_METRICS + AO_REPLICA_SYNC_METRICS + AO_REPLICA_FAILOVER_METRICS

AO_METRICS_PRIMARY = [
    ('sqlserver.ao.primary_replica_health', 'sys.dm_hadr_availability_group_states', 'primary_recovery_health'),
]

AO_METRICS_SECONDARY = [
    ('sqlserver.ao.secondary_replica_health', 'sys.dm_hadr_availability_group_states', 'secondary_recovery_health'),
]

# Non-performance table metrics - can be database specific
# datadog metric name, sql table, column name
OS_SCHEDULER_METRICS = [
    ('sqlserver.scheduler.current_tasks_count', 'sys.dm_os_schedulers', 'current_tasks_count'),
    ('sqlserver.scheduler.current_workers_count', 'sys.dm_os_schedulers', 'current_workers_count'),
    ('sqlserver.scheduler.active_workers_count', 'sys.dm_os_schedulers', 'active_workers_count'),
    ('sqlserver.scheduler.runnable_tasks_count', 'sys.dm_os_schedulers', 'runnable_tasks_count'),
    ('sqlserver.scheduler.work_queue_count', 'sys.dm_os_schedulers', 'work_queue_count'),
]
OS_TASK_METRICS = [
    ('sqlserver.task.context_switches_count', 'sys.dm_os_tasks', 'context_switches_count'),
    ('sqlserver.task.pending_io_count', 'sys.dm_os_tasks', 'pending_io_count'),
    ('sqlserver.task.pending_io_byte_count', 'sys.dm_os_tasks', 'pending_io_byte_count'),
    ('sqlserver.task.pending_io_byte_average', 'sys.dm_os_tasks', 'pending_io_byte_average'),
]
TASK_SCHEDULER_METRICS = OS_SCHEDULER_METRICS + OS_TASK_METRICS

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
DATABASE_FILES_METRICS = [
    ('sqlserver.database.files.size', 'sys.database_files', 'size'),
    ('sqlserver.database.files.space_used', 'sys.database_files', 'space_used'),
    ('sqlserver.database.files.state', 'sys.database_files', 'state'),
]
DATABASE_STATS_METRICS = [
    ('sqlserver.database.state', 'sys.databases', 'state'),
    ('sqlserver.database.is_sync_with_backup', 'sys.databases', 'is_sync_with_backup'),
    ('sqlserver.database.is_in_standby', 'sys.databases', 'is_in_standby'),
    ('sqlserver.database.is_read_only', 'sys.databases', 'is_read_only'),
]
DATABASE_BACKUP_METRICS = [
    ('sqlserver.database.backup_count', 'msdb.dbo.backupset', 'backup_set_id_count'),
]
DATABASE_METRICS = DATABASE_FILES_METRICS + DATABASE_STATS_METRICS

DATABASE_INDEX_METRICS = [
    'sqlserver.index.user_seeks',
    'sqlserver.index.user_scans',
    'sqlserver.index.user_lookups',
    'sqlserver.index.user_updates',
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
    (
        'sqlserver.database.index_page_count',
        'sys.dm_db_index_physical_stats',
        'page_count',
    ),
]

DATABASE_MASTER_FILES = [
    ('sqlserver.database.master_files.size', 'sys.master_files', 'size'),
    ('sqlserver.database.master_files.state', 'sys.master_files', 'state'),
]

TEMPDB_FILE_SPACE_USAGE_METRICS = [
    ('sqlserver.tempdb.file_space_usage.free_space', 'sys.dm_db_file_space_usage', 'free_space'),
    (
        'sqlserver.tempdb.file_space_usage.version_store_space',
        'sys.dm_db_file_space_usage',
        'used_space_by_version_store',
    ),
    (
        'sqlserver.tempdb.file_space_usage.internal_object_space',
        'sys.dm_db_file_space_usage',
        'used_space_by_internal_object',
    ),
    (
        'sqlserver.tempdb.file_space_usage.user_object_space',
        'sys.dm_db_file_space_usage',
        'used_space_by_user_object',
    ),
    ('sqlserver.tempdb.file_space_usage.mixed_extent_space', 'sys.dm_db_file_space_usage', 'mixed_extent_space'),
]

PROC_CHAR_LIMIT = 500
