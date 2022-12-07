# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Database Disk Space
# https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Views-Reference/DiskSpaceV-X
DISK_SPACE = {
    'name': 'disk_space',
    'query': "SELECT Vproc, TRIM(BOTH FROM AccountName), TRIM(BOTH FROM DatabaseName), "
    "MaxPerm, MaxSpool, MaxTemp, CurrentPerm, CurrentSpool, CurrentPersistentSpool, CurrentTemp, PeakPerm, "
    "PeakSpool, PeakPersistentSpool, PeakTemp, MaxProfileSpool, MaxProfileTemp, AllocatedPerm, AllocatedSpool,"
    "AllocatedTemp, PermSkew, SpoolSkew, TempSkew FROM DBC.DiskSpaceV WHERE DatabaseName='{}';",
    'columns': [
        {'name': 'td_amp', 'type': 'tag'},
        {'name': 'td_account', 'type': 'tag'},
        {'name': 'td_database', 'type': 'tag'},
        {'name': 'disk_space.max_perm.total', 'type': 'gauge'},
        {'name': 'disk_space.max_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.max_temp.total', 'type': 'gauge'},
        {'name': 'disk_space.curr_perm.total', 'type': 'gauge'},
        {'name': 'disk_space.curr_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.curr_persist_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.curr_temp.total', 'type': 'gauge'},
        {'name': 'disk_space.peak_perm.total', 'type': 'gauge'},
        {'name': 'disk_space.peak_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.peak_persist_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.peak_temp.total', 'type': 'gauge'},
        {'name': 'disk_space.max_prof_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.max_prof_temp.total', 'type': 'gauge'},
        {'name': 'disk_space.alloc_perm.total', 'type': 'gauge'},
        {'name': 'disk_space.alloc_spool.total', 'type': 'gauge'},
        {'name': 'disk_space.alloc_temp.total', 'type': 'gauge'},
        {'name': 'disk_space.perm_skew.total', 'type': 'gauge'},
        {'name': 'disk_space.spool_skew.total', 'type': 'gauge'},
        {'name': 'disk_space.temp_skew.total', 'type': 'gauge'},
    ],
}

# Database and Table Disk Space
# https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Views-Reference/AllSpaceV-X
ALL_SPACE = {
    'name': 'all_space',
    'query': "SELECT Vproc, TRIM(BOTH FROM AccountName), TRIM(BOTH FROM DatabaseName), TRIM(BOTH FROM TableName), "
    "MaxPerm, MaxSpool, MaxTemp, CurrentPerm, CurrentSpool, CurrentPersistentSpool, CurrentTemp, PeakPerm, "
    "PeakSpool, PeakPersistentSpool, PeakTemp, MaxProfileSpool, MaxProfileTemp, AllocatedPerm, AllocatedSpool,"
    "AllocatedTemp, PermSkew, SpoolSkew, TempSkew FROM DBC.AllSpaceV WHERE DatabaseName='{}';",
    'columns': [
        {'name': 'td_amp', 'type': 'tag'},
        {'name': 'td_account', 'type': 'tag'},
        {'name': 'td_database', 'type': 'tag'},
        {'name': 'td_table', 'type': 'tag'},
        {'name': 'disk_space.max_perm', 'type': 'gauge'},
        {'name': 'disk_space.max_spool', 'type': 'gauge'},
        {'name': 'disk_space.max_temp', 'type': 'gauge'},
        {'name': 'disk_space.curr_perm', 'type': 'gauge'},
        {'name': 'disk_space.curr_spool', 'type': 'gauge'},
        {'name': 'disk_space.curr_persist_spool', 'type': 'gauge'},
        {'name': 'disk_space.curr_temp', 'type': 'gauge'},
        {'name': 'disk_space.peak_perm', 'type': 'gauge'},
        {'name': 'disk_space.peak_spool', 'type': 'gauge'},
        {'name': 'disk_space.peak_persist_spool', 'type': 'gauge'},
        {'name': 'disk_space.peak_temp', 'type': 'gauge'},
        {'name': 'disk_space.max_prof_spool', 'type': 'gauge'},
        {'name': 'disk_space.max_prof_temp', 'type': 'gauge'},
        {'name': 'disk_space.alloc_perm', 'type': 'gauge'},
        {'name': 'disk_space.alloc_spool', 'type': 'gauge'},
        {'name': 'disk_space.alloc_temp', 'type': 'gauge'},
        {'name': 'disk_space.perm_skew', 'type': 'gauge'},
        {'name': 'disk_space.spool_skew', 'type': 'gauge'},
        {'name': 'disk_space.temp_skew', 'type': 'gauge'},
    ],
}

# Access Module Processor (AMP) Usage
# https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Views-Reference/AMPUsageV-X
AMP_USAGE = {
    'name': 'amp_usage',
    'query': 'SELECT Vproc, TRIM(BOTH FROM AccountName), TRIM(BOTH FROM UserName), CpuTime,'
    'DiskIO, CPUTimeNorm FROM DBC.AMPUsageV;',
    'columns': [
        {'name': 'td_amp', 'type': 'tag'},
        {'name': 'td_account', 'type': 'tag'},
        {'name': 'td_user', 'type': 'tag'},
        {'name': 'amp.cpu_time', 'type': 'gauge'},
        {'name': 'amp.disk_io', 'type': 'gauge'},
        {'name': 'amp.cpu_time_norm', 'type': 'gauge'},
    ],
}

# Requires enabling the Resource Usage Table, ResUsageSpma:
# https://docs.teradata.com/r/Teradata-VantageTM-Resource-Usage-Macros-and-Tables/July-2021/ResUsageSpma-Table/Statistics-Columns
RESOURCE_USAGE = {
    'name': 'resource_usage',
    'query': 'SELECT TOP 1 TheTimestamp, FileLockBlocks, FileLockDeadlocks, FileLockEnters, DBLockBlocks, '
    'DBLockDeadlocks, IoThrottleCount, IoThrottleTime, IoThrottleTimeMax, MemCtxtPageReads, MemCtxtPageWrites,'
    'MemTextPageReads, VHCacheKB, KernMemInuseKB, SegMDLInuseKB, SegMaxAvailMB, SegInuseMB, SegCacheMB, '
    'SegMDLAlloc, SegMDLFree, SegMDLRelease, SegMDLRecycle, SegMDLAllocKB, SegMDLFreeKB, SegMDLReleaseKB, '
    'SegMDLRecycleKB, FsgCacheKB, PageMajorFaults, PageMinorFaults, ProcBlocked, ProcReady, ProcReadyMax, '
    'CPUIdle, CPUIoWait, CPUUServ, CPUUExec, CpuThrottleCount, CpuThrottleTime FROM DBC.ResSpmaView '
    'ORDER BY TheTimestamp DESC;',
    'columns': [
        {'name': 'timestamp', 'type': 'source'},
        {'name': 'file_lock.blocks', 'type': 'gauge'},
        {'name': 'file_lock.deadlocks', 'type': 'gauge'},
        {'name': 'file_lock.enters', 'type': 'gauge'},
        {'name': 'db_lock.blocks', 'type': 'gauge'},
        {'name': 'db_lock.deadlocks', 'type': 'gauge'},
        {'name': 'io.throttle_count', 'type': 'gauge'},
        {'name': 'io.throttle_time', 'type': 'gauge'},
        {'name': 'io.throttle_time_max', 'type': 'gauge'},
        {'name': 'mem.ctxt_page_reads', 'type': 'gauge'},
        {'name': 'mem.ctxt_page_writes', 'type': 'gauge'},
        {'name': 'mem.txt_page_reads', 'type': 'gauge'},
        {'name': 'mem.vh_cache_size', 'type': 'gauge'},
        {'name': 'mem.kernel_inuse_size', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.inuse_size', 'type': 'gauge'},
        {'name': 'mem.seg_max_avail_size', 'type': 'gauge'},
        {'name': 'mem.seg_in_use_size', 'type': 'gauge'},
        {'name': 'mem.seg_cache_size', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.alloc', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.free', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.release', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.recycle', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.alloc_size', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.free_size', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.release_size', 'type': 'gauge'},
        {'name': 'mem.seg_mdl.recycle_size', 'type': 'gauge'},
        {'name': 'mem.fsg.cache_size', 'type': 'gauge'},
        {'name': 'mem.page_faults_major', 'type': 'gauge'},
        {'name': 'mem.page_faults_minor', 'type': 'gauge'},
        {'name': 'process.blocked', 'type': 'gauge'},
        {'name': 'process.ready', 'type': 'gauge'},
        {'name': 'process.ready_max', 'type': 'gauge'},
        {'name': 'process.cpu_idle_cs', 'type': 'source'},
        {'name': 'process.cpu_io_wait_cs', 'type': 'source'},
        {'name': 'process.cpu_serv_cs', 'type': 'source'},
        {'name': 'process.cpu_exec_cs', 'type': 'source'},
        {'name': 'process.cpu_throttle', 'type': 'gauge'},
        {'name': 'process.cpu_throttle_time_cs', 'type': 'source'},
    ],
    # convert centiseconds to milliseconds
    'extras': [
        {'name': 'process.cpu_idle', 'expression': 'process.cpu_idle_cs * 10', 'submit_type': 'gauge'},
        {'name': 'process.cpu_io_wait', 'expression': 'process.cpu_io_wait_cs * 10', 'submit_type': 'gauge'},
        {'name': 'process.cpu_serv', 'expression': 'process.cpu_serv_cs * 10', 'submit_type': 'gauge'},
        {'name': 'process.cpu_exec', 'expression': 'process.cpu_exec_cs * 10', 'submit_type': 'gauge'},
        {
            'name': 'process.cpu_throttle_time',
            'expression': 'process.cpu_throttle_time_cs * 10',
            'submit_type': 'gauge',
        },
    ],
}

TERADATA_VERSION = {
    'name': 'teradata_version',
    'query': "SELECT InfoData FROM DBC.DBCInfoV WHERE InfoKey='VERSION';",
    'columns': [{'name': 'teradata_version', 'type': 'source'}],
}

DEFAULT_QUERIES = [DISK_SPACE, AMP_USAGE, TERADATA_VERSION]

COLLECT_RES_USAGE = [RESOURCE_USAGE]

COLLECT_ALL_SPACE = [ALL_SPACE]
