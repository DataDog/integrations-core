import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck

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
        "agent-integrations-openstack-ironic",
        replace={
            'identity/v3/auth/tokens': lambda d: {
                **d,
                **{
                    'token': {
                        **d['token'],
                        **{'catalog': d['token'].get('catalog', [])[3:]},
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
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:18a64e25fb53453ebd10a45fd974b816',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:01b21103a92d4997ab09e46ff8346bd5',
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
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
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
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
