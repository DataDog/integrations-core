# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

import mock
import pytest
from openstack.exceptions import SDKException

from datadog_checks.openstack_controller.legacy.api import OpenstackSDKApi
from datadog_checks.openstack_controller.legacy.exceptions import (
    AuthenticationNeeded,
    KeystoneUnreachable,
    MissingNeutronEndpoint,
    MissingNovaEndpoint,
)

from . import common

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.environ.get('OPENSTACK_E2E_LEGACY') is None or os.environ.get('OPENSTACK_E2E_LEGACY') == 'false',
        reason='Legacy test',
    ),
]

EXAMPLE_PROJECTS_VALUE = [
    {
        'id': '680031a39ce040e1b81289ea8c73fb11',
        'domain_id': 'default',
        'name': 'admin',
        'parent_id': 'default',
        'properties': {},
        'is_enabled': True,
        'is_domain': False,
        'description': 'Bootstrap project for initializing the cloud.',
        'enabled': True,
        'location': {
            'project': {'domain_id': 'default', 'id': 'default', 'name': None, 'domain_name': None},
            'zone': None,
            'region_name': None,
            'cloud': 'test_cloud',
        },
    },
    {
        'id': '69db552bcb5e41ad925b388e73d73dbe',
        'domain_id': 'default',
        'name': 'testProj1',
        'parent_id': 'default',
        'properties': {},
        'is_enabled': True,
        'is_domain': False,
        'description': 'test project',
        'enabled': True,
        'location': {
            'project': {'domain_id': 'default', 'id': 'default', 'name': None, 'domain_name': None},
            'zone': None,
            'region_name': None,
            'cloud': 'test_cloud',
        },
    },
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
        'project': {'domain_id': None, 'id': '680031a39ce040e1b81289ea8c73fb11', 'name': None, 'domain_name': None},
        'zone': None,
        'region_name': 'RegionOne',
        'cloud': 'test_cloud',
    },
    'max_personality': 5,
    'max_total_instances': 10,
    'properties': {
        'totalFloatingIpsUsed': 0,
        'maxSecurityGroupRules': 20,
        'totalSecurityGroupsUsed': 0,
        'maxImageMeta': 128,
        'maxSecurityGroups': 10,
        'maxTotalFloatingIps': 10,
    },
    'max_server_meta': 128,
}

EXAMPLE_AGGREGATES_VALUE = [
    {
        "availability_zone": "london",
        "created_at": "2016-12-27T23:47:32.911515",
        "deleted": False,
        "deleted_at": None,
        "hosts": ["compute"],
        "id": 1,
        "metadata": {"availability_zone": "london"},
        "name": "name",
        "updated_at": None,
        # "uuid" is not returned by OpenstackSDKApi
        # "uuid": "6ba28ba7-f29b-45cc-a30b-6e3a40c2fb14"
    }
]

EXAMPLE_FLAVORS_VALUE = [
    {
        'name': 'test_flavor',
        'ephemeral': 0,
        'ram': 1024,
        'is_disabled': False,
        'properties': {
            'OS-FLV-DISABLED:disabled': False,
            'OS-FLV-EXT-DATA:ephemeral': 0,
            'os-flavor-access:is_public': True,
        },
        'OS-FLV-DISABLED:disabled': False,
        'vcpus': 2,
        'extra_specs': {},
        'location': {
            'project': {'domain_id': None, 'id': '0123456789abcdef', 'name': 'testProj2', 'domain_name': None},
            'zone': None,
            'region_name': 'RegionOne',
            'cloud': 'test_cloud',
        },
        'os-flavor-access:is_public': True,
        'rxtx_factor': 2.0,
        'is_public': True,
        'OS-FLV-EXT-DATA:ephemeral': 0,
        'disk': 10,
        'id': '10',
        'swap': 0,
    },
    {
        'name': 'FinalTestHopefully',
        'ephemeral': 0,
        'ram': 5934,
        'is_disabled': False,
        'properties': {
            'OS-FLV-DISABLED:disabled': False,
            'OS-FLV-EXT-DATA:ephemeral': 0,
            'os-flavor-access:is_public': True,
        },
        'OS-FLV-DISABLED:disabled': False,
        'vcpus': 8,
        'extra_specs': {},
        'location': {
            'project': {'domain_id': None, 'id': '0123456789abcdef', 'name': 'testProj2', 'domain_name': None},
            'zone': None,
            'region_name': 'RegionOne',
            'cloud': 'test_cloud',
        },
        'os-flavor-access:is_public': True,
        'rxtx_factor': 1.0,
        'is_public': True,
        'OS-FLV-EXT-DATA:ephemeral': 0,
        'disk': 48,
        'id': '625c2e4b-0a1f-4236-bb67-5ceee1a766e5',
        'swap': 0,
    },
]


EXAMPLE_NETWORKS_VALUE = [
    {
        'status': 'ACTIVE',
        'subnets': [],
        'description': '',
        'provider:physical_network': None,
        'tags': [],
        'ipv6_address_scope': None,
        'updated_at': '2018-08-16T20:22:34Z',
        'is_default': False,
        'revision_number': 4,
        'port_security_enabled': False,
        'mtu': 1450,
        'id': '2755452c-4fe8-4ba1-9b26-8898665b0958',
        'provider:segmentation_id': 91,
        'router:external': True,
        'availability_zone_hints': ['nova'],
        'availability_zones': [],
        'name': 'net2',
        'admin_state_up': True,
        'tenant_id': '680031a39ce040e1b81289ea8c73fb11',
        'created_at': '2018-08-16T20:22:34Z',
        'provider:network_type': 'vxlan',
        'ipv4_address_scope': None,
        'shared': False,
        'project_id': '680031a39ce040e1b81289ea8c73fb11',
    }
]


class MockOpenstackConnection:
    def __init__(self):
        pass

    def get_service(self, service_name):
        if service_name == 'keystone':
            return {
                'description': None,
                'service_type': 'identity',
                'type': 'identity',
                'enabled': True,
                'id': 'cb1478c7210540dfa0ddffeeea017167',
                'name': 'keystone',
            }
        elif service_name == 'nova':
            return {
                'description': 'Nova Compute Service',
                'service_type': 'compute',
                'type': 'compute',
                'enabled': True,
                'id': '30b4e3ac5e7a4cf5b83c9f7226705d1f',
                'name': 'nova',
            }

        elif service_name == 'neutron':
            return {
                'description': 'OpenStack Networking',
                'service_type': 'network',
                'type': 'network',
                'enabled': True,
                'id': '97557fe6cb0f409bbf2e586ef169a6f4',
                'name': 'neutron',
            }

        return None

    def search_endpoints(self, filters):
        if filters['service_id'] == 'cb1478c7210540dfa0ddffeeea017167':
            return [
                {
                    'region_id': 'RegionOne',
                    'links': {'self': 'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'},
                    'url': 'http://10.0.3.44:5000/v3',
                    'region': 'RegionOne',
                    'enabled': True,
                    'interface': 'public',
                    'service_id': 'cb1478c7210540dfa0ddffeeea017167',
                    'id': 'a536052eba574bd4baf89ff83e3a23db',
                },
                {
                    'region_id': 'RegionOne',
                    'links': {'self': 'http://10.0.3.44:5000/v3/endpoints/abe4ce9a9b6947ecbcba164430b9febe'},
                    'url': 'http://172.29.236.101:5000/v3',
                    'region': 'RegionOne',
                    'enabled': True,
                    'interface': 'internal',
                    'service_id': 'cb1478c7210540dfa0ddffeeea017167',
                    'id': 'abe4ce9a9b6947ecbcba164430b9febe',
                },
            ]

        elif filters['service_id'] == '30b4e3ac5e7a4cf5b83c9f7226705d1f':
            return [
                {
                    'region_id': 'RegionOne',
                    'links': {'self': 'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'},
                    'url': 'http://10.0.3.229:8774/v2.1/%(tenant_id)s',
                    'region': 'RegionOne',
                    'enabled': True,
                    'interface': 'public',
                    'service_id': '30b4e3ac5e7a4cf5b83c9f7226705d1f',
                    'id': '0adb9d108440437fa6841d31a989ed89',
                },
                {
                    'region_id': 'RegionOne',
                    'links': {'self': 'http://10.0.3.44:5000/v3/endpoints/195bc656072447edba7c311a35de47a2'},
                    'url': 'http://172.29.236.101:8774/v2.1/%(tenant_id)s',
                    'region': 'RegionOne',
                    'enabled': True,
                    'interface': 'admin',
                    'service_id': '30b4e3ac5e7a4cf5b83c9f7226705d1f',
                    'id': '195bc656072447edba7c311a35de47a2',
                },
            ]

        elif filters['service_id'] == '97557fe6cb0f409bbf2e586ef169a6f4':
            return [
                {
                    'region_id': 'RegionOne',
                    'links': {'self': 'http://10.0.3.44:5000/v3/endpoints/6f9e5a99c33545bb88c62dad9b28d1ca'},
                    'url': 'http://172.29.236.101:9696',
                    'region': 'RegionOne',
                    'enabled': True,
                    'interface': 'admin',
                    'service_id': '97557fe6cb0f409bbf2e586ef169a6f4',
                    'id': '6f9e5a99c33545bb88c62dad9b28d1ca',
                },
                {
                    'region_id': 'RegionOne',
                    'links': {'self': 'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'},
                    'url': 'http://172.29.236.101:9696',
                    'region': 'RegionOne',
                    'enabled': True,
                    'interface': 'internal',
                    'service_id': '97557fe6cb0f409bbf2e586ef169a6f4',
                    'id': '408fbfd00abf4bd1a71044f4849abf66',
                },
            ]

        return []

    def get_compute_limits(self, project_id):
        if project_id == '680031a39ce040e1b81289ea8c73fb11':
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

    def get_network_quotas(self, project, details=False):
        if not details:
            return {}
        return {'floatingip': {'used': 1, 'limit': 10}}


def test_get_endpoint():
    api = OpenstackSDKApi(None)

    with pytest.raises(AuthenticationNeeded):
        api._check_authentication()

    api.connection = MockOpenstackConnection()

    assert api.get_keystone_endpoint() == 'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'
    assert api.get_nova_endpoint() == 'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'
    assert api.get_neutron_endpoint() == 'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'

    # Test cache
    assert api.get_keystone_endpoint() == 'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'
    assert api.get_nova_endpoint() == 'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'
    assert api.get_neutron_endpoint() == 'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'

    with mock.patch(
        'datadog_checks.openstack_controller.legacy.api.OpenstackSDKApi._get_service',
        return_value={'id': 'invalid_id'},
    ):
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

    assert api.get_project_limits('680031a39ce040e1b81289ea8c73fb11') == common.EXAMPLE_GET_PROJECT_LIMITS_RETURN_VALUE
    with pytest.raises(SDKException):
        api.get_project_limits('invalid_id')


def test_get_os_hypervisors_detail():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_os_hypervisors_detail() == common.EXAMPLE_GET_OS_HYPERVISORS_RETURN_VALUE


def test_get_os_aggregates():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    aggregates = api.get_os_aggregates()

    for i in range(len(aggregates)):
        for key, value in common.EXAMPLE_GET_OS_AGGREGATES_RETURN_VALUE[i].items():
            assert value == aggregates[i][key]


def test_get_flavors_detail():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    flavors = api.get_flavors_detail(query_params={})
    for i in range(len(flavors)):
        for key, value in common.EXAMPLE_GET_FLAVORS_DETAIL_RETURN_VALUE[i].items():
            assert value == flavors[i][key]


def test_get_networks():
    api = OpenstackSDKApi(None)
    api.connection = MockOpenstackConnection()

    networks = api.get_networks()
    for i in range(len(networks)):
        for key, value in common.EXAMPLE_GET_NETWORKS_RETURN_VALUE[i].items():
            assert value == networks[i][key]
