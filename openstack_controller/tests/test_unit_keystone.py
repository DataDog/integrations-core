# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

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
    assert 'Exception while reporting identity response time' in caplog.text


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
    aggregator.assert_metric(
        'openstack.keystone.response_time',
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
        ],
    )


def test_auth_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default",
        defaults={'identity/v3/auth/tokens/unscoped': MockResponse(status_code=500)},
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'HTTPError while authenticating user unscoped' in caplog.text


def test_auth_domain_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default",
        defaults={'identity/v3/auth/tokens/domain': MockResponse(status_code=500)},
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))
    caplog.set_level(logging.DEBUG)
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'HTTPError while authenticating domain scoped' in caplog.text
    assert 'Authenticated user for project' in caplog.text

    # Anyway domain metrics are reported in the projects loop, and we need to check it
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
            'domain_name:Default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domains.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:03e40b01788d403e98e4b9a20210492e',
            'domain_name:New domain',
            'foo',
            'bar',
        ],
    )


def test_auth_project_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default",
        defaults={'identity/v3/auth/tokens/project': MockResponse(status_code=500)},
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'HTTPError while authenticating project scoped' in caplog.text


def test_domains_metrics_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default", defaults={'identity/v3/domains': MockResponse(status_code=500)}
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))
    caplog.set_level(logging.DEBUG)
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('openstack.keystone.domains.count', count=0)
    aggregator.assert_metric('openstack.keystone.domains.enabled', count=0)
    assert 'HTTPError while reporting identity domains metrics' in caplog.text


def test_domains_metrics(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))
    caplog.set_level(logging.DEBUG)
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
            'domain_name:Default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domains.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:03e40b01788d403e98e4b9a20210492e',
            'domain_name:New domain',
            'foo',
            'bar',
        ],
    )
    assert "Authenticated user for domain, reporting metrics using domain scope" in caplog.text


def test_projects_metrics_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default", defaults={'identity/v3/projects': MockResponse(status_code=500)}
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('openstack.keystone.projects.count', count=0)
    aggregator.assert_metric('openstack.keystone.projects.enabled', count=0)
    assert 'HTTPError while reporting identity projects metrics' in caplog.text


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
            'foo',
            'bar',
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


def test_users_metrics_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default", defaults={'identity/v3/users': MockResponse(status_code=500)}
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('openstack.keystone.users.count', count=0)
    aggregator.assert_metric('openstack.keystone.users.enabled', count=0)
    assert 'HTTPError while reporting identity users metrics' in caplog.text


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


def test_groups_metrics_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default", defaults={'identity/v3/groups': MockResponse(status_code=500)}
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('openstack.keystone.groups.count', count=0)
    aggregator.assert_metric('openstack.keystone.groups.users', count=0)
    assert 'HTTPError while reporting identity groups metrics' in caplog.text


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


def test_services_metrics_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default", defaults={'identity/v3/services': MockResponse(status_code=500)}
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('openstack.keystone.services.count', count=0)
    aggregator.assert_metric('openstack.keystone.services.enabled', count=0)
    assert 'HTTPError while reporting identity services metrics' in caplog.text


def test_services_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.services.count',
        value=8,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:155d28a57a054d5fae86410b566ffca1',
            'service_name:placement',
            'service_type:placement',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:17d8088bf93b41b19ae971eb6f2aa7a5',
            'service_name:nova_legacy',
            'service_type:compute_legacy',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:271afc4cc62e493592b6be9b87bfb108',
            'service_name:keystone',
            'service_type:identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:3ef836a26c2c40acabb07a6415384f20',
            'service_name:cinderv3',
            'service_type:volumev3',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:55b21161725a461793a2222749229306',
            'service_name:cinder',
            'service_type:block-storage',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:7dca0a2e55d74d66995f3105ed69608f',
            'service_name:neutron',
            'service_type:network',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:82624ab61fb04f058d043facf315fa3c',
            'service_name:glance',
            'service_type:image',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.services.enabled',
        value=1,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'service_id:9aca42df11e84366924013b2f1a1259b',
            'service_name:nova',
            'service_type:compute',
        ],
    )


def test_limits_metrics_error(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default", defaults={'identity/v3/limits': MockResponse(status_code=500)}
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('openstack.keystone.limits', count=0)
    assert 'HTTPError while reporting identity limits metrics' in caplog.text


def test_limits_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.limits',
        value=1000,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'limit_id:dd4fefa5602a4414b1c0a01ac7514b97',
            'region_id:RegionOne',
            'resource_name:image_size_total',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limits',
        value=1000,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'limit_id:5e7d44c9d30d47919187a5c1a58a8885',
            'region_id:RegionOne',
            'resource_name:image_stage_total',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limits',
        value=100,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'limit_id:9f489d63900841f4a70fe58036c81339',
            'region_id:RegionOne',
            'resource_name:image_count_total',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limits',
        value=100,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'domain_id:default',
            'limit_id:5d26b57b414c4e25848cd34b38f56606',
            'region_id:RegionOne',
            'resource_name:image_count_uploading',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
