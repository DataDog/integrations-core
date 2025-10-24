# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


CLUSTER_STATS_METRICS = {
    "aggregateHypervisorMemoryUsagePpm": "cluster.aggregate_hypervisor.memory.usage",  # ppm
    "controllerAvgIoLatencyUsecs": "cluster.controller.avg.io.latency",  # usecs
    "controllerAvgReadIoLatencyUsecs": "cluster.controller.avg.read.io.latency",  # usecs
    "controllerAvgWriteIoLatencyUsecs": "cluster.controller.avg.write.io.latency",  # usecs
    "controllerNumIops": "cluster.controller.num.iops",
    "controllerNumReadIops": "cluster.controller.num.read.iops",
    "controllerNumWriteIops": "cluster.controller.num.write.iops",
    "controllerReadIoBandwidthKbps": "cluster.controller.read.io.bandwidth",  # kbps
    "controllerWriteIoBandwidthKbps": "cluster.controller.write.io.bandwidth",  # kbps
    "cpuCapacityHz": "cluster.cpu.capacity",  # hz
    "cpuUsageHz": "cluster.cpu.usage",  # hz
    "freePhysicalStorageBytes": "cluster.free.physical_storage",  # bytes
    "healthCheckScore": "cluster.health.check_score",
    "hypervisorCpuUsagePpm": "cluster.hypervisor.cpu.usage",  # ppm
    "ioBandwidthKbps": "cluster.io.bandwidth",  # kbps
    "logicalStorageUsageBytes": "cluster.logical.storage.usage",  # bytes
    "memoryCapacityBytes": "cluster.memory.capacity",  # bytes
    "overallMemoryUsageBytes": "cluster.overall.memory.usage",  # bytes
    "overallSavingsBytes": "cluster.overall.savings",  # bytes
    "overallSavingsRatio": "cluster.overall.savings_ratio",
    "powerConsumptionInstantWatt": "cluster.power_consumption_instant_watt",
    "recycleBinUsageBytes": "cluster.recycle_bin.usage",  # bytes
    "snapshotCapacityBytes": "cluster.snapshot.capacity",  # bytes
    "storageCapacityBytes": "cluster.storage.capacity",  # bytes
    "storageUsageBytes": "cluster.storage.usage",  # bytes
}

HOST_STATS_METRICS = {
    "aggregateHypervisorMemoryUsagePpm": "host.aggregate_hypervisor.memory.usage",  # ppm
    "controllerAvgIoLatencyUsecs": "host.controller.avg.io.latency",  # usecs
    "controllerAvgReadIoLatencyUsecs": "host.controller.avg.read.io.latency",  # usecs
    "controllerAvgWriteIoLatencyUsecs": "host.controller.avg.write.io.latency",  # usecs
    "controllerNumIops": "host.controller.num.iops",
    "controllerNumReadIops": "host.controller.num.read.iops",
    "controllerNumWriteIops": "host.controller.num.write.iops",
    "controllerReadIoBandwidthKbps": "host.controller.read.io.bandwidth",  # kbps
    "controllerWriteIoBandwidthKbps": "host.controller.write.io.bandwidth",  # kbps
    "cpuCapacityHz": "host.cpu.capacity",  # hz
    "cpuUsageHz": "host.cpu.usage",  # hz
    "freePhysicalStorageBytes": "host.free.physical_storage",  # bytes
    "healthCheckScore": "host.health.check_score",
    "hypervisorCpuUsagePpm": "host.hypervisor.cpu.usage",  # ppm
    "ioBandwidthKbps": "host.io.bandwidth",  # kbps
    "logicalStorageUsageBytes": "host.logical.storage.usage",  # bytes
    "memoryCapacityBytes": "host.memory.capacity",  # bytes
    "overallMemoryUsageBytes": "host.overall.memory.usage",  # bytes
    # "overallMemoryUsagePpm": "host.overall.memory.usage", # ppm
    "powerConsumptionInstantWatt": "host.power.consumption.instant_watt",
    "storageCapacityBytes": "host.storage.capacity",  # bytes
    "storageUsageBytes": "host.storage.usage",  # bytes
}
