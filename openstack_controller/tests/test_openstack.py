# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
from copy import deepcopy

import mock
import pytest
from mock import ANY

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.api import AbstractApi
from datadog_checks.openstack_controller.exceptions import IncompleteConfig

from . import common

pytestmark = pytest.mark.unit


def test_parse_uptime_string(aggregator):
    instance = copy.deepcopy(common.KEYSTONE_INSTANCE)
    instance['tags'] = ['optional:tag1']
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, [instance])
    response = u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n'
    uptime_parsed = check._parse_uptime_string(response)
    assert uptime_parsed == [0.04, 0.14, 0.19]


@mock.patch(
    'datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
    return_value=common.MOCK_NOVA_SERVERS,
)
def test_populate_servers_cache_between_runs(servers_detail, aggregator):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    check = OpenStackControllerCheck("test", {'ssl_verify': False}, [common.KEYSTONE_INSTANCE])

    # Start off with a list of servers
    check.servers_cache = copy.deepcopy(common.SERVERS_CACHE_MOCK)
    # Update the cached list of servers based on what the endpoint returns
    check.populate_servers_cache(
        {
            'testproj': {"id": '6f70656e737461636b20342065766572', "name": "testproj"},
            'blacklist_1': {"id": 'blacklist_1', "name": 'blacklist_1'},
            'blacklist_2': {"id": 'blacklist_2', "name": 'blacklist_2'},
        },
        [],
    )
    servers = check.servers_cache['servers']
    assert 'server-1' not in servers
    assert 'server_newly_added' in servers
    assert 'other-1' in servers
    assert 'other-2' in servers


@mock.patch(
    'datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
    return_value=common.MOCK_NOVA_SERVERS,
)
def test_populate_servers_cache_with_project_name_none(servers_detail, aggregator):
    """
    Ensure the cache contains the expected VMs between check runs.
    """
    check = OpenStackControllerCheck("test", {'ssl_verify': False}, [copy.deepcopy(common.KEYSTONE_INSTANCE)])

    # Start off with a list of servers
    check.servers_cache = copy.deepcopy(common.SERVERS_CACHE_MOCK)
    # Update the cached list of servers based on what the endpoint returns
    check.populate_servers_cache(
        {
            '': {"id": '6f70656e737461636b20342065766572', "name": None},
            'blacklist_1': {"id": 'blacklist_1', "name": 'blacklist_1'},
            'blacklist_2': {"id": 'blacklist_2', "name": 'blacklist_2'},
        },
        [],
    )
    servers = check.servers_cache['servers']
    assert 'server_newly_added' not in servers
    assert 'server-1' not in servers
    assert 'other-1' in servers
    assert 'other-2' in servers


@mock.patch('datadog_checks.openstack_controller.api.ApiFactory.create', return_value=mock.MagicMock(AbstractApi))
def test_check(mock_api, aggregator):
    check = OpenStackControllerCheck("test", {'ssl_verify': False}, [common.KEYSTONE_INSTANCE])

    check.check(common.KEYSTONE_INSTANCE)

    aggregator.assert_service_check('openstack.keystone.api.up', AgentCheck.OK)
    aggregator.assert_service_check('openstack.nova.api.up', AgentCheck.OK)
    aggregator.assert_service_check('openstack.neutron.api.up', AgentCheck.OK)
    mock_api.assert_called_with(ANY, common.KEYSTONE_INSTANCE, ANY)


@mock.patch('datadog_checks.openstack_controller.api.ApiFactory.create', return_value=mock.MagicMock(AbstractApi))
def test_check_with_config_file(mock_api, aggregator):
    check = OpenStackControllerCheck("test", {'ssl_verify': False}, [common.CONFIG_FILE_INSTANCE])

    check.check(common.CONFIG_FILE_INSTANCE)

    aggregator.assert_service_check('openstack.keystone.api.up', AgentCheck.OK)
    aggregator.assert_service_check('openstack.nova.api.up', AgentCheck.OK)
    aggregator.assert_service_check('openstack.neutron.api.up', AgentCheck.OK)
    mock_api.assert_called_with(ANY, common.CONFIG_FILE_INSTANCE, ANY)


def get_server_details_response(params):
    if 'marker' not in params:
        return common.MOCK_NOVA_SERVERS_PAGINATED
    return common.EMPTY_NOVA_SERVERS


@mock.patch(
    'datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
    side_effect=get_server_details_response,
)
def test_get_paginated_server(servers_detail, aggregator):
    """
    Ensure the server cache is updated while using pagination
    """

    check = OpenStackControllerCheck(
        "test", {'ssl_verify': False, 'paginated_server_limit': 1}, [common.KEYSTONE_INSTANCE]
    )
    check.populate_servers_cache({'testproj': {"id": "6f70656e737461636b20342065766572", "name": "testproj"}}, [])
    servers = check.servers_cache['servers']
    assert 'server-1' in servers
    assert 'other-1' not in servers
    assert 'other-2' not in servers


OS_AGGREGATES_RESPONSE = [
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
        "uuid": "6ba28ba7-f29b-45cc-a30b-6e3a40c2fb14",
    }
]


def get_server_diagnostics_pre_2_48_response(server_id):
    return {
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
        "vnet1_tx_packets": 662,
        "vnet2_rx": 2070139,
        "vnet2_rx_drop": 0,
        "vnet2_rx_errors": 0,
        "vnet2_rx_packets": 26701,
        "vnet2_tx": 140208,
        "vnet2_tx_drop": 0,
        "vnet2_tx_errors": 0,
        "vnet2_tx_packets": 662,
    }


@mock.patch(
    'datadog_checks.openstack_controller.OpenStackControllerCheck.get_server_diagnostics',
    side_effect=get_server_diagnostics_pre_2_48_response,
)
@mock.patch(
    'datadog_checks.openstack_controller.OpenStackControllerCheck.get_os_aggregates',
    return_value=OS_AGGREGATES_RESPONSE,
)
def test_collect_server_metrics_pre_2_48(server_diagnostics, os_aggregates, aggregator):
    check = OpenStackControllerCheck(
        "test", {'ssl_verify': False, 'paginated_server_limit': 1}, [common.KEYSTONE_INSTANCE]
    )

    check.collect_server_diagnostic_metrics({})

    aggregator.assert_metric(
        'openstack.nova.server.vda_read_req', value=112.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.vda_read', value=262144.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.memory', value=524288.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.cpu0_time', value=17300000000.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.vda_errors', value=-1.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.vda_write_req', value=488.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.vda_write', value=5778432.0, tags=['nova_managed_server', 'availability_zone:NA'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx_drop',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx',
        value=140208.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx_drop',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx',
        value=2070139.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx_packets',
        value=662.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx_errors',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx_packets',
        value=26701.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx_errors',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx_drop',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx',
        value=140208.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx_drop',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx',
        value=2070139.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx_packets',
        value=662.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.tx_errors',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx_packets',
        value=26701.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )
    aggregator.assert_metric(
        'openstack.nova.server.rx_errors',
        value=0.0,
        tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
    )

    aggregator.assert_all_metrics_covered()


def test_get_keystone_url_from_openstack_config():
    check = OpenStackControllerCheck(
        "test", {'ssl_verify': False, 'paginated_server_limit': 1}, [common.CONFIG_FILE_INSTANCE]
    )
    keystone_server_url = check._get_keystone_server_url(common.CONFIG_FILE_INSTANCE)
    assert keystone_server_url == 'http://xxx.xxx.xxx.xxx:5000/v2.0/'


def test_get_keystone_url_from_datadog_config():
    check = OpenStackControllerCheck(
        "test", {'ssl_verify': False, 'paginated_server_limit': 1}, [common.KEYSTONE_INSTANCE]
    )
    keystone_server_url = check._get_keystone_server_url(common.KEYSTONE_INSTANCE)
    assert keystone_server_url == 'http://10.0.2.15:5000'


def test_get_keystone_url_from_implicit_openstack_config():
    # This test is for documentation purposes because it is really testing OpenStackConfig
    instance = copy.deepcopy(common.CONFIG_FILE_INSTANCE)
    instance['openstack_cloud_name'] = 'rackspace'
    check = OpenStackControllerCheck("test", {}, [instance])
    keystone_server_url = check._get_keystone_server_url(instance)
    assert keystone_server_url == 'https://identity.api.rackspacecloud.com/v2.0/'


def test_missing_keystone_server_url():
    # This test is for documentation purposes because it is really testing OpenStackConfig
    instance = copy.deepcopy(common.KEYSTONE_INSTANCE)
    instance['keystone_server_url'] = None
    check = OpenStackControllerCheck("test", {}, [instance])

    with pytest.raises(IncompleteConfig):
        check._get_keystone_server_url(instance)


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("new config", {'tls_verify': True, 'timeout': 3}, {'verify': True, 'timeout': (3.0, 3.0)}),
        ("legacy config", {'ssl_verify': True, 'request_timeout': 5}, {'verify': True, 'timeout': (5.0, 5.0)}),
    ],
)
def test_config(test_case, extra_config, expected_http_kwargs):
    instance = deepcopy(common.KEYSTONE_INSTANCE)
    instance.update(extra_config)
    check = OpenStackControllerCheck('openstack_controller', {}, instances=[instance])

    for key, value in expected_http_kwargs.items():
        assert check.http.options[key] == value, "Expected '{}' to be {} but was {}".format(
            key, value, check.http.options[key]
        )
