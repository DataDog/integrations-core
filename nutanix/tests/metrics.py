# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

CLUSTER_STATS_METRICS_REQUIRED = [
    "nutanix.cluster.aggregate_hypervisor.memory.usage",
    "nutanix.cluster.controller.avg.io.latency",
    "nutanix.cluster.controller.avg.read.io.latency",
    "nutanix.cluster.controller.avg.write.io.latency",
    "nutanix.cluster.controller.num.iops",
    "nutanix.cluster.controller.num.read.iops",
    "nutanix.cluster.controller.num.write.iops",
    "nutanix.cluster.controller.read.io.bandwidth",
    "nutanix.cluster.controller.write.io.bandwidth",
    "nutanix.cluster.free.physical_storage",
    "nutanix.cluster.health.check_score",
    "nutanix.cluster.hypervisor.cpu.usage",
    "nutanix.cluster.io.bandwidth",
    "nutanix.cluster.logical.storage.usage",
    "nutanix.cluster.storage.capacity",
    "nutanix.cluster.storage.usage",
]

CLUSTER_STATS_METRICS_OPTIONAL = [
    "nutanix.cluster.cpu.capacity",
    "nutanix.cluster.cpu.usage",
    "nutanix.cluster.memory.capacity",
    "nutanix.cluster.overall.memory.usage",
    "nutanix.cluster.overall.savings",
    "nutanix.cluster.overall.savings_ratio",
    "nutanix.cluster.power_consumption_instant_watt",
    "nutanix.cluster.recycle_bin.usage",
    "nutanix.cluster.snapshot.capacity",
]

HOST_STATS_METRICS_REQUIRED = [
    "nutanix.host.aggregate_hypervisor.memory.usage",
    "nutanix.host.controller.avg.io.latency",
    "nutanix.host.controller.avg.read.io.latency",
    "nutanix.host.controller.avg.write.io.latency",
    "nutanix.host.controller.num.iops",
    "nutanix.host.controller.num.read.iops",
    "nutanix.host.controller.num.write.iops",
    "nutanix.host.controller.read.io.bandwidth",
    "nutanix.host.controller.write.io.bandwidth",
    "nutanix.host.cpu.capacity",
    "nutanix.host.free.physical_storage",
    "nutanix.host.health.check_score",
    "nutanix.host.hypervisor.cpu.usage",
    "nutanix.host.io.bandwidth",
    "nutanix.host.logical.storage.usage",
    "nutanix.host.memory.capacity",
    "nutanix.host.storage.capacity",
    "nutanix.host.storage.usage",
]

HOST_STATS_METRICS_OPTIONAL = [
    "nutanix.host.cpu.usage",
    "nutanix.host.overall.memory.usage",
    "nutanix.host.power.consumption.instant_watt",
]
