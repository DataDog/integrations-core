# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

LSID_METRICS = [
    "ibm_spectrum_lsf.can_connect",
]

CLUSTER_METRICS = [
    "ibm_spectrum_lsf.cluster.hosts",
    "ibm_spectrum_lsf.cluster.servers",
    "ibm_spectrum_lsf.cluster.status",
]

BHOST_METRICS = [
    "ibm_spectrum_lsf.server.max_jobs",
    "ibm_spectrum_lsf.server.num_jobs",
    "ibm_spectrum_lsf.server.reserved",
    "ibm_spectrum_lsf.server.running",
    "ibm_spectrum_lsf.server.slots_per_user",
    "ibm_spectrum_lsf.server.status",
    "ibm_spectrum_lsf.server.suspended",
    "ibm_spectrum_lsf.server.user_suspended",
]

LHOST_METRICS = [
    "ibm_spectrum_lsf.host.cpu_factor",
    "ibm_spectrum_lsf.host.is_server",
    "ibm_spectrum_lsf.host.max_mem",
    "ibm_spectrum_lsf.host.max_swap",
    "ibm_spectrum_lsf.host.max_temp",
    "ibm_spectrum_lsf.host.num_cores",
    "ibm_spectrum_lsf.host.num_cpus",
    "ibm_spectrum_lsf.host.num_procs",
    "ibm_spectrum_lsf.host.num_threads",
]

LSLOAD_METRICS = [
    "ibm_spectrum_lsf.load.cpu.run_queue_length.15m",
    "ibm_spectrum_lsf.load.cpu.run_queue_length.15s",
    "ibm_spectrum_lsf.load.cpu.run_queue_length.1m",
    "ibm_spectrum_lsf.load.cpu.utilization",
    "ibm_spectrum_lsf.load.disk.io",
    "ibm_spectrum_lsf.load.idle_time",
    "ibm_spectrum_lsf.load.login_users",
    "ibm_spectrum_lsf.load.mem.available_ram",
    "ibm_spectrum_lsf.load.mem.available_swap",
    "ibm_spectrum_lsf.load.mem.free",
    "ibm_spectrum_lsf.load.mem.paging_rate",
    "ibm_spectrum_lsf.load.status",
]

BSLOTS_METRICS = ["ibm_spectrum_lsf.slots.backfill.available", "ibm_spectrum_lsf.slots.runtime_limit"]

BQUEUES_METRICS = [
    "ibm_spectrum_lsf.queue.is_active",
    "ibm_spectrum_lsf.queue.is_open",
    "ibm_spectrum_lsf.queue.max_jobs",
    "ibm_spectrum_lsf.queue.max_jobs_per_host",
    "ibm_spectrum_lsf.queue.max_jobs_per_processor",
    "ibm_spectrum_lsf.queue.max_jobs_per_user",
    "ibm_spectrum_lsf.queue.num_job_slots",
    "ibm_spectrum_lsf.queue.pending",
    "ibm_spectrum_lsf.queue.priority",
    "ibm_spectrum_lsf.queue.running",
    "ibm_spectrum_lsf.queue.suspended",
]
ALL_METRICS = (
    LSID_METRICS + CLUSTER_METRICS + BHOST_METRICS + BSLOTS_METRICS + LHOST_METRICS + LSLOAD_METRICS + BQUEUES_METRICS
)
