import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.metrics import NEUTRON_AGENTS_METRICS, NEUTRON_QUOTAS_METRICS

from .common import MockHttp

pytestmark = [pytest.mark.unit]


def test_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", exceptions={'networking': Exception()})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting network metrics' in caplog.text


def test_endpoint_not_in_catalog(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default",
        replace={
            'identity/v3/auth/tokens': lambda d: {
                **d,
                **{
                    'token': {
                        **d['token'],
                        **{'catalog': d['token'].get('catalog', [])[:5] + d['token'].get('catalog', [])[6:]},
                    }
                },
            }
        },
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


def test_endpoint_down(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", defaults={'networking': MockResponse(status_code=500)})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


def test_endpoint_up(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.OK,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.OK,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


def test_quotas_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    not_found_metrics = NEUTRON_QUOTAS_METRICS
    for metric in aggregator.metric_names:
        if metric in NEUTRON_QUOTAS_METRICS:
            not_found_metrics.remove(metric)
            aggregator.assert_metric(
                metric,
                tags=[
                    'domain_id:default',
                    'keystone_server:{}'.format(instance["keystone_server_url"]),
                    'project_id:1e6e233e637d4d55a50a62b63398ad15',
                    'project_name:demo',
                ],
            )
            aggregator.assert_metric(
                metric,
                tags=[
                    'domain_id:default',
                    'keystone_server:{}'.format(instance["keystone_server_url"]),
                    'project_id:6e39099cccde4f809b003d9e0dd09304',
                    'project_name:admin',
                ],
            )
    assert not_found_metrics == [], f"No neutron quotas metrics found: {not_found_metrics}"


def test_agents_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    not_found_metrics = NEUTRON_AGENTS_METRICS
    agent_tags = [
        'agent_availability_zone:',
        'agent_host:agent-integrations-openstack-default',
        'agent_id:203083d6-ddae-4023-aa83-ab679c9f4d2d',
        'agent_name:ovn-controller',
        'agent_type:OVN Controller Gateway agent',
    ]
    for metric in aggregator.metric_names:
        if metric in NEUTRON_AGENTS_METRICS:
            not_found_metrics.remove(metric)
            aggregator.assert_metric(
                metric,
                tags=[]
                if 'openstack.neutron.agents.count'
                else agent_tags
                + [
                    'keystone_server:{}'.format(instance["keystone_server_url"]),
                    'project_id:1e6e233e637d4d55a50a62b63398ad15',
                    'project_name:demo',
                ],
            )
            aggregator.assert_metric(
                metric,
                tags=[]
                if 'openstack.neutron.agents.count'
                else agent_tags
                + [
                    'domain_id:default',
                    'keystone_server:{}'.format(instance["keystone_server_url"]),
                    'project_id:6e39099cccde4f809b003d9e0dd09304',
                    'project_name:admin',
                ],
            )
    assert not_found_metrics == [], f"No neutron agents metrics found: {not_found_metrics}"
