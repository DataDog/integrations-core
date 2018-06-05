# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

ALL_IDS = ['server-1', 'server-2', 'other-1', 'other-2']
EXCLUDED_NETWORK_IDS = ['server-1', 'other-.*']
EXCLUDED_SERVER_IDS = ['server-2', 'other-.*']
FILTERED_NETWORK_ID = 'server-2'
FILTERED_SERVER_ID = 'server-1'

EXAMPLE_AUTH_RESPONSE = {
    u'token': {
        u'methods': [
            u'password'
        ],
        u'roles': [
            {
                u'id': u'f20c215f5a4d47b7a6e510bc65485ced',
                u'name': u'datadog_monitoring'
            },
            {
                u'id': u'9fe2ff9ee4384b1894a90878d3e92bab',
                u'name': u'_member_'
            }
        ],
        u'expires_at': u'2015-11-02T15: 57: 43.911674Z',
        u'project': {
            u'domain': {
                u'id': u'default',
                u'name': u'Default'
            },
            u'id': u'0850707581fe4d738221a72db0182876',
            u'name': u'admin'
        },
        u'catalog': [
            {
                u'endpoints': [
                    {
                        u'url': u'http://10.0.2.15:8773/',
                        u'interface': u'public',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'541baeb9ab7542609d7ae307a7a9d5f0'
                    },
                    {
                        u'url': u'http: //10.0.2.15:8773/',
                        u'interface': u'admin',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'5c648acaea9941659a5dc04fb3b18e49'
                    },
                    {
                        u'url': u'http: //10.0.2.15:8773/',
                        u'interface': u'internal',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'cb70e610620542a1804522d365226981'
                    }
                ],
                u'type': u'compute',
                u'id': u'1398dc02f9b7474eb165106485033b48',
                u'name': u'nova'
            },
            {
                u'endpoints': [
                    {
                        u'url': u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876',
                        u'interface': u'internal',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'354e35ed19774e398f80dc2a90d07f4b'
                    },
                    {
                        u'url': u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876',
                        u'interface': u'public',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'36e8e2bf24384105b9d56a65b0900172'
                    },
                    {
                        u'url': u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876',
                        u'interface': u'admin',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'de93edcbf7f9446286687ec68423c36f'
                    }
                ],
                u'type': u'computev21',
                u'id': u'2023bd4f451849ba8abeaaf283cdde4f',
                u'name': u'novav21'
            },
            {
                u'endpoints': [
                    {
                        u'url': u'http://10.0.2.15:9292',
                        u'interface': u'internal',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'7c1e318d8f7f42029fcb591598df2ef5'
                    },
                    {
                        u'url': u'http://10.0.2.15:9292',
                        u'interface': u'public',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'afcc88b1572f48a38bb393305dc2b584'
                    },
                    {
                        u'url': u'http://10.0.2.15:9292',
                        u'interface': u'admin',
                        u'region': u'RegionOne',
                        u'region_id': u'RegionOne',
                        u'id': u'd9730dbdc07844d785913219da64a197'
                    }
                ],
                u'type': u'network',
                u'id': u'21ad241f26194bccb7d2e49ee033d5a2',
                u'name': u'neutron'
            },

        ],
        u'extras': {

        },
        u'user': {
            u'domain': {
                u'id': u'default',
                u'name': u'Default'
            },
            u'id': u'5f10e63fbd6b411186e561dc62a9a675',
            u'name': u'datadog'
        },
        u'audit_ids': [
            u'OMQQg9g3QmmxRHwKrfWxyQ'
        ],
        u'issued_at': u'2015-11-02T14: 57: 43.911697Z'
    }
}

EXAMPLE_PROJECTS_RESPONSE = {
    "projects": [
        {
            "domain_id": "1789d1",
            "enabled": True,
            "id": "263fd9",
            "links": {
                "self": "https://example.com/identity/v3/projects/263fd9"
            },
            "name": "Test Group"
        },
    ],
    "links": {
        "self": "https://example.com/identity/v3/auth/projects",
        "previous": None,
        "next": None,
    }
}

BAD_AUTH_SCOPES = [
    {'auth_scope': {'project': {}}},
    {'auth_scope': {'project': {'id': ''}}},
    {'auth_scope': {'project': {'name': 'test'}}},
    {'auth_scope': {'project': {'name': 'test', 'domain': {}}}},
    {'auth_scope': {'project': {'name': 'test', 'domain': {'id': ''}}}},
]

GOOD_UNSCOPED_AUTH_SCOPES = [
    {'auth_scope': {}},  # unscoped project
]

GOOD_AUTH_SCOPES = [
    {'auth_scope': {'project': {'id': 'test_project_id'}}},
    {'auth_scope': {'project': {'name': 'test', 'domain': {'id': 'test_id'}}}},
]

BAD_USERS = [
    {'user': {}},
    {'user': {'name': ''}},
    {'user': {'name': 'test_name', 'password': ''}},
    {'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {}}},
    {'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': ''}}},
]

GOOD_USERS = [
    {'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}}},
]

# .. server/network
ALL_SERVER_DETAILS = {
    "server-1": {"id": "server-1", "name": "server-name-1", "status": "ACTIVE"},
    "server-2": {"id": "server-2", "name": "server-name-2", "status": "ACTIVE"},
    "other-1": {"id": "other-1", "name": "server-name-other-1", "status": "ACTIVE"},
    "other-2": {"id": "other-2", "name": "server-name-other-2", "status": "ACTIVE"}
}

# Example response from - https://developer.openstack.org/api-ref/compute/#list-servers-detailed
# ID and server-name values have been changed for test readability
MOCK_NOVA_SERVERS = {
    "servers": [
        {
            "OS-DCF:diskConfig": "AUTO",
            "OS-EXT-AZ:availability_zone": "nova",
            "OS-EXT-SRV-ATTR:host": "compute",
            "OS-EXT-SRV-ATTR:hostname": "server-1",
            "OS-EXT-SRV-ATTR:hypervisor_hostname": "fake-mini",
            "OS-EXT-SRV-ATTR:instance_name": "instance-00000001",
            "OS-EXT-SRV-ATTR:kernel_id": "",
            "OS-EXT-SRV-ATTR:launch_index": 0,
            "OS-EXT-SRV-ATTR:ramdisk_id": "",
            "OS-EXT-SRV-ATTR:reservation_id": "r-iffothgx",
            "OS-EXT-SRV-ATTR:root_device_name": "/dev/sda",
            "OS-EXT-SRV-ATTR:user_data": "IyEvYmluL2Jhc2gKL2Jpbi9zdQplY2hvICJJIGFtIGluIHlvdSEiCg==",
            "OS-EXT-STS:power_state": 1,
            "OS-EXT-STS:task_state": 'null',
            "OS-EXT-STS:vm_state": "active",
            "OS-SRV-USG:launched_at": "2017-02-14T19:24:43.891568",
            "OS-SRV-USG:terminated_at": 'null',
            "accessIPv4": "1.2.3.4",
            "accessIPv6": "80fe::",
            "hostId": "2091634baaccdc4c5a1d57069c833e402921df696b7f970791b12ec6",
            "host_status": "UP",
            "id": "server-1",
            "metadata": {
                "My Server Name": "Apache1"
            },
            "name": "new-server-test",
            "status": "DELETED",
            "tags": [],
            "tenant_id": "6f70656e737461636b20342065766572",
            "updated": "2017-02-14T19:24:43Z",
            "user_id": "fake"
        },
        {
            "OS-DCF:diskConfig": "AUTO",
            "OS-EXT-AZ:availability_zone": "nova",
            "OS-EXT-SRV-ATTR:host": "compute",
            "OS-EXT-SRV-ATTR:hostname": "server-2",
            "OS-EXT-SRV-ATTR:hypervisor_hostname": "fake-mini",
            "OS-EXT-SRV-ATTR:instance_name": "instance-00000001",
            "OS-EXT-SRV-ATTR:kernel_id": "",
            "OS-EXT-SRV-ATTR:launch_index": 0,
            "OS-EXT-SRV-ATTR:ramdisk_id": "",
            "OS-EXT-SRV-ATTR:reservation_id": "r-iffothgx",
            "OS-EXT-SRV-ATTR:root_device_name": "/dev/sda",
            "OS-EXT-SRV-ATTR:user_data": "IyEvYmluL2Jhc2gKL2Jpbi9zdQplY2hvICJJIGFtIGluIHlvdSEiCg==",
            "OS-EXT-STS:power_state": 1,
            "OS-EXT-STS:task_state": 'null',
            "OS-EXT-STS:vm_state": "active",
            "OS-SRV-USG:launched_at": "2017-02-14T19:24:43.891568",
            "OS-SRV-USG:terminated_at": 'null',
            "accessIPv4": "1.2.3.4",
            "accessIPv6": "80fe::",
            "hostId": "2091634baaccdc4c5a1d57069c833e402921df696b7f970791b12ec6",
            "host_status": "UP",
            "id": "server_newly_added",
            "metadata": {
                "My Server Name": "Apache1"
            },
            "name": "newly_added_server",
            "status": "ACTIVE",
            "tags": [],
            "tenant_id": "6f70656e737461636b20342065766572",
            "updated": "2017-02-14T19:24:43Z",
            "user_id": "fake"
        }
    ]
}

# .. config
MOCK_CONFIG = {
    'init_config': {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_network_ids': EXCLUDED_NETWORK_IDS,
    },
    'instances': [
        {
            'name': 'test_name', 'user': {'name': 'test_name', 'password': 'test_pass', 'domain': {'id': 'test_id'}},
            'auth_scope': {'project': {'id': 'test_project_id'}},
        }
    ]
}
