# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

HEALTH_METRICS = ["nutanix.health.up"]

CLUSTER_STATS_METRICS_REQUIRED = [
    "nutanix.cluster.aggregate_hypervisor.memory_usage",
    "nutanix.cluster.controller.avg_io_latency",
    "nutanix.cluster.controller.avg_read_io_latency",
    "nutanix.cluster.controller.avg_write_io_latency",
    "nutanix.cluster.controller.num_iops",
    "nutanix.cluster.controller.num_read_iops",
    "nutanix.cluster.controller.num_write_iops",
    "nutanix.cluster.controller.read_io_bandwidth",
    "nutanix.cluster.controller.write_io_bandwidth",
    "nutanix.cluster.free_physical_storage",
    "nutanix.cluster.health_check_score",
    "nutanix.cluster.hypervisor.cpu_usage",
    "nutanix.cluster.io_bandwidth",
    "nutanix.cluster.logical_storage_usage",
    "nutanix.cluster.storage_capacity",
    "nutanix.cluster.storage_usage",
]

CLUSTER_STATS_METRICS_OPTIONAL = [
    "nutanix.cluster.cpu_capacity",
    "nutanix.cluster.cpu_usage",
    "nutanix.cluster.memory_capacity",
    "nutanix.cluster.overall_memory_usage",
    "nutanix.cluster.overall_savings",
    "nutanix.cluster.overall_savings_ratio",
    "nutanix.cluster.power_consumption_instant_watt",
    "nutanix.cluster.recycle_bin_usage",
    "nutanix.cluster.snapshot_capacity",
]

HOST_STATS_METRICS_REQUIRED = [
    "nutanix.host.aggregate_hypervisor.memory_usage",
    "nutanix.host.controller.avg_io_latency",
    "nutanix.host.controller.avg_read_io_latency",
    "nutanix.host.controller.avg_write_io_latency",
    "nutanix.host.controller.num_iops",
    "nutanix.host.controller.num_read_iops",
    "nutanix.host.controller.num_write_iops",
    "nutanix.host.controller.read_io_bandwidth",
    "nutanix.host.controller.write_io_bandwidth",
    "nutanix.host.cpu_capacity",
    "nutanix.host.free_physical_storage",
    "nutanix.host.health_check_score",
    "nutanix.host.hypervisor.cpu_usage",
    "nutanix.host.io_bandwidth",
    "nutanix.host.logical_storage_usage",
    "nutanix.host.memory_capacity",
    "nutanix.host.storage_capacity",
    "nutanix.host.storage_usage",
]

HOST_STATS_METRICS_OPTIONAL = [
    "nutanix.host.cpu_usage",
    "nutanix.host.overall_memory_usage",
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
    "nutanix.vm.guest_memory_usage_ppm",
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
    "nutanix.vm.memory_usage_ppm",
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
    "nutanix.vm.frame_buffer_usage_ppm",
    "nutanix.vm.gpu_usage_ppm",
    "nutanix.vm.hypervisor.memory_balloon_reclaim_target_bytes",
    "nutanix.vm.hypervisor.memory_balloon_reclaimed_bytes",
    "nutanix.vm.hypervisor.swap_in_rate_kbps",
    "nutanix.vm.hypervisor.swap_out_rate_kbps",
    "nutanix.vm.memory_usage_bytes",
    "nutanix.vm.disk_capacity_bytes",
    "nutanix.vm.disk_usage_ppm",
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
