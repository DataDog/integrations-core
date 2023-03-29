# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import HTTPError

from datadog_checks.base import AgentCheck
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import MockHttp

pytestmark = [pytest.mark.unit]


def test_connect_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    monkeypatch.setattr(
        'requests.get', mock.MagicMock(side_effect=MockHttp(exceptions={'identity/v3': Exception()}).get)
    )
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

    with pytest.raises(Exception):
        check = OpenStackControllerCheck('test', {}, [instance])
        dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=check.CRITICAL,
        tags=['keystone_server:{}'.format(instance["keystone_server_url"])],
    )
    assert 'Exception while creating api' in caplog.text


def test_connect_http_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    monkeypatch.setattr(
        'requests.get', mock.MagicMock(side_effect=MockHttp(exceptions={'identity/v3': HTTPError()}).get)
    )
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=check.CRITICAL,
        tags=['keystone_server:{}'.format(instance["keystone_server_url"])],
    )
    assert 'HTTPError while creating api' in caplog.text


def test_connect_ok(aggregator, dd_run_check, instance, monkeypatch):
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:{}'.format(instance["keystone_server_url"])],
    )


# @pytest.mark.parametrize(
#     ('hypervisors_mock_file', 'os_aggregates_mock_file', 'status'),
#     [
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_none/hypervisors_detail_up.json',
#             'fixtures/api/compute/nova_microversion_none/os_aggregates.json',
#             AgentCheck.OK,
#             id='up',
#         ),
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_none/hypervisors_detail_down.json',
#             'fixtures/api/compute/nova_microversion_none/os_aggregates.json',
#             AgentCheck.CRITICAL,
#             id='down',
#         ),
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_none/hypervisors_detail_unknown.json',
#             'fixtures/api/compute/nova_microversion_none/os_aggregates.json',
#             AgentCheck.UNKNOWN,
#             id='unknown',
#         ),
#     ],
# )
# def test_compute_hypervisor_service_check(
#     hypervisors_mock_file, os_aggregates_mock_file, status, aggregator, dd_run_check
# ):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project, open(os.path.join(get_here(), hypervisors_mock_file), 'r') as hypervisors, open(
#         os.path.join(get_here(), os_aggregates_mock_file), 'r'
#     ) as os_aggregates:
#         project_tags = ['project_id:667aee39f2b64032b4d7585809d31e6f', 'project_name:admin']
#         tags = project_tags + [
#             'aggregate:my-aggregate',
#             'availability_zone:availability-zone',
#             'hypervisor:agent-integrations-openstack-default',
#             'hypervisor_id:1',
#             'status:enabled',
#             'virt_type:QEMU',
#         ]
#
#         compute_response_time = 2.659812
#         one_project_content = json.load(one_project)
#         hypervisors_content = json.load(hypervisors)
#         os_aggregates_content = json.load(os_aggregates)
#         api = mock.MagicMock()
#         api.get_compute_response_time.return_value = compute_response_time
#         api.get_network_response_time.return_value = None
#         api.get_baremetal_response_time.return_value = None
#         api.get_load_balancer_response_time.return_value = None
#         api.get_projects.return_value = one_project_content
#         api.get_compute_hypervisors.return_value = hypervisors_content
#         api.get_compute_os_aggregates.return_value = os_aggregates_content
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_service_check('openstack.nova.hypervisor.up', status=status, tags=tags)
#
#
# @pytest.mark.parametrize(
#     ('hypervisors_mock_file', 'os_aggregates_mock_file', 'instance'),
#     [
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_none/hypervisors_detail.json',
#             'fixtures/api/compute/nova_microversion_none/os_aggregates.json',
#             {
#                 'keystone_server_url': 'http://10.164.0.83/identity',
#                 'user_name': 'admin',
#                 'user_password': 'password',
#             },
#             id='default values',
#         ),
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_none/hypervisors_detail.json',
#             'fixtures/api/compute/nova_microversion_none/os_aggregates.json',
#             {
#                 'keystone_server_url': 'http://10.164.0.83/identity',
#                 'user_name': 'admin',
#                 'user_password': 'password',
#                 'collect_hypervisor_metrics': False,
#             },
#             id='collect_hypervisor_metrics: False',
#         ),
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_latest/hypervisors_detail.json',
#             'fixtures/api/compute/nova_microversion_latest/os_aggregates.json',
#             {
#                 'keystone_server_url': 'http://10.164.0.83/identity',
#                 'user_name': 'admin',
#                 'user_password': 'password',
#                 'nova_microversion': 'latest',
#             },
#             id='nova_microversion: latest',
#         ),
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_none/hypervisors_detail.json',
#             'fixtures/api/compute/nova_microversion_none/os_aggregates.json',
#             {
#                 'keystone_server_url': 'http://10.164.0.83/identity',
#                 'user_name': 'admin',
#                 'user_password': 'password',
#                 'report_legacy_metrics': False,
#             },
#             id='report_legacy_metrics: False',
#         ),
#         pytest.param(
#             'fixtures/api/compute/nova_microversion_latest/hypervisors_detail.json',
#             'fixtures/api/compute/nova_microversion_latest/os_aggregates.json',
#             {
#                 'keystone_server_url': 'http://10.164.0.83/identity',
#                 'user_name': 'admin',
#                 'user_password': 'password',
#                 'nova_microversion': 'latest',
#                 'report_legacy_metrics': False,
#             },
#             id='nova_microversion: latest and report_legacy_metrics: False',
#         ),
#     ],
# )
# def test_compute_hypervisor_metrics(hypervisors_mock_file, os_aggregates_mock_file, instance, aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project, open(os.path.join(get_here(), hypervisors_mock_file), 'r') as hypervisors, open(
#         os.path.join(get_here(), os_aggregates_mock_file), 'r'
#     ) as os_aggregates:
#         nova_microversion_latest = instance.get('nova_microversion') == 'latest'
#         report_legacy_metrics = instance.get('report_legacy_metrics', True)
#         count = 1 if instance.get('collect_hypervisor_metrics', True) else 0
#         project_tags = ['project_id:667aee39f2b64032b4d7585809d31e6f', 'project_name:admin']
#         tags = project_tags + [
#             'aggregate:my-aggregate',
#             'availability_zone:availability-zone',
#             'hypervisor:agent-integrations-openstack-default',
#             'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661' if nova_microversion_latest else 'hypervisor_id:1',
#             'status:enabled',
#             'virt_type:QEMU',
#         ]
#
#         compute_response_time = 2.659812
#         one_project_content = json.load(one_project)
#         hypervisors_content = json.load(hypervisors)
#         os_aggregates_content = json.load(os_aggregates)
#         api = mock.MagicMock()
#         api.get_compute_response_time.return_value = compute_response_time
#         api.get_network_response_time.return_value = None
#         api.get_baremetal_response_time.return_value = None
#         api.get_load_balancer_response_time.return_value = None
#         api.get_projects.return_value = one_project_content
#         api.get_compute_hypervisors.return_value = hypervisors_content
#         api.get_compute_os_aggregates.return_value = os_aggregates_content
#         mocked_api.return_value = api
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_metric('openstack.controller', value=1, count=1, tags=[])
#         aggregator.assert_metric(
#             'openstack.nova.response_time', value=compute_response_time, count=1, tags=project_tags
#         )
#         if not nova_microversion_latest:
#             aggregator.assert_metric('openstack.nova.hypervisor.vcpus', value=4, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.memory_mb', value=14990, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.local_gb', value=96, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.vcpus_used', value=1, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.memory_mb_used', value=768, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.local_gb_used', value=0, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.free_ram_mb', value=14222, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.free_disk_gb', value=96, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.current_workload', value=0, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.running_vms', value=1, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor.disk_available_least', value=84, count=count, tags=tags)
#             if report_legacy_metrics:
#                 aggregator.assert_metric('openstack.nova.vcpus', value=4, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.memory_mb', value=14990, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.local_gb', value=96, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.vcpus_used', value=1, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.memory_mb_used', value=768, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.local_gb_used', value=0, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.free_ram_mb', value=14222, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.free_disk_gb', value=96, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.current_workload', value=0, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.running_vms', value=1, count=count, tags=tags)
#                 aggregator.assert_metric('openstack.nova.disk_available_least', value=84, count=count, tags=tags)
#         aggregator.assert_metric('openstack.nova.hypervisor.load_1', value=0.12, count=count, tags=tags)
#         aggregator.assert_metric('openstack.nova.hypervisor.load_5', value=0.17, count=count, tags=tags)
#         aggregator.assert_metric('openstack.nova.hypervisor.load_15', value=0.19, count=count, tags=tags)
#         if report_legacy_metrics:
#             aggregator.assert_metric('openstack.nova.hypervisor_load.1', value=0.12, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor_load.5', value=0.17, count=count, tags=tags)
#             aggregator.assert_metric('openstack.nova.hypervisor_load.15', value=0.19, count=count, tags=tags)
#         aggregator.assert_all_metrics_covered()
#
#
# def test_network_endpoint_down(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(one_project)
#         api.get_network_response_time.return_value = None
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.CRITICAL)
#
#
# def test_network_response_time(aggregator, dd_run_check):
#     response_time = 2.659812
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(one_project)
#         api.get_network_response_time.return_value = response_time
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_metric('openstack.neutron.response_time', response_time)
#         aggregator.assert_service_check('openstack.neutron.api.up', status=AgentCheck.OK)
#
#
# def test_network_quotas(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project, open(os.path.join(get_here(), 'fixtures/api/network/quotas.json'), 'r') as quotas:
#         one_project_content = json.load(one_project)
#         quotas_content = json.load(quotas)
#         api = mock.MagicMock()
#         api.get_projects.return_value = one_project_content
#         api.get_network_quotas.return_value = quotas_content
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         for metric, value in quotas_content.items():
#             aggregator.assert_metric(f'openstack.neutron.quotas.{metric}', value)
#
#
# def test_baremetal_endpoint_down(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(one_project)
#         api.get_baremetal_response_time.return_value = None
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.CRITICAL)
#
#
# def test_baremetal_response_time(aggregator, dd_run_check):
#     response_time = 2.659812
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(one_project)
#         api.get_baremetal_response_time.return_value = response_time
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_metric('openstack.ironic.response_time', response_time)
#         aggregator.assert_service_check('openstack.ironic.api.up', status=AgentCheck.OK)
#
#
# def test_load_balancer_endpoint_down(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(one_project)
#         api.get_load_balancer_response_time.return_value = None
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.CRITICAL)
#
#
# def test_load_balancer_response_time(aggregator, dd_run_check):
#     response_time = 2.659812
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project:
#         api = mock.MagicMock()
#         api.get_projects.return_value = json.load(one_project)
#         api.get_load_balancer_response_time.return_value = response_time
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         aggregator.assert_metric('openstack.octavia.response_time', response_time)
#         aggregator.assert_service_check('openstack.octavia.api.up', status=AgentCheck.OK)
#
#
# def test_report_legacy_metrics_default(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project, open(
#         os.path.join(get_here(), 'fixtures/api/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
#     ) as hypervisors:
#         one_project_content = json.load(one_project)
#         hypervisors_content = json.load(hypervisors)
#         api = mock.MagicMock()
#         api.get_projects.return_value = one_project_content
#         api.get_compute_hypervisors.return_value = hypervisors_content
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         for metric in LEGACY_NOVA_HYPERVISOR_METRICS:
#             aggregator.assert_metric('openstack.nova.{}'.format(metric))
#
#
# def test_report_legacy_metrics_false(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project, open(
#         os.path.join(get_here(), 'fixtures/api/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
#     ) as hypervisors:
#         one_project_content = json.load(one_project)
#         hypervisors_content = json.load(hypervisors)
#         api = mock.MagicMock()
#         api.get_projects.return_value = one_project_content
#         api.get_compute_hypervisors.return_value = hypervisors_content
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#             'report_legacy_metrics': False,
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         for metric in LEGACY_NOVA_HYPERVISOR_METRICS:
#             aggregator.assert_metric('openstack.nova.{}'.format(metric), count=0)
#
#
# def test_report_legacy_metrics_true(aggregator, dd_run_check):
#     with mock.patch('datadog_checks.openstack_controller.check.make_api') as mocked_api, open(
#         os.path.join(get_here(), 'fixtures/api/one_project.json'), 'r'
#     ) as one_project, open(
#         os.path.join(get_here(), 'fixtures/api/compute/nova_microversion_none/hypervisors_detail.json'), 'r'
#     ) as hypervisors:
#         one_project_content = json.load(one_project)
#         hypervisors_content = json.load(hypervisors)
#         api = mock.MagicMock()
#         api.get_projects.return_value = one_project_content
#         api.get_compute_hypervisors.return_value = hypervisors_content
#         mocked_api.return_value = api
#         instance = {
#             'keystone_server_url': 'http://10.164.0.83/identity',
#             'user_name': 'admin',
#             'user_password': 'password',
#             'report_legacy_metrics': True,
#         }
#         check = OpenStackControllerCheck('test', {}, [instance])
#         dd_run_check(check)
#         for metric in LEGACY_NOVA_HYPERVISOR_METRICS:
#             aggregator.assert_metric('openstack.nova.{}'.format(metric))
