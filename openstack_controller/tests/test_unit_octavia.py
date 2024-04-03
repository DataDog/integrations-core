# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import logging
import os

import mock
import pytest

import tests.configs as configs
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
def test_disable_octavia_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.')


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
def test_disable_octavia_loadbalancer_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "loadbalancers": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.loadbalancer.')


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
def test_disable_octavia_loadbalancer_stats_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "loadbalancers": {
                    "include": [
                        {
                            "name": ".*",
                            "stats": False,
                        }
                    ],
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.loadbalancer.stats.')


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
def test_disable_octavia_listener_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "listeners": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.listener.')


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
def test_disable_octavia_listener_stats_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "listeners": {
                    "include": [
                        {
                            "name": ".*",
                            "stats": False,
                        }
                    ],
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.listener.stats.')


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
def test_disable_octavia_pool_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "pools": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.pool.')


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
def test_disable_octavia_pool_member_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "pools": {
                    "include": [
                        {
                            "name": ".*",
                            "members": False,
                        }
                    ],
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.pool.member')


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
def test_disable_octavia_healthmonitor_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "healthmonitors": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.healthmonitor.')


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
def test_disable_octavia_quota_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "quotas": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.quota.')


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
def test_disable_octavia_amphora_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "amphorae": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.amphora.')


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
def test_disable_octavia_amphora_stats_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "load-balancer": {
                "amphorae": {
                    "include": [
                        {
                            "id": ".*",
                            "stats": False,
                        }
                    ],
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.octavia.amphora.stats')


@pytest.mark.parametrize(
    ('mock_http_post', 'session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['load-balancer'])}},
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
        'openstack.octavia.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:9876/load-balancer') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert session_auth.get_access.call_count == 4
    assert '`load-balancer` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/load-balancer': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/load-balancer': MockResponse(status_code=500)}},
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
        'openstack.octavia.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:9876/load-balancer') == 2


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
        'openstack.octavia.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.octavia.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:9876/load-balancer') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/lbaas/loadbalancers': MockResponse(status_code=500),
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
                    'load_balancers': {
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
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_loadbalancers_exception(aggregator, check, dd_run_check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/loadbalancers'], '1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/loadbalancers'], '6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_load_balancer.load_balancers.call_count == 2
        assert (
            connection_load_balancer.load_balancers.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_load_balancer.load_balancers.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


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
def test_loadbalancers_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.stats.active_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.stats.bytes_in',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.stats.bytes_out',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.stats.request_errors',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.stats.total_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'loadbalancer_name:loadbalancer-1',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            3,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            2,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            1,
            id='api sdk small limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_loadbalancers_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    api_type,
    dd_run_check,
    mock_http_get,
    connection_load_balancer,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
            params = kwargs.get('params', {})
            limit = params.get('limit')
            args_list += [(args[0], limit)]
        assert (
            args_list.count(('http://127.0.0.1:9876/load-balancer/v2/lbaas/loadbalancers', paginated_limit))
            == expected_api_calls
        )
    else:
        assert connection_load_balancer.load_balancers.call_count == 2
        assert (
            connection_load_balancer.load_balancers.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_load_balancer.load_balancers.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )
    test_loadbalancers_metrics(aggregator, openstack_controller_check(paginated_instance), dd_run_check)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/lbaas/listeners': MockResponse(status_code=500),
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
                    'listeners': {
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
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_listeners_exception(aggregator, check, dd_run_check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.listener.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/listeners'], '6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )
        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/listeners'], '1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_load_balancer.listeners.call_count == 2
        assert (
            connection_load_balancer.listeners.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_load_balancer.listeners.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


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
def test_listeners_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.listener.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.connection_limit',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.connection_limit',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.connection_limit',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_client_data',
        value=50000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_client_data',
        value=50000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_client_data',
        value=50000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_member_connect',
        value=5000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_member_connect',
        value=5000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_member_connect',
        value=5000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_member_data',
        value=50000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_member_data',
        value=50000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_member_data',
        value=50000,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_tcp_inspect',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_tcp_inspect',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.timeout_tcp_inspect',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.active_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.active_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.active_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.bytes_in',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.bytes_in',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.bytes_in',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.bytes_out',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.bytes_out',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.bytes_out',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.request_errors',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.request_errors',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.request_errors',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.total_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'listener_name:listener-1',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.total_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'listener_name:listener-2',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.listener.stats.total_connections',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'listener_name:listener-3',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'operating_status:ONLINE',
            'provisioning_status:ACTIVE',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            4,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            2,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            1,
            id='api sdk small limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_listeners_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    api_type,
    dd_run_check,
    mock_http_get,
    connection_load_balancer,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
            params = kwargs.get('params', {})
            limit = params.get('limit')
            args_list += [(args[0], limit)]
        assert (
            args_list.count(('http://127.0.0.1:9876/load-balancer/v2/lbaas/listeners', paginated_limit))
            == expected_api_calls
        )
    else:
        assert connection_load_balancer.listeners.call_count == 2
        assert (
            connection_load_balancer.listeners.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_load_balancer.listeners.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )

    test_listeners_metrics(aggregator, openstack_controller_check(paginated_instance), dd_run_check)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/lbaas/pools': MockResponse(status_code=500),
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
                    'pools': {
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
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_pools_exception(aggregator, dd_run_check, check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.pool.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/pools'], '1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/pools'], '6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_load_balancer.pools.call_count == 2
        assert (
            connection_load_balancer.pools.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_load_balancer.pools.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


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
def test_pools_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.pool.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'operating_status:ERROR',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'pool_name:pool-1',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            3,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            2,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            1,
            id='api sdk small limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_pools_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    api_type,
    dd_run_check,
    mock_http_get,
    connection_load_balancer,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
            params = kwargs.get('params', {})
            limit = params.get('limit')
            args_list += [(args[0], limit)]
        assert (
            args_list.count(('http://127.0.0.1:9876/load-balancer/v2/lbaas/pools', paginated_limit))
            == expected_api_calls
        )
    else:
        assert connection_load_balancer.pools.call_count == 2
        assert (
            connection_load_balancer.pools.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_load_balancer.pools.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )
    test_pools_metrics(aggregator, openstack_controller_check(paginated_instance), dd_run_check)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/lbaas/pools/d0335b34-3115-4b3b-9a1a-7e2363ebfee3/members': MockResponse(
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
                    'pool_members': {
                        'd0335b34-3115-4b3b-9a1a-7e2363ebfee3': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_pool_members_exception(aggregator, check, dd_run_check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.pool.member.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (
                    ['http://127.0.0.1:9876/load-balancer/v2/lbaas/pools/d0335b34-3115-4b3b-9a1a-7e2363ebfee3/members'],
                    '1e6e233e637d4d55a50a62b63398ad15',
                )
            )
            == 1
        )
        assert (
            args_list.count(
                (
                    ['http://127.0.0.1:9876/load-balancer/v2/lbaas/pools/d0335b34-3115-4b3b-9a1a-7e2363ebfee3/members'],
                    '6e39099cccde4f809b003d9e0dd09304',
                )
            )
            == 0
        )
    if api_type == ApiType.SDK:
        assert (
            connection_load_balancer.members.call_args_list.count(
                mock.call('d0335b34-3115-4b3b-9a1a-7e2363ebfee3', project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )


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
def test_pool_members_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.pool.member.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'member_id:e79e1011-2eb4-486f-84c3-99d2a4aef88d',
            'member_name:amphora-a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.pool.member.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'member_id:e79e1011-2eb4-486f-84c3-99d2a4aef88d',
            'member_name:amphora-a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.pool.member.weight',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'member_id:e79e1011-2eb4-486f-84c3-99d2a4aef88d',
            'member_name:amphora-a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.pool.member.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'member_id:0abcafea-2ad2-44cd-957f-690644ba479c',
            'member_name:amphora-042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.pool.member.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'member_id:0abcafea-2ad2-44cd-957f-690644ba479c',
            'member_name:amphora-042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.pool.member.weight',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'member_id:0abcafea-2ad2-44cd-957f-690644ba479c',
            'member_name:amphora-042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'operating_status:ERROR',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/lbaas/healthmonitors': MockResponse(status_code=500),
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
                    'health_monitors': {
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
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_healthmonitors_exception(aggregator, check, dd_run_check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.healthmonitor.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/healthmonitors'], '1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/healthmonitors'], '6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert (
            connection_load_balancer.health_monitors.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_load_balancer.health_monitors.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


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
def test_healthmonitors_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.healthmonitor.count',
        value=1,
        tags=[
            'domain_id:default',
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'keystone_server:http://127.0.0.1:8080/identity',
            'operating_status:ONLINE',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'type:HTTP',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.healthmonitor.delay',
        value=5,
        tags=[
            'domain_id:default',
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'keystone_server:http://127.0.0.1:8080/identity',
            'operating_status:ONLINE',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'type:HTTP',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.healthmonitor.timeout',
        value=5,
        tags=[
            'domain_id:default',
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'keystone_server:http://127.0.0.1:8080/identity',
            'operating_status:ONLINE',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'type:HTTP',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.healthmonitor.max_retries',
        value=3,
        tags=[
            'domain_id:default',
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'keystone_server:http://127.0.0.1:8080/identity',
            'operating_status:ONLINE',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'type:HTTP',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.healthmonitor.max_retries_down',
        value=3,
        tags=[
            'domain_id:default',
            'healthmonitor_id:268883b7-c057-4e85-b2c5-d8760267dad1',
            'healthmonitor_name:healthmonitor-1',
            'keystone_server:http://127.0.0.1:8080/identity',
            'operating_status:ONLINE',
            'pool_id:d0335b34-3115-4b3b-9a1a-7e2363ebfee3',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'provisioning_status:ACTIVE',
            'type:HTTP',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/lbaas/quotas': MockResponse(status_code=500),
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
                    'quotas': {
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
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quotas_exception(aggregator, check, dd_run_check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.quota.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/quotas'], '1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/lbaas/quotas'], '6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_load_balancer.quotas.call_count == 2
        assert (
            connection_load_balancer.quotas.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_load_balancer.quotas.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


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
def test_quotas_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.quota.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.loadbalancer',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.loadbalancer',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.load_balancer',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.load_balancer',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.listener',
        value=20,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.listener',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.member',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.member',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.pool',
        value=20,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.pool',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.healthmonitor',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.healthmonitor',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.health_monitor',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.health_monitor',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.l7policy',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.l7policy',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.l7rule',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.quota.l7rule',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_load_balancer', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/load-balancer/v2/octavia/amphorae': MockResponse(status_code=500),
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
                    'amphorae': {
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
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_amphorae_exception(aggregator, check, dd_run_check, mock_http_get, connection_load_balancer, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.amphora.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/octavia/amphorae'], '1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            args_list.count(
                (['http://127.0.0.1:9876/load-balancer/v2/octavia/amphorae'], '6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )

    if api_type == ApiType.SDK:
        assert connection_load_balancer.quotas.call_count == 2
        assert (
            connection_load_balancer.amphorae.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_load_balancer.amphorae.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304')
            )
            == 1
        )


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
def test_amphorae_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.amphora.count',
        value=1,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.active_connections',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.bytes_in',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.bytes_out',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.request_errors',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.total_connections',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:de81cbdc-8207-4253-8f21-3eea9870e7a9',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.active_connections',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.bytes_in',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.bytes_out',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.request_errors',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.total_connections',
        value=0,
        tags=[
            'amphora_id:a34dc4b7-b608-4a9d-9fbd-2a4e611475c2',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:9da03992-77a4-4b65-b39a-0e106961f577',
            'loadbalancer_id:4bb7bfb1-83c2-45e8-b0e1-ed3022329115',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.count',
        value=1,
        tags=[
            'amphora_id:042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.active_connections',
        value=0,
        tags=[
            'amphora_id:042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.bytes_in',
        value=0,
        tags=[
            'amphora_id:042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.bytes_out',
        value=0,
        tags=[
            'amphora_id:042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.request_errors',
        value=0,
        tags=[
            'amphora_id:042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )
    aggregator.assert_metric(
        'openstack.octavia.amphora.stats.total_connections',
        value=0,
        tags=[
            'amphora_id:042bcca4-4d97-47a9-bc04-d88c1e3a4d72',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'listener_id:243decd9-3370-4fc1-b163-80c4155bda04',
            'loadbalancer_id:ae54877c-b186-4b90-b71c-d331b9e732bc',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'status:ALLOCATED',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            3,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            2,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            1,
            id='api sdk small limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_amphorae_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    api_type,
    dd_run_check,
    mock_http_get,
    connection_load_balancer,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
            params = kwargs.get('params', {})
            limit = params.get('limit')
            args_list += [(args[0], limit)]
        assert (
            args_list.count(('http://127.0.0.1:9876/load-balancer/v2/octavia/amphorae', paginated_limit))
            == expected_api_calls
        )
    else:
        assert connection_load_balancer.amphorae.call_count == 2
        assert (
            connection_load_balancer.amphorae.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_load_balancer.amphorae.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )
    test_amphorae_metrics(aggregator, openstack_controller_check(paginated_instance), dd_run_check)
