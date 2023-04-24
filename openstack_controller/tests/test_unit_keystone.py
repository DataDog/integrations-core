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


def test_users_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.users.count',
        value=13,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:3472440960de4595be3b975d230979d3',
            'user_name:alt_demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:87e289ddac6d4dce8626a659c5ea88ae',
            'user_name:alt_demo_member',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:2059bc7347c94546bef812b1092cc5cf',
            'user_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:61f0cd4dec604f968ff6cc92d4c1c278',
            'user_name:alt_demo_reader',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:ad9f72f911744acbbf69379e45a3ef37',
            'user_name:glance',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:af4653d4f2dc4a38b8af36cbd3993d5a',
            'user_name:cinder',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:5d0c9a6896c9430b8a1528424c9ee6f6',
            'user_name:system_member',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:bc603ecd6ed940119be9a3a933c39509',
            'user_name:nova',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:fc7c3571bed548e98e7df266f57a50f7',
            'user_name:placement',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:78205c506b534738bc851d3e189a00c3',
            'user_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:94fb5df1e547496894f9304a9b4a06d4',
            'user_name:neutron',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:aeaa8e9835284e4380583e10bb2575fd',
            'user_name:system_reader',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.users.enabled',
        value=0,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'user_id:e3e3e90d24b34e52970a54c9e8656778',
            'user_name:demo_reader',
        ],
    )


def test_groups_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.groups.count',
        value=2,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.groups.users',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'group_id:89b36a4c32c44b0ea8856b6357f101ea',
            'group_name:admins',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.groups.users',
        value=0,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'group_id:9acda6caf16e4828935f4f681ee8b3e5',
            'group_name:nonadmins',
        ],
    )
