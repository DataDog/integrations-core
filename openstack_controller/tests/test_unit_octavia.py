import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import MockHttp

pytestmark = [pytest.mark.unit]


def test_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia", exceptions={'load-balancer': Exception()})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting load balancer metrics' in caplog.text


def test_endpoint_not_in_catalog(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )


def test_endpoint_down(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia", defaults={'load-balancer': MockResponse(status_code=500)})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )


def test_endpoint_up(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.OK,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )


def test_loadbalancers_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:admin',
    ]

    demo_loadbalancers = [
        [
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'provisioning_status:ACTIVE',
            'operating_status:ERROR',
        ]
    ]

    for loadbalancer_tags in demo_loadbalancers:
        tags = demo_project_tags + loadbalancer_tags
        aggregator.assert_metric('openstack.octavia.loadbalancer.admin_state_up', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.loadbalancer.active_connections', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.loadbalancer.bytes_in', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.loadbalancer.bytes_out', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.loadbalancer.request_errors', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.loadbalancer.total_connections', count=1, tags=tags)


def test_listeners_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:admin',
    ]

    demo_listeners = [
        [
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
        ]
    ]

    for listener_tags in demo_listeners:
        tags = demo_project_tags + listener_tags
        aggregator.assert_metric('openstack.octavia.listener.connection_limit', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.timeout_client_data', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.timeout_member_connect', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.timeout_member_data', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.timeout_tcp_inspect', count=1, tags=tags)

        aggregator.assert_metric('openstack.octavia.listener.active_connections', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.bytes_in', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.bytes_out', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.request_errors', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.listener.total_connections', count=1, tags=tags)


def test_members_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:admin',
    ]

    demo_members = [
        [
            'member_id:0abcafea-2ad2-44cd-957f-690644ba479c',
            'member_name:amphora-042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'pool_name:pool-1',
            'provisioning_status:ACTIVE',
            'operating_status:ERROR',
        ]
    ]

    for member_tags in demo_members:
        tags = demo_project_tags + member_tags
        aggregator.assert_metric('openstack.octavia.member.admin_state_up', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.member.weight', count=1, tags=tags)


def test_healthmonitors_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:admin',
    ]

    demo_healthmonitors = [
        [
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'operating_status:ONLINE',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'pool_name:pool-1',
            'provisioning_status:ACTIVE',
            'type:HTTP',
        ]
    ]

    for healthmonitor_tags in demo_healthmonitors:
        tags = demo_project_tags + healthmonitor_tags
        aggregator.assert_metric('openstack.octavia.healthmonitor.admin_state_up', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.healthmonitor.delay', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.healthmonitor.max_retries', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.healthmonitor.max_retries_down', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.healthmonitor.timeout', count=1, tags=tags)


def test_pools_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:admin',
    ]

    demo_pools = [
        [
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'pool_name:pool-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'member_id:0abcafea-2ad2-44cd-957f-690644ba479c',
            'member_id:e79e1011-2eb4-486f-84c3-99d2a4aef88d',
            'member_name:amphora-042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'member_name:amphora-a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'provisioning_status:ACTIVE',
            'operating_status:ERROR',
        ],
    ]

    for pool_tags in demo_pools:
        tags = demo_project_tags + pool_tags
        aggregator.assert_metric('openstack.octavia.pool.admin_state_up', count=1, tags=tags)


def test_amphora_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:admin',
    ]

    demo_amphora = [
        [
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'amphora_compute_id:ace67097-e457-4044-b05c-be7ac830304a',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'status:ALLOCATED',
        ],
    ]

    for amphora_tags in demo_amphora:
        tags = demo_project_tags + amphora_tags

        aggregator.assert_metric('openstack.octavia.amphora.active_connections', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.amphora.bytes_in', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.amphora.bytes_out', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.amphora.request_errors', count=1, tags=tags)
        aggregator.assert_metric('openstack.octavia.amphora.total_connections', count=1, tags=tags)
