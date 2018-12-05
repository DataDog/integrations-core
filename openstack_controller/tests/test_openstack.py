# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time
import mock
from . import common
from datadog_checks.openstack_controller import OpenStackControllerCheck


def test_parse_uptime_string():
    instance = common.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])
    uptime_parsed = check._parse_uptime_string(
        u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n')
    assert uptime_parsed.get('loads') == [0.04, 0.14, 0.19]


def test_cache_utils():
    instance = common.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])
    check.CACHE_TTL['aggregates'] = 1
    expected_aggregates = {'hyp_1': ['aggregate:staging', 'availability_zone:test']}

    with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_aggregate_hypervisors',
                    return_value=expected_aggregates):
        assert check._get_and_set_aggregate_list() == expected_aggregates
        time.sleep(1.5)
        assert check._is_expired('aggregates')


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            return_value=common.MOCK_NOVA_SERVERS)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="tenant-1")
def test_cache_between_runs(*args):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    check.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    # Update the cached list of servers based on what the endpoint returns
    check.get_all_servers(None, "test_instance")

    cached_servers = check.server_details_by_id
    assert 'server-1' not in cached_servers
    assert 'server_newly_added' in cached_servers


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            return_value=common.MOCK_NOVA_SERVERS)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="None")
def test_project_name_none(*args):
    """
    Ensure the cache contains the expected VMs between check runs.
    """
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    check.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    # Update the cached list of servers based on what the endpoint returns
    check.get_all_servers(None, "test_instance")
    assert 'server_newly_added' in check.server_details_by_id
    assert 'server-1' not in check.server_details_by_id


def get_server_details_response(params, timeout=None):
    if 'marker' not in params:
        return common.MOCK_NOVA_SERVERS_PAGINATED
    return common.EMPTY_NOVA_SERVERS


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
            side_effect=get_server_details_response)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="proj_name")
def test_get_paginated_server(*args):
    """
    Ensure the server cache is updated while using pagination
    """

    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
        'paginated_server_limit': 1
    }, {}, instances=common.MOCK_CONFIG)
    check.get_all_servers(None, "test_instance")
    assert len(check.server_details_by_id) == 1
    assert 'server-1' in check.server_details_by_id


OS_AGGREGATES_RESPONSE = {
    "aggregates": [
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
}


def get_diagnostics_pre_2_48_response(url, headers=None, params=None, timeout=None):
    if "diagnostics" in url:
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
    if "os-aggregates" in url:
        return OS_AGGREGATES_RESPONSE


def test_get_stats_for_single_server_pre_2_48(aggregator, *args):

    with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck._make_request_with_auth_fallback',
                    side_effect=get_diagnostics_pre_2_48_response):
        with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_nova_endpoint',
                        return_value="http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876"):
            with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_auth_token',
                            return_value="test_auth_token"):
                openstackCheck = OpenStackControllerCheck("test", {
                    'keystone_server_url': 'http://10.0.2.15:5000',
                    'ssl_verify': False,
                    'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
                    'paginated_server_limit': 1
                }, {}, instances=common.MOCK_CONFIG)

                openstackCheck.get_stats_for_single_server({})

        aggregator.assert_metric('openstack.nova.server.vda_read_req', value=112.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.vda_read', value=262144.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.memory', value=524288.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.cpu0_time', value=17300000000.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.vda_write_req', value=488.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.vda_write', value=5778432.0,
                                 tags=['availability_zone:NA'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx', value=140208.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx', value=2070139.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx_packets', value=662.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx_packets', value=26701.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet1'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx', value=140208.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx', value=2070139.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx_packets', value=662.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx_packets', value=26701.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')
        aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                 tags=['availability_zone:NA', 'interface:vnet2'],
                                 hostname='')

    aggregator.assert_all_metrics_covered()
