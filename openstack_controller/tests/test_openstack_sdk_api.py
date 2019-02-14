import mock
import pytest

from openstack.exceptions import SDKException

from datadog_checks.openstack_controller.api import OpenstackSDKApi
from datadog_checks.openstack_controller.exceptions import (AuthenticationNeeded, KeystoneUnreachable,
                                                            MissingNovaEndpoint, MissingNeutronEndpoint)
from . import common


EXAMPLE_PROJECTS_VALUE = [
    {
        'id': u'680031a39ce040e1b81289ea8c73fb11',
        'domain_id': u'default',
        'name': u'admin',
        'parent_id': u'default',
        'properties': {},
        'is_enabled': True,
        'is_domain': False,
        'description': u'Bootstrap project for initializing the cloud.',
        'enabled': True,
        'location': {
            'project': {
                'domain_id': u'default',
                'id': u'default',
                'name': None,
                'domain_name': None
            },
            'zone': None,
            'region_name': None,
            'cloud': 'test_cloud'
        }
    },
    {
        'id': u'69db552bcb5e41ad925b388e73d73dbe',
        'domain_id': u'default',
        'name': u'testProj1',
        'parent_id': u'default',
        'properties': {},
        'is_enabled': True,
        'is_domain': False,
        'description': u'test project',
        'enabled': True,
        'location': {
            'project': {
                'domain_id': u'default',
                'id': u'default',
                'name': None,
                'domain_name': None
            },
            'zone': None,
            'region_name': None,
            'cloud': 'test_cloud'
        }
    }
]

EXAMPLE_COMPUTE_LIMITS_VALUE = {
    'total_server_groups_used': 0,
    'max_server_groups': 10,
    'total_instances_used': 0,
    'max_total_ram_size': 51200,
    'total_ram_used': 0,
    'total_cores_used': 0,
    'max_total_cores': 20,
    'max_personality_size': 10240,
    'max_total_keypairs': 100,
    'max_server_group_members': 10,
    'location': {
        'project': {
            'domain_id': None,
            'id': u'680031a39ce040e1b81289ea8c73fb11',
            'name': None,
            'domain_name': None
        },
        'zone': None,
        'region_name': 'RegionOne',
        'cloud': 'test_cloud'
    },
    'max_personality': 5,
    'max_total_instances': 10,
    'properties': {
        u'totalFloatingIpsUsed': 0,
        u'maxSecurityGroupRules': 20,
        u'totalSecurityGroupsUsed': 0,
        u'maxImageMeta': 128,
        u'maxSecurityGroups': 10,
        u'maxTotalFloatingIps': 10
    },
    'max_server_meta': 128
}

EXAMPLE_AGGREGATES_VALUE = [
    {
        "availability_zone": "london",
        "created_at": "2016-12-27T23:47:32.911515",
        "deleted": False,
        "deleted_at": None,
        "hosts": [
            "compute"
        ],
        "id": 1,
        "metadata": {
            "availability_zone": "london"
        },
        "name": "name",
        "updated_at": None,
        # "uuid" is not returned by OpenstackSDKApi
        # "uuid": "6ba28ba7-f29b-45cc-a30b-6e3a40c2fb14"
    }
]

EXAMPLE_FLAVORS_VALUE = [
    {
        'name': u'test_flavor',
        'ephemeral': 0,
        'ram': 1024,
        'is_disabled': False,
        'properties': {
            u'OS-FLV-DISABLED:disabled': False,
            u'OS-FLV-EXT-DATA:ephemeral': 0,
            u'os-flavor-access:is_public': True
        },
        u'OS-FLV-DISABLED:disabled': False,
        'vcpus': 2,
        'extra_specs': {},
        'location': {
            'project': {
                'domain_id': None,
                'id': u'0123456789abcdef',
                'name': 'testProj2',
                'domain_name': None
            },
            'zone': None,
            'region_name': 'RegionOne',
            'cloud': 'test_cloud'
        },
        u'os-flavor-access:is_public': True,
        'rxtx_factor': 2.0,
        'is_public': True,
        u'OS-FLV-EXT-DATA:ephemeral': 0,
        'disk': 10,
        'id': u'10',
        'swap': 0
    },
    {
        'name': u'FinalTestHopefully',
        'ephemeral': 0,
        'ram': 5934,
        'is_disabled': False,
        'properties': {
            u'OS-FLV-DISABLED:disabled': False,
            u'OS-FLV-EXT-DATA:ephemeral': 0,
            u'os-flavor-access:is_public': True
        },
        u'OS-FLV-DISABLED:disabled': False,
        'vcpus': 8,
        'extra_specs': {},
        'location': {
            'project': {
                'domain_id': None,
                'id': u'0123456789abcdef',
                'name': 'testProj2',
                'domain_name': None
            },
            'zone': None,
            'region_name': 'RegionOne',
            'cloud': 'test_cloud'
        },
        u'os-flavor-access:is_public': True,
        'rxtx_factor': 1.0,
        'is_public': True,
        u'OS-FLV-EXT-DATA:ephemeral': 0,
        'disk': 48,
        'id': u'625c2e4b-0a1f-4236-bb67-5ceee1a766e5',
        'swap': 0
    }
]


EXAMPLE_NETWORKS_VALUE = [
    {
        u'status': u'ACTIVE',
        u'subnets': [],
        u'description': u'',
        u'provider:physical_network': None,
        u'tags': [],
        u'ipv6_address_scope': None,
        u'updated_at': u'2018-08-16T20:22:34Z',
        u'is_default': False,
        u'revision_number': 4,
        u'port_security_enabled': False,
        u'mtu': 1450,
        u'id': u'2755452c-4fe8-4ba1-9b26-8898665b0958',
        u'provider:segmentation_id': 91,
        u'router:external': True,
        u'availability_zone_hints': [
            u'nova'
        ],
        u'availability_zones': [],
        u'name': u'net2',
        u'admin_state_up': True,
        u'tenant_id': u'680031a39ce040e1b81289ea8c73fb11',
        u'created_at': u'2018-08-16T20:22:34Z',
        u'provider:network_type': u'vxlan',
        u'ipv4_address_scope': None,
        u'shared': False,
        u'project_id': u'680031a39ce040e1b81289ea8c73fb11'
    }
]


class MockOpenstackConnection:
    def __init__(self):
        pass

    def get_service(self, service_name):
        if service_name == u'keystone':
            return {
                'description': None,
                'service_type': u'identity',
                'type': u'identity',
                'enabled': True,
                'id': u'cb1478c7210540dfa0ddffeeea017167',
                'name': u'keystone'
            }
        elif service_name == u'nova':
            return {
                'description': u'Nova Compute Service',
                'service_type': u'compute',
                'type': u'compute',
                'enabled': True,
                'id': u'30b4e3ac5e7a4cf5b83c9f7226705d1f',
                'name': u'nova'
            }

        elif service_name == u'neutron':
            return {
                'description': u'OpenStack Networking',
                'service_type': u'network',
                'type': u'network',
                'enabled': True,
                'id': u'97557fe6cb0f409bbf2e586ef169a6f4',
                'name': u'neutron'
            }

        return None

    def search_endpoints(self, filters):
        if filters[u'service_id'] == u'cb1478c7210540dfa0ddffeeea017167':
            return [
                {
                    u'region_id': u'RegionOne',
                    u'links': {
                        u'self': u'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'
                    },
                    u'url': u'http://10.0.3.44:5000/v3',
                    u'region': u'RegionOne',
                    u'enabled': True,
                    u'interface': u'public',
                    u'service_id': u'cb1478c7210540dfa0ddffeeea017167',
                    u'id': u'a536052eba574bd4baf89ff83e3a23db'
                },
                {
                    u'region_id': u'RegionOne',
                    u'links': {
                        u'self': u'http://10.0.3.44:5000/v3/endpoints/abe4ce9a9b6947ecbcba164430b9febe'
                    },
                    u'url': u'http://172.29.236.101:5000/v3',
                    u'region': u'RegionOne',
                    u'enabled': True,
                    u'interface': u'internal',
                    u'service_id': u'cb1478c7210540dfa0ddffeeea017167',
                    u'id': u'abe4ce9a9b6947ecbcba164430b9febe'
                }
            ]

        elif filters[u'service_id'] == u'30b4e3ac5e7a4cf5b83c9f7226705d1f':
            return [
                {
                    u'region_id': u'RegionOne',
                    u'links': {
                        u'self': u'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'
                    },
                    u'url': u'http://10.0.3.229:8774/v2.1/%(tenant_id)s',
                    u'region': u'RegionOne',
                    u'enabled': True,
                    u'interface': u'public',
                    u'service_id': u'30b4e3ac5e7a4cf5b83c9f7226705d1f',
                    u'id': u'0adb9d108440437fa6841d31a989ed89'
                },
                {
                    u'region_id': u'RegionOne',
                    u'links': {
                        u'self': u'http://10.0.3.44:5000/v3/endpoints/195bc656072447edba7c311a35de47a2'
                    },
                    u'url': u'http://172.29.236.101:8774/v2.1/%(tenant_id)s',
                    u'region': u'RegionOne',
                    u'enabled': True,
                    u'interface': u'admin',
                    u'service_id': u'30b4e3ac5e7a4cf5b83c9f7226705d1f',
                    u'id': u'195bc656072447edba7c311a35de47a2'
                }
            ]

        elif filters[u'service_id'] == u'97557fe6cb0f409bbf2e586ef169a6f4':
            return [
                {
                    u'region_id': u'RegionOne',
                    u'links': {
                        u'self': u'http://10.0.3.44:5000/v3/endpoints/6f9e5a99c33545bb88c62dad9b28d1ca'
                    },
                    u'url': u'http://172.29.236.101:9696',
                    u'region': u'RegionOne',
                    u'enabled': True,
                    u'interface': u'admin',
                    u'service_id': u'97557fe6cb0f409bbf2e586ef169a6f4',
                    u'id': u'6f9e5a99c33545bb88c62dad9b28d1ca'
                },
                {
                    u'region_id': u'RegionOne',
                    u'links': {
                        u'self': u'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'
                    },
                    u'url': u'http://172.29.236.101:9696',
                    u'region': u'RegionOne',
                    u'enabled': True,
                    u'interface': u'internal',
                    u'service_id': u'97557fe6cb0f409bbf2e586ef169a6f4',
                    u'id': u'408fbfd00abf4bd1a71044f4849abf66'
                }
            ]

        return []

    def get_compute_limits(self, project_id):
        if project_id == u'680031a39ce040e1b81289ea8c73fb11':
            return EXAMPLE_COMPUTE_LIMITS_VALUE
        raise SDKException()

    def search_projects(self):
        return EXAMPLE_PROJECTS_VALUE

    def list_hypervisors(self):
        return common.EXAMPLE_GET_OS_HYPERVISORS_RETURN_VALUE

    def list_aggregates(self):
        return EXAMPLE_AGGREGATES_VALUE

    def list_networks(self):
        return EXAMPLE_NETWORKS_VALUE

    def search_flavors(self, filters):
        return EXAMPLE_FLAVORS_VALUE


def test_get_endpoint():
    api = OpenstackSDKApi(None)

    with pytest.raises(AuthenticationNeeded):
        api._check_authentication()

    api.connection = MockOpenstackConnection()

    assert api.get_keystone_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'
    assert api.get_nova_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'
    assert api.get_neutron_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'

    # Test cache
    assert api.get_keystone_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'
    assert api.get_nova_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'
    assert api.get_neutron_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'

    with mock.patch('datadog_checks.openstack_controller.api.OpenstackSDKApi._get_service',
                    return_value={u'id': 'invalid_id'}):
        api.endpoints = {}
        with pytest.raises(KeystoneUnreachable):
            api.get_keystone_endpoint()

        with pytest.raises(MissingNovaEndpoint):
            api.get_nova_endpoint()

        with pytest.raises(MissingNeutronEndpoint):
            api.get_neutron_endpoint()


def test_get_project():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_projects() == EXAMPLE_PROJECTS_VALUE


def test_get_project_limit():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_project_limits(u'680031a39ce040e1b81289ea8c73fb11') == common.EXAMPLE_GET_PROJECT_LIMITS_RETURN_VALUE
    with pytest.raises(SDKException):
        api.get_project_limits('invalid_id')


def test_get_os_hypervisors_detail():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_os_hypervisors_detail() == common.EXAMPLE_GET_OS_HYPERVISORS_RETURN_VALUE


def test_get_os_aggregates():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_os_aggregates() == EXAMPLE_AGGREGATES_VALUE


def test_get_flavors_detail():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_flavors_detail(query_params={}) == EXAMPLE_FLAVORS_VALUE


def test_get_networks():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_networks() == EXAMPLE_NETWORKS_VALUE
