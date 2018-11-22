# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import re
import time
import mock
import pytest

from . import common

from datadog_checks.openstack_controller import OpenStackControllerCheck

instance = common.MOCK_CONFIG["instances"][0]
instance['tags'] = ['optional:tag1']
init_config = common.MOCK_CONFIG['init_config']
openstack_check = OpenStackControllerCheck('openstack', init_config, {}, instances=[instance])


@pytest.fixture
def aggregator():
    from datadog_checks.stubs import aggregator
    aggregator.reset()
    return aggregator


def test_parse_uptime_string():
    uptime_parsed = openstack_check._parse_uptime_string(
        u' 16:53:48 up 1 day, 21:34,  3 users,  load average: 0.04, 0.14, 0.19\n')
    assert uptime_parsed.get('loads') == [0.04, 0.14, 0.19]


def test_cache_utils():
    openstack_check.CACHE_TTL['aggregates'] = 1
    expected_aggregates = {'hyp_1': ['aggregate:staging', 'availability_zone:test']}

    with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_aggregate_hypervisors',
                    return_value=expected_aggregates):
        assert openstack_check._get_and_set_aggregate_list() == expected_aggregates
        time.sleep(1.5)
        assert openstack_check._is_expired('aggregates')


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_servers',
            return_value=common.ALL_SERVER_DETAILS)
def test_server_exclusion(*args):
    """
    Exclude servers using regular expressions.
    """
    openstackCheck = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Retrieve servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    openstackCheck.filter_excluded_servers()
    server_ids = openstackCheck.server_details_by_id
    # Assert
    # .. 1 out of 4 server ids filtered
    assert len(server_ids) == 1

    # Ensure the server IDs filtered are the ones expected
    for server_id in server_ids:
        assert server_id in common.FILTERED_SERVER_ID


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_servers',
            return_value=common.ALL_SERVER_DETAILS)
def test_server_exclusion_by_project(*args):
    """
    Exclude servers using regular expressions.
    """
    openstackCheck = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'blacklist_project_names': ["blacklist*"]
    }, {}, instances=common.MOCK_CONFIG)

    # Retrieve servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    openstackCheck.filter_excluded_servers()
    server_ids = openstackCheck.server_details_by_id
    # Assert
    # .. 2 out of 4 server ids filtered
    assert len(server_ids) == 2

    # Ensure the server IDs filtered are the ones expected
    for server_id in server_ids:
        assert server_id in common.FILTERED_BY_PROJ_SERVER_ID


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_servers',
            return_value=common.ALL_SERVER_DETAILS)
def test_server_include_all_by_default(*args):
    """
    Exclude servers using regular expressions.
    """
    openstackCheck = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False
    }, {}, instances=common.MOCK_CONFIG)

    # Retrieve servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    openstackCheck.filter_excluded_servers()
    server_ids = openstackCheck.server_details_by_id
    # Assert
    # All 4 servers should still be monitored
    assert len(server_ids) == 4


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_all_network_ids',
            return_value=common.ALL_IDS)
def test_network_exclusion(*args):
    """
    Exclude networks using regular expressions.
    """
    with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_stats_for_single_network') \
            as mock_get_stats_single_network:

        openstack_check.exclude_network_id_rules = set([re.compile(rule) for rule in common.EXCLUDED_NETWORK_IDS])

        # Retrieve network stats
        openstack_check.get_network_stats([])

        # Assert
        # .. 1 out of 4 network filtered in
        assert mock_get_stats_single_network.call_count == 1
        assert mock_get_stats_single_network.call_args[0][0] == common.FILTERED_NETWORK_ID

        # cleanup
        openstack_check.exclude_network_id_rules = set([])


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck._make_request_with_auth_fallback',
            return_value=common.MOCK_NOVA_SERVERS)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_nova_endpoint',
            return_value="http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876")
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_auth_token',
            return_value="test_auth_token")
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="tenant-1")
def test_cache_between_runs(*args):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    openstackCheck = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    i_key = "test_instance"

    # Update the cached list of servers based on what the endpoint returns
    openstackCheck.get_all_servers(i_key)

    cached_servers = openstackCheck.server_details_by_id
    assert 'server-1' not in cached_servers
    assert 'server_newly_added' in cached_servers


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck._make_request_with_auth_fallback',
            return_value=common.MOCK_NOVA_SERVERS)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_nova_endpoint',
            return_value="http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876")
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_auth_token',
            return_value="test_auth_token")
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="None")
def test_project_name_none(*args):
    """
    Ensure the cache contains the expected VMs between check runs.
    """

    openstackCheck = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS
    }, {}, instances=common.MOCK_CONFIG)

    # Start off with a list of servers
    openstackCheck.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    i_key = "test_instance"

    # Update the cached list of servers based on what the endpoint returns
    openstackCheck.get_all_servers(i_key)
    assert 'server_newly_added' in openstackCheck.server_details_by_id
    assert 'server-1' not in openstackCheck.server_details_by_id


def get_server_details_response(self, url, headers=None, params=None, timeout=None):
    if 'marker' not in params:
        return common.MOCK_NOVA_SERVERS_PAGINATED
    return common.EMPTY_NOVA_SERVERS


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck._make_request_with_auth_fallback',
            side_effect=get_server_details_response)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_nova_endpoint',
            return_value="http://10.0.2.15:8774/v2.1/0850707581fe4d738221a72db0182876", autospec=True)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_auth_token',
            return_value="test_auth_token", autospec=True)
@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
            return_value="None", autospec=True)
def test_get_paginated_server(*args):
    """
    Ensure the server cache is updated while using pagination
    """

    openstackCheck = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
        'paginated_server_limit': 1
    }, {}, instances=common.MOCK_CONFIG)

    i_key = "test_instance"
    openstackCheck.get_all_servers(i_key)
    assert len(openstackCheck.server_details_by_id) == 1
    assert 'server-1' in openstackCheck.server_details_by_id
