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
ALL_METRICS = LSID_METRICS + CLUSTER_METRICS + BHOST_METRICS
