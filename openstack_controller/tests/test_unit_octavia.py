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
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
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
            'project_id:cadda9ffc8d44aedbac4c7d6adc43c51',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:4762874c945945c38d820cce29fbb66e',
            'project_name:admin',
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
            'project_id:cadda9ffc8d44aedbac4c7d6adc43c51',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.OK,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:4762874c945945c38d820cce29fbb66e',
            'project_name:admin',
        ],
    )


def test_loadbalancers_metrics_default(aggregator, dd_run_check, instance, monkeypatch):
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
        ['listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9', 'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115', 'loadbalancer_name:loadbalancer-1', 'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3']
    ]

    for loadbalancer_tags in demo_loadbalancers:
        tags = demo_project_tags + loadbalancer_tags
        aggregator.assert_metric(
            'openstack.octavia.loadbalancer.active_connections', 
            value=0.0, 
            metric_type=aggregator.GAUGE,
            count=1,
            tags=tags)
        # aggregator.assert_metric('openstack.octavia.loadbalancer.bytes_in', count=0, tags=tags)
        # aggregator.assert_metric('openstack.octavia.loadbalancer.bytes_out', count=0, tags=tags)
        # aggregator.assert_metric('openstack.octavia.loadbalancer.request_errors', count=0, tags=tags)
        # aggregator.assert_metric('openstack.octavia.loadbalancer.total_connections', count=0, tags=tags)

def test_listeners_metrics_default(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-octavia")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['domain_id:default', 'keystone_server:{}'.format(instance["keystone_server_url"])]

    demo_project_tags = base_tags + [
        'project_id:4762874c945945c38d820cce29fbb66e',
        'project_name:demo',
    ]

    demo_listeners = [
        ['listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9', 'listener_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115', 'listener_name:listener-1', 'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3']
    ]

    for listener_tags in demo_listeners:
        tags = demo_project_tags + listener_tags
        # aggregator.assert_metric('openstack.octavia.listener.connection_limit', count=1, tags=tags)
        # aggregator.assert_metric('openstack.octavia.listener.timeout_client_data', count=0, tags=tags)
        # aggregator.assert_metric('openstack.octavia.listener.timeout_member_connect', count=0, tags=tags)
        # aggregator.assert_metric('openstack.octavia.listener.timeout_member_data', count=0, tags=tags)
        # aggregator.assert_metric('openstack.octavia.listener.timeout_tcp_inspect', count=0, tags=tags)