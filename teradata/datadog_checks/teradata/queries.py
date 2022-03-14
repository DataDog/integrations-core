# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
# Database and Table Disk Space
# https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Views-Reference/AllSpaceV-X
DISK_SPACE = {
    "name": "disk_space",
    "query": """
        SELECT Vproc, DatabaseName, AccountName, TableName, MaxPerm, MaxSpool, MaxTemp, CurrentPerm,
        CurrentSpool, CurrentPersistentSpool, CurrentTemp, PeakPerm, PeakSpool, PeakPersistentSpool, PeakTemp,
        MaxProfileSpool, MaxProfileTemp, AllocatedPerm, AllocatedSpool, AllocatedTemp, PermSkew, SpoolSkew,
        TempSkew FROM DBC.AllSpaceV WHERE DatabaseName='{}';
        """,
    "columns": [
        {"name": "td_vproc", "type": "tag"},
        {"name": "td_database", "type": "tag"},
        {"name": "td_account", "type": "tag"},
        {"name": "td_table", "type": "tag"},
        {"name": "disk_space.max_perm", "type": "gauge"},
        {"name": "disk_space.max_spool", "type": "gauge"},
        {"name": "disk_space.max_temp", "type": "gauge"},
        {"name": "disk_space.curr_perm", "type": "gauge"},
        {"name": "disk_space.curr_spool", "type": "gauge"},
        {"name": "disk_space.curr_persist_spool", "type": "gauge"},
        {"name": "disk_space.curr_temp", "type": "gauge"},
        {"name": "disk_space.peak_perm", "type": "gauge"},
        {"name": "disk_space.peak_spool", "type": "gauge"},
        {"name": "disk_space.peak_persist_spool", "type": "gauge"},
        {"name": "disk_space.peak_temp", "type": "gauge"},
        {"name": "disk_space.max_prof_spool", "type": "gauge"},
        {"name": "disk_space.max_prof_temp", "type": "gauge"},
        {"name": "disk_space.alloc_perm", "type": "gauge"},
        {"name": "disk_space.alloc_spool", "type": "gauge"},
        {"name": "disk_space.alloc_temp", "type": "gauge"},
        {"name": "disk_space.perm_skew", "type": "gauge"},
        {"name": "disk_space.spool_skew", "type": "gauge"},
        {"name": "disk_space.temp_skew", "type": "gauge"},
    ],
}

# Access Module Processor (AMP) Usage
# https://docs.teradata.com/r/Teradata-VantageTM-Data-Dictionary/July-2021/Views-Reference/AMPUsageV-X
AMP_USAGE = {
    "name": "amp_usage",
    "query": "SELECT AccountName, UserName, CpuTime, DiskIO, CPUTimeNorm, Vproc, VprocType FROM DBC.AMPUsageV;",
    "columns": [
        {"name": "td_account", "type": "tag"},
        {"name": "td_user", "type": "tag"},
        {"name": "amp.cpu_time", "type": "gauge"},
        {"name": "amp.disk_io", "type": "gauge"},
        {"name": "amp.cpu_time_norm", "type": "gauge"},
        {"name": "td_vproc", "type": "tag"},
        {"name": "td_vproc_type", "type": "tag"},
    ],
}

# Requires enabling the Resource Usage Table, ResUsageSpma:
# https://docs.teradata.com/r/Teradata-VantageTM-Resource-Usage-Macros-and-Tables/July-2021/ResUsageSpma-Table
RESOURCE_USAGE = {
    "name": "resource_usage",
    "query": """
        SELECT FileLockBlocks, FileLockDeadlocks, FileLockEnters, DBLockBlocks, DBLockDeadlocks,IoThrottleCount, IoThrottleTime,
        IoThrottleTimeMax, MemCtxtPageReads, MemCtxtPageWrites, MemTextPageReads, VHCacheKB, KernMemInuseKB, SegMDLInuseKB,
        SegMaxAvailMB, SegInuseMB, SegCacheMB, SegMDLAlloc, SegMDLFree, SegMDLRelease, SegMDLRecycle,
        SegMDLAllocKB, SegMDLFreeKB, SegMDLReleaseKB, SegMDLRecycleKB, FsgCacheKB, PageMajorFaults,
        PageMinorFaults, ProcBlocked, ProcReady, ProcReadyMax, CPUIdle, CPUIoWait, CPUUServ, CPUUExec,
        CpuThrottleCount, CpuThrottleTime FROM DBC.ResSpmaView;
        """,
    "columns": [
        {"name": "file_lock.blocks", "type": "gauge"},
        {"name": "file_lock.deadlocks", "type": "gauge"},
        {"name": "file_lock.enters", "type": "gauge"},
        {"name": "db_lock.blocks", "type": "gauge"},
        {"name": "db_lock.deadlocks", "type": "gauge"},
        {"name": "io.throttle_count", "type": "gauge"},
        {"name": "io.throttle_time", "type": "gauge"},
        {"name": "io.throttle_time_max", "type": "gauge"},
        {"name": "mem.ctxt_page_reads", "type": "gauge"},
        {"name": "mem.ctxt_page_writes", "type": "gauge"},
        {"name": "mem.txt_page_reads", "type": "gauge"},
        {"name": "mem.vh_cache_size", "type": "gauge"},
        {"name": "mem.kernel_inuse_size", "type": "gauge"},
        {"name": "mem.seg_mdl.inuse_size", "type": "gauge"},
        {"name": "mem.seg_max_avail_size", "type": "gauge"},
        {"name": "mem.seg_in_use_size", "type": "gauge"},
        {"name": "mem.seg_cache_size", "type": "gauge"},
        {"name": "mem.seg_mdl.alloc", "type": "gauge"},
        {"name": "mem.seg_mdl.free", "type": "gauge"},
        {"name": "mem.seg_mdl.release", "type": "gauge"},
        {"name": "mem.seg_mdl.recycle", "type": "gauge"},
        {"name": "mem.seg_mdl.alloc_size", "type": "gauge"},
        {"name": "mem.seg_mdl.free_size", "type": "gauge"},
        {"name": "mem.seg_mdl.release_size", "type": "gauge"},
        {"name": "mem.seg_mdl.recycle_size", "type": "gauge"},
        {"name": "mem.fsg.cache_size", "type": "gauge"},
        {"name": "mem.page_faults_major", "type": "gauge"},
        {"name": "mem.page_faults_minor", "type": "gauge"},
        {"name": "process.blocked", "type": "gauge"},
        {"name": "process.ready", "type": "gauge"},
        {"name": "process.ready_max", "type": "gauge"},
        {"name": "process.cpu_idle", "type": "gauge"},
        {"name": "process.cpu_io_wait", "type": "gauge"},
        {"name": "process.cpu_serv", "type": "gauge"},
        {"name": "process.cpu_exec", "type": "gauge"},
        {"name": "process.cpu_throttle", "type": "gauge"},
        {"name": "process.cpu_throttle_time", "type": "gauge"},
    ],
}

DEFAULT_QUERIES = [DISK_SPACE, AMP_USAGE]

COLLECT_RES_USAGE = deepcopy(DEFAULT_QUERIES)
COLLECT_RES_USAGE.extend(RESOURCE_USAGE)