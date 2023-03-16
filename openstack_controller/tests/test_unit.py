# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import mock
import pytest
from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.dev import get_here
from datadog_checks.openstack_controller import OpenStackControllerCheck

pytestmark = [pytest.mark.unit]


# @pytest.mark.parametrize(
#     'instance, expected_exception',
#     [
#         pytest.param(
#             {},
#             pytest.raises(
#                 Exception, match='Either `keystone_server_url` or `openstack_config_file_path` need to be configured'
#             ),
#             id='keystone_server_url_not_configured',
#         ),
#         pytest.param(
#             {'keystone_server_url': 'http://127.0.0.1/identity'},
#             pytest.raises(Exception, match='`user_name` and `user_password` need to be configured'),
#             id='user_name_not_configured',
#         ),
#         pytest.param(
#             {'keystone_server_url': 'http://127.0.0.1/identity', 'user_name': 'admin'},
#             pytest.raises(Exception, match='`user_name` and `user_password` need to be configured'),
#             id='user_password_not_configured',
#         ),
#         pytest.param(
#             {
#                 'keystone_server_url': 'http://127.0.0.1:8080/identity',
#                 'user_name': 'admin',
#                 'user_password': 'password',
#             },
#             does_not_raise(),
#             id='ok',
#         ),
#     ],
# )
# def test_config_validation(
#     aggregator,
#     dd_run_check,
#     instance,
#     expected_exception,
# ):
#     with expected_exception, mock.patch(
#         'datadog_checks.openstack_controller.openstack_controller.make_api'
#     ) as mocked_api, open(os.path.join(get_here(), 'fixtures/empty_projects.json'), 'r') as empty_projects:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(empty_projects)
#         mocked_api.return_value = api
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)


def test_connect_exception(aggregator, dd_run_check):
    with pytest.raises(Exception), mock.patch(
        'datadog_checks.openstack_controller.openstack_controller.make_api'
    ) as mocked_api:
        api = mock.MagicMock()
        api.create_connection.side_effect = [Exception()]
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)


def test_connect_http_error(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api:
        api = mock.MagicMock()
        api.create_connection.side_effect = [HTTPError()]
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.keystone.api.up', status=check.CRITICAL)


def test_connect_ok(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/empty_projects.json'), 'r'
    ) as empty_projects:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(empty_projects)
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.keystone.api.up', status=AgentCheck.OK)


def test_nova_endpoint_down(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(two_projects)
        api.get_compute_response_time.return_value = None
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.CRITICAL)


def test_compute_response_time(aggregator, dd_run_check):
    compute_response_time = 2.659812
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(two_projects)
        api.get_compute_response_time.return_value = compute_response_time
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric('openstack.nova.response_time', compute_response_time)
        aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)


def test_compute_limits(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects, open(os.path.join(get_here(), 'fixtures/compute_limits.json'), 'r') as compute_limits:
        two_projects_content = json.load(two_projects)
        compute_limits_content = json.load(compute_limits)
        api = mock.MagicMock()
        api.get_projects.return_value = two_projects_content
        api.get_compute_limits.return_value = compute_limits_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in compute_limits_content.items():
            aggregator.assert_metric(f'openstack.nova.limits.{metric}', value)


def test_compute_quota_set(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects, open(os.path.join(get_here(), 'fixtures/compute_quota_set.json'), 'r') as compute_quota_set:
        two_projects_content = json.load(two_projects)
        compute_quota_set_content = json.load(compute_quota_set)
        api = mock.MagicMock()
        api.get_projects.return_value = two_projects_content
        api.get_compute_quota_set.return_value = compute_quota_set_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in compute_quota_set_content.items():
            aggregator.assert_metric(f'openstack.nova.quota_set.{metric}', value)


def test_compute_servers(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects, open(os.path.join(get_here(), 'fixtures/compute_servers.json'), 'r') as compute_servers:
        two_projects_content = json.load(two_projects)
        compute_servers_content = json.load(compute_servers)
        api = mock.MagicMock()
        api.get_projects.return_value = two_projects_content
        api.get_compute_servers.return_value = compute_servers_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _server_id, server_data in compute_servers_content.items():
            for metric, value in server_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.servers.{metric}', value)


def test_compute_flavors(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects, open(os.path.join(get_here(), 'fixtures/compute_flavors.json'), 'r') as compute_flavors:
        two_projects_content = json.load(two_projects)
        compute_flavors_content = json.load(compute_flavors)
        api = mock.MagicMock()
        api.get_projects.return_value = two_projects_content
        api.get_compute_flavors.return_value = compute_flavors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _flavor_id, flavor_data in compute_flavors_content.items():
            for metric, value in flavor_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.flavors.{metric}', value)


def test_network_endpoint_down(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(two_projects)
        api.get_network_response_time.return_value = None
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.CRITICAL)


def test_network_response_time(aggregator, dd_run_check):
    compute_response_time = 2.659812
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as two_projects:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(two_projects)
        api.get_network_response_time.return_value = compute_response_time
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric('openstack.neutron.response_time', compute_response_time)
        aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
