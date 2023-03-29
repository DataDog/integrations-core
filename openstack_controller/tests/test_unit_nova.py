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
    NOVA_LATEST_LIMITS_METRICS,
    NOVA_LATEST_QUOTA_SETS_METRICS,
    NOVA_LATEST_SERVER_METRICS,
    NOVA_LIMITS_METRICS,
    NOVA_QUOTA_SETS_METRICS,
    NOVA_SERVER_METRICS,
)

from .common import MockHttp

pytestmark = [pytest.mark.unit]


def test_endpoint_down(aggregator, dd_run_check, instance, monkeypatch):
    monkeypatch.setattr(
        'requests.get',
        mock.MagicMock(side_effect=MockHttp(defaults={'compute/v2.1': MockResponse(status_code=500)}).get),
    )
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
    monkeypatch.setattr('requests.get', mock.MagicMock(side_effect=MockHttp().get))
    monkeypatch.setattr('requests.post', mock.MagicMock(side_effect=MockHttp().post))

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
