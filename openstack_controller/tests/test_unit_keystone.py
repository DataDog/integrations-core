import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

from .common import MockHttp

pytestmark = [pytest.mark.unit]


def test_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", exceptions={'identity/v3': Exception()})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting identity metrics' in caplog.text


def test_endpoint_down(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", defaults={'identity/v3': MockResponse(status_code=500)})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )


def test_endpoint_up(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.response_time',
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )


def test_domains_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.domains.count',
        value=2,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domains.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domains.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:03e40b01788d403e98e4b9a20210492e',
        ],
    )


def test_projects_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.projects.count',
        value=5,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.projects.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.projects.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.projects.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'project_id:b0700d860b244dcbb038541976cd8f32',
            'project_name:alt_demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.projects.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'project_id:e9e405ed5811407db982e3113e52d26b',
            'project_name:service',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.projects.enabled',
        value=0,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'project_id:c1147335eac0402ea9cabaae59c267e1',
            'project_name:invisible_to_admin',
        ],
    )
