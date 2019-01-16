# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import copy
from . import common
from datadog_checks.openstack_controller import OpenStackControllerCheck


def test_parse_uptime_string(aggregator):
    instance = common.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])
    response = u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n'
    uptime_parsed = check._parse_uptime_string(response)
    assert uptime_parsed == [0.04, 0.14, 0.19]


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            return_value=common.MOCK_NOVA_SERVERS)
def test_get_all_servers_between_runs(servers_detail, aggregator):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    check.servers_cache = copy.deepcopy(common.SERVERS_CACHE_MOCK)
    # Update the cached list of servers based on what the endpoint returns
    check.get_all_servers({'6f70656e737461636b20342065766572': 'testproj',
                           'blacklist_1': 'blacklist_1',
                           'blacklist_2': 'blacklist_2'}, "test_name", [])
    servers = check.servers_cache['test_name']['servers']
    assert 'server-1' not in servers
    assert 'server_newly_added' in servers
    assert 'other-1' in servers
    assert 'other-2' in servers


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            return_value=common.MOCK_NOVA_SERVERS)
def test_get_all_servers_with_project_name_none(servers_detail, aggregator):
    """
    Ensure the cache contains the expected VMs between check runs.
    """
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    check.servers_cache = copy.deepcopy(common.SERVERS_CACHE_MOCK)
    # Update the cached list of servers based on what the endpoint returns
    check.get_all_servers({'6f70656e737461636b20342065766572': None,
                           'blacklist_1': 'blacklist_1',
                           'blacklist_2': 'blacklist_2'}, "test_name", [])
    servers = check.servers_cache['test_name']['servers']
    assert 'server_newly_added' not in servers
    assert 'server-1' not in servers
    assert 'other-1' in servers
    assert 'other-2' in servers


def get_server_details_response(params, timeout=None):
    if 'marker' not in params:
        return common.MOCK_NOVA_SERVERS_PAGINATED
    return common.EMPTY_NOVA_SERVERS


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            side_effect=get_server_details_response)
def test_get_paginated_server(servers_detail, aggregator):
    """
    Ensure the server cache is updated while using pagination
    """

    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
        'paginated_server_limit': 1
    }, {}, instances=common.MOCK_CONFIG)
    check.get_all_servers({"6f70656e737461636b20342065766572": "testproj"}, "test_name", [])
    assert len(check.servers_cache) == 1
    servers = check.servers_cache['test_name']['servers']
    assert 'server-1' in servers
    assert 'other-1' not in servers
    assert 'other-2' not in servers


OS_AGGREGATES_RESPONSE = [
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
        "vnet2_tx_packets": 662
    }


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_server_diagnostics',
            side_effect=get_server_diagnostics_pre_2_48_response)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_os_aggregates',
            return_value=OS_AGGREGATES_RESPONSE)
def test_collect_server_metrics_pre_2_48(server_diagnostics, os_aggregates, aggregator):
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
        'paginated_server_limit': 1
    }, {}, instances=common.MOCK_CONFIG)

    check.collect_server_diagnostic_metrics({})

    aggregator.assert_metric('openstack.nova.server.vda_read_req', value=112.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_read', value=262144.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.memory', value=524288.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.cpu0_time', value=17300000000.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_write_req', value=488.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.vda_write', value=5778432.0,
                             tags=['nova_managed_server', 'availability_zone:NA'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx', value=140208.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx', value=2070139.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_packets', value=662.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_packets', value=26701.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet1'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx', value=140208.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx', value=2070139.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_packets', value=662.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_packets', value=26701.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')
    aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                             tags=['nova_managed_server', 'availability_zone:NA', 'interface:vnet2'],
                             hostname='')

    aggregator.assert_all_metrics_covered()
