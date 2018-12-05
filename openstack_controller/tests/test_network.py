# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import re
import mock
import conftest
from . import common
from datadog_checks.openstack_controller import OpenStackControllerCheck


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_network_ids',
            return_value=conftest.ALL_IDS)
def test_server_exclusion(network_ids):
    """
    Exclude servers using regular expressions.
    """
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'exclude_server_ids': conftest.EXCLUDED_SERVER_IDS
    }, {}, instances=conftest.MOCK_CONFIG)

    # Retrieve servers
    check.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    check.filter_excluded_servers()
    server_ids = check.server_details_by_id
    # Assert
    # .. 1 out of 4 server ids filtered
    assert len(server_ids) == 1

    # Ensure the server IDs filtered are the ones expected
    for server_id in server_ids:
        assert server_id in conftest.FILTERED_SERVER_ID


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_network_ids',
            return_value=common.ALL_SERVER_DETAILS)
def test_server_exclusion_by_project(network_ids):
    """
    Exclude servers using regular expressions.
    """
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False,
        'blacklist_project_names': ["blacklist*"]
    }, {}, instances=conftest.MOCK_CONFIG)

    # Retrieve servers
    check.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    check.filter_excluded_servers()
    server_ids = check.server_details_by_id
    # Assert
    # .. 2 out of 4 server ids filtered
    assert len(server_ids) == 2

    # Ensure the server IDs filtered are the ones expected
    for server_id in server_ids:
        assert server_id in conftest.FILTERED_BY_PROJ_SERVER_ID


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_network_ids',
            return_value=common.ALL_SERVER_DETAILS)
def test_server_include_all_by_default(network_ids):
    """
    Exclude servers using regular expressions.
    """
    check = OpenStackControllerCheck("test", {
        'keystone_server_url': 'http://10.0.2.15:5000',
        'ssl_verify': False
    }, {}, instances=conftest.MOCK_CONFIG)

    # Retrieve servers
    check.server_details_by_id = copy.deepcopy(common.ALL_SERVER_DETAILS)
    check.filter_excluded_servers()
    server_ids = check.server_details_by_id
    # Assert
    # All 4 servers should still be monitored
    assert len(server_ids) == 4


@mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_network_ids',
            return_value=conftest.ALL_IDS)
def test_network_exclusion(network_ids):
    """
    Exclude networks using regular expressions.
    """
    instance = conftest.MOCK_CONFIG["instances"][0]
    instance['tags'] = ['optional:tag1']
    init_config = conftest.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])

    with mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_stats_for_single_network') \
            as mock_get_stats_single_network:
        check.exclude_network_id_rules = set([re.compile(rule) for rule in conftest.EXCLUDED_NETWORK_IDS])

        # Retrieve network stats
        check.get_network_stats([])

        # Assert
        # .. 1 out of 4 network filtered in
        assert mock_get_stats_single_network.call_count == 1
        assert mock_get_stats_single_network.call_args[0][0] == conftest.FILTERED_NETWORK_ID

        # cleanup
        check.exclude_network_id_rules = set([])
