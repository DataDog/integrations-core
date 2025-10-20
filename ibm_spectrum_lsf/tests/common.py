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
ALL_METRICS = LSID_METRICS + CLUSTER_METRICS + BHOST_METRICS + LHOST_METRICS
