# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


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
