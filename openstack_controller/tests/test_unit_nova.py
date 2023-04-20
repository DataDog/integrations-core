# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.metrics import (
    NOVA_FLAVOR_METRICS,
    NOVA_HYPERVISOR_LOAD_METRICS,
    NOVA_HYPERVISOR_METRICS,
    NOVA_LIMITS_METRICS,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_SERVER_METRICS,
    NOVA_SERVICE_CHECK,
)

from .common import CONFIG, CONFIG_NOVA_MICROVERSION_LATEST, MockHttp, check_microversion, is_mandatory

pytestmark = [pytest.mark.unit]


def test_exception(aggregator, dd_run_check, instance, caplog, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", exceptions={'compute/v2.1': Exception()})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    assert 'Exception while reporting compute metrics' in caplog.text


def test_endpoint_not_in_catalog(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default",
        replace={
            'identity/v3/auth/tokens': lambda d: {
                **d,
                **{
                    'token': {
                        **d['token'],
                        **{'catalog': d['token'].get('catalog', [])[:7] + d['token'].get('catalog', [])[8:]},
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
        NOVA_SERVICE_CHECK,
        status=AgentCheck.UNKNOWN,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        NOVA_SERVICE_CHECK,
        status=AgentCheck.UNKNOWN,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


def test_endpoint_down(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default", defaults={'compute/v2.1': MockResponse(status_code=500)})
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check(
        NOVA_SERVICE_CHECK,
        status=AgentCheck.CRITICAL,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        NOVA_SERVICE_CHECK,
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
        NOVA_SERVICE_CHECK,
        status=AgentCheck.OK,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        NOVA_SERVICE_CHECK,
        status=AgentCheck.OK,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.response_time',
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.response_time',
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


@pytest.mark.parametrize(
    "instance",
    [
        pytest.param(CONFIG, id="default"),
        pytest.param(CONFIG_NOVA_MICROVERSION_LATEST, id="latest"),
    ],
)
def test_limits_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    not_found_metrics = []
    for key, value in NOVA_LIMITS_METRICS.items():
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
            else:
                not_found_metrics.append(key)
    assert not_found_metrics == [], f"No nova limits metrics found: {not_found_metrics}"


@pytest.mark.parametrize(
    "instance",
    [
        pytest.param(CONFIG, id="default"),
        pytest.param(CONFIG_NOVA_MICROVERSION_LATEST, id="latest"),
    ],
)
def test_quota_set_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    not_found_metrics = []
    for key, value in NOVA_QUOTA_SETS_METRICS.items():
        if check_microversion(instance, value):
            if key in aggregator.metric_names:
                aggregator.assert_metric(
                    key,
                    tags=[
                        'domain_id:default',
                        'keystone_server:{}'.format(instance["keystone_server_url"]),
                        'project_id:1e6e233e637d4d55a50a62b63398ad15',
                        'project_name:demo',
                        'quota_id:1e6e233e637d4d55a50a62b63398ad15',
                    ],
                )
                aggregator.assert_metric(
                    key,
                    tags=[
                        'domain_id:default',
                        'keystone_server:{}'.format(instance["keystone_server_url"]),
                        'project_id:6e39099cccde4f809b003d9e0dd09304',
                        'project_name:admin',
                        'quota_id:6e39099cccde4f809b003d9e0dd09304',
                    ],
                )
            elif is_mandatory(value):
                not_found_metrics.append(key)
    assert not_found_metrics == [], f"No nova quotas metrics found: {not_found_metrics}"


@pytest.mark.parametrize(
    "instance",
    [
        pytest.param(CONFIG, id="default"),
        pytest.param(CONFIG_NOVA_MICROVERSION_LATEST, id="latest"),
    ],
)
def test_server_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    not_found_metrics = []
    for key, value in NOVA_SERVER_METRICS.items():
        if check_microversion(instance, value):
            if key in aggregator.metric_names:
                if key == "openstack.nova.server.count":
                    tags = [
                        'domain_id:default',
                        'keystone_server:{}'.format(instance["keystone_server_url"]),
                        'project_id:6e39099cccde4f809b003d9e0dd09304',
                        'project_name:admin',
                    ]
                else:
                    tags = [
                        'domain_id:default',
                        'keystone_server:{}'.format(instance["keystone_server_url"]),
                        'project_id:6e39099cccde4f809b003d9e0dd09304',
                        'project_name:admin',
                        'server_id:2c653a68-b520-4582-a05d-41a68067d76c',
                        'server_name:server',
                        'server_status:active',
                        'hypervisor:agent-integrations-openstack-default',
                        'flavor_name:cirros256',
                    ]
                aggregator.assert_metric(key, tags=tags)
            elif is_mandatory(value):
                not_found_metrics.append(key)
    assert not_found_metrics == [], f"No nova server metrics found: {not_found_metrics}"


@pytest.mark.parametrize(
    "instance",
    [
        pytest.param(CONFIG, id="default"),
        pytest.param(CONFIG_NOVA_MICROVERSION_LATEST, id="latest"),
    ],
)
def test_flavor_metrics(aggregator, dd_run_check, monkeypatch, instance):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    found = False
    for metric in aggregator.metric_names:
        if metric in NOVA_FLAVOR_METRICS:
            found = True
            aggregator.assert_metric(
                metric,
                tags=[
                    'domain_id:default',
                    'keystone_server:{}'.format(instance["keystone_server_url"]),
                    'project_id:6e39099cccde4f809b003d9e0dd09304',
                    'project_name:admin',
                    'flavor_id:1',
                    'flavor_name:m1.tiny',
                ],
            )
    assert found, "No flavor metrics found"


def test_hypervisor_service_check_up(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    project_tags = [
        'domain_id:default',
        'keystone_server:{}'.format(instance["keystone_server_url"]),
        'project_id:6e39099cccde4f809b003d9e0dd09304',
        'project_name:admin',
    ]
    tags = project_tags + [
        'aggregate:my-aggregate',
        'availability_zone:availability-zone',
        'hypervisor:agent-integrations-openstack-default',
        'hypervisor_id:1',
        'status:enabled',
        'virt_type:QEMU',
    ]
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('openstack.nova.hypervisor.up', status=AgentCheck.OK, tags=tags)


def test_hypervisor_service_check_down(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp(
        "agent-integrations-openstack-default",
        replace={
            'compute/v2.1/os-hypervisors/detail?with_servers=true': lambda d: {
                **d,
                **{
                    'hypervisors': d['hypervisors'][:0]
                    + [{**d['hypervisors'][0], **{'state': 'down'}}]
                    + d['hypervisors'][1:]
                },
            }
        },
    )
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    project_tags = [
        'domain_id:default',
        'keystone_server:{}'.format(instance["keystone_server_url"]),
        'project_id:6e39099cccde4f809b003d9e0dd09304',
        'project_name:admin',
    ]
    tags = project_tags + [
        'aggregate:my-aggregate',
        'availability_zone:availability-zone',
        'hypervisor:agent-integrations-openstack-default',
        'hypervisor_id:1',
        'status:enabled',
        'virt_type:QEMU',
    ]
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_service_check('openstack.nova.hypervisor.up', status=AgentCheck.CRITICAL, tags=tags)


def test_hypervisor_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in NOVA_HYPERVISOR_METRICS:
        aggregator.assert_metric(
            metric,
            tags=[
                'domain_id:default',
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
                'aggregate:my-aggregate',
                'availability_zone:availability-zone',
                'hypervisor:agent-integrations-openstack-default',
                'hypervisor_id:1',
                'status:enabled',
                'virt_type:QEMU',
            ],
        )


def test_latest_hypervisor_metrics(aggregator, dd_run_check, instance_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_nova_microversion_latest])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.hypervisor.up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'aggregate:my-aggregate',
            'availability_zone:availability-zone',
            'hypervisor:agent-integrations-openstack-default',
            'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661',
            'status:enabled',
            'virt_type:QEMU',
        ],
    )
    for metric in NOVA_HYPERVISOR_LOAD_METRICS:
        aggregator.assert_metric(
            metric,
            tags=[
                'domain_id:default',
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
                'aggregate:my-aggregate',
                'availability_zone:availability-zone',
                'hypervisor:agent-integrations-openstack-default',
                'hypervisor_id:d884b51a-e464-49dc-916c-766da0237661',
                'status:enabled',
                'virt_type:QEMU',
            ],
        )
