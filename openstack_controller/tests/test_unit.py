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
from datadog_checks.openstack_controller.openstack_controller import LEGACY_NOVA_HYPERVISOR_METRICS

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
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
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
    response_time = 2.659812
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
        api.get_compute_response_time.return_value = response_time
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric('openstack.nova.response_time', response_time)
        aggregator.assert_service_check('openstack.nova.api.up', status=AgentCheck.OK)


def test_compute_limits(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/limits.json'), 'r'
    ) as limits:
        one_project_content = json.load(one_project)
        limits_content = json.load(limits)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_limits.return_value = limits_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in limits_content.items():
            aggregator.assert_metric(f'openstack.nova.limits.{metric}', value)


def test_compute_limits_nova_microversion_last(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_last/limits.json'), 'r'
    ) as limits:
        one_project_content = json.load(one_project)
        limits_content = json.load(limits)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_limits.return_value = limits_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'nova_microversion': 'last',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in limits_content.items():
            aggregator.assert_metric(f'openstack.nova.limits.{metric}', value)


def test_compute_quota_set(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/quota_set.json'), 'r'
    ) as quota_set:
        one_project_content = json.load(one_project)
        quota_set_content = json.load(quota_set)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_quota_set.return_value = quota_set_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in quota_set_content.items():
            aggregator.assert_metric(f'openstack.nova.quota_set.{metric}', value)


def test_compute_quota_set_nova_microversion_last(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_last/quota_set.json'), 'r'
    ) as quota_set:
        one_project_content = json.load(one_project)
        quota_set_content = json.load(quota_set)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_quota_set.return_value = quota_set_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'nova_microversion': 'last',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in quota_set_content.items():
            aggregator.assert_metric(f'openstack.nova.quota_set.{metric}', value)


def test_compute_servers(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/servers.json'), 'r'
    ) as servers:
        one_project_content = json.load(one_project)
        servers_content = json.load(servers)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_servers.return_value = servers_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _server_id, server_data in servers_content.items():
            for metric, value in server_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.server.{metric}', value)


def test_compute_servers_nova_microversion_last(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_last/servers.json'), 'r'
    ) as servers:
        one_project_content = json.load(one_project)
        servers_content = json.load(servers)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_servers.return_value = servers_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'nova_microversion': 'last',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _server_id, server_data in servers_content.items():
            for metric, value in server_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.server.{metric}', value)


def test_compute_flavors(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/flavors.json'), 'r'
    ) as flavors:
        one_project_content = json.load(one_project)
        flavors_content = json.load(flavors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_flavors.return_value = flavors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _flavor_id, flavor_data in flavors_content.items():
            for metric, value in flavor_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.flavor.{metric}', value)


def test_compute_flavors_nova_microversion_last(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_last/flavors.json'), 'r'
    ) as flavors:
        one_project_content = json.load(one_project)
        flavors_content = json.load(flavors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_flavors.return_value = flavors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'nova_microversion': 'last',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _flavor_id, flavor_data in flavors_content.items():
            for metric, value in flavor_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.flavor.{metric}', value)


def test_collect_hypervisor_metrics_false(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
    ) as hypervisors:
        one_project_content = json.load(one_project)
        hypervisors_content = json.load(hypervisors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_hypervisors_detail.return_value = hypervisors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'collect_hypervisor_metrics': False,
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _hypervisor_id, hypervisor_data in hypervisors_content.items():
            for metric, _value in hypervisor_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.hypervisor.{metric}', count=0)


def test_compute_hypervisors_detail(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
    ) as hypervisors:
        one_project_content = json.load(one_project)
        hypervisors_content = json.load(hypervisors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_hypervisors_detail.return_value = hypervisors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _hypervisor_id, hypervisor_data in hypervisors_content.items():
            for metric, value in hypervisor_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.hypervisor.{metric}', value)


def test_compute_hypervisors_detail_nova_microversion_last(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_last/hypervisors_detail.json'), 'r'
    ) as hypervisors:
        one_project_content = json.load(one_project)
        hypervisors_content = json.load(hypervisors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_hypervisors_detail.return_value = hypervisors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'nova_microversion': 'last',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for _hypervisor_id, hypervisor_data in hypervisors_content.items():
            for metric, value in hypervisor_data['metrics'].items():
                aggregator.assert_metric(f'openstack.nova.hypervisor.{metric}', value)


def test_network_endpoint_down(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
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
    response_time = 2.659812
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
        api.get_network_response_time.return_value = response_time
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric('openstack.neutron.response_time', response_time)
        aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)


def test_network_quotas(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(os.path.join(get_here(), 'fixtures/network/quotas.json'), 'r') as quotas:
        one_project_content = json.load(one_project)
        quotas_content = json.load(quotas)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_network_quotas.return_value = quotas_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric, value in quotas_content.items():
            aggregator.assert_metric(f'openstack.neutron.quotas.{metric}', value)


def test_baremetal_endpoint_down(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
        api.get_baremetal_response_time.return_value = None
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.CRITICAL)


def test_baremetal_response_time(aggregator, dd_run_check):
    response_time = 2.659812
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
        api.get_baremetal_response_time.return_value = response_time
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric('openstack.ironic.response_time', response_time)
        aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)


def test_load_balancer_endpoint_down(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
        api.get_load_balancer_response_time.return_value = None
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.CRITICAL)


def test_load_balancer_response_time(aggregator, dd_run_check):
    response_time = 2.659812
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project:
        api = mock.MagicMock()
        api.get_projects.return_value = json.load(one_project)
        api.get_load_balancer_response_time.return_value = response_time
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        aggregator.assert_metric('openstack.octavia.response_time', response_time)
        aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)


def test_report_legacy_metrics_default(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
    ) as hypervisors:
        one_project_content = json.load(one_project)
        hypervisors_content = json.load(hypervisors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_hypervisors_detail.return_value = hypervisors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric in LEGACY_NOVA_HYPERVISOR_METRICS:
            aggregator.assert_metric('openstack.nova.{}'.format(metric))


def test_report_legacy_metrics_false(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
    ) as hypervisors:
        one_project_content = json.load(one_project)
        hypervisors_content = json.load(hypervisors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_hypervisors_detail.return_value = hypervisors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'report_legacy_metrics': False,
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric in LEGACY_NOVA_HYPERVISOR_METRICS:
            aggregator.assert_metric('openstack.nova.{}'.format(metric), count=0)


def test_report_legacy_metrics_true(aggregator, dd_run_check):
    with mock.patch('datadog_checks.openstack_controller.openstack_controller.make_api') as mocked_api, open(
        os.path.join(get_here(), 'fixtures/one_project.json'), 'r'
    ) as one_project, open(
        os.path.join(get_here(), 'fixtures/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
    ) as hypervisors:
        one_project_content = json.load(one_project)
        hypervisors_content = json.load(hypervisors)
        api = mock.MagicMock()
        api.get_projects.return_value = one_project_content
        api.get_compute_hypervisors_detail.return_value = hypervisors_content
        mocked_api.return_value = api
        instance = {
            'keystone_server_url': 'http://10.164.0.83/identity',
            'user_name': 'admin',
            'user_password': 'password',
            'report_legacy_metrics': True,
        }
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
        for metric in LEGACY_NOVA_HYPERVISOR_METRICS:
            aggregator.assert_metric('openstack.nova.{}'.format(metric))
