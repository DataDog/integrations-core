SINFO_PARTITION_PARAMS = ["-hO", "Partition:|,NodeList:|,CPUs:|,Available:|,Memory:|,Cluster:|,NodeAIOT:|,"]
SINFO_NODE_PARAMS = ["-hNO", "PartitionName:|,Available:|,NodeList:|,NodeAIOT:|,Memory:|,Cluster:|,"]
SINFO_ADDITIONAL_NODE_PARAMS = "CPUsLoad:|,FreeMem:|,Disk:|,StateLong:|,Reason:|,features_act:|,Threads:|,"
GPU_PARAMS = "Gres:|,GresUsed:|,"
SQUEUE_PARAMS = ["-ho", "%A|%u|%j|%T|%N|%C|%R|%m"]
SSHARE_PARAMS = ["-lnpU"]
SACCT_PARAMS = [
    "-npo",
    "JobID,JobName%40,Partition,Account,AllocCPUs,AllocTRES%40,Elapsed,CPUTimeRAW,MaxRSS,MaxVMSize,AveCPU,AveRSS,State,ExitCode,Start,End,NodeList",
    "--units=M",
    "--starttime=now-15seconds",
]

PARTITION_MAP = {
    "tags": [
        {"name": "slurm_partition_name", "index": 0},
        {"name": "slurm_partition_node_list", "index": 1},
        {"name": "slurm_partition_cpus_assigned", "index": 2},
        {"name": "slurm_partition_state", "index": 3},
        {"name": "slurm_partition_memory_assigned", "index": 4},
        {"name": "slurm_partition_available", "index": 5},
    ],
}

NODE_MAP = {
    "tags": [
        {"name": "slurm_partition", "index": 0},
        {"name": "slurm_node_availability", "index": 1},
        {"name": "slurm_node_name", "index": 2},
        {"name": "slurm_node_memory", "index": 4},
        {"name": "slurm_node_cluster", "index": 5},
    ],
    "extended_tags": [
        {"name": "slurm_node_state", "index": 9},
        {"name": "slurm_node_reason", "index": 10},
        {"name": "slurm_node_active_features", "index": 11},
        {"name": "slurm_node_threads", "index": 12},
    ],
    "metrics": [
        {"name": "node.cpu_load", "index": 6},
        {"name": "node.free_mem", "index": 7},
        {"name": "node.tmp_disk", "index": 8},
    ],
}

SQUEUE_MAP = {
    "tags": [
        {"name": "slurm_job_id", "index": 0},
        {"name": "slurm_job_user", "index": 1},
        {"name": "slurm_job_name", "index": 2},
        {"name": "slurm_job_state", "index": 3},
        {"name": "slurm_job_node_list", "index": 4},
        {"name": "slurm_job_cpus", "index": 5},
        {"name": "slurm_job_reason", "index": 6},
        {"name": "slurm_job_tres_per_node", "index": 7},
    ],
}

SACCT_MAP = {
    "tags": [
        {"name": "slurm_job_id", "index": 0},
        {"name": "slurm_job_name", "index": 1},
        {"name": "slurm_job_partition", "index": 2},
        {"name": "slurm_job_account", "index": 3},
        {"name": "slurm_job_cpus", "index": 4},
        {"name": "slurm_job_tres_per_node", "index": 5},
        {"name": "slurm_job_maxvm", "index": 9},
        {"name": "slurm_job_state", "index": 12},
        {"name": "slurm_job_exitcode", "index": 13},
        # {"name": "slurm_job_start", "index": 14},
        # {"name": "slurm_job_end", "index": 15},
        {"name": "slurm_job_node_list", "index": 16},
    ],
    "metrics": [
        {"name": "slurm_job_cputime", "index": 7},
        {"name": "slurm_job_maxrss", "index": 8},
        {"name": "slurm_job_avgcpu", "index": 10},
        {"name": "slurm_job_avgrss", "index": 11},
    ],
}

SSHARE_MAP = {
    "tags": [
        {"name": "slurm_account", "index": 0},
        {"name": "slurm_user", "index": 1},
        {"name": "slurm_group_tres_mins", "index": 9},
        {"name": "slurm_tres_run_mins", "index": 10},
    ],
    "metrics": [
        {"name": "share.raw_shares", "index": 2},
        {"name": "share.norm_shares", "index": 3},
        {"name": "share.raw_usage", "index": 4},
        {"name": "share.norm_usage", "index": 5},
        {"name": "share.effective_usage", "index": 6},
        {"name": "share.fair_share", "index": 7},
        {"name": "share.level_fs", "index": 8},
    ],
}

SDIAG_MAP = {
    'main_stats': {
        'server_thread_count': 'Server thread count:',
        'agent_queue_size': 'Agent queue size:',
        'agent_count': 'Agent count:',
        'agent_thread_count': 'Agent thread count:',
        'queue_size': 'Last queue length:',
        'dbd_agent_queue_size': 'DBD Agent queue size:',
        'jobs_submitted': 'Jobs submitted:',
        'jobs_started': 'Jobs started:',
        'jobs_completed': 'Jobs completed:',
        'jobs_failed': 'Jobs failed:',
        'jobs_canceled': 'Jobs canceled:',
        'jobs_pending': 'Jobs pending:',
        'jobs_running': 'Jobs running:',
        'last_cycle': 'Last cycle:',
        'max_cycle': 'Max cycle:',
        'total_cycles': 'Total cycles:',
        'mean_cycle': 'Mean cycle:',
        'mean_cycle_depth': 'Mean cycle depth:',
        'cycles_per_minute': 'Cycles per minute:',
        'last_queue_length': 'Last queue length:',
    },
    "backfill_stats": {
        'backfill.total_jobs_since_start': 'Total backfilled jobs (since last slurm start):',
        'backfill.total_jobs_since_cycle_start': 'Total backfilled jobs (since last stats cycle start):',
        'backfill.total_heterogeneous_components': 'Total backfilled heterogeneous job components:',
        'backfill.total_cycles': 'Total cycles:',
        'backfill.last_cycles': 'Last cycle:',
        'backfill.max_cycles': 'Max cycle:',
        'backfill.last_depth_cycle': 'Last depth cycle:',
        'backfill.last_depth_try_schedule': 'Last depth cycle (try sched):',
        'backfill.last_queue_length': 'Last queue length:',
        'backfill.last_table_size': 'Last table size:',
    },
}
