# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base import AgentCheck

HYPERVISOR_SERVICE_CHECK = {'up': AgentCheck.OK, 'down': AgentCheck.CRITICAL}

KEYSTONE_SERVICE_CHECK = "openstack.keystone.api.up"

NOVA_SERVICE_CHECK = "openstack.nova.api.up"
NOVA_LIMITS_METRICS_PREFIX = "openstack.nova.limits"
NOVA_LIMITS_METRICS = {
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_total_instances": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_total_cores": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_total_ram_size": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_server_meta": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_image_meta": {"max_version": "2.38"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_personality": {"max_version": "2.56"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_personality_size": {"max_version": "2.56"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_total_keypairs": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_server_groups": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_server_group_members": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_total_floating_ips": {"max_version": "2.35"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_security_groups": {"max_version": "2.35"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.max_security_group_rules": {"max_version": "2.35"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.total_ram_used": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.total_cores_used": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.total_instances_used": {},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.total_floating_ips_used": {"max_version": "2.35"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.total_security_groups_used": {"max_version": "2.35"},
    f"{NOVA_LIMITS_METRICS_PREFIX}.absolute.total_server_groups_used": {},
}

NOVA_QUOTA_SETS_METRICS_PREFIX = "openstack.nova.quota_set"
NOVA_QUOTA_SETS_METRICS = {
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.cores": {},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.fixed_ips": {"max_version": "2.35"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.floating_ips": {"max_version": "2.35"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.injected_file_content_bytes": {"max_version": "2.56"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.injected_file_path_bytes": {"max_version": "2.56"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.injected_files": {"max_version": "2.56"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.instances": {},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.key_pairs": {},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.metadata_items": {},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.ram": {},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.security_group_rules": {"max_version": "2.35"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.security_groups": {"max_version": "2.35"},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.server_group_members": {},
    f"{NOVA_QUOTA_SETS_METRICS_PREFIX}.server_groups": {},
}

NOVA_SERVER_METRICS_PREFIX = "openstack.nova.server"
NOVA_SERVER_METRICS = {
    f"{NOVA_SERVER_METRICS_PREFIX}.count": {},
    f"{NOVA_SERVER_METRICS_PREFIX}.active": {"optional": True},
    f"{NOVA_SERVER_METRICS_PREFIX}.error": {"optional": True},
    f"{NOVA_SERVER_METRICS_PREFIX}.cpu0_time": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.vda_read_req": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.vda_read": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.vda_write_req": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.vda_write": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.vda_errors": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_actual": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_swap_in": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_swap_out": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_major_fault": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_minor_fault": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_unused": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_available": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_usable": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_last_update": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_disk_caches": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_hugetlb_pgalloc": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_hugetlb_pgfail": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.memory_rss": {"max_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.vcpus": {},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.ram": {},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.disk": {},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.os_flv_ext_data:ephemeral": {"optional": True},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.ephemeral": {"min_version": "2.47"},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.swap": {"optional": True},
    f"{NOVA_SERVER_METRICS_PREFIX}.flavor.rxtx_factor": {"optional": True},
    f"{NOVA_SERVER_METRICS_PREFIX}.disk_details.read_bytes": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.disk_details.read_requests": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.disk_details.write_bytes": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.disk_details.write_requests": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.disk_details.errors_count": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.cpu_details.id": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.cpu_details.time": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.cpu_details.utilisation": {"min_version": "2.48", "optional": True},
    f"{NOVA_SERVER_METRICS_PREFIX}.uptime": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.num_cpus": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.num_nics": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.num_disks": {"min_version": "2.48"},
}

NOVA_FLAVOR_METRICS = [
    'openstack.nova.flavor.ram',
    'openstack.nova.flavor.disk',
    'openstack.nova.flavor.swap',
    'openstack.nova.flavor.os_flv_ext_data:ephemeral',
    'openstack.nova.flavor.vcpus',
    'openstack.nova.flavor.rxtx_factor',
]

NOVA_HYPERVISOR_METRICS = [
    'openstack.nova.hypervisor.current_workload',  # Available until version 2.87
    'openstack.nova.hypervisor.disk_available_least',  # Available until version 2.87
    'openstack.nova.hypervisor.free_disk_gb',  # Available until version 2.87
    'openstack.nova.hypervisor.free_ram_mb',  # Available until version 2.87
    'openstack.nova.hypervisor.local_gb',  # Available until version 2.87
    'openstack.nova.hypervisor.local_gb_used',  # Available until version 2.87
    'openstack.nova.hypervisor.memory_mb',  # Available until version 2.87
    'openstack.nova.hypervisor.memory_mb_used',  # Available until version 2.87
    'openstack.nova.hypervisor.running_vms',  # Available until version 2.87
    'openstack.nova.hypervisor.vcpus',  # Available until version 2.87
    'openstack.nova.hypervisor.vcpus_used',  # Available until version 2.87
    'openstack.nova.hypervisor.up',
]

NOVA_HYPERVISOR_LOAD_METRICS = [
    'openstack.nova.hypervisor.load_1',
    'openstack.nova.hypervisor.load_5',
    'openstack.nova.hypervisor.load_15',
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

NEUTRON_QUOTAS_METRICS_PREFIX = "openstack.neutron.quotas"
NEUTRON_QUOTAS_METRICS = [
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.floatingip",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.network",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.port",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.rbac_policy",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.router",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.security_group",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.security_group_rule",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.subnet",
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.subnetpool",
]

NEUTRON_AGENTS_METRICS_PREFIX = "openstack.neutron.agents"
NEUTRON_AGENTS_METRICS = [
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.count",
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.alive",
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.admin_state_up",
]


def get_normalized_key(key):
    return re.sub(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower().replace("-", "_")


def get_normalized_metrics(log, metrics, parent=None):
    normalized_metrics = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            log.debug("get_normalized_metrics: %s", key)
            normalized_metrics[f'{parent}.{get_normalized_key(key)}' if parent else get_normalized_key(key)] = value
        elif isinstance(value, bool):
            normalized_metrics[f'{parent}.{get_normalized_key(key)}' if parent else get_normalized_key(key)] = (
                1 if value else 0
            )
        elif isinstance(value, dict):
            normalized_metrics.update(get_normalized_metrics(log, value, get_normalized_key(key)))
    return normalized_metrics
