# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
# import re
# import mock
# from . import common
# from datadog_checks.openstack_controller import OpenStackControllerCheck


# @mock.patch('datadog_checks.openstack_controller.OpenStackControllerCheck.get_networks',
#             return_value=common.ALL_IDS)
# def test_network_exclusion(network_ids):
#     """
#     Exclude networks using regular expressions.
#     """
#     instance = common.MOCK_CONFIG["instances"][0]
#     instance['tags'] = ['optional:tag1']
#     init_config = common.MOCK_CONFIG['init_config']
#     check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])
#
#     check.exclude_network_id_rules = set([re.compile(rule) for rule in common.EXCLUDED_NETWORK_IDS])
#
#     # Retrieve network stats
#     check.get_network_stats([])
#
#     # Assert
#     # .. 1 out of 4 network filtered in
#     assert mock_get_stats_single_network.call_count == 1
#     assert mock_get_stats_single_network.call_args[0][0] == common.FILTERED_NETWORK_ID
#
#     # cleanup
#     check.exclude_network_id_rules = set([])
