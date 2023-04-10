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
    NOVA_LATEST_LIMITS_METRICS,
    NOVA_LATEST_QUOTA_SETS_METRICS,
    NOVA_LATEST_SERVER_METRICS,
    NOVA_LIMITS_METRICS,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_SERVER_METRICS,
)

from .common import MockHttp

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
        'openstack.nova.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:18a64e25fb53453ebd10a45fd974b816',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.UNKNOWN,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:01b21103a92d4997ab09e46ff8346bd5',
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
        'openstack.nova.api.up',
        status=AgentCheck.CRITICAL,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
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
        'openstack.nova.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.OK,
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.response_time',
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.response_time',
        tags=[
            'keystone_server:{}'.format(instance["keystone_server_url"]),
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


def test_limits_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in NOVA_LIMITS_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.limits.{metric}',
            tags=[
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:1e6e233e637d4d55a50a62b63398ad15',
                'project_name:demo',
            ],
        )
        aggregator.assert_metric(
            f'openstack.nova.limits.{metric}',
            tags=[
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
            ],
        )


def test_latest_limits_metrics(aggregator, dd_run_check, instance_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_nova_microversion_latest])
    dd_run_check(check)
    for metric in NOVA_LATEST_LIMITS_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.limits.{metric}',
            tags=[
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:1e6e233e637d4d55a50a62b63398ad15',
                'project_name:demo',
            ],
        )
        aggregator.assert_metric(
            f'openstack.nova.limits.{metric}',
            tags=[
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
            ],
        )


def test_quota_set_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in NOVA_QUOTA_SETS_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.quota_set.{metric}',
            tags=[
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:1e6e233e637d4d55a50a62b63398ad15',
                'project_name:demo',
            ],
        )
        aggregator.assert_metric(
            f'openstack.nova.quota_set.{metric}',
            tags=[
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
            ],
        )


def test_latest_quota_set_metrics(aggregator, dd_run_check, instance_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_nova_microversion_latest])
    dd_run_check(check)
    for metric in NOVA_LATEST_QUOTA_SETS_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.quota_set.{metric}',
            tags=[
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:1e6e233e637d4d55a50a62b63398ad15',
                'project_name:demo',
            ],
        )
        aggregator.assert_metric(
            f'openstack.nova.quota_set.{metric}',
            tags=[
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
            ],
        )


def test_server_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in NOVA_SERVER_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.server.{metric}',
            tags=[
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
                'server_id:2c653a68-b520-4582-a05d-41a68067d76c',
                'server_name:server',
            ],
        )


def test_latest_server_metrics(aggregator, dd_run_check, instance_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_nova_microversion_latest])
    dd_run_check(check)
    for metric in NOVA_LATEST_SERVER_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.server.{metric}',
            tags=[
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
                'server_id:2c653a68-b520-4582-a05d-41a68067d76c',
                'server_name:server',
            ],
        )


def test_flavor_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in NOVA_FLAVOR_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.flavor.{metric}',
            tags=[
                'keystone_server:{}'.format(instance["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
                'flavor_id:1',
                'flavor_name:m1.tiny',
            ],
        )


def test_latest_flavor_metrics(aggregator, dd_run_check, instance_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_nova_microversion_latest])
    dd_run_check(check)
    for metric in NOVA_FLAVOR_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.flavor.{metric}',
            tags=[
                'keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"]),
                'project_id:6e39099cccde4f809b003d9e0dd09304',
                'project_name:admin',
                'flavor_id:1',
                'flavor_name:m1.tiny',
            ],
        )


def test_hypervisor_service_check_up(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    project_tags = [
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
            f'openstack.nova.hypervisor.{metric}',
            tags=[
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
    for metric in NOVA_HYPERVISOR_LOAD_METRICS:
        aggregator.assert_metric(
            f'openstack.nova.hypervisor.{metric}',
            tags=[
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


def test_nova_metrics_ironic(aggregator, dd_run_check, instance_ironic_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_ironic_nova_microversion_latest])
    dd_run_check(check)
    for metric in NOVA_FLAVOR_METRICS:
        aggregator.assert_metric(f'openstack.nova.flavor.{metric}')

    for metric in NOVA_LATEST_LIMITS_METRICS:
        aggregator.assert_metric(f'openstack.nova.limits.{metric}')

    for metric in NOVA_LATEST_QUOTA_SETS_METRICS:
        aggregator.assert_metric(f'openstack.nova.quota_set.{metric}')

    # we can't collect hypervisor metrics for bare metal
    for metric in NOVA_HYPERVISOR_LOAD_METRICS:
        aggregator.assert_metric(f'openstack.nova.quota_set.{metric}', count=0)


def test_latest_service_metrics(aggregator, dd_run_check, instance_nova_microversion_latest, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance_nova_microversion_latest])
    dd_run_check(check)

    base_tags = ['keystone_server:{}'.format(instance_nova_microversion_latest["keystone_server_url"])]

    admin_project_tags = base_tags + [
        'project_id:6e39099cccde4f809b003d9e0dd09304',
        'project_name:admin',
    ]

    demo_project_tags = base_tags + [
        'project_id:1e6e233e637d4d55a50a62b63398ad15',
        'project_name:demo',
    ]

    aggregator.assert_metric(
        "openstack.nova.services.nova_compute.status",
        count=1,
        value=1,
        tags=demo_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:7bf08d7e-a939-46c3-bdae-fbe3ebfe78a4',
        ],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_compute.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:7bf08d7e-a939-46c3-bdae-fbe3ebfe78a4',
        ],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=demo_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:df55f706-a60e-4d3d-8cd6-30f5b33d79ce',
        ],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:df55f706-a60e-4d3d-8cd6-30f5b33d79ce',
        ],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:aadbda65-f523-419a-b3df-c287d196a2c1',
        ],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:aadbda65-f523-419a-b3df-c287d196a2c1',
        ],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_scheduler.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:2ec2027d-ac70-4e2b-95ed-fb1756d24996',
        ],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_scheduler.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + [
            'nova_service_state:up',
            'nova_service_host:agent-integrations-openstack-default',
            'nova_service_id:2ec2027d-ac70-4e2b-95ed-fb1756d24996',
        ],
    )


def test_default_service_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-default")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['keystone_server:{}'.format(instance["keystone_server_url"])]

    admin_project_tags = base_tags + [
        'project_id:6e39099cccde4f809b003d9e0dd09304',
        'project_name:admin',
    ]

    demo_project_tags = base_tags + [
        'project_id:1e6e233e637d4d55a50a62b63398ad15',
        'project_name:demo',
    ]

    aggregator.assert_metric(
        "openstack.nova.services.nova_compute.status",
        count=1,
        value=1,
        tags=demo_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:3'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_compute.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:3'],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=demo_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:5'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:5'],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:1'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:1'],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_scheduler.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:2'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_scheduler.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-default', 'nova_service_id:2'],
    )


def test_default_ironic_service_metrics(aggregator, dd_run_check, instance, monkeypatch):
    http = MockHttp("agent-integrations-openstack-ironic")
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=http.get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=http.post))

    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)

    base_tags = ['keystone_server:{}'.format(instance["keystone_server_url"])]

    admin_project_tags = base_tags + [
        'project_id:01b21103a92d4997ab09e46ff8346bd5',
        'project_name:admin',
    ]

    demo_project_tags = base_tags + [
        'project_id:18a64e25fb53453ebd10a45fd974b816',
        'project_name:demo',
    ]

    aggregator.assert_metric(
        "openstack.nova.services.nova_compute.status",
        count=1,
        value=1,
        tags=demo_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:3'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_compute.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:3'],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=demo_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:5'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:5'],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:1'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_conductor.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:1'],
    )

    aggregator.assert_metric(
        "openstack.nova.services.nova_scheduler.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:2'],
    )
    aggregator.assert_metric(
        "openstack.nova.services.nova_scheduler.status",
        count=1,
        value=1,
        tags=admin_project_tags
        + ['nova_service_state:up', 'nova_service_host:agent-integrations-openstack-ironic', 'nova_service_id:2'],
    )
