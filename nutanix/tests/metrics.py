# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

CLUSTER_STATS_METRICS_REQUIRED = [
    "nutanix.aggregate_hypervisor.memory.usage_ppm",
    "nutanix.controller.avg.io.latency.usecs",
    "nutanix.controller.avg.read.io.latency.usecs",
    "nutanix.controller.avg.write.io.latency.usecs",
    "nutanix.controller.num.iops",
    "nutanix.controller.num.read.iops",
    "nutanix.controller.num.write.iops",
    "nutanix.controller.read.io.bandwidth.kbps",
    "nutanix.controller.write.io.bandwidth.kbps",
    "nutanix.free.physical.storage_bytes",
    "nutanix.health.check_score",
    "nutanix.hypervisor.cpu.usage_ppm",
    "nutanix.io.bandwidth.kbps",
    "nutanix.logical.storage.usage_bytes",
    "nutanix.storage.capacity_bytes",
    "nutanix.storage.usage_bytes",
]

CLUSTER_STATS_METRICS_OPTIONAL = [
    "nutanix.cpu.capacity_hz",
    "nutanix.cpu.usage_hz",
    "nutanix.memory.capacity_bytes",
    "nutanix.overall.memory.usage_bytes",
    "nutanix.overall.savings_bytes",
    "nutanix.overall.savings_ratio",
    "nutanix.power.consumption.instant_watt",
    "nutanix.recycle.bin.usage_bytes",
    "nutanix.snapshot.capacity_bytes",
]
