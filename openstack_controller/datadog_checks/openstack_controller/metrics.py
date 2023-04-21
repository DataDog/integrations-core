# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from datadog_checks.base import AgentCheck

HYPERVISOR_SERVICE_CHECK = {'up': AgentCheck.OK, 'down': AgentCheck.CRITICAL}

KEYSTONE_SERVICE_CHECK = "openstack.keystone.api.up"

NOVA_SERVICE_CHECK = "openstack.nova.api.up"
NOVA_METRICS_PREFIX = "openstack.nova"

NOVA_LIMITS_METRICS = {
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_total_instances": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_total_cores": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_total_ram_size": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_server_meta": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_image_meta": {"max_version": "2.38"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_personality": {"max_version": "2.56"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_personality_size": {"max_version": "2.56"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_total_keypairs": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_server_groups": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_server_group_members": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_total_floating_ips": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_security_groups": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.max_security_group_rules": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.total_ram_used": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.total_cores_used": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.total_instances_used": {},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.total_floating_ips_used": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.total_security_groups_used": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.limits.absolute.total_server_groups_used": {},
}

NOVA_QUOTA_SETS_METRICS = {
    f"{NOVA_METRICS_PREFIX}.quota_set.cores": {},
    f"{NOVA_METRICS_PREFIX}.quota_set.fixed_ips": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.quota_set.floating_ips": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.quota_set.injected_file_content_bytes": {"max_version": "2.56"},
    f"{NOVA_METRICS_PREFIX}.quota_set.injected_file_path_bytes": {"max_version": "2.56"},
    f"{NOVA_METRICS_PREFIX}.quota_set.injected_files": {"max_version": "2.56"},
    f"{NOVA_METRICS_PREFIX}.quota_set.instances": {},
    f"{NOVA_METRICS_PREFIX}.quota_set.key_pairs": {},
    f"{NOVA_METRICS_PREFIX}.quota_set.metadata_items": {},
    f"{NOVA_METRICS_PREFIX}.quota_set.ram": {},
    f"{NOVA_METRICS_PREFIX}.quota_set.security_group_rules": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.quota_set.security_groups": {"max_version": "2.35"},
    f"{NOVA_METRICS_PREFIX}.quota_set.server_group_members": {},
    f"{NOVA_METRICS_PREFIX}.quota_set.server_groups": {},
}

NOVA_SERVER_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.server"
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
    f"{NOVA_SERVER_METRICS_PREFIX}.cpu_details.utilisation": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.rx_drop": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.rx_errors": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.rx_octets": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.rx_packets": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.rx_rate": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.tx_drop": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.tx_errors": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.tx_octets": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.tx_packets": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.nic_details.tx_rate": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.uptime": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.num_cpus": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.num_nics": {"min_version": "2.48"},
    f"{NOVA_SERVER_METRICS_PREFIX}.num_disks": {"min_version": "2.48"},
}

NOVA_FLAVOR_METRICS = {
    f"{NOVA_METRICS_PREFIX}.flavor.vcpus": {},
    f"{NOVA_METRICS_PREFIX}.flavor.ram": {},
    f"{NOVA_METRICS_PREFIX}.flavor.disk": {},
    f"{NOVA_METRICS_PREFIX}.flavor.os_flv_ext_data:ephemeral": {"optional": True},
    f"{NOVA_METRICS_PREFIX}.flavor.swap": {"optional": True},
    f"{NOVA_METRICS_PREFIX}.flavor.rxtx_factor": {"optional": True},
}

NOVA_HYPERVISOR_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.hypervisor"
NOVA_HYPERVISOR_SERVICE_CHECK = f"{NOVA_HYPERVISOR_METRICS_PREFIX}.up"
NOVA_HYPERVISOR_METRICS = {
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.current_workload": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.disk_available_least": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.free_disk_gb": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.free_ram_mb": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.local_gb": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.local_gb_used": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.memory_mb": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.memory_mb_used": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.running_vms": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.vcpus": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.vcpus_used": {"max_version": "2.87"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.up": {},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_1": {"min_version": "2.88"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_5": {"min_version": "2.88"},
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_15": {"min_version": "2.88"},
}

NEUTRON_METRICS_PREFIX = "openstack.nova"

NEUTRON_QUOTAS_METRICS_PREFIX = f"{NEUTRON_METRICS_PREFIX}.quotas"
NEUTRON_QUOTAS_METRICS = {
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.floatingip": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.network": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.port": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.rbac_policy": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.router": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.security_group": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.security_group_rule": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.subnet": {},
    f"{NEUTRON_QUOTAS_METRICS_PREFIX}.subnetpool": {},
}

NEUTRON_AGENTS_METRICS_PREFIX = f"{NEUTRON_METRICS_PREFIX}.agents"
NEUTRON_AGENTS_METRICS = {
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.count": {},
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.alive": {},
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.admin_state_up": {},
}


def get_normalized_key(key):
    return re.sub(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower().replace("-", "_")


def get_normalized_metrics(metrics, prefix, reference_metrics):
    normalized_metrics = {}
    if isinstance(metrics, dict):
        for key, value in metrics.items():
            long_metric_name = f'{prefix}.{get_normalized_key(key)}'
            referenced_metric = reference_metrics.get(long_metric_name)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if referenced_metric is not None:
                    normalized_metrics[long_metric_name] = value
            elif isinstance(value, bool):
                if referenced_metric is not None:
                    normalized_metrics[long_metric_name] = 1 if value else 0
            elif isinstance(value, list):
                for item in value:
                    normalized_metrics.update(get_normalized_metrics(item, long_metric_name, reference_metrics))
            elif isinstance(value, type(None)):
                if referenced_metric is not None and not referenced_metric.get("optional", False):
                    normalized_metrics[long_metric_name] = 0
            else:
                normalized_metrics.update(get_normalized_metrics(value, long_metric_name, reference_metrics))
    return normalized_metrics
