# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.metrics import NEUTRON_AGENTS_METRICS, NEUTRON_QUOTAS_METRICS

from .common import MockHttp, check_microversion, is_mandatory

pytestmark = [pytest.mark.unit]


def test_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", exceptions={'networking': Exception()})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting network domain metrics' in caplog.text


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
        ],
    )


def test_quotas_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    not_found_metrics = []
    for key, value in NEUTRON_QUOTAS_METRICS.items():
        if check_microversion(instance, value):
            if key in aggregator.metric_names:
                aggregator.assert_metric(
                    key,
                    tags=[
                        'domain_id:default',
                        'keystone_server:{}'.format(instance["keystone_server_url"]),
                        'project_id:1e6e233e637d4d55a50a62b63398ad15',
                        'project_name:demo',
                    ],
                )
                aggregator.assert_metric(
                    key,
                    tags=[
                        'domain_id:default',
                        'keystone_server:{}'.format(instance["keystone_server_url"]),
                        'project_id:6e39099cccde4f809b003d9e0dd09304',
                        'project_name:admin',
                    ],
                )
            elif is_mandatory(value):
                not_found_metrics.append(key)
    assert not_found_metrics == [], f"No neutron quotas metrics found: {not_found_metrics}"


def test_agents_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    default_tags = ['keystone_server:{}'.format(instance["keystone_server_url"]), 'domain_id:default']
    agent_tags = [
        'agent_availability_zone:None',
        'agent_host:agent-integrations-openstack-default',
        'agent_id:203083d6-ddae-4023-aa83-ab679c9f4d2d',
        'agent_name:ovn-controller',
        'agent_type:OVN Controller Gateway agent',
    ]
    not_found_metrics = []
    for key, value in NEUTRON_AGENTS_METRICS.items():
        if key in aggregator.metric_names:
            tags = default_tags if key == 'openstack.neutron.agents.count' else agent_tags + default_tags
            aggregator.assert_metric(key, tags=tags)
        elif is_mandatory(value):
            not_found_metrics.append(key)
    assert not_found_metrics == [], f"No neutron agents metrics found: {not_found_metrics}"
