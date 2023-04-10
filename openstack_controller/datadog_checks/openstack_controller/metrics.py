# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

HYPERVISOR_SERVICE_CHECK = {'up': AgentCheck.OK, 'down': AgentCheck.CRITICAL}

NOVA_LIMITS_METRICS = [
    "max_total_instances",
    "max_total_cores",
    "max_total_ram_size",
    "max_server_meta",
    "max_image_meta",
    "max_personality",
    "max_personality_size",
    "max_total_keypairs",
    "max_server_groups",
    "max_server_group_members",
    "max_total_floating_ips",
    "max_security_groups",
    "max_security_group_rules",
    "total_ram_used",
    "total_cores_used",
    "total_instances_used",
    "total_floating_ips_used",
    "total_security_groups_used",
    "total_server_groups_used",
]

NOVA_LATEST_LIMITS_METRICS = [
    "max_total_instances",
    "max_total_cores",
    "max_total_ram_size",
    "max_server_meta",
    "max_total_keypairs",
    "max_server_groups",
    "max_server_group_members",
    "total_ram_used",
    "total_cores_used",
    "total_instances_used",
    "total_server_groups_used",
]

NOVA_QUOTA_SETS_METRICS = [
    "cores",
    "fixed_ips",
    "floating_ips",
    "injected_file_content_bytes",
    "injected_file_path_bytes",
    "injected_files",
    "instances",
    "key_pairs",
    "metadata_items",
    "ram",
    "security_group_rules",
    "security_groups",
    "server_group_members",
    "server_groups",
]

NOVA_LATEST_QUOTA_SETS_METRICS = [
    "cores",
    "instances",
    "key_pairs",
    "metadata_items",
    "ram",
    "server_group_members",
    "server_groups",
]

NOVA_SERVER_METRICS = [
    "cpu0_time",
    "vda_read_req",
    "vda_read",
    "vda_write_req",
    "vda_write",
    "vda_errors",
    "memory",
    "memory_actual",
    "memory_swap_in",
    "memory_swap_out",
    "memory_major_fault",
    "memory_minor_fault",
    "memory_unused",
    "memory_available",
    "memory_usable",
    "memory_last_update",
    "memory_disk_caches",
    "memory_hugetlb_pgalloc",
    "memory_hugetlb_pgfail",
    "memory_rss",
]

NOVA_LATEST_SERVER_METRICS = [
    "uptime",
    "num_cpus",
    "num_nics",
    "num_disks",
]

NOVA_FLAVOR_METRICS = [
    'ram',
    'disk',
    'os_flv_ext_data:ephemeral',
    'vcpus',
    'rxtx_factor',
]

NOVA_SERVICE_METRICS = [
    'nova_compute',
    'nova_scheduler',
    'nova_conductor',
]

NOVA_HYPERVISOR_METRICS = [
    'current_workload',  # Available until version 2.87
    'disk_available_least',  # Available until version 2.87
    'free_disk_gb',  # Available until version 2.87
    'free_ram_mb',  # Available until version 2.87
    'local_gb',  # Available until version 2.87
    'local_gb_used',  # Available until version 2.87
    'memory_mb',  # Available until version 2.87
    'memory_mb_used',  # Available until version 2.87
    'running_vms',  # Available until version 2.87
    'vcpus',  # Available until version 2.87
    'vcpus_used',  # Available until version 2.87
]

NOVA_HYPERVISOR_LOAD_METRICS = [
    'load_1',
    'load_5',
    'load_15',
]

LEGACY_NOVA_HYPERVISOR_METRICS = [
    'current_workload',
    'disk_available_least',
    'free_disk_gb',
    'free_ram_mb',
    'local_gb',
    'local_gb_used',
    'memory_mb',
    'memory_mb_used',
    'running_vms',
    'vcpus',
    'vcpus_used',
]

LEGACY_NOVA_HYPERVISOR_LOAD_METRICS = {
    'load_1': 'hypervisor_load.1',
    'load_5': 'hypervisor_load.5',
    'load_15': 'hypervisor_load.15',
}
