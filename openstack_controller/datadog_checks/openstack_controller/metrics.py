# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

KEYSTONE_METRICS_PREFIX = "openstack.keystone"
KEYSTONE_SERVICE_CHECK = f"{KEYSTONE_METRICS_PREFIX}.api.up"
KEYSTONE_RESPONSE_TIME = f"{KEYSTONE_METRICS_PREFIX}.response_time"

KEYSTONE_REGION_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.region"
KEYSTONE_REGION_COUNT = f"{KEYSTONE_REGION_METRICS_PREFIX}.count"
KEYSTONE_REGION_TAGS = {
    'id': 'region_id',
}
KEYSTONE_REGION_METRICS = {}

KEYSTONE_DOMAIN_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.domain"
KEYSTONE_DOMAIN_COUNT = f"{KEYSTONE_DOMAIN_METRICS_PREFIX}.count"
KEYSTONE_DOMAIN_TAGS = {
    'id': 'domain_id',
    'name': 'domain_name',
}
KEYSTONE_DOMAIN_METRICS = {
    f"{KEYSTONE_DOMAIN_METRICS_PREFIX}.enabled": {},
}

KEYSTONE_PROJECT_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.project"
KEYSTONE_PROJECT_COUNT = f"{KEYSTONE_PROJECT_METRICS_PREFIX}.count"
KEYSTONE_PROJECT_TAGS = {
    'domain_id': 'domain_id',
    'id': 'project_id',
    'name': 'project_name',
}
KEYSTONE_PROJECT_METRICS = {
    f"{KEYSTONE_PROJECT_METRICS_PREFIX}.enabled": {},
}

KEYSTONE_USER_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.user"
KEYSTONE_USER_COUNT = f"{KEYSTONE_USER_METRICS_PREFIX}.count"
KEYSTONE_USER_TAGS = {
    'domain_id': 'domain_id',
    'id': 'user_id',
    'name': 'user_name',
}
KEYSTONE_USER_METRICS = {
    f"{KEYSTONE_USER_METRICS_PREFIX}.enabled": {},
}

KEYSTONE_GROUP_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.group"
KEYSTONE_GROUP_COUNT = f"{KEYSTONE_GROUP_METRICS_PREFIX}.count"
KEYSTONE_GROUP_TAGS = {
    'domain_id': 'domain_id',
    'id': 'group_id',
    'name': 'group_name',
}
KEYSTONE_GROUP_METRICS = {}
KEYSTONE_GROUP_USERS = f"{KEYSTONE_GROUP_METRICS_PREFIX}.users"

KEYSTONE_SERVICE_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.service"
KEYSTONE_SERVICE_COUNT = f"{KEYSTONE_SERVICE_METRICS_PREFIX}.count"
KEYSTONE_SERVICE_TAGS = {
    'id': 'service_id',
    'name': 'service_name',
    'type': 'service_type',
}
KEYSTONE_SERVICE_METRICS = {
    f"{KEYSTONE_SERVICE_METRICS_PREFIX}.enabled": {},
}

KEYSTONE_REGISTERED_LIMIT_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.limit"
KEYSTONE_REGISTERED_LIMIT_TAGS = {
    'id': 'limit_id',
    'region_id': 'region_id',
    'resource_name': 'resource_name',
    'service_id': 'service_id',
}
KEYSTONE_REGISTERED_LIMIT_METRICS = {
    f"{KEYSTONE_REGISTERED_LIMIT_METRICS_PREFIX}.limit": {},
}

KEYSTONE_LIMIT_METRICS_PREFIX = f"{KEYSTONE_METRICS_PREFIX}.limit"
KEYSTONE_LIMIT_TAGS = {
    'domain_id': 'domain_id',
    'id': 'limit_id',
    'project_id': 'project_id',
    'region_id': 'region_id',
    'resource_name': 'resource_name',
    'service_id': 'service_id',
}
KEYSTONE_LIMIT_METRICS = {
    f"{KEYSTONE_LIMIT_METRICS_PREFIX}.limit": {},
}

NOVA_METRICS_PREFIX = "openstack.nova"
NOVA_SERVICE_CHECK = f"{NOVA_METRICS_PREFIX}.api.up"
NOVA_RESPONSE_TIME = f"{NOVA_METRICS_PREFIX}.response_time"

NOVA_LIMITS_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.limit"
NOVA_LIMITS_TAGS = {}
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

NOVA_SERVICES_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.service"
NOVA_SERVICES_COUNT = f"{NOVA_SERVICES_METRICS_PREFIX}.count"
NOVA_SERVICES_TAGS = {
    'id': 'service_id',
    'binary': 'service_name',
    'host': 'service_host',
    'status': 'service_status',
    'state': 'service_state',
    'zone': 'service_zone',
}
NOVA_SERVICES_METRICS = {
    f"{NOVA_SERVICES_METRICS_PREFIX}.up": {},
}

NOVA_QUOTA_SET_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.quota_set"
NOVA_QUOTA_SET_TAGS = {
    'id': 'quota_id',
}
NOVA_QUOTA_SET_METRICS = {
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.cores",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.fixed_ips",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.floating_ips",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.injected_file_content_bytes",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.injected_file_path_bytes",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.injected_files",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.instances",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.key_pairs",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.metadata_items",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.ram",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.security_group_rules",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.security_groups",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.server_group_members",
    f"{NOVA_QUOTA_SET_METRICS_PREFIX}.server_groups",
}

NOVA_SERVER_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.server"
NOVA_SERVER_COUNT = f"{NOVA_SERVER_METRICS_PREFIX}.count"
NOVA_SERVER_TAGS = {
    'id': 'server_id',
    'name': 'server_name',
    'status': 'server_status',
    'OS-EXT-SRV-ATTR:hypervisor_hostname': 'hypervisor',
    'OS-EXT-SRV-ATTR:instance_name': 'instance_name',
    'OS-EXT-SRV-ATTR:hostname': 'instance_hostname',
}
NOVA_SERVER_METRICS = {
    f"{NOVA_SERVER_METRICS_PREFIX}.active",
    f"{NOVA_SERVER_METRICS_PREFIX}.error",
}
NOVA_SERVER_FLAVOR_METRICS_PREFIX = f"{NOVA_SERVER_METRICS_PREFIX}.flavor"
NOVA_SERVER_FLAVOR_TAGS = {
    'id': 'flavor_id',
    'name': 'flavor_name',
}
NOVA_SERVER_FLAVOR_METRICS = {
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.vcpus",
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.ram",
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.disk",
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.os_flv_ext_data_ephemeral",
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.ephemeral",
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.swap",
    f"{NOVA_SERVER_FLAVOR_METRICS_PREFIX}.rxtx_factor",
}
NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX = f"{NOVA_SERVER_METRICS_PREFIX}.diagnostic"
NOVA_SERVER_DIAGNOSTIC_TAGS = {
    'driver': 'server_driver',
}
NOVA_SERVER_DIAGNOSTIC_METRICS = {
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.cpu0_time",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.vda_read_req",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.vda_read",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.vda_write_req",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.vda_write",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.vda_errors",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_actual",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_swap_in",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_swap_out",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_major_fault",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_minor_fault",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_unused",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_available",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_usable",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_last_update",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_disk_caches",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_hugetlb_pgalloc",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_hugetlb_pgfail",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_rss",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_details.maximum",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.memory_details.used",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.uptime",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.num_cpus",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.num_nics",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.num_disks",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.rx",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.rx_packets",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.rx_errors",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.rx_drop",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.tx",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.tx_packets",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.tx_errors",
    f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.tx_drop",
}
NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX = f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.disk_details"
NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_TAGS = {}
NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS = {
    f"{NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX}.read_bytes",
    f"{NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX}.read_requests",
    f"{NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX}.write_bytes",
    f"{NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX}.write_requests",
    f"{NOVA_SERVER_DIAGNOSTIC_DISK_DETAILS_METRICS_PREFIX}.errors_count",
}
NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS_PREFIX = f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.cpu_details"
NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_TAGS = {
    'id': 'cpu_id',
}
NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS = {
    f"{NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS_PREFIX}.time",
    f"{NOVA_SERVER_DIAGNOSTIC_CPU_DETAILS_METRICS_PREFIX}.utilisation",
}
NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX = f"{NOVA_SERVER_DIAGNOSTIC_METRICS_PREFIX}.nic_details"
NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_TAGS = {
    'mac_address': 'mac_address',
}
NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS = {
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.rx_drop",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.rx_errors",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.rx_octets",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.rx_packets",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.rx_rate",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.tx_drop",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.tx_errors",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.tx_octets",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.tx_packets",
    f"{NOVA_SERVER_DIAGNOSTIC_NIC_DETAILS_METRICS_PREFIX}.tx_rate",
}

NOVA_FLAVORS_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.flavor"
NOVA_FLAVORS_TAGS = {
    'id': 'flavor_id',
    'name': 'flavor_name',
}
NOVA_FLAVORS_METRICS = {
    f"{NOVA_FLAVORS_METRICS_PREFIX}.vcpus",
    f"{NOVA_FLAVORS_METRICS_PREFIX}.ram",
    f"{NOVA_FLAVORS_METRICS_PREFIX}.disk",
    f"{NOVA_FLAVORS_METRICS_PREFIX}.os_flv_ext_data_ephemeral",
    f"{NOVA_FLAVORS_METRICS_PREFIX}.swap",
    f"{NOVA_FLAVORS_METRICS_PREFIX}.rxtx_factor",
}

NOVA_HYPERVISOR_METRICS_PREFIX = f"{NOVA_METRICS_PREFIX}.hypervisor"
NOVA_HYPERVISOR_COUNT = f"{NOVA_HYPERVISOR_METRICS_PREFIX}.count"
NOVA_HYPERVISOR_TAGS = {
    'id': 'hypervisor_id',
    'hypervisor_hostname': 'hypervisor_name',
    'hypervisor_type': 'hypervisor_type',
    'status': 'hypervisor_status',
    'state': 'hypervisor_state',
}
NOVA_HYPERVISOR_METRICS = {
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.current_workload",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.disk_available_least",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.free_disk_gb",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.free_ram_mb",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.local_gb",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.local_gb_used",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.memory_mb",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.memory_mb_used",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.running_vms",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.vcpus",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.vcpus_used",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.up",
}
NOVA_HYPERVISOR_UPTIME_METRICS = {
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_1",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_5",
    f"{NOVA_HYPERVISOR_METRICS_PREFIX}.load_15",
}

NEUTRON_METRICS_PREFIX = "openstack.neutron"
NEUTRON_SERVICE_CHECK = f"{NEUTRON_METRICS_PREFIX}.api.up"
NEUTRON_RESPONSE_TIME = f"{NEUTRON_METRICS_PREFIX}.response_time"

NEUTRON_NETWORK_METRICS_PREFIX = f"{NEUTRON_METRICS_PREFIX}.network"
NEUTRON_NETWORK_COUNT = f"{NEUTRON_NETWORK_METRICS_PREFIX}.count"
NEUTRON_NETWORK_TAGS = {
    'id': 'network_id',
    'name': 'network_name',
    'status': 'network_status',
}
NEUTRON_NETWORK_METRICS = {
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.admin_state_up",
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.l2_adjacency",
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.mtu",
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.port_security_enabled",
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.shared",
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.vlan_transparent",
    f"{NEUTRON_NETWORK_METRICS_PREFIX}.is_default",
}

NEUTRON_QUOTA_METRICS_PREFIX = f"{NEUTRON_METRICS_PREFIX}.quota"
NEUTRON_QUOTA_TAGS = {}
NEUTRON_QUOTA_METRICS = {
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.floatingip",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.network",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.port",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.rbac_policy",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.router",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.security_group",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.security_group_rule",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.subnet",
    f"{NEUTRON_QUOTA_METRICS_PREFIX}.subnetpool",
}

NEUTRON_AGENTS_METRICS_PREFIX = f"{NEUTRON_METRICS_PREFIX}.agent"
NEUTRON_AGENTS_COUNT = f"{NEUTRON_AGENTS_METRICS_PREFIX}.count"
NEUTRON_AGENTS_TAGS = {
    'id': 'agent_id',
    'binary': 'agent_name',
    'host': 'agent_host',
    'availability_zone': 'agent_availability_zone',
    'agent_type': 'agent_type',
}
NEUTRON_AGENTS_METRICS = {
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.alive",
    f"{NEUTRON_AGENTS_METRICS_PREFIX}.admin_state_up",
}

NEUTRON_GLOBAL_METRICS = NEUTRON_AGENTS_METRICS
NEUTRON_PROJECT_METRICS = NEUTRON_NETWORK_METRICS | NEUTRON_QUOTA_METRICS

CINDER_METRICS_PREFIX = "openstack.cinder"
CINDER_SERVICE_CHECK = f"{CINDER_METRICS_PREFIX}.api.up"
CINDER_POOL_PREFIX = f"{CINDER_METRICS_PREFIX}.pool"
CINDER_POOL_COUNT = f"{CINDER_POOL_PREFIX}.count"
CINDER_POOL_METRICS = {
    f"{CINDER_POOL_PREFIX}.capabilities.total_capacity_gb": {},
    f"{CINDER_POOL_PREFIX}.capabilities.free_capacity_gb": {},
    f"{CINDER_POOL_PREFIX}.capabilities.reserved_percentage": {},
}
CINDER_POOL_TAGS = {
    'name': 'pool_name',
    'capabilities.volume_backend_name': 'pool_volume_backend_name',
}
CINDER_RESPONSE_TIME = f"{CINDER_METRICS_PREFIX}.response_time"
CINDER_CLUSTER_PREFIX = f"{CINDER_METRICS_PREFIX}.cluster"
CINDER_CLUSTER_COUNT = f"{CINDER_CLUSTER_PREFIX}.count"
CINDER_CLUSTER_METRICS = {f"{CINDER_CLUSTER_PREFIX}.num_hosts": {}, f"{CINDER_CLUSTER_PREFIX}.num_down_hosts": {}}
CINDER_CLUSTER_TAGS = {'name': 'cluster-name'}
CINDER_SNAPSHOT_PREFIX = f"{CINDER_METRICS_PREFIX}.snapshot"
CINDER_SNAPSHOT_COUNT = f"{CINDER_SNAPSHOT_PREFIX}.count"
CINDER_SNAPSHOT_METRICS = {f"{CINDER_SNAPSHOT_PREFIX}.size": {}}
CINDER_SNAPSHOT_TAGS = {'id': 'snapshot_id', 'volume_id': 'volume_id'}
CINDER_TRANSFER_COUNT = f"{CINDER_METRICS_PREFIX}.volume.transfer.count"
CINDER_TRANSFER_TAGS = {'id': 'transfer_id', 'volume_id': 'volume_id', 'name': 'volume_name'}
CINDER_VOLUME_PREFIX = f"{CINDER_METRICS_PREFIX}.volume"
CINDER_VOLUME_COUNT = f"{CINDER_VOLUME_PREFIX}.count"
CINDER_VOLUME_METRICS = {f"{CINDER_VOLUME_PREFIX}.size": {}}
CINDER_VOLUME_TAGS = {'id': 'volume_id', 'name': 'volume_name', 'status': 'volume_status'}

IRONIC_METRICS_PREFIX = "openstack.ironic"
IRONIC_SERVICE_CHECK = f"{IRONIC_METRICS_PREFIX}.api.up"
IRONIC_RESPONSE_TIME = f"{IRONIC_METRICS_PREFIX}.response_time"

IRONIC_NODE_METRICS_PREFIX = f"{IRONIC_METRICS_PREFIX}.node"
IRONIC_NODE_COUNT = f"{IRONIC_NODE_METRICS_PREFIX}.count"
IRONIC_NODE_TAGS = {
    'uuid': 'node_uuid',
    'name': 'node_name',
    'conductor_group': 'conductor_group',
    'power_state': 'power_state',
    'provision_state': 'provision_state',
    'target_provision_state': 'target_provision_state',
    'driver': 'driver',
}
IRONIC_NODE_METRICS = {
    f"{IRONIC_NODE_METRICS_PREFIX}.up": {},
}

IRONIC_CONDUCTOR_METRICS_PREFIX = f"{IRONIC_METRICS_PREFIX}.conductor"
IRONIC_CONDUCTOR_COUNT = f"{IRONIC_CONDUCTOR_METRICS_PREFIX}.count"
IRONIC_CONDUCTOR_TAGS = {
    'hostname': 'conductor_hostname',
    'conductor_group': 'conductor_group',
}
IRONIC_CONDUCTOR_METRICS = {
    f"{IRONIC_CONDUCTOR_METRICS_PREFIX}.up": {},
}

OCTAVIA_METRICS_PREFIX = "openstack.octavia"
OCTAVIA_SERVICE_CHECK = f"{OCTAVIA_METRICS_PREFIX}.api.up"
OCTAVIA_RESPONSE_TIME = f"{OCTAVIA_METRICS_PREFIX}.response_time"

OCTAVIA_LOAD_BALANCER_METRICS_PREFIX = f"{OCTAVIA_METRICS_PREFIX}.loadbalancer"
OCTAVIA_LOAD_BALANCER_COUNT = f"{OCTAVIA_LOAD_BALANCER_METRICS_PREFIX}.count"
OCTAVIA_LOAD_BALANCER_TAGS = {
    'id': 'loadbalancer_id',
    'name': 'loadbalancer_name',
    'provisioning_status': 'provisioning_status',
    'operating_status': 'operating_status',
    'listeners': {
        'id': 'listener_id',
    },
}
OCTAVIA_LOAD_BALANCER_METRICS = {
    f"{OCTAVIA_LOAD_BALANCER_METRICS_PREFIX}.admin_state_up": {},
}
OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX = f"{OCTAVIA_LOAD_BALANCER_METRICS_PREFIX}.stats"
OCTAVIA_LOAD_BALANCER_STATS_METRICS = {
    f"{OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX}.active_connections": {},
    f"{OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX}.bytes_in": {},
    f"{OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX}.bytes_out": {},
    f"{OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX}.request_errors": {},
    f"{OCTAVIA_LOAD_BALANCER_STATS_METRICS_PREFIX}.total_connections": {},
}

OCTAVIA_LISTENER_METRICS_PREFIX = f"{OCTAVIA_METRICS_PREFIX}.listener"
OCTAVIA_LISTENER_COUNT = f"{OCTAVIA_LISTENER_METRICS_PREFIX}.count"
OCTAVIA_LISTENER_TAGS = {
    'id': 'listener_id',
    'name': 'listener_name',
    'provisioning_status': 'provisioning_status',
    'operating_status': 'operating_status',
    'loadbalancers': {
        'id': 'loadbalancer_id',
    },
}
OCTAVIA_LISTENER_METRICS = {
    f"{OCTAVIA_LISTENER_METRICS_PREFIX}.connection_limit": {},
    f"{OCTAVIA_LISTENER_METRICS_PREFIX}.timeout_client_data": {},
    f"{OCTAVIA_LISTENER_METRICS_PREFIX}.timeout_member_connect": {},
    f"{OCTAVIA_LISTENER_METRICS_PREFIX}.timeout_member_data": {},
    f"{OCTAVIA_LISTENER_METRICS_PREFIX}.timeout_tcp_inspect": {},
}
OCTAVIA_LISTENER_STATS_METRICS_PREFIX = f"{OCTAVIA_LISTENER_METRICS_PREFIX}.stats"
OCTAVIA_LISTENER_STATS_METRICS = {
    f"{OCTAVIA_LISTENER_STATS_METRICS_PREFIX}.active_connections": {},
    f"{OCTAVIA_LISTENER_STATS_METRICS_PREFIX}.bytes_in": {},
    f"{OCTAVIA_LISTENER_STATS_METRICS_PREFIX}.bytes_out": {},
    f"{OCTAVIA_LISTENER_STATS_METRICS_PREFIX}.request_errors": {},
    f"{OCTAVIA_LISTENER_STATS_METRICS_PREFIX}.total_connections": {},
}

OCTAVIA_POOL_METRICS_PREFIX = f"{OCTAVIA_METRICS_PREFIX}.pool"
OCTAVIA_POOL_COUNT = f"{OCTAVIA_POOL_METRICS_PREFIX}.count"
OCTAVIA_POOL_TAGS = {
    'id': 'pool_id',
    'name': 'pool_name',
    'provisioning_status': 'provisioning_status',
    'operating_status': 'operating_status',
    'loadbalancers': {
        'id': 'loadbalancer_id',
    },
    'listeners': {
        'id': 'listener_id',
    },
}
OCTAVIA_POOL_METRICS = {
    f"{OCTAVIA_POOL_METRICS_PREFIX}.admin_state_up": {},
}

OCTAVIA_POOL_MEMBERS_METRICS_PREFIX = f"{OCTAVIA_POOL_METRICS_PREFIX}.member"
OCTAVIA_POOL_MEMBERS_COUNT = f"{OCTAVIA_POOL_MEMBERS_METRICS_PREFIX}.count"
OCTAVIA_POOL_MEMBERS_TAGS = {
    'id': 'member_id',
    'name': 'member_name',
    'provisioning_status': 'provisioning_status',
    'operating_status': 'operating_status',
    'loadbalancers': {
        'id': 'loadbalancer_id',
    },
    'listeners': {
        'id': 'listener_id',
    },
}
OCTAVIA_POOL_MEMBERS_METRICS = {
    f"{OCTAVIA_POOL_MEMBERS_METRICS_PREFIX}.admin_state_up": {},
    f"{OCTAVIA_POOL_MEMBERS_METRICS_PREFIX}.weight": {},
}


OCTAVIA_HEALTHMONITOR_METRICS_PREFIX = f"{OCTAVIA_METRICS_PREFIX}.healthmonitor"
OCTAVIA_HEALTHMONITOR_COUNT = f"{OCTAVIA_HEALTHMONITOR_METRICS_PREFIX}.count"
OCTAVIA_HEALTHMONITOR_TAGS = {
    'id': 'healthmonitor_id',
    'name': 'healthmonitor_name',
    'provisioning_status': 'provisioning_status',
    'operating_status': 'operating_status',
    'type': 'type',
    'pools': {
        'id': 'pool_id',
    },
}
OCTAVIA_HEALTHMONITOR_METRICS = {
    f"{OCTAVIA_HEALTHMONITOR_METRICS_PREFIX}.admin_state_up": {},
    f"{OCTAVIA_HEALTHMONITOR_METRICS_PREFIX}.delay": {},
    f"{OCTAVIA_HEALTHMONITOR_METRICS_PREFIX}.timeout": {},
    f"{OCTAVIA_HEALTHMONITOR_METRICS_PREFIX}.max_retries": {},
    f"{OCTAVIA_HEALTHMONITOR_METRICS_PREFIX}.max_retries_down": {},
}


OCTAVIA_QUOTA_METRICS_PREFIX = f"{OCTAVIA_METRICS_PREFIX}.quota"
OCTAVIA_QUOTA_COUNT = f"{OCTAVIA_QUOTA_METRICS_PREFIX}.count"
OCTAVIA_QUOTA_TAGS = {}
OCTAVIA_QUOTA_METRICS = {
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.loadbalancer": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.load_balancer": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.listener": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.member": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.pool": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.healthmonitor": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.health_monitor": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.l7policy": {},
    f"{OCTAVIA_QUOTA_METRICS_PREFIX}.l7rule": {},
}

OCTAVIA_AMPHORA_METRICS_PREFIX = f"{OCTAVIA_METRICS_PREFIX}.amphora"
OCTAVIA_AMPHORA_COUNT = f"{OCTAVIA_AMPHORA_METRICS_PREFIX}.count"
OCTAVIA_AMPHORA_TAGS = {
    'id': 'amphora_id',
    'loadbalancer_id': 'loadbalancer_id',
    'status': 'status',
}
OCTAVIA_AMPHORA_METRICS = {}
OCTAVIA_AMPHORA_STATS_METRICS_PREFIX = f"{OCTAVIA_AMPHORA_METRICS_PREFIX}.stats"
OCTAVIA_AMPHORA_STATS_TAGS = {
    'listener_id': 'listener_id',
}
OCTAVIA_AMPHORA_STATS_METRICS = {
    f"{OCTAVIA_AMPHORA_STATS_METRICS_PREFIX}.active_connections": {},
    f"{OCTAVIA_AMPHORA_STATS_METRICS_PREFIX}.bytes_in": {},
    f"{OCTAVIA_AMPHORA_STATS_METRICS_PREFIX}.bytes_out": {},
    f"{OCTAVIA_AMPHORA_STATS_METRICS_PREFIX}.request_errors": {},
    f"{OCTAVIA_AMPHORA_STATS_METRICS_PREFIX}.total_connections": {},
}

GLANCE_METRICS_PREFIX = "openstack.glance"
GLANCE_SERVICE_CHECK = f"{GLANCE_METRICS_PREFIX}.api.up"
GLANCE_RESPONSE_TIME = f"{GLANCE_METRICS_PREFIX}.response_time"
GLANCE_IMAGE_PREFIX = f"{GLANCE_METRICS_PREFIX}.image"
GLANCE_IMAGE_COUNT = f"{GLANCE_IMAGE_PREFIX}.count"
GLANCE_IMAGE_METRICS = {
    f"{GLANCE_IMAGE_PREFIX}.up": {},
    f"{GLANCE_IMAGE_PREFIX}.size": {},
}
GLANCE_IMAGE_TAGS = {
    'id': 'image_id',
    'name': 'image_name',
    'status': 'status',
    'container_format': 'container_format',
}
GLANCE_MEMBER_PREFIX = f"{GLANCE_IMAGE_PREFIX}.member"
GLANCE_MEMBER_COUNT = f"{GLANCE_MEMBER_PREFIX}.count"
GLANCE_MEMBER_TAGS = {
    'member_id': 'member_id',
    'image_id': 'image_id',
    'status': 'status',
}


def is_interface_metric(label):
    return any(seg in label for seg in ['_rx', '_tx'])


def get_normalized_key(key):
    return re.sub(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', key).lower().replace("-", "_")


def get_normalized_tags(data, prefix, tags):
    normalized_tags = []
    if isinstance(data, dict):
        for key, value in data.items():
            long_tag_name = f'{prefix}.{key}' if prefix else key
            if value is not None and long_tag_name in tags:
                if isinstance(value, list):
                    for item in value:
                        normalized_tags.extend(get_normalized_tags(item, None, tags[long_tag_name]))
                else:
                    normalized_tags.append(f'{tags[long_tag_name]}:{value}')
            else:
                normalized_tags.extend(get_normalized_tags(value, long_tag_name, tags))
    return normalized_tags


def get_normalized_metrics(data, prefix, metrics, lambda_name=None, lambda_value=None):
    normalized_metrics = {}
    if isinstance(data, dict):
        for key, value in data.items():
            long_metric_name = f'{prefix}.{get_normalized_key(key if not lambda_name else lambda_name(key))}'
            value = value if not lambda_value else lambda_value(key, value)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if long_metric_name in metrics:
                    normalized_metrics[long_metric_name] = value
                if is_interface_metric(key):
                    normalized_metrics[key] = value
            elif isinstance(value, bool):
                if long_metric_name in metrics:
                    normalized_metrics[long_metric_name] = 1 if value else 0
            elif isinstance(value, str):
                if long_metric_name in metrics:
                    try:
                        normalized_metrics[long_metric_name] = int(value) if value else 0
                    except ValueError:
                        pass
            elif isinstance(value, type(None)):
                if long_metric_name in metrics:
                    normalized_metrics[long_metric_name] = 0
            else:
                normalized_metrics.update(
                    get_normalized_metrics(value, long_metric_name, metrics, lambda_name, lambda_value)
                )
    return normalized_metrics


def get_metrics_and_tags(data, tags, prefix, metrics, lambda_name=None, lambda_value=None):
    return {
        'tags': get_normalized_tags(data, None, tags),
        'metrics': get_normalized_metrics(data, prefix, metrics, lambda_name, lambda_value),
    }
