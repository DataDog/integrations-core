# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import logging
import copy
import pytest
import simplejson as json

from datadog_checks.openstack_controller.api import SimpleApi, Authenticator, Credential
from datadog_checks.openstack_controller.exceptions import (IncompleteIdentity, MissingNovaEndpoint,
                                                            MissingNeutronEndpoint)
from . import common

log = logging.getLogger('test_openstack_controller')


def test_get_endpoint():
    authenticator = Authenticator()
    assert authenticator._get_nova_endpoint(
        common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876'
    with pytest.raises(MissingNovaEndpoint):
        authenticator._get_nova_endpoint({})

    assert authenticator._get_neutron_endpoint(common.EXAMPLE_AUTH_RESPONSE) == u'http://10.0.2.15:9292'
    with pytest.raises(MissingNeutronEndpoint):
        authenticator._get_neutron_endpoint({})

    assert authenticator._get_valid_endpoint({}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": []}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{}]}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [],
        u'type': u'compute',
        u'name': u'nova'}]}}, None, None) is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url', u'interface': u'dummy'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'interface': u'public'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') is None
    assert authenticator._get_valid_endpoint({'token': {"catalog": [{
        u'endpoints': [{u'url': u'dummy_url', u'interface': u'internal'}],
        u'type': u'compute',
        u'name': u'nova'}]}}, 'nova', 'compute') == 'dummy_url'


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


def _test_bad_user(user):
    authenticator = Authenticator()
    with pytest.raises(IncompleteIdentity):
        authenticator._get_user_identity(user['user'])


def test_get_user_identity():
    authenticator = Authenticator()
    for user in BAD_USERS:
        _test_bad_user(user)

    for user in GOOD_USERS:
        parsed_user = authenticator._get_user_identity(user['user'])
        assert parsed_user == {'methods': ['password'], 'password': user}


class MockHTTPResponse(object):
    def __init__(self, response_dict, headers):
        self.response_dict = response_dict
        self.headers = headers

    def json(self):
        return self.response_dict


PROJECTS_RESPONSE = [
        {},
        {
            "domain_id": "0000",
        },
        {
            "domain_id": "1111",
            "id": "0000",
        },
        {
            "domain_id": "2222",
            "id": "1111",
            "name": "name 1"
        },
        {
            "domain_id": "3333",
            "id": "2222",
            "name": "name 2"
        },
    ]

PROJECT_RESPONSE = [
        {
            "domain_id": "1111",
            "id": "3333",
            "name": "name 1"
        }
    ]


def test_from_config():
    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    with mock.patch('datadog_checks.openstack_controller.api.Authenticator._post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.api.Authenticator._get_auth_projects',
                        return_value=PROJECTS_RESPONSE):
            cred = Authenticator.from_config(log, 'http://10.0.2.15:5000', GOOD_USERS[0]['user'])
            assert isinstance(cred, Credential)
            assert cred.auth_token == "fake_token"
            assert cred.name == "name 2"
            assert cred.domain_id == "3333"
            assert cred.tenant_id == "2222"
            assert cred.nova_endpoint == "http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876"
            assert cred.neutron_endpoint == "http://10.0.2.15:9292"


def test_from_config_with_missing_name():
    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECT_RESPONSE)
    del project_response_without_name[0]["name"]

    with mock.patch('datadog_checks.openstack_controller.api.Authenticator._post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.api.Authenticator._get_auth_projects',
                        return_value=project_response_without_name):
            cred = Authenticator.from_config(log, 'http://10.0.2.15:5000', GOOD_USERS[0]['user'])
            assert cred is None


def test_from_config_with_missing_id():
    mock_http_response = copy.deepcopy(common.EXAMPLE_AUTH_RESPONSE)
    mock_response = MockHTTPResponse(response_dict=mock_http_response, headers={'X-Subject-Token': 'fake_token'})

    project_response_without_name = copy.deepcopy(PROJECT_RESPONSE)
    del project_response_without_name[0]["id"]

    with mock.patch('datadog_checks.openstack_controller.api.Authenticator._post_auth_token',
                    return_value=mock_response):
        with mock.patch('datadog_checks.openstack_controller.api.Authenticator._get_auth_projects',
                        return_value=project_response_without_name):
            cred = Authenticator.from_config(log, 'http://10.0.2.15:5000', GOOD_USERS[0]['user'])
            assert cred is None


def get_os_hypervisor_uptime_pre_v2_52_response(url, header, params=None, timeout=None):
    return json.loads("""{
        "hypervisor": {
            "hypervisor_hostname": "fake-mini",
            "id": 1,
            "state": "up",
            "status": "enabled",
            "uptime": " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"
        }
    }""")


def get_os_hypervisor_uptime_post_v2_53_response(url, header, params=None, timeout=None):
    return json.loads("""{
        "hypervisor": {
            "hypervisor_hostname": "fake-mini",
            "id": "b1e43b5f-eec1-44e0-9f10-7b4945c0226d",
            "state": "up",
            "status": "enabled",
            "uptime": " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"
        }
    }""")


def test_get_os_hypervisor_uptime(aggregator):
    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_os_hypervisor_uptime_pre_v2_52_response):
        api = SimpleApi(None, None)
        assert api.get_os_hypervisor_uptime(1) == \
            " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"

    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_os_hypervisor_uptime_post_v2_53_response):
        api = SimpleApi(None, None)
        assert api.get_os_hypervisor_uptime(1) == \
            " 08:32:11 up 93 days, 18:25, 12 users,  load average: 0.20, 0.12, 0.14"


def get_os_aggregates_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "aggregates": [
            {
                "availability_zone": "london",
                "created_at": "2016-12-27T23:47:32.911515",
                "deleted": false,
                "deleted_at": null,
                "hosts": [
                    "compute"
                ],
                "id": 1,
                "metadata": {
                    "availability_zone": "london"
                },
                "name": "name",
                "updated_at": null,
                "uuid": "6ba28ba7-f29b-45cc-a30b-6e3a40c2fb14"
            }
        ]
    }""")


def test_get_os_aggregates(aggregator):
    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_os_aggregates_response):
        api = SimpleApi(None, None)
        assert api.get_os_aggregates() == [
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
                "uuid": "6ba28ba7-f29b-45cc-a30b-6e3a40c2fb14"
            }
        ]


def get_os_hypervisors_detail_post_v2_33_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "hypervisors": [
            {
                "cpu_info": {
                    "arch": "x86_64",
                    "model": "Nehalem",
                    "vendor": "Intel",
                    "features": [
                        "pge",
                        "clflush"
                    ],
                    "topology": {
                        "cores": 1,
                        "threads": 1,
                        "sockets": 4
                    }
                },
                "current_workload": 0,
                "status": "enabled",
                "state": "up",
                "disk_available_least": 0,
                "host_ip": "1.1.1.1",
                "free_disk_gb": 1028,
                "free_ram_mb": 7680,
                "hypervisor_hostname": "host1",
                "hypervisor_type": "fake",
                "hypervisor_version": 1000,
                "id": 2,
                "local_gb": 1028,
                "local_gb_used": 0,
                "memory_mb": 8192,
                "memory_mb_used": 512,
                "running_vms": 0,
                "service": {
                    "host": "host1",
                    "id": 7,
                    "disabled_reason": null
                },
                "vcpus": 2,
                "vcpus_used": 0
            }
        ],
        "hypervisors_links": [
            {
                "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/hypervisors/detail?limit=1&marker=2",
                "rel": "next"
            }
        ]
    }""")  # noqa: E501


def get_os_hypervisors_detail_post_v2_53_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "hypervisors": [
            {
                "cpu_info": {
                    "arch": "x86_64",
                    "model": "Nehalem",
                    "vendor": "Intel",
                    "features": [
                        "pge",
                        "clflush"
                    ],
                    "topology": {
                        "cores": 1,
                        "threads": 1,
                        "sockets": 4
                    }
                },
                "current_workload": 0,
                "status": "enabled",
                "state": "up",
                "disk_available_least": 0,
                "host_ip": "1.1.1.1",
                "free_disk_gb": 1028,
                "free_ram_mb": 7680,
                "hypervisor_hostname": "host2",
                "hypervisor_type": "fake",
                "hypervisor_version": 1000,
                "id": "1bb62a04-c576-402c-8147-9e89757a09e3",
                "local_gb": 1028,
                "local_gb_used": 0,
                "memory_mb": 8192,
                "memory_mb_used": 512,
                "running_vms": 0,
                "service": {
                    "host": "host1",
                    "id": "62f62f6e-a713-4cbe-87d3-3ecf8a1e0f8d",
                    "disabled_reason": null
                },
                "vcpus": 2,
                "vcpus_used": 0
            }
        ],
        "hypervisors_links": [
            {
                "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/hypervisors/detail?limit=1&marker=1bb62a04-c576-402c-8147-9e89757a09e3",
                "rel": "next"
            }
        ]
    }""")  # noqa: E501


def test_get_os_hypervisors_detail(aggregator):
    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_os_hypervisors_detail_post_v2_33_response):
        api = SimpleApi(None, None)
        assert api.get_os_hypervisors_detail() == common.EXAMPLE_GET_OS_HYPERVISORS_RETURN_VALUE

    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_os_hypervisors_detail_post_v2_53_response):
        api = SimpleApi(None, None)
        assert api.get_os_hypervisors_detail() == [
            {
                "cpu_info": {
                    "arch": "x86_64",
                    "model": "Nehalem",
                    "vendor": "Intel",
                    "features": [
                        "pge",
                        "clflush"
                    ],
                    "topology": {
                        "cores": 1,
                        "threads": 1,
                        "sockets": 4
                    }
                },
                "current_workload": 0,
                "status": "enabled",
                "state": "up",
                "disk_available_least": 0,
                "host_ip": "1.1.1.1",
                "free_disk_gb": 1028,
                "free_ram_mb": 7680,
                "hypervisor_hostname": "host2",
                "hypervisor_type": "fake",
                "hypervisor_version": 1000,
                "id": "1bb62a04-c576-402c-8147-9e89757a09e3",
                "local_gb": 1028,
                "local_gb_used": 0,
                "memory_mb": 8192,
                "memory_mb_used": 512,
                "running_vms": 0,
                "service": {
                    "host": "host1",
                    "id": "62f62f6e-a713-4cbe-87d3-3ecf8a1e0f8d",
                    "disabled_reason": None
                },
                "vcpus": 2,
                "vcpus_used": 0
            }]


def get_servers_detail_post_v2_63_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "servers": [
            {
                "OS-DCF:diskConfig": "AUTO",
                "OS-EXT-AZ:availability_zone": "nova",
                "OS-EXT-SRV-ATTR:host": "compute",
                "OS-EXT-SRV-ATTR:hostname": "new-server-test",
                "OS-EXT-SRV-ATTR:hypervisor_hostname": "fake-mini",
                "OS-EXT-SRV-ATTR:instance_name": "instance-00000001",
                "OS-EXT-SRV-ATTR:kernel_id": "",
                "OS-EXT-SRV-ATTR:launch_index": 0,
                "OS-EXT-SRV-ATTR:ramdisk_id": "",
                "OS-EXT-SRV-ATTR:reservation_id": "r-y0w4v32k",
                "OS-EXT-SRV-ATTR:root_device_name": "/dev/sda",
                "OS-EXT-SRV-ATTR:user_data": "IyEvYmluL2Jhc2gKL2Jpbi9zdQplY2hvICJJIGFtIGluIHlvdSEiCg==",
                "OS-EXT-STS:power_state": 1,
                "OS-EXT-STS:task_state": null,
                "OS-EXT-STS:vm_state": "active",
                "OS-SRV-USG:launched_at": "2017-10-10T15:49:09.516729",
                "OS-SRV-USG:terminated_at": null,
                "accessIPv4": "1.2.3.4",
                "accessIPv6": "80fe::",
                "addresses": {
                    "private": [
                        {
                            "OS-EXT-IPS-MAC:mac_addr": "aa:bb:cc:dd:ee:ff",
                            "OS-EXT-IPS:type": "fixed",
                            "addr": "192.168.0.3",
                            "version": 4
                        }
                    ]
                },
                "config_drive": "",
                "created": "2017-10-10T15:49:08Z",
                "description": null,
                "flavor": {
                    "disk": 1,
                    "ephemeral": 0,
                    "extra_specs": {
                        "hw:cpu_policy": "dedicated",
                        "hw:mem_page_size": "2048"
                    },
                    "original_name": "m1.tiny.specs",
                    "ram": 512,
                    "swap": 0,
                    "vcpus": 1
                },
                "hostId": "2091634baaccdc4c5a1d57069c833e402921df696b7f970791b12ec6",
                "host_status": "UP",
                "id": "569f39f9-7c76-42a1-9c2d-8394e2638a6d",
                "image": {
                    "id": "70a599e0-31e7-49b7-b260-868f441e862b",
                    "links": [
                        {
                            "href": "http://openstack.example.com/6f70656e737461636b20342065766572/images/70a599e0-31e7-49b7-b260-868f441e862b",
                            "rel": "bookmark"
                        }
                    ]
                },
                "key_name": null,
                "links": [
                    {
                        "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/servers/569f39f9-7c76-42a1-9c2d-8394e2638a6d",
                        "rel": "self"
                    },
                    {
                        "href": "http://openstack.example.com/6f70656e737461636b20342065766572/servers/569f39f9-7c76-42a1-9c2d-8394e2638a6d",
                        "rel": "bookmark"
                    }
                ],
                "locked": false,
                "metadata": {
                    "My Server Name": "Apache1"
                },
                "name": "new-server-test",
                "os-extended-volumes:volumes_attached": [],
                "progress": 0,
                "security_groups": [
                    {
                        "name": "default"
                    }
                ],
                "status": "ACTIVE",
                "tags": [],
                "tenant_id": "6f70656e737461636b20342065766572",
                "trusted_image_certificates": [
                    "0b5d2c72-12cc-4ba6-a8d7-3ff5cc1d8cb8",
                    "674736e3-f25c-405c-8362-bbf991e0ce0a"
                ],
                "updated": "2017-10-10T15:49:09Z",
                "user_id": "fake"
            }
        ],
        "servers_links": [
            {
                "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/servers/detail?limit=1&marker=569f39f9-7c76-42a1-9c2d-8394e2638a6d",
                "rel": "next"
            }
        ]
    }""")  # noqa: E501


def test_get_servers_detail(aggregator):
    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_servers_detail_post_v2_63_response):
        api = SimpleApi(None, None)
        assert api.get_servers_detail(None) == [
            {
                "OS-DCF:diskConfig": "AUTO",
                "OS-EXT-AZ:availability_zone": "nova",
                "OS-EXT-SRV-ATTR:host": "compute",
                "OS-EXT-SRV-ATTR:hostname": "new-server-test",
                "OS-EXT-SRV-ATTR:hypervisor_hostname": "fake-mini",
                "OS-EXT-SRV-ATTR:instance_name": "instance-00000001",
                "OS-EXT-SRV-ATTR:kernel_id": "",
                "OS-EXT-SRV-ATTR:launch_index": 0,
                "OS-EXT-SRV-ATTR:ramdisk_id": "",
                "OS-EXT-SRV-ATTR:reservation_id": "r-y0w4v32k",
                "OS-EXT-SRV-ATTR:root_device_name": "/dev/sda",
                "OS-EXT-SRV-ATTR:user_data": "IyEvYmluL2Jhc2gKL2Jpbi9zdQplY2hvICJJIGFtIGluIHlvdSEiCg==",
                "OS-EXT-STS:power_state": 1,
                "OS-EXT-STS:task_state": None,
                "OS-EXT-STS:vm_state": "active",
                "OS-SRV-USG:launched_at": "2017-10-10T15:49:09.516729",
                "OS-SRV-USG:terminated_at": None,
                "accessIPv4": "1.2.3.4",
                "accessIPv6": "80fe::",
                "addresses": {
                    "private": [
                        {
                            "OS-EXT-IPS-MAC:mac_addr": "aa:bb:cc:dd:ee:ff",
                            "OS-EXT-IPS:type": "fixed",
                            "addr": "192.168.0.3",
                            "version": 4
                        }
                    ]
                },
                "config_drive": "",
                "created": "2017-10-10T15:49:08Z",
                "description": None,
                "flavor": {
                    "disk": 1,
                    "ephemeral": 0,
                    "extra_specs": {
                        "hw:cpu_policy": "dedicated",
                        "hw:mem_page_size": "2048"
                    },
                    "original_name": "m1.tiny.specs",
                    "ram": 512,
                    "swap": 0,
                    "vcpus": 1
                },
                "hostId": "2091634baaccdc4c5a1d57069c833e402921df696b7f970791b12ec6",
                "host_status": "UP",
                "id": "569f39f9-7c76-42a1-9c2d-8394e2638a6d",
                "image": {
                    "id": "70a599e0-31e7-49b7-b260-868f441e862b",
                    "links": [
                        {
                            "href": "http://openstack.example.com/6f70656e737461636b20342065766572/images/70a599e0-31e7-49b7-b260-868f441e862b",  # noqa: E501
                            "rel": "bookmark"
                        }
                    ]
                },
                "key_name": None,
                "links": [
                    {
                        "href": "http://openstack.example.com/v2.1/6f70656e737461636b20342065766572/servers/569f39f9-7c76-42a1-9c2d-8394e2638a6d",  # noqa: E501
                        "rel": "self"
                    },
                    {
                        "href": "http://openstack.example.com/6f70656e737461636b20342065766572/servers/569f39f9-7c76-42a1-9c2d-8394e2638a6d",  # noqa: E501
                        "rel": "bookmark"
                    }
                ],
                "locked": False,
                "metadata": {
                    "My Server Name": "Apache1"
                },
                "name": "new-server-test",
                "os-extended-volumes:volumes_attached": [],
                "progress": 0,
                "security_groups": [
                    {
                        "name": "default"
                    }
                ],
                "status": "ACTIVE",
                "tags": [],
                "tenant_id": "6f70656e737461636b20342065766572",
                "trusted_image_certificates": [
                    "0b5d2c72-12cc-4ba6-a8d7-3ff5cc1d8cb8",
                    "674736e3-f25c-405c-8362-bbf991e0ce0a"
                ],
                "updated": "2017-10-10T15:49:09Z",
                "user_id": "fake"
            }
        ]


def get_server_diagnostics_post_v2_48_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "config_drive": true,
        "cpu_details": [
            {
                "id": 0,
                "time": 17300000000,
                "utilisation": 15
            }
        ],
        "disk_details": [
            {
                "errors_count": 1,
                "read_bytes": 262144,
                "read_requests": 112,
                "write_bytes": 5778432,
                "write_requests": 488
            }
        ],
        "driver": "libvirt",
        "hypervisor": "kvm",
        "hypervisor_os": "ubuntu",
        "memory_details": {
            "maximum": 524288,
            "used": 0
        },
        "nic_details": [
            {
                "mac_address": "01:23:45:67:89:ab",
                "rx_drop": 200,
                "rx_errors": 100,
                "rx_octets": 2070139,
                "rx_packets": 26701,
                "rx_rate": 300,
                "tx_drop": 500,
                "tx_errors": 400,
                "tx_octets": 140208,
                "tx_packets": 662,
                "tx_rate": 600
            }
        ],
        "num_cpus": 1,
        "num_disks": 1,
        "num_nics": 1,
        "state": "running",
        "uptime": 46664
    }""")


def get_server_diagnostics_post_v2_1_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "cpu0_time": 17300000000,
        "memory": 524288,
        "vda_errors": -1,
        "vda_read": 262144,
        "vda_read_req": 112,
        "vda_write": 5778432,
        "vda_write_req": 488,
        "vnet1_rx": 2070139,
        "vnet1_rx_drop": 0,
        "vnet1_rx_errors": 0,
        "vnet1_rx_packets": 26701,
        "vnet1_tx": 140208,
        "vnet1_tx_drop": 0,
        "vnet1_tx_errors": 0,
        "vnet1_tx_packets": 662
    }""")


def test_get_server_diagnostics(aggregator):
    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_server_diagnostics_post_v2_48_response):
        api = SimpleApi(None, None)
        assert api.get_server_diagnostics(None) == {
            "config_drive": True,
            "cpu_details": [
                {
                    "id": 0,
                    "time": 17300000000,
                    "utilisation": 15
                }
            ],
            "disk_details": [
                {
                    "errors_count": 1,
                    "read_bytes": 262144,
                    "read_requests": 112,
                    "write_bytes": 5778432,
                    "write_requests": 488
                }
            ],
            "driver": "libvirt",
            "hypervisor": "kvm",
            "hypervisor_os": "ubuntu",
            "memory_details": {
                "maximum": 524288,
                "used": 0
            },
            "nic_details": [
                {
                    "mac_address": "01:23:45:67:89:ab",
                    "rx_drop": 200,
                    "rx_errors": 100,
                    "rx_octets": 2070139,
                    "rx_packets": 26701,
                    "rx_rate": 300,
                    "tx_drop": 500,
                    "tx_errors": 400,
                    "tx_octets": 140208,
                    "tx_packets": 662,
                    "tx_rate": 600
                }
            ],
            "num_cpus": 1,
            "num_disks": 1,
            "num_nics": 1,
            "state": "running",
            "uptime": 46664
        }

    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_server_diagnostics_post_v2_1_response):
        api = SimpleApi(None, None)
        assert api.get_server_diagnostics(None) == {
            "cpu0_time": 17300000000,
            "memory": 524288,
            "vda_errors": -1,
            "vda_read": 262144,
            "vda_read_req": 112,
            "vda_write": 5778432,
            "vda_write_req": 488,
            "vnet1_rx": 2070139,
            "vnet1_rx_drop": 0,
            "vnet1_rx_errors": 0,
            "vnet1_rx_packets": 26701,
            "vnet1_tx": 140208,
            "vnet1_tx_drop": 0,
            "vnet1_tx_errors": 0,
            "vnet1_tx_packets": 662
        }


def get_project_limits_response(url, headers, params=None, timeout=None):
    return json.loads("""{
        "limits": {
            "absolute": {
                "maxImageMeta": 128,
                "maxPersonality": 5,
                "maxPersonalitySize": 10240,
                "maxSecurityGroupRules": 20,
                "maxSecurityGroups": 10,
                "maxServerMeta": 128,
                "maxTotalCores": 20,
                "maxTotalFloatingIps": 10,
                "maxTotalInstances": 10,
                "maxTotalKeypairs": 100,
                "maxTotalRAMSize": 51200,
                "maxServerGroups": 10,
                "maxServerGroupMembers": 10,
                "totalCoresUsed": 0,
                "totalInstancesUsed": 0,
                "totalRAMUsed": 0,
                "totalSecurityGroupsUsed": 0,
                "totalFloatingIpsUsed": 0,
                "totalServerGroupsUsed": 0
            },
            "rate": []
        }
    }""")


def test_get_project_limits(aggregator):
    with mock.patch('datadog_checks.openstack_controller.api.SimpleApi._make_request',
                    side_effect=get_project_limits_response):
        api = SimpleApi(None, None)
        assert api.get_project_limits(None) == common.EXAMPLE_GET_PROJECT_LIMITS_RETURN_VALUE
