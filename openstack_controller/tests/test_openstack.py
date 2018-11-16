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
    check.get_all_servers("test_instance")

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
    check.get_all_servers("test_instance")
    assert 'server_newly_added' in check.server_details_by_id
    assert 'server-1' not in check.server_details_by_id


def get_server_details_response(self, query_params, timeout=None):
    if 'marker' not in query_params:
        return common.MOCK_NOVA_SERVERS_PAGINATED
    return common.EMPTY_NOVA_SERVERS


# @mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_servers_detail',
#             side_effect=get_server_details_response)
# @mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_project_name_from_id',
#             return_value=None, autospec=True)
# def test_get_paginated_server(*args):
#     """
#     Ensure the server cache is updated while using pagination
#     """
#
#     check = OpenStackControllerCheck("test", {
#         'keystone_server_url': 'http://10.0.2.15:5000',
#         'ssl_verify': False,
#         'exclude_server_ids': common.EXCLUDED_SERVER_IDS,
#         'paginated_server_limit': 1
#     }, {}, instances=common.MOCK_CONFIG)
#
#     check.get_all_servers("test_instance")
#     assert len(check.server_details_by_id) == 1
#     assert 'server-1' in check.server_details_by_id
