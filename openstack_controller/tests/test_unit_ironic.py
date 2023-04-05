import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import MockHttp

pytestmark = [pytest.mark.unit]


def test_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic", exceptions={'baremetal': Exception()})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting baremetal metrics' in caplog.text


def test_endpoint_not_in_catalog(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


def test_endpoint_down(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic", defaults={'baremetal': MockResponse(status_code=500)})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:41ee3922506448f1a869f60f115c55c0',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:223fd91579d448feb399f68655515efb',
            'project_name:admin',
        ],
    )


def test_endpoint_up(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:41ee3922506448f1a869f60f115c55c0',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:223fd91579d448feb399f68655515efb',
            'project_name:admin',
        ],
    )


def test_node_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    nodes = [
        ['node_name:node-0', 'maintence:false', 'power_state:power_on'],
        ['node_name:node-1', 'maintence:false', 'power_state:power_off'],
        ['node_name:node-3', 'maintence:false', 'power_state:power_off'],
    ]

    for node_tags in nodes:
        aggregator.assert_metric('openstack.ironic.nodes.count', count=0, tags=node_tags)


def test_node_metrics_default(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['keystone_server:http://127.0.0.1:8080/identity']

    demo_project_tags = base_tags + [
        'project_id:41ee3922506448f1a869f60f115c55c0',
        'project_name:demo',
    ]

    nodes = [
        ['node_uuid:a91c98d9-7e58-4552-9d95-62ea85ae923c', 'maintenance:False', 'power_state:power on'],
        ['node_uuid:b4b2971b-355b-4cc2-953d-2e95232bd7e2', 'maintenance:False', 'power_state:power off'],
        ['node_uuid:6bc313ce-066d-4be0-97b0-acd7ff7f46da', 'maintenance:False', 'power_state:power off'],
    ]

    for node_tags in nodes:
        tags = demo_project_tags + node_tags
        aggregator.assert_metric('openstack.ironic.nodes.count', count=1, tags=tags)
