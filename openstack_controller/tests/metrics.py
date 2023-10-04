# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


COMPUTE_SERVICES_NOVA_MICROVERSION_DEFAULT = [
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:2',
            'service_name:nova-scheduler',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:2',
            'service_name:nova-scheduler',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:3',
            'service_name:nova-compute',
            'service_state:up',
            'service_status:enabled',
            'service_zone:availability-zone',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:3',
            'service_name:nova-compute',
            'service_state:up',
            'service_status:enabled',
            'service_zone:availability-zone',
        ],
    },
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:5',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:5',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
]

COMPUTE_SERVICES_NOVA_MICROVERSION_2_93 = [
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:aadbda65-f523-419a-b3df-c287d196a2c1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:aadbda65-f523-419a-b3df-c287d196a2c1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:2ec2027d-ac70-4e2b-95ed-fb1756d24996',
            'service_name:nova-scheduler',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:2ec2027d-ac70-4e2b-95ed-fb1756d24996',
            'service_name:nova-scheduler',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:7bf08d7e-a939-46c3-bdae-fbe3ebfe78a4',
            'service_name:nova-compute',
            'service_state:up',
            'service_status:enabled',
            'service_zone:availability-zone',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:7bf08d7e-a939-46c3-bdae-fbe3ebfe78a4',
            'service_name:nova-compute',
            'service_state:up',
            'service_status:enabled',
            'service_zone:availability-zone',
        ],
    },
    {
        'name': 'openstack.nova.service.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:aadbda65-f523-419a-b3df-c287d196a2c1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
    {
        'name': 'openstack.nova.service.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:aadbda65-f523-419a-b3df-c287d196a2c1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    },
]

COMPUTE_HYPERVISORS_NOVA_MICROVERSION_DEFAULT = [
    {
        'name': 'openstack.nova.hypervisor.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
    {
        'name': 'openstack.nova.hypervisor.load_1',
        'count': 1,
        'value': 0.29,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
    {
        'name': 'openstack.nova.hypervisor.load_5',
        'count': 1,
        'value': 0.36,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
    {
        'name': 'openstack.nova.hypervisor.load_15',
        'count': 1,
        'value': 0.35,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
]

COMPUTE_HYPERVISORS_NOVA_MICROVERSION_2_93 = [
    {
        'name': 'openstack.nova.hypervisor.up',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
    {
        'name': 'openstack.nova.hypervisor.load_1',
        'count': 1,
        'value': 0.28,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
    {
        'name': 'openstack.nova.hypervisor.load_5',
        'count': 1,
        'value': 0.35,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
    {
        'name': 'openstack.nova.hypervisor.load_15',
        'count': 1,
        'value': 0.35,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    },
]

COMPUTE_QUOTA_SETS_NOVA_MICROVERSION_DEFAULT = [
    {
        'name': 'openstack.nova.quota_set.cores',
        'count': 1,
        'value': 20,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.fixed_ips',
        'count': 1,
        'value': -1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.floating_ips',
        'count': 1,
        'value': -1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.injected_file_content_bytes',
        'count': 1,
        'value': 10240,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.injected_file_path_bytes',
        'count': 1,
        'value': 255,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.injected_files',
        'count': 1,
        'value': 5,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.instances',
        'count': 1,
        'value': 5,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.key_pairs',
        'count': 1,
        'value': 100,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.metadata_items',
        'count': 1,
        'value': 128,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.ram',
        'count': 1,
        'value': 51200,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.security_group_rules',
        'count': 1,
        'value': -1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.security_groups',
        'count': 1,
        'value': -1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.server_group_members',
        'count': 1,
        'value': 10,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.server_groups',
        'count': 1,
        'value': 10,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
]

COMPUTE_QUOTA_SETS_NOVA_MICROVERSION_2_93 = [
    {
        'name': 'openstack.nova.quota_set.cores',
        'count': 1,
        'value': 20,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.instances',
        'count': 1,
        'value': 5,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.key_pairs',
        'count': 1,
        'value': 100,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.metadata_items',
        'count': 1,
        'value': 128,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.ram',
        'count': 1,
        'value': 51200,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.server_group_members',
        'count': 1,
        'value': 10,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
    {
        'name': 'openstack.nova.quota_set.server_groups',
        'count': 1,
        'value': 10,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    },
]

COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT = [
    {
        'name': 'openstack.nova.server.count',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.active',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.diagnostic.cpu0_time',
        'count': 1,
        'value': 7211540000000,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
]

COMPUTE_SERVERS_NOVA_MICROVERSION_2_93 = [
    {
        'name': 'openstack.nova.server.count',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.active',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.diagnostic.disk_details.read_bytes',
        'count': 1,
        'value': 23407104,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
]

COMPUTE_SERVERS_NO_DIAGNOSTICS_NOVA_MICROVERSION_DEFAULT = [
    {
        'name': 'openstack.nova.server.count',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.active',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.diagnostic.cpu0_time',
        'count': 0,
    },
]

COMPUTE_SERVERS_NO_DIAGNOSTICS_NOVA_MICROVERSION_2_93 = [
    {
        'name': 'openstack.nova.server.count',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.active',
        'count': 1,
        'value': 1,
        'tags': [
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    },
    {
        'name': 'openstack.nova.server.diagnostic.disk_details.read_bytes',
        'count': 0,
    },
]

NODES_METRICS_IRONIC_MICROVERSION_DEFAULT = [
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_uuid:9d72cf53-19c8-4942-9314-005fa5d2a6a0',
        ],
    },
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_uuid:bd7a61bb-5fe0-4c93-9628-55e312f9ef0e',
        ],
    },
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_uuid:54855e59-83ca-46f8-a78f-55d3370e0656',
        ],
    },
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_uuid:20512deb-e493-4796-a046-5d6e4e072c95',
            'power_state:power on',
        ],
    },
]

NODES_METRICS_IRONIC_MICROVERSION_1_80 = [
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'conductor_group:',
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_name:node-0',
            'node_uuid:9d72cf53-19c8-4942-9314-005fa5d2a6a0',
        ],
    },
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'conductor_group:',
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_name:node-1',
            'node_uuid:bd7a61bb-5fe0-4c93-9628-55e312f9ef0e',
        ],
    },
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'conductor_group:',
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_name:node-2',
            'node_uuid:54855e59-83ca-46f8-a78f-55d3370e0656',
        ],
    },
    {
        'name': 'openstack.ironic.node.count',
        'count': 1,
        'value': 1,
        'tags': [
            'conductor_group:',
            'keystone_server:http://127.0.0.1:8080/identity',
            'node_name:test',
            'node_uuid:20512deb-e493-4796-a046-5d6e4e072c95',
            'power_state:power on',
        ],
    },
]

CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT = []

CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80 = [
    {
        'name': 'openstack.ironic.conductor.count',
        'count': 1,
        'value': 1,
        'tags': [
            'conductor_group:',
            'conductor_hostname:agent-integrations-openstack-ironic',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    },
]
