# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

HYPERVISOR_SERVICE_CHECK = {'up': AgentCheck.OK, 'down': AgentCheck.CRITICAL}

KEYSTONE_SERVICE_CHECK = "openstack.keystone.api.up"

NOVA_SERVICE_CHECK = "openstack.nova.api.up"
NOVA_LIMITS_METRICS_PREFIX = "openstack.nova.limits"
NOVA_LIMITS_METRICS = [
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_total_instances",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_total_cores",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_total_ram_size",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_server_meta",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_image_meta",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_personality",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_personality_size",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_total_keypairs",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_server_groups",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_server_group_members",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_total_floating_ips",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_security_groups",
    f"{NOVA_LIMITS_METRICS_PREFIX}.max_security_group_rules",
    f"{NOVA_LIMITS_METRICS_PREFIX}.total_ram_used",
    f"{NOVA_LIMITS_METRICS_PREFIX}.total_cores_used",
    f"{NOVA_LIMITS_METRICS_PREFIX}.total_instances_used",
    f"{NOVA_LIMITS_METRICS_PREFIX}.total_floating_ips_used",
    f"{NOVA_LIMITS_METRICS_PREFIX}.total_security_groups_used",
    f"{NOVA_LIMITS_METRICS_PREFIX}.total_server_groups_used",
]

NOVA_QUOTA_SETS_METRICS_PREFIX = "openstack.nova.quota_set"
NOVA_QUOTA_SETS_METRICS = [
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.cores",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.fixed_ips",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.floating_ips",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.injected_file_content_bytes",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.injected_file_path_bytes",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.injected_files",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.instances",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.key_pairs",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.metadata_items",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.ram",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.security_group_rules",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.security_groups",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.server_group_members",
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.server_groups",
]

NOVA_SERVER_METRICS = [
    "openstack.nova.server.count",
    "openstack.nova.server.active",
    "openstack.nova.server.error",
    "openstack.nova.server.cpu0_time",
    "openstack.nova.server.vda_read_req",
    "openstack.nova.server.vda_read",
    "openstack.nova.server.vda_write_req",
    "openstack.nova.server.vda_write",
    "openstack.nova.server.vda_errors",
    "openstack.nova.server.memory",
    "openstack.nova.server.memory_actual",
    "openstack.nova.server.memory_swap_in",
    "openstack.nova.server.memory_swap_out",
    "openstack.nova.server.memory_major_fault",
    "openstack.nova.server.memory_minor_fault",
    "openstack.nova.server.memory_unused",
    "openstack.nova.server.memory_available",
    "openstack.nova.server.memory_usable",
    "openstack.nova.server.memory_last_update",
    "openstack.nova.server.memory_disk_caches",
    "openstack.nova.server.memory_hugetlb_pgalloc",
    "openstack.nova.server.memory_hugetlb_pgfail",
    "openstack.nova.server.memory_rss",
    "openstack.nova.server.flavor.vcpus",
    "openstack.nova.server.flavor.ram",
    "openstack.nova.server.flavor.disk",
    "openstack.nova.server.flavor.os_flv_ext_data:ephemeral",
    "openstack.nova.server.flavor.ephemeral",
    "openstack.nova.server.flavor.swap",
    "openstack.nova.server.flavor.rxtx_factor",
    "openstack.nova.server.disk_details.read_bytes",
    "openstack.nova.server.disk_details.read_requests",
    "openstack.nova.server.disk_details.write_bytes",
    "openstack.nova.server.disk_details.write_requests",
    "openstack.nova.server.disk_details.errors_count",
    "openstack.nova.server.cpu_details.id",
    "openstack.nova.server.cpu_details.time",
    "openstack.nova.server.cpu_details.utilisation",
    "openstack.nova.server.uptime",
    "openstack.nova.server.num_cpus",
    "openstack.nova.server.num_nics",
    "openstack.nova.server.num_disks",
]

NOVA_FLAVOR_METRICS = [
    'openstack.nova.flavor.ram',
    'openstack.nova.flavor.disk',
    'openstack.nova.flavor.swap',
    'openstack.nova.flavor.os_flv_ext_data:ephemeral',
    'openstack.nova.flavor.vcpus',
    'openstack.nova.flavor.rxtx_factor',
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
