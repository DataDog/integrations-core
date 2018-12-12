# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import os
import json
from . import common
from datadog_checks.openstack_controller import OpenStackControllerCheck


def make_request_responses(url, header, params=None, timeout=None):
    mock_path = None
    if url == "http://10.0.2.15:5000/v3/projects":
        mock_path = "v3_projects.json"
    elif url == "http://10.0.2.15:9696":
        return
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1":
        return
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/limits":
        mock_path = "v2.1_4bfc1_limits"
        if params.get("tenant_id") == u'***************************d91a1':
            mock_path = "{}_d91a1.json".format(mock_path)
        elif params.get("tenant_id") == u'***************************4bfc1':
            mock_path = "{}_4bfc1.json".format(mock_path)
        elif params.get("tenant_id") == u'***************************73dbe':
            mock_path = "{}_73dbe.json".format(mock_path)
        elif params.get("tenant_id") == u'***************************3fb11':
            mock_path = "{}_3fb11.json".format(mock_path)
        elif params.get("tenant_id") == u'***************************44736':
            mock_path = "{}_44736.json".format(mock_path)
        elif params.get("tenant_id") == u'***************************147d1':
            mock_path = "{}_147d1.json".format(mock_path)
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/os-hypervisors/detail":
        mock_path = "v2.1_4bfc1_os-hypervisors_detail.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/os-aggregates":
        mock_path = "v2.1_4bfc1_os-aggregates.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/detail":
        mock_path = "v2.1_4bfc1_servers_detail.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/ff2f581c-5d03-4a27-a0ba-f102603fe38f/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_ff2f581c-5d03-4a27-a0ba-f102603fe38f_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/acb4197c-f54e-488e-a40a-1b7f59cc9117/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_acb4197c-f54e-488e-a40a-1b7f59cc9117_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/b3c8eee3-7e22-4a7c-9745-759073673cbe/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_b3c8eee3-7e22-4a7c-9745-759073673cbe_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/412c79b2-25f2-44d6-8e3b-be4baee11a7f/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_412c79b2-25f2-44d6-8e3b-be4baee11a7f_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7e622c28-4b12-4a58-8ac2-4a2e854f84eb/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_7e622c28-4b12-4a58-8ac2-4a2e854f84eb_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/4ceb4c69-a332-4b9d-907b-e99635aae644/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_4ceb4c69-a332-4b9d-907b-e99635aae644_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/1cc21586-8d43-40ea-bdc9-6f54a79957b4/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_1cc21586-8d43-40ea-bdc9-6f54a79957b4_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/836f724f-0028-4dc0-b9bd-e0843d767ca2/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_836f724f-0028-4dc0-b9bd-e0843d767ca2_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7eaa751c-1e37-4963-a836-0a28bc283a9a/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_7eaa751c-1e37-4963-a836-0a28bc283a9a_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/5357e70e-f12c-4bb7-85a2-b40d642a7e92/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_5357e70e-f12c-4bb7-85a2-b40d642a7e92_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/f2dd3f90-e738-4135-84d4-1a2d30d04929/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_f2dd3f90-e738-4135-84d4-1a2d30d04929_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/30888944-fb39-4590-9073-ef977ac1f039/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_30888944-fb39-4590-9073-ef977ac1f039_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/4d7cb923-788f-4b61-9061-abfc576ecc1a/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_4d7cb923-788f-4b61-9061-abfc576ecc1a_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/2e1ce152-b19d-4c4a-9cc7-0d150fa97a18/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_2e1ce152-b19d-4c4a-9cc7-0d150fa97a18_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/52561f29-e479-43d7-85de-944d29ef178d/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_52561f29-e479-43d7-85de-944d29ef178d_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/1b7a987f-c4fb-4b6b-aad9-3b461df2019d/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_1b7a987f-c4fb-4b6b-aad9-3b461df2019d_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/7324440d-915b-4e12-8b85-ec8c9a524d6c/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_7324440d-915b-4e12-8b85-ec8c9a524d6c_diagnostics.json"
    elif url == "http://10.0.2.15:8774/v2.1/***************************4bfc1/servers/57030997-f1b5-4f79-9429-8cb285318633/diagnostics":  # noqa E501
        mock_path = "v2.1_4bfc1_servers_57030997-f1b5-4f79-9429-8cb285318633_diagnostics.json"
    elif url == "http://10.0.2.15:9696/v2.0/networks":
        mock_path = "v2.0_networks.json"

    print(url)
    mock_path = os.path.join(common.FIXTURES_DIR, mock_path)
    with open(mock_path, 'r') as f:
        return json.loads(f.read())


class MockHTTPResponse(object):
    def __init__(self, response_dict, headers):
        self.response_dict = response_dict
        self.headers = headers

    def json(self):
        return self.response_dict


@mock.patch('datadog_checks.openstack_controller.api.AbstractApi._make_request',
            side_effect=make_request_responses)
def test_scenario(make_request, aggregator):
    instance = common.MOCK_CONFIG["instances"][0]
    init_config = common.MOCK_CONFIG['init_config']
    check = OpenStackControllerCheck('openstack_controller', init_config, {}, instances=[instance])

    auth_tokens_response_path = os.path.join(common.FIXTURES_DIR, "auth_tokens_response.json")
    with open(auth_tokens_response_path, 'r') as f:
        auth_tokens_response = json.loads(f.read())
        auth_tokens_response = MockHTTPResponse(response_dict=auth_tokens_response,
                                                headers={'X-Subject-Token': 'fake_token'})

    auth_projects_response_path = os.path.join(common.FIXTURES_DIR, "auth_projects_response.json")
    with open(auth_projects_response_path, 'r') as f:
        auth_projects_response = json.loads(f.read())

    with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.post_auth_token',
                    return_value=auth_tokens_response):
        with mock.patch('datadog_checks.openstack_controller.scopes.KeystoneApi.get_auth_projects',
                        return_value=auth_projects_response):
            check.check(common.MOCK_CONFIG['instances'][0])

            # for m in aggregator.not_asserted():
            #     print(m)
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')

            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.rx', value=17286.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_image_meta', value=128.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality', value=10.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality', value=5.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb', value=7982.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.tx', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.rx', value=16542.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=1.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=1.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_security_groups_used', value=0.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=20.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_cores', value=40.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.rx', value=15564.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_floating_ips_used', value=0.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=170.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.rx', value=6306.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.current_workload', value=0.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_floating_ips', value=10.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=17408.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=1024.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_ram_used', value=0.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.rx', value=15408.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.rx', value=5946.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=3886.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=5934.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=3886.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=5934.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=3886.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=5934.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_ram_mb', value=2862.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=207.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=67.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2422550000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=648410000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=6915020290000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=830250000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3008600000000.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=741940000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2406870000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3193240000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2616630000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3608370000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2124150000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=556800000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=4697690000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=3320700000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=1876660000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2512910000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=567940000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.cpu0_time', value=2242410000000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_personality_size', value=10240.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=67.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=193.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_server_meta', value=128.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=4.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=0.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=4.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=0.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=4.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=0.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus_used', value=6.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_keypairs', value=100.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_groups', value=10.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=2.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=0.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=2.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=0.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=2.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=0.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.running_vms', value=3.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.vcpus', value=8.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=17.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=1.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_instances_used', value=0.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=71.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.rx', value=15306.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=26.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=46.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=26.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=46.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=26.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=46.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.free_disk_gb', value=16.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=22.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=2.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=22.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=2.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=22.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=2.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.local_gb_used', value=32.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'], hostname='')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.memory', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=195.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=199.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=71.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.rx', value=5946.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=198.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=172.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=34.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=2.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.total_cores_used', value=0.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.rx', value=17826.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=296960.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=356352.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=146432.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=369664.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=307200.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=359424.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=297984.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=305152.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=351232.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=373760.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=299008.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=368640.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=316416.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=297984.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=105472.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.vda_write', value=295936.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.rx', value=17466.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.rx', value=15228.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova', 'interface:tapab9b23ee-c1'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=66.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.rx', value=18522.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=197.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1154.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=825.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1161.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1171.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=877.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1156.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1157.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=1128.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=875.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=424.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=574.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=424.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.vda_read_req', value=878.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20432896.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=15403008.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20445184.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20473856.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20164608.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20458496.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20431872.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20446208.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20153344.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=13560832.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=15155200.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=13560832.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.vda_read', value=20160512.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.memory_actual', value=1048576.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova', 'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')

            aggregator.assert_metric('openstack.nova.server.vda_errors', value=-1.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.local_gb', value=48.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.tx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.rx', value=6306.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=10.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_instances', value=20.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.rx', value=5844.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova', 'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=154.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=14.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=-2.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=38.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=2.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=14.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=37.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=3.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=13.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=3.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.disk_available_least', value=3.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova', 'interface:tapf3e5d7a2-94'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_total_ram_size', value=51200.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=84.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=105.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=32.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=106.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=82.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=105.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=85.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=84.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=108.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=107.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=82.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=105.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=89.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=84.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=28.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.vda_write_req', value=83.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=145116.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=160832.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=147684.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=148000.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=141980.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=161108.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=144728.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=142012.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=146064.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=145892.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-1',
                                           'availability_zone:nova'],
                                     hostname=u'4d7cb923-788f-4b61-9061-abfc576ecc1a')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=140812.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=149456.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=146460.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:jenga',
                                           'availability_zone:nova'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=142300.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=146188.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=144460.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-1',
                                           'availability_zone:nova'],
                                     hostname=u'7eaa751c-1e37-4963-a836-0a28bc283a9a')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=148752.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:blacklist',
                                           'availability_zone:nova'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.memory_rss', value=143992.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=185.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute4.openstack.local', 'server_name:server_take_zero-2',
                                           'availability_zone:nova', 'interface:tapad123605-18'],
                                     hostname=u'ff2f581c-5d03-4a27-a0ba-f102603fe38f')
            aggregator.assert_metric('openstack.nova.server.rx', value=13788.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=199.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=4096.0,
                                     tags=['hypervisor:compute1.openstack.local', 'hypervisor_id:1',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                     tags=['hypervisor:compute2.openstack.local', 'hypervisor_id:2',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=2048.0,
                                     tags=['hypervisor:compute3.openstack.local', 'hypervisor_id:8',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                     tags=['hypervisor:compute4.openstack.local', 'hypervisor_id:9',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=4096.0,
                                     tags=['hypervisor:compute5.openstack.local', 'hypervisor_id:10',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=2048.0,
                                     tags=['hypervisor:compute6.openstack.local', 'hypervisor_id:11',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                     tags=['hypervisor:compute7.openstack.local', 'hypervisor_id:12',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=4096.0,
                                     tags=['hypervisor:compute8.openstack.local', 'hypervisor_id:13',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=2048.0,
                                     tags=['hypervisor:compute9.openstack.local', 'hypervisor_id:14',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.memory_mb_used', value=5120.0,
                                     tags=['hypervisor:compute10.openstack.local', 'hypervisor_id:15',
                                           'virt_type:QEMU', 'status:enabled'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:finalDestination-6',
                                           'availability_zone:nova', 'interface:tape690927f-80'],
                                     hostname=u'acb4197c-f54e-488e-a40a-1b7f59cc9117')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.rx', value=17748.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                     tags=['tenant_id:***************************4bfc1', 'project_name:service'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                     tags=['tenant_id:***************************3fb11', 'project_name:admin'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                     tags=['tenant_id:***************************d91a1', 'project_name:testProj2'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                     tags=['tenant_id:***************************73dbe', 'project_name:testProj1'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                     tags=['tenant_id:***************************147d1', 'project_name:12345'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.limits.max_security_group_rules', value=20.0,
                                     tags=['tenant_id:***************************44736', 'project_name:abcde'],
                                     hostname='')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:jnrgjoner',
                                           'availability_zone:nova', 'interface:tap66a9ffb5-8f'],
                                     hostname=u'b3c8eee3-7e22-4a7c-9745-759073673cbe')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local',
                                           'server_name:HoneyIShrunkTheServer', 'availability_zone:nova',
                                           'interface:tap9ac4ed56-d2'],
                                     hostname=u'1b7a987f-c4fb-4b6b-aad9-3b461df2019d')
            aggregator.assert_metric('openstack.nova.server.rx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:finalDestination-5',
                                           'availability_zone:nova', 'interface:tapf86369c0-84'],
                                     hostname=u'5357e70e-f12c-4bb7-85a2-b40d642a7e92')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:testProj1',
                                           'hypervisor:compute4.openstack.local', 'server_name:blacklistServer',
                                           'availability_zone:nova', 'interface:tap9bff9e73-2f'],
                                     hostname=u'57030997-f1b5-4f79-9429-8cb285318633')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-2',
                                           'availability_zone:nova', 'interface:tap39a71720-01'],
                                     hostname=u'52561f29-e479-43d7-85de-944d29ef178d')
            aggregator.assert_metric('openstack.nova.server.rx', value=17826.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute8.openstack.local', 'server_name:finalDestination-7',
                                           'availability_zone:nova', 'interface:tapc929a75b-94'],
                                     hostname=u'1cc21586-8d43-40ea-bdc9-6f54a79957b4')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local', 'server_name:Rocky',
                                           'availability_zone:nova', 'interface:tapcb21dae0-46'],
                                     hostname=u'2e1ce152-b19d-4c4a-9cc7-0d150fa97a18')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-8',
                                           'availability_zone:nova', 'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=174.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute2.openstack.local', 'server_name:ReadyServerOne',
                                           'availability_zone:nova', 'interface:tap8880f875-12'],
                                     hostname=u'412c79b2-25f2-44d6-8e3b-be4baee11a7f')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local',
                                           'server_name:finalDestination-8', 'availability_zone:nova',
                                           'interface:tap73364860-8e'],
                                     hostname=u'836f724f-0028-4dc0-b9bd-e0843d767ca2')
            aggregator.assert_metric('openstack.nova.server.tx', value=1464.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute1.openstack.local',
                                           'server_name:jenga', 'availability_zone:nova',
                                           'interface:tap3fd8281c-97'],
                                     hostname=u'f2dd3f90-e738-4135-84d4-1a2d30d04929')
            aggregator.assert_metric('openstack.nova.server.rx', value=17646.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local',
                                           'server_name:moarserver-13', 'availability_zone:nova',
                                           'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.rx_errors', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local',
                                           'server_name:blacklist', 'availability_zone:nova',
                                           'interface:tap702092ed-a5'],
                                     hostname=u'7324440d-915b-4e12-8b85-ec8c9a524d6c')
            aggregator.assert_metric('openstack.nova.server.tx_drop', value=0.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute5.openstack.local', 'server_name:moarserver-13',
                                           'availability_zone:nova', 'interface:tap69a50430-3b'],
                                     hostname=u'4ceb4c69-a332-4b9d-907b-e99635aae644')
            aggregator.assert_metric('openstack.nova.server.rx_packets', value=171.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute10.openstack.local', 'server_name:anotherServer',
                                           'availability_zone:nova', 'interface:tap56f02c54-da'],
                                     hostname=u'30888944-fb39-4590-9073-ef977ac1f039')
            aggregator.assert_metric('openstack.nova.server.tx_packets', value=9.0,
                                     tags=['nova_managed_server', 'project_name:admin',
                                           'hypervisor:compute7.openstack.local', 'server_name:finalDestination-4',
                                           'availability_zone:nova', 'interface:tapb488fc1e-3e'],
                                     hostname=u'7e622c28-4b12-4a58-8ac2-4a2e854f84eb')

        # Assert coverage for this check on this instance
        aggregator.assert_all_metrics_covered()
