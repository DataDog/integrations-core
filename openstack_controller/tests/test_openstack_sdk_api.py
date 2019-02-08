import mock
import pytest

from datadog_checks.openstack_controller.api import OpenstackSdkApi
from datadog_checks.openstack_controller.exceptions import (KeystoneUnreachable, MissingNovaEndpoint,
                                                            MissingNeutronEndpoint)


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

    def search_endpoints(self, filter):
        if filter[u'service_id'] == u'cb1478c7210540dfa0ddffeeea017167':
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

        elif filter[u'service_id'] == u'30b4e3ac5e7a4cf5b83c9f7226705d1f':
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

        elif filter[u'service_id'] == u'97557fe6cb0f409bbf2e586ef169a6f4':
            return [
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
                },
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
                }
            ]

        return []


def test_get_endpoint():
    api = OpenstackSdkApi(None)
    api.connection = MockOpenstackConnection()

    assert api.get_keystone_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/a536052eba574bd4baf89ff83e3a23db'
    assert api.get_nova_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/0adb9d108440437fa6841d31a989ed89'
    assert api.get_neutron_endpoint() == u'http://10.0.3.44:5000/v3/endpoints/408fbfd00abf4bd1a71044f4849abf66'

    with mock.patch('datadog_checks.openstack_controller.api.OpenstackSdkApi._get_endpoint', return_value=None):
        with pytest.raises(KeystoneUnreachable):
            api.get_keystone_endpoint()

        with pytest.raises(MissingNovaEndpoint):
            api.get_nova_endpoint()

        with pytest.raises(MissingNeutronEndpoint):
            api.get_neutron_endpoint()
