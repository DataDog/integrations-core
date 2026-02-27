# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


CLUSTER_STATS_METRICS = {
    "aggregateHypervisorMemoryUsagePpm": "cluster.aggregate_hypervisor.memory_usage",  # ppm
    "controllerAvgIoLatencyUsecs": "cluster.controller.avg_io_latency",  # usecs
    "controllerAvgReadIoLatencyUsecs": "cluster.controller.avg_read_io_latency",  # usecs
    "controllerAvgWriteIoLatencyUsecs": "cluster.controller.avg_write_io_latency",  # usecs
    "controllerNumIops": "cluster.controller.num_iops",
    "controllerNumReadIops": "cluster.controller.num_read_iops",
    "controllerNumWriteIops": "cluster.controller.num_write_iops",
    "controllerReadIoBandwidthKbps": "cluster.controller.read_io_bandwidth",  # kbps
    "controllerWriteIoBandwidthKbps": "cluster.controller.write_io_bandwidth",  # kbps
    "cpuCapacityHz": "cluster.cpu_capacity",  # hz
    "cpuUsageHz": "cluster.cpu_usage",  # hz
    "freePhysicalStorageBytes": "cluster.free_physical_storage",  # bytes
    "healthCheckScore": "cluster.health_check_score",
    "hypervisorCpuUsagePpm": "cluster.hypervisor.cpu_usage",  # ppm
    "ioBandwidthKbps": "cluster.io_bandwidth",  # kbps
    "logicalStorageUsageBytes": "cluster.logical_storage_usage",  # bytes
    "memoryCapacityBytes": "cluster.memory_capacity",  # bytes
    "overallMemoryUsageBytes": "cluster.overall_memory_usage",  # bytes
    "overallSavingsBytes": "cluster.overall_savings",  # bytes
    "overallSavingsRatio": "cluster.overall_savings_ratio",
    "powerConsumptionInstantWatt": "cluster.power_consumption_instant_watt",
    "recycleBinUsageBytes": "cluster.recycle_bin_usage",  # bytes
    "snapshotCapacityBytes": "cluster.snapshot_capacity",  # bytes
    "storageCapacityBytes": "cluster.storage_capacity",  # bytes
    "storageUsageBytes": "cluster.storage_usage",  # bytes
}

HOST_STATS_METRICS = {
    "aggregateHypervisorMemoryUsagePpm": "host.aggregate_hypervisor.memory_usage",  # ppm
    "controllerAvgIoLatencyUsecs": "host.controller.avg_io_latency",  # usecs
    "controllerAvgReadIoLatencyUsecs": "host.controller.avg_read_io_latency",  # usecs
    "controllerAvgWriteIoLatencyUsecs": "host.controller.avg_write_io_latency",  # usecs
    "controllerNumIops": "host.controller.num_iops",
    "controllerNumReadIops": "host.controller.num_read_iops",
    "controllerNumWriteIops": "host.controller.num_write_iops",
    "controllerReadIoBandwidthKbps": "host.controller.read_io_bandwidth",  # kbps
    "controllerWriteIoBandwidthKbps": "host.controller.write_io_bandwidth",  # kbps
    "cpuCapacityHz": "host.cpu_capacity",  # hz
    "cpuUsageHz": "host.cpu_usage",  # hz
    "freePhysicalStorageBytes": "host.free_physical_storage",  # bytes
    "healthCheckScore": "host.health_check_score",
    "hypervisorCpuUsagePpm": "host.hypervisor.cpu_usage",  # ppm
    "ioBandwidthKbps": "host.io_bandwidth",  # kbps
    "logicalStorageUsageBytes": "host.logical_storage_usage",  # bytes
    "memoryCapacityBytes": "host.memory_capacity",  # bytes
    "overallMemoryUsageBytes": "host.overall_memory_usage",  # bytes
    # "overallMemoryUsagePpm": "host.overall_memory_usage", # ppm
    "powerConsumptionInstantWatt": "host.power.consumption.instant_watt",
    "storageCapacityBytes": "host.storage_capacity",  # bytes
    "storageUsageBytes": "host.storage_usage",  # bytes
}

VM_STATS_METRICS = {
    "checkScore": "vm.check_score",
    "controllerAvgIoLatencyMicros": "vm.controller.avg_io_latency_micros",
    "controllerAvgReadIoLatencyMicros": "vm.controller.avg_read_io_latency_micros",
    "controllerAvgReadIoSizeKb": "vm.controller.avg_read_io_size_kb",
    "controllerAvgWriteIoLatencyMicros": "vm.controller.avg_write_io_latency_micros",
    "controllerAvgWriteIoSizeKb": "vm.controller.avg_write_io_size_kb",
    "controllerIoBandwidthKbps": "vm.controller.io_bandwidth_kbps",
    "controllerNumIo": "vm.controller.num_io",
    "controllerNumIops": "vm.controller.num_iops",
    "controllerNumRandomIo": "vm.controller.num_random_io",
    "controllerNumReadIo": "vm.controller.num_read_io",
    "controllerNumReadIops": "vm.controller.num_read_iops",
    "controllerNumSeqIo": "vm.controller.num_seq_io",
    "controllerNumWriteIo": "vm.controller.num_write_io",
    "controllerNumWriteIops": "vm.controller.num_write_iops",
    "controllerOplogDrainDestHddBytes": "vm.controller.oplog_drain_dest_hdd_bytes",
    "controllerOplogDrainDestSsdBytes": "vm.controller.oplog_drain_dest_ssd_bytes",
    "controllerRandomIoPpm": "vm.controller.random_io_ppm",
    "controllerReadIoBandwidthKbps": "vm.controller.read_io_bandwidth_kbps",
    "controllerReadIoPpm": "vm.controller.read_io_ppm",
    "controllerReadSourceEstoreHddLocalBytes": "vm.controller.read_source_estore_hdd_local_bytes",
    "controllerReadSourceEstoreHddRemoteBytes": "vm.controller.read_source_estore_hdd_remote_bytes",
    "controllerReadSourceEstoreSsdLocalBytes": "vm.controller.read_source_estore_ssd_local_bytes",
    "controllerReadSourceEstoreSsdRemoteBytes": "vm.controller.read_source_estore_ssd_remote_bytes",
    "controllerReadSourceOplogBytes": "vm.controller.read_source_oplog_bytes",
    "controllerSeqIoPpm": "vm.controller.seq_io_ppm",
    "controllerSharedUsageBytes": "vm.controller.shared_usage_bytes",
    "controllerSnapshotUsageBytes": "vm.controller.snapshot_usage_bytes",
    "controllerStorageTierSsdUsageBytes": "vm.controller.storage_tier_ssd_usage_bytes",
    "controllerTimespanMicros": "vm.controller.timespan_micros",
    "controllerTotalIoSizeKb": "vm.controller.total_io_size_kb",
    "controllerTotalIoTimeMicros": "vm.controller.total_io_time_micros",
    "controllerTotalReadIoSizeKb": "vm.controller.total_read_io_size_kb",
    "controllerTotalReadIoTimeMicros": "vm.controller.total_read_io_time_micros",
    "controllerTotalTransformedUsageBytes": "vm.controller.total_transformed_usage_bytes",
    "controllerUserBytes": "vm.controller.user_bytes",
    "controllerWriteDestEstoreHddBytes": "vm.controller.write_dest_estore_hdd_bytes",
    "controllerWriteDestEstoreSsdBytes": "vm.controller.write_dest_estore_ssd_bytes",
    "controllerWriteIoBandwidthKbps": "vm.controller.write_io_bandwidth_kbps",
    "controllerWriteIoPpm": "vm.controller.write_io_ppm",
    "controllerWss120SecondReadMb": "vm.controller.wss120second_read_mb",
    "controllerWss120SecondUnionMb": "vm.controller.wss120second_union_mb",
    "controllerWss120SecondWriteMb": "vm.controller.wss120second_write_mb",
    "controllerWss3600SecondReadMb": "vm.controller.wss3600second_read_mb",
    "controllerWss3600SecondUnionMb": "vm.controller.wss3600second_union_mb",
    "controllerWss3600SecondWriteMb": "vm.controller.wss3600second_write_mb",
    "diskCapacityBytes": "vm.disk_capacity_bytes",
    "diskUsagePpm": "vm.disk_usage_ppm",
    "frameBufferUsagePpm": "vm.frame_buffer_usage_ppm",
    "gpuUsagePpm": "vm.gpu_usage_ppm",
    "guestMemoryUsagePpm": "vm.guest_memory_usage_ppm",
    "hypervisorAvgIoLatencyMicros": "vm.hypervisor.avg_io_latency_micros",
    "hypervisorCpuReadyTimePpm": "vm.hypervisor.cpu_ready_time_ppm",
    "hypervisorCpuUsagePpm": "vm.hypervisor.cpu_usage_ppm",
    "hypervisorIoBandwidthKbps": "vm.hypervisor.io_bandwidth_kbps",
    "hypervisorMemoryBalloonReclaimTargetBytes": "vm.hypervisor.memory_balloon_reclaim_target_bytes",
    "hypervisorMemoryBalloonReclaimedBytes": "vm.hypervisor.memory_balloon_reclaimed_bytes",
    "hypervisorMemoryUsagePpm": "vm.hypervisor.memory_usage_ppm",
    "hypervisorNumIo": "vm.hypervisor.num_io",
    "hypervisorNumIops": "vm.hypervisor.num_iops",
    "hypervisorNumReadIo": "vm.hypervisor.num_read_io",
    "hypervisorNumReadIops": "vm.hypervisor.num_read_iops",
    "hypervisorNumReceivePacketsDropped": "vm.hypervisor.num_receive_packets_dropped",
    "hypervisorNumReceivedBytes": "vm.hypervisor.num_received_bytes",
    "hypervisorNumTransmitPacketsDropped": "vm.hypervisor.num_transmit_packets_dropped",
    "hypervisorNumTransmittedBytes": "vm.hypervisor.num_transmitted_bytes",
    "hypervisorNumWriteIo": "vm.hypervisor.num_write_io",
    "hypervisorNumWriteIops": "vm.hypervisor.num_write_iops",
    "hypervisorReadIoBandwidthKbps": "vm.hypervisor.read_io_bandwidth_kbps",
    "hypervisorSwapInRateKbps": "vm.hypervisor.swap_in_rate_kbps",
    "hypervisorSwapOutRateKbps": "vm.hypervisor.swap_out_rate_kbps",
    "hypervisorTimespanMicros": "vm.hypervisor.timespan_micros",
    "hypervisorTotalIoSizeKb": "vm.hypervisor.total_io_size_kb",
    "hypervisorTotalIoTimeMicros": "vm.hypervisor.total_io_time_micros",
    "hypervisorTotalReadIoSizeKb": "vm.hypervisor.total_read_io_size_kb",
    "hypervisorVmRunningTimeUsecs": "vm.hypervisor.vm_running_time_usecs",
    "hypervisorWriteIoBandwidthKbps": "vm.hypervisor.write_io_bandwidth_kbps",
    "memoryUsageBytes": "vm.memory_usage_bytes",
    "memoryUsagePpm": "vm.memory_usage_ppm",
    "numVcpusUsedPpm": "vm.num_vcpus_used_ppm",
}
