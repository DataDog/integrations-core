# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

CLUSTER_STATS_METRICS_REQUIRED = [
    "nutanix.cluster.aggregate_hypervisor.memory.usage_ppm",
    "nutanix.cluster.controller.avg.io.latency.usecs",
    "nutanix.cluster.controller.avg.read.io.latency.usecs",
    "nutanix.cluster.controller.avg.write.io.latency.usecs",
    "nutanix.cluster.controller.num.iops",
    "nutanix.cluster.controller.num.read.iops",
    "nutanix.cluster.controller.num.write.iops",
    "nutanix.cluster.controller.read.io.bandwidth.kbps",
    "nutanix.cluster.controller.write.io.bandwidth.kbps",
    "nutanix.cluster.free.physical.storage_bytes",
    "nutanix.cluster.health.check_score",
    "nutanix.cluster.hypervisor.cpu.usage_ppm",
    "nutanix.cluster.io.bandwidth.kbps",
    "nutanix.cluster.logical.storage.usage_bytes",
    "nutanix.cluster.storage.capacity_bytes",
    "nutanix.cluster.storage.usage_bytes",
]

CLUSTER_STATS_METRICS_OPTIONAL = [
    "nutanix.cluster.cpu.capacity_hz",
    "nutanix.cluster.cpu.usage_hz",
    "nutanix.cluster.memory.capacity_bytes",
    "nutanix.cluster.overall.memory.usage_bytes",
    "nutanix.cluster.overall.savings_bytes",
    "nutanix.cluster.overall.savings_ratio",
    "nutanix.cluster.power.consumption.instant_watt",
    "nutanix.cluster.recycle.bin.usage_bytes",
    "nutanix.cluster.snapshot.capacity_bytes",
]

HOST_STATS_METRICS_REQUIRED = [
    "nutanix.host.aggregate_hypervisor.memory.usage_ppm",
    "nutanix.host.controller.avg.io.latency.usecs",
    "nutanix.host.controller.avg.read.io.latency.usecs",
    "nutanix.host.controller.avg.write.io.latency.usecs",
    "nutanix.host.controller.num.iops",
    "nutanix.host.controller.num.read.iops",
    "nutanix.host.controller.num.write.iops",
    "nutanix.host.controller.read.io.bandwidth.kbps",
    "nutanix.host.controller.write.io.bandwidth.kbps",
    "nutanix.host.cpu.capacity_hz",
    "nutanix.host.free.physical.storage_bytes",
    "nutanix.host.health.check_score",
    "nutanix.host.hypervisor.cpu.usage_ppm",
    "nutanix.host.io.bandwidth.kbps",
    "nutanix.host.logical.storage.usage_bytes",
    "nutanix.host.memory.capacity_bytes",
    "nutanix.host.storage.capacity_bytes",
    "nutanix.host.storage.usage_bytes",
]

HOST_STATS_METRICS_OPTIONAL = [
    "nutanix.host.cpu.usage_hz",
    "nutanix.host.overall.memory.usage_bytes",
    "nutanix.host.overall.memory.usage_ppm",
    "nutanix.host.power.consumption.instant_watt",
]
