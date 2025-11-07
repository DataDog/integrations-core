# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

LSID_METRICS = [{"name": "ibm_spectrum_lsf.can_connect", "tags": ["lsf_cluster_name:test-cluster"], "val": 1}]

CLUSTER_METRICS = [
    {
        "name": "ibm_spectrum_lsf.cluster.hosts",
        "tags": [
            'lsf_admin:ec2-user',
            'lsf_cluster:test-cluster',
            'lsf_cluster_name:test-cluster',
            'lsf_management_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.cluster.servers",
        "tags": [
            'lsf_admin:ec2-user',
            'lsf_cluster:test-cluster',
            'lsf_cluster_name:test-cluster',
            'lsf_management_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.cluster.status",
        "tags": [
            'lsf_admin:ec2-user',
            'lsf_cluster:test-cluster',
            'lsf_cluster_name:test-cluster',
            'lsf_management_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1,
    },
]

BHOST_METRICS = [
    {
        "name": "ibm_spectrum_lsf.server.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 4,
    },
    {
        "name": "ibm_spectrum_lsf.server.num_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.reserved",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.running",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.slots_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.server.status",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.server.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.user_suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
]

LHOST_METRICS = [
    {
        "name": "ibm_spectrum_lsf.host.cpu_factor",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 12.5,
    },
    {
        "name": "ibm_spectrum_lsf.host.is_server",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.host.max_mem",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 16030,
    },
    {
        "name": "ibm_spectrum_lsf.host.max_swap",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.host.max_temp",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 81886,
    },
    {
        "name": "ibm_spectrum_lsf.host.num_cores",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 4,
    },
    {
        "name": "ibm_spectrum_lsf.host.num_cpus",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 4,
    },
    {
        "name": "ibm_spectrum_lsf.host.num_procs",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.host.num_threads",
        "tags": [
            'host_model:Intel_E5',
            'host_type:X86_64',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1,
    },
]

LSLOAD_METRICS = [
    {
        "name": "ibm_spectrum_lsf.load.cpu.run_queue_length.15m",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.load.cpu.run_queue_length.15s",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.load.cpu.run_queue_length.1m",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.load.cpu.utilization",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.load.disk.io",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 1.0,
    },
    {
        "name": "ibm_spectrum_lsf.load.idle_time",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 1.0,
    },
    {
        "name": "ibm_spectrum_lsf.load.login_users",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.load.mem.available_ram",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 15348,
    },
    {
        "name": "ibm_spectrum_lsf.load.mem.available_swap",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.load.mem.free",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 73057.6,
    },
    {
        "name": "ibm_spectrum_lsf.load.mem.paging_rate",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.load.status",
        "tags": ['lsf_cluster_name:test-cluster', 'lsf_host:ip-11-21-111-198.ec2.internal'],
        "val": 1,
    },
]

BSLOTS_METRICS = [
    {"name": "ibm_spectrum_lsf.slots.backfill.available", "tags": ['lsf_cluster_name:test-cluster'], "val": 2},
    {"name": "ibm_spectrum_lsf.slots.runtime_limit", "tags": ['lsf_cluster_name:test-cluster'], "val": -1},
]

BQUEUES_METRICS = [
    # idle
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": 1,
    },
    {"name": "ibm_spectrum_lsf.queue.is_open", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'], "val": 1},
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": 0,
    },
    {"name": "ibm_spectrum_lsf.queue.pending", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": 20,
    },
    {"name": "ibm_spectrum_lsf.queue.running", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:idle'],
        "val": 0,
    },
    # night
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": 0,
    },
    {"name": "ibm_spectrum_lsf.queue.is_open", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'], "val": 1},
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": 0,
    },
    {"name": "ibm_spectrum_lsf.queue.pending", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": 40,
    },
    {"name": "ibm_spectrum_lsf.queue.running", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:night'],
        "val": 0,
    },
    # interactive
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.is_open",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.pending",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 30,
    },
    {
        "name": "ibm_spectrum_lsf.queue.running",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:interactive'],
        "val": 0,
    },
    # normal
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.is_open",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.pending",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 30,
    },
    {
        "name": "ibm_spectrum_lsf.queue.running",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:normal'],
        "val": 0,
    },
    # short
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": 1,
    },
    {"name": "ibm_spectrum_lsf.queue.is_open", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'], "val": 1},
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": 0,
    },
    {"name": "ibm_spectrum_lsf.queue.pending", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": 35,
    },
    {"name": "ibm_spectrum_lsf.queue.running", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:short'],
        "val": 0,
    },
    # priority
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.is_open",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.pending",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 43,
    },
    {
        "name": "ibm_spectrum_lsf.queue.running",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:priority'],
        "val": 0,
    },
    # owners
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.is_open",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.pending",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 43,
    },
    {
        "name": "ibm_spectrum_lsf.queue.running",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:owners'],
        "val": 0,
    },
    # admin
    {
        "name": "ibm_spectrum_lsf.queue.is_active",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": 1,
    },
    {"name": "ibm_spectrum_lsf.queue.is_open", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'], "val": 1},
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_host",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_processor",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.max_jobs_per_user",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.queue.num_job_slots",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": 0,
    },
    {"name": "ibm_spectrum_lsf.queue.pending", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.priority",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": 50,
    },
    {"name": "ibm_spectrum_lsf.queue.running", "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'], "val": 0},
    {
        "name": "ibm_spectrum_lsf.queue.suspended",
        "tags": ['lsf_cluster_name:test-cluster', 'queue_name:admin'],
        "val": 0,
    },
]

BJOBS_METRICS = [
    # 173
    {
        "name": "ibm_spectrum_lsf.job.cpu_used",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.idle_factor",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.mem",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": 7,
    },
    {
        "name": "ibm_spectrum_lsf.job.percent_complete",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.run_time",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": 79,
    },
    {
        "name": "ibm_spectrum_lsf.job.swap",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.job.time_left",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'exec_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:173',
            'job_id:173',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    # 174
    {
        "name": "ibm_spectrum_lsf.job.cpu_used",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.idle_factor",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.mem",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.percent_complete",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.run_time",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.job.swap",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.time_left",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:174',
            'job_id:174',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    # 175
    {
        "name": "ibm_spectrum_lsf.job.cpu_used",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.idle_factor",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.mem",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.percent_complete",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.run_time",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.job.swap",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
    {
        "name": "ibm_spectrum_lsf.job.time_left",
        "tags": [
            'from_host:ip-11-21-111-198.ec2.internal',
            'full_job_id:175',
            'job_id:175',
            'lsf_cluster_name:test-cluster',
            'queue:normal',
        ],
        "val": -1,
    },
]

GPULOAD_METRICS = [
    {
        "name": "ibm_spectrum_lsf.server.gpu.mode",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.status",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 1.0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.ecc",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.power",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 25972.0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.error",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.mem.total",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 15,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.mem.used",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 431,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.mem.utilization",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.power",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 25972,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.pstate",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 0,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.temperature",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 26,
    },
    {
        "name": "ibm_spectrum_lsf.server.gpu.utilization",
        "tags": [
            'gpu_id:0',
            'gpu_model:TeslaT4',
            'lsf_cluster_name:test-cluster',
            'lsf_host:ip-11-21-111-198.ec2.internal',
        ],
        "val": 5,
    },
]

ALL_METRICS = (
    LSID_METRICS
    + CLUSTER_METRICS
    + BHOST_METRICS
    + BSLOTS_METRICS
    + LHOST_METRICS
    + LSLOAD_METRICS
    + BQUEUES_METRICS
    + BJOBS_METRICS
    + GPULOAD_METRICS
)
