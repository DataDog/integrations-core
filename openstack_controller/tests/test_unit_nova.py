# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import logging
import os

import mock
import pytest

import tests.configs as configs
import tests.metrics as metrics
from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller.api.type import ApiType
from tests.common import remove_service_from_catalog

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(os.environ.get('OPENSTACK_E2E_LEGACY') == 'true', reason='Not Legacy test'),
]


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_nova_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.nova.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_nova_limit_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "limits": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.nova.limit.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_nova_service_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "services": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.nova.service.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_nova_flavor_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "flavors": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.nova.flavor.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_nova_quota_set_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "quota_sets": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.nova.quota_set.')


@pytest.mark.parametrize(
    ('mock_http_post', 'session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['compute'])}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'catalog': []},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post', 'session_auth'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_not_in_catalog(aggregator, check, dd_run_check, caplog, mock_http_post, session_auth, api_type):
    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    aggregator.assert_metric(
        'openstack.nova.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8774/compute/v2.1') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert session_auth.get_access.call_count == 4
    assert '`compute` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/compute/v2.1': MockResponse(status_code=500)}},
            configs.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time_exception(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8774/compute/v2.1') == 2


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8774/compute/v2.1') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/limits?tenant_id=1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/compute/v2.1/limits?tenant_id=6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                }
            },
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'limits': {
                        '1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                        '6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_limits_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_instances',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_cores',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_ram_size',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_meta',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        num_calls = sum('http://127.0.0.1:8774/compute/v2.1/limits?tenant_id=' in arg for arg in args_list)
        assert num_calls == 2
    if api_type == ApiType.SDK:
        assert connection_compute.get_limits.call_count == 2


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_limits_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_instances',
        value=10,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_instances',
        value=10,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_cores',
        value=20,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_cores',
        value=20,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_ram_size',
        value=51200,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_ram_size',
        value=51200,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_meta',
        value=128,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_meta',
        value=128,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_keypairs',
        value=100,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_total_keypairs',
        value=100,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_groups',
        value=10,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_groups',
        value=10,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_group_members',
        value=10,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.max_server_group_members',
        value=10,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_ram_used',
        value=2048,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_ram_used',
        value=2048,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_cores_used',
        value=8,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_cores_used',
        value=8,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_instances_used',
        value=8,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_instances_used',
        value=8,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )

    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_server_groups_used',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:admin',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.limit.absolute.total_server_groups_used',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/os-services': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'services': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_services_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.service.up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/os-services') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.services.call_count == 2


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            metrics.COMPUTE_SERVICES_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVICES_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            metrics.COMPUTE_SERVICES_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVICES_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_services_metrics(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
        )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/flavors/detail': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'flavors': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_flavors_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/flavors/detail') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.flavors.call_count == 2


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_flavors_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:1',
            'flavor_name:m1.tiny',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:2',
            'flavor_name:m1.small',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=2,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:3',
            'flavor_name:m1.medium',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=4,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:4',
            'flavor_name:m1.large',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:42',
            'flavor_name:m1.nano',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=8,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:5',
            'flavor_name:m1.xlarge',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:84',
            'flavor_name:m1.micro',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:c1',
            'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d1',
            'flavor_name:ds512M',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d2',
            'flavor_name:ds1G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=2,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d3',
            'flavor_name:ds2G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=4,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d4',
            'flavor_name:ds4G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:1',
            'flavor_name:m1.tiny',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:2',
            'flavor_name:m1.small',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:3',
            'flavor_name:m1.medium',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:4',
            'flavor_name:m1.large',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:42',
            'flavor_name:m1.nano',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:5',
            'flavor_name:m1.xlarge',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:84',
            'flavor_name:m1.micro',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:c1',
            'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d1',
            'flavor_name:ds512M',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d2',
            'flavor_name:ds1G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d3',
            'flavor_name:ds2G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d4',
            'flavor_name:ds4G',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/os-hypervisors/detail': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'hypervisors': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_hypervisors_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.hypervisor.up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/os-hypervisors/detail') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.hypervisors.call_count == 2


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/os-hypervisors/1/uptime': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'hypervisor_uptime': {1: MockResponse(status_code=500)}}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_hypervisor_uptime_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.hypervisor.up',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
        hostname='agent-integrations-openstack-default',
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_1',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_5',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_15',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/os-hypervisors/1/uptime') == 1
    if api_type == ApiType.SDK:
        assert connection_compute.get_hypervisor_uptime.call_count == 1
        assert connection_compute.get_hypervisor_uptime.call_args_list.count(mock.call(1)) == 1


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_hypervisors_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "hypervisors": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NOVA_ALL_HYPERVISOR_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_all_hypervisors_uptime_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "hypervisors": {
                    "include": [
                        {
                            "hypervisor_hostname": ".*",
                            "uptime": False,
                        },
                    ],
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NOVA_HYPERVISOR_UPTIME_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            metrics.COMPUTE_HYPERVISORS_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_HYPERVISORS_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            metrics.COMPUTE_HYPERVISORS_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_HYPERVISORS_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_hypervisors_metrics(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest nova microverion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk nova microverion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_compute_collect_for_all_projects(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NOVA_PROJECT_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest nova microverion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk nova microverion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_servers_collect_for_all_projects(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "servers": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NOVA_ALL_SERVER_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest nova microverion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk nova microverion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_flavors_collect_for_all_servers(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "servers": {
                    "include": [
                        {
                            "name": ".*",
                            "flavors": False,
                        }
                    ]
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NOVA_SERVER_FLAVOR_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            id='api rest nova microverion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            id='api sdk nova microverion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_diagnostics_collect_for_all_servers(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "compute": {
                "servers": {
                    "include": [
                        {
                            "name": ".*",
                            "diagnostics": False,
                        }
                    ]
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NOVA_ALL_DIAGNOSTIC_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/os-quota-sets/1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/compute/v2.1/os-quota-sets/6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                }
            },
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'quota_sets': {
                        '1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                        '6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quota_sets_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.quota_set.cores',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/os-quota-sets/1e6e233e637d4d55a50a62b63398ad15') == 1
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/os-quota-sets/6e39099cccde4f809b003d9e0dd09304') == 1
    if api_type == ApiType.SDK:
        assert connection_compute.get_quota_set.call_count == 2
        assert connection_compute.get_quota_set.call_args_list.count(mock.call('1e6e233e637d4d55a50a62b63398ad15')) == 1
        assert connection_compute.get_quota_set.call_args_list.count(mock.call('6e39099cccde4f809b003d9e0dd09304')) == 1


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            metrics.COMPUTE_QUOTA_SETS_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_QUOTA_SETS_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            metrics.COMPUTE_QUOTA_SETS_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_QUOTA_SETS_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quota_sets_metrics(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
        )


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_QUOTA_SETS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_QUOTA_SETS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_QUOTA_SETS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_QUOTA_SETS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quota_sets_metrics_excluding_demo_project(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
        )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/servers/detail?project_id=1e6e233e637d4d55a50a62b63398ad15': MockResponse(
                        status_code=500
                    ),
                    '/compute/v2.1/servers/detail?project_id=6e39099cccde4f809b003d9e0dd09304': MockResponse(
                        status_code=500
                    ),
                }
            },
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'servers': {
                        '1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                        '6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_exception(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.server.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/detail?project_id=1e6e233e637d4d55a50a62b63398ad15'
            )
            == 1
        )
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/detail?project_id=6e39099cccde4f809b003d9e0dd09304'
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_compute.servers.call_count == 2
        assert (
            connection_compute.servers.call_args_list.count(
                mock.call(details=True, project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_compute.servers.call_args_list.count(
                mock.call(details=True, project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


@pytest.mark.parametrize(
    ('instance', 'api_type'),
    [
        pytest.param(
            configs.REST_DEMO_SERVERS_COLLECT_FALSE,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            configs.SDK_DEMO_SERVERS_COLLECT_FALSE,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_disable_call(aggregator, check, dd_run_check, mock_http_get, connection_compute, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.server.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:admin-1',
            'server_status:ACTIVE',
            'hypervisor:agent-integrations-openstack-default',
            'instance_name:instance-0000004a',
        ],
        hostname='5102fbbf-7156-48dc-8355-af7ab992266f',
    )
    aggregator.assert_metric(
        'openstack.nova.server.count',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:67ca710a-e73f-4801-a12f-d0c55ccb8955',
            'server_name:demo-1',
            'server_status:ACTIVE',
        ],
    ),
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/detail?project_id=1e6e233e637d4d55a50a62b63398ad15'
            )
            == 0
        )
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/detail?project_id=6e39099cccde4f809b003d9e0dd09304'
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_compute.servers.call_count == 1
        assert (
            connection_compute.servers.call_args_list.count(
                mock.call(details=True, project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 0
        )
        assert (
            connection_compute.servers.call_args_list.count(
                mock.call(details=True, project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_metrics(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93_EXCLUDING_DEMO_PROJECT,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEMO_PROJECT_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_metrics_excluding_demo_project(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST_EXCLUDING_DEV_SERVERS,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEV_SERVERS_NOVA_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93_EXCLUDING_DEV_SERVERS,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEV_SERVERS_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK_EXCLUDING_DEV_SERVERS,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEV_SERVERS_NOVA_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93_EXCLUDING_DEV_SERVERS,
            metrics.COMPUTE_SERVERS_EXCLUDING_DEV_SERVERS_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_metrics_excluding_dev_servers(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'metrics', 'api_type', 'microversion'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/flavors/c1': MockResponse(status_code=500),
                }
            },
            None,
            configs.REST,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT_FLAVOR_EXCEPTION,
            ApiType.REST,
            None,
            id='api rest no microversion',
        ),
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/flavors/c1': MockResponse(status_code=500),
                }
            },
            None,
            configs.REST_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_2_93_FLAVOR_EXCEPTION,
            ApiType.REST,
            '2.93',
            id='api rest microversion 2.93',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'flavors': {
                        'c1': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT_FLAVOR_EXCEPTION,
            ApiType.SDK,
            None,
            id='api sdk no microversion',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'flavors': {
                        'c1': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_2_93_FLAVOR_EXCEPTION,
            ApiType.SDK,
            '2.93',
            id='api sdk microversion 2.93',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_server_flavors_exception(
    aggregator, check, dd_run_check, mock_http_get, connection_compute, metrics, api_type, microversion
):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/5102fbbf-7156-48dc-8355-af7ab992266f/diagnostics'
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_compute.get_server_diagnostics.call_count == 11
        assert (
            connection_compute.get_server_diagnostics.call_args_list.count(
                mock.call('5102fbbf-7156-48dc-8355-af7ab992266f')
            )
            == 1
        )


@pytest.mark.parametrize(
    ('instance', 'metrics', 'api_type', 'microversion', 'get_flavor_calls'),
    [
        pytest.param(
            configs.REST_DEMO_SERVERS_FLAVORS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_FLAVORS_NOVA_MICROVERSION_DEFAULT,
            ApiType.REST,
            None,
            3,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93_DEMO_SERVERS_FLAVORS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_FLAVORS_NOVA_MICROVERSION_2_93,
            ApiType.REST,
            '2.93',
            0,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK_DEMO_SERVERS_FLAVORS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_FLAVORS_NOVA_MICROVERSION_DEFAULT,
            ApiType.SDK,
            None,
            3,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93_DEMO_SERVERS_FLAVORS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_FLAVORS_NOVA_MICROVERSION_2_93,
            ApiType.SDK,
            '2.93',
            0,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_server_disable_flavors(
    aggregator,
    check,
    dd_run_check,
    mock_http_get,
    connection_compute,
    metrics,
    api_type,
    microversion,
    get_flavor_calls,
):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8774/compute/v2.1/flavors/c1') == get_flavor_calls
    if api_type == ApiType.SDK:
        assert connection_compute.get_flavor.call_args_list.count(mock.call('c1')) == get_flavor_calls


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'metrics', 'api_type', 'microversion'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/servers/5102fbbf-7156-48dc-8355-af7ab992266f/diagnostics': MockResponse(
                        status_code=500
                    ),
                }
            },
            None,
            configs.REST,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT_SERVER_DIAGNOSTICS_EXCEPTION,
            ApiType.REST,
            None,
            id='api rest no microversion',
        ),
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/servers/5102fbbf-7156-48dc-8355-af7ab992266f/diagnostics': MockResponse(
                        status_code=500
                    ),
                }
            },
            None,
            configs.REST_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_2_93_SERVER_DIAGNOSTICS_EXCEPTION,
            ApiType.REST,
            '2.93',
            id='api rest microversion 2.93',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'server_diagnostics': {
                        '5102fbbf-7156-48dc-8355-af7ab992266f': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_DEFAULT_SERVER_DIAGNOSTICS_EXCEPTION,
            ApiType.SDK,
            None,
            id='api sdk no microversion',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'server_diagnostics': {
                        '5102fbbf-7156-48dc-8355-af7ab992266f': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK_NOVA_MICROVERSION_2_93,
            metrics.COMPUTE_SERVERS_NOVA_MICROVERSION_2_93_SERVER_DIAGNOSTICS_EXCEPTION,
            ApiType.SDK,
            '2.93',
            id='api sdk microversion 2.93',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_server_diagnostics_exception(
    aggregator, check, dd_run_check, mock_http_get, connection_compute, metrics, api_type, microversion
):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/5102fbbf-7156-48dc-8355-af7ab992266f/diagnostics'
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_compute.get_server_diagnostics.call_count == 11
        assert (
            connection_compute.get_server_diagnostics.call_args_list.count(
                mock.call('5102fbbf-7156-48dc-8355-af7ab992266f')
            )
            == 1
        )


@pytest.mark.parametrize(
    ('instance', 'metrics', 'api_type', 'microversion'),
    [
        pytest.param(
            configs.REST_DEMO_SERVERS_DIAGNOSTICS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_DIAGNOSTICS_NOVA_MICROVERSION_DEFAULT,
            ApiType.REST,
            None,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_NOVA_MICROVERSION_2_93_DEMO_SERVERS_DIAGNOSTICS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_DIAGNOSTICS_NOVA_MICROVERSION_2_93,
            ApiType.REST,
            '2.93',
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK_DEMO_SERVERS_DIAGNOSTICS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_DIAGNOSTICS_NOVA_MICROVERSION_DEFAULT,
            ApiType.SDK,
            None,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_NOVA_MICROVERSION_2_93_DEMO_SERVERS_DIAGNOSTICS_FALSE,
            metrics.COMPUTE_SERVERS_DISABLED_DIAGNOSTICS_NOVA_MICROVERSION_2_93,
            ApiType.SDK,
            '2.93',
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_server_disable_diagnostics(
    aggregator, check, dd_run_check, mock_http_get, connection_compute, metrics, api_type, microversion
):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric.get('count'),
            value=metric.get('value'),
            tags=metric.get('tags'),
            hostname=metric.get('hostname'),
        )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://127.0.0.1:8774/compute/v2.1/servers/67ca710a-e73f-4801-a12f-d0c55ccb8955/diagnostics'
            )
            == 0
        )
    if api_type == ApiType.SDK:
        assert (
            connection_compute.get_server_diagnostics.call_args_list.count(
                mock.call('67ca710a-e73f-4801-a12f-d0c55ccb8955', microversion=microversion)
            )
            == 0
        )
