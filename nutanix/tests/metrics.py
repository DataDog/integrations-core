# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

HEALTH_METRICS = ["nutanix.health.up"]

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
    "nutanix.cluster.health_check_score",
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
    "nutanix.host.health_check_score",
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

VM_STATS_METRICS_REQUIRED = [
    "nutanix.vm.controller.avg_io_latency_micros",
    "nutanix.vm.controller.avg_read_io_latency_micros",
    "nutanix.vm.controller.avg_read_io_size_kb",
    "nutanix.vm.controller.avg_write_io_latency_micros",
    "nutanix.vm.controller.avg_write_io_size_kb",
    "nutanix.vm.controller.io_bandwidth_kbps",
    "nutanix.vm.controller.num_io",
    "nutanix.vm.controller.num_iops",
    "nutanix.vm.controller.num_read_io",
    "nutanix.vm.controller.num_read_iops",
    "nutanix.vm.controller.num_write_io",
    "nutanix.vm.controller.num_write_iops",
    "nutanix.vm.controller.oplog_drain_dest_hdd_bytes",
    "nutanix.vm.controller.oplog_drain_dest_ssd_bytes",
    "nutanix.vm.controller.read_io_bandwidth_kbps",
    "nutanix.vm.controller.read_io_ppm",
    "nutanix.vm.controller.read_source_estore_hdd_local_bytes",
    "nutanix.vm.controller.read_source_estore_hdd_remote_bytes",
    "nutanix.vm.controller.read_source_estore_ssd_local_bytes",
    "nutanix.vm.controller.read_source_estore_ssd_remote_bytes",
    "nutanix.vm.controller.read_source_oplog_bytes",
    "nutanix.vm.controller.storage_tier_ssd_usage_bytes",
    "nutanix.vm.controller.timespan_micros",
    "nutanix.vm.controller.total_io_size_kb",
    "nutanix.vm.controller.total_io_time_micros",
    "nutanix.vm.controller.total_read_io_size_kb",
    "nutanix.vm.controller.total_read_io_time_micros",
    "nutanix.vm.controller.total_transformed_usage_bytes",
    "nutanix.vm.controller.user_bytes",
    "nutanix.vm.controller.write_dest_estore_hdd_bytes",
    "nutanix.vm.controller.write_dest_estore_ssd_bytes",
    "nutanix.vm.controller.write_io_bandwidth_kbps",
    "nutanix.vm.controller.write_io_ppm",
    "nutanix.vm.controller.wss120second_read_mb",
    "nutanix.vm.controller.wss120second_union_mb",
    "nutanix.vm.controller.wss120second_write_mb",
    "nutanix.vm.controller.wss3600second_read_mb",
    "nutanix.vm.controller.wss3600second_union_mb",
    "nutanix.vm.controller.wss3600second_write_mb",
    "nutanix.vm.guest.memory_usage_ppm",
    "nutanix.vm.hypervisor.avg_io_latency_micros",
    "nutanix.vm.hypervisor.cpu_ready_time_ppm",
    "nutanix.vm.hypervisor.cpu_usage_ppm",
    "nutanix.vm.hypervisor.io_bandwidth_kbps",
    "nutanix.vm.hypervisor.memory_usage_ppm",
    "nutanix.vm.hypervisor.num_io",
    "nutanix.vm.hypervisor.num_iops",
    "nutanix.vm.hypervisor.num_read_io",
    "nutanix.vm.hypervisor.num_read_iops",
    "nutanix.vm.hypervisor.num_receive_packets_dropped",
    "nutanix.vm.hypervisor.num_received_bytes",
    "nutanix.vm.hypervisor.num_transmit_packets_dropped",
    "nutanix.vm.hypervisor.num_transmitted_bytes",
    "nutanix.vm.hypervisor.num_write_io",
    "nutanix.vm.hypervisor.num_write_iops",
    "nutanix.vm.hypervisor.read_io_bandwidth_kbps",
    "nutanix.vm.hypervisor.timespan_micros",
    "nutanix.vm.hypervisor.total_io_size_kb",
    "nutanix.vm.hypervisor.total_io_time_micros",
    "nutanix.vm.hypervisor.total_read_io_size_kb",
    "nutanix.vm.hypervisor.write_io_bandwidth_kbps",
    "nutanix.vm.memory.usage_ppm",
    "nutanix.vm.num_vcpus_used_ppm",
]

VM_STATS_METRICS_OPTIONAL = [
    "nutanix.vm.check_score",
    "nutanix.vm.controller.num_random_io",
    "nutanix.vm.controller.num_seq_io",
    "nutanix.vm.controller.random_io_ppm",
    "nutanix.vm.controller.seq_io_ppm",
    "nutanix.vm.controller.shared_usage_bytes",
    "nutanix.vm.controller.snapshot_usage_bytes",
    "nutanix.vm.frame.buffer_usage_ppm",
    "nutanix.vm.gpu.usage_ppm",
    "nutanix.vm.hypervisor.memory_balloon_reclaim_target_bytes",
    "nutanix.vm.hypervisor.memory_balloon_reclaimed_bytes",
    "nutanix.vm.hypervisor.swap_in_rate_kbps",
    "nutanix.vm.hypervisor.swap_out_rate_kbps",
    "nutanix.vm.memory.usage_bytes",
    "nutanix.vm.disk.capacity_bytes",
    "nutanix.vm.disk.usage_ppm",
    "nutanix.vm.hypervisor.vm_running_time_usecs",
]

CLUSTER_BASIC_METRICS = [
    "nutanix.cluster.count",
    "nutanix.cluster.nbr_nodes",
    "nutanix.cluster.vm.count",
    "nutanix.cluster.vm.inefficient_count",
]

HOST_BASIC_METRICS = [
    "nutanix.host.count",
]

VM_BASIC_METRICS = [
    "nutanix.vm.count",
]

ALL_METRICS = (
    HEALTH_METRICS
    + CLUSTER_BASIC_METRICS
    + CLUSTER_STATS_METRICS_REQUIRED
    + CLUSTER_STATS_METRICS_OPTIONAL
    + HOST_BASIC_METRICS
    + HOST_STATS_METRICS_REQUIRED
    + HOST_STATS_METRICS_OPTIONAL
    + VM_BASIC_METRICS
    + VM_STATS_METRICS_REQUIRED
    + VM_STATS_METRICS_OPTIONAL
)
