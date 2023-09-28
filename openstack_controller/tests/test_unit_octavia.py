# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.api.type import ApiType
from tests.common import CONFIG_REST, CONFIG_SDK, remove_service_from_catalog

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['load-balancer'])}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'catalog': []},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post', 'connection_session_auth'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_not_in_catalog(aggregator, dd_run_check, instance, caplog, mock_http_post, connection_session_auth, api_type):
    with caplog.at_level(logging.DEBUG):
        check = OpenStackControllerCheck('test', {}, [instance])
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
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 3
    if api_type == ApiType.SDK:
        assert connection_session_auth.get_access.call_count == 3
    assert '`load-balancer` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/load-balancer': MockResponse(status_code=500)}},
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/load-balancer': MockResponse(status_code=500)}},
            CONFIG_SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time_exception(aggregator, dd_run_check, instance, mock_http_get):
    check = OpenStackControllerCheck('test', {}, [instance])
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
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time(aggregator, dd_run_check, instance, mock_http_get):
    check = OpenStackControllerCheck('test', {}, [instance])
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
                    '/load-balancer/v2/lbaas/loadbalancers?project_id=1e6e233e637d4d55a50a62b63398ad15': MockResponse(
                        status_code=500
                    ),
                    '/load-balancer/v2/lbaas/loadbalancers?project_id=6e39099cccde4f809b003d9e0dd09304': MockResponse(
                        status_code=500
                    ),
                }
            },
            None,
            CONFIG_REST,
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
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_load_balancer'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_loadbalancers_exception(aggregator, dd_run_check, instance, mock_http_get, connection_load_balancer, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.octavia.loadbalancer.admin_state_up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://127.0.0.1:9876/load-balancer/v2/lbaas/loadbalancers?project_id=1e6e233e637d4d55a50a62b63398ad15'
            )
            == 1
        )
        assert (
            args_list.count(
                'http://127.0.0.1:9876/load-balancer/v2/lbaas/loadbalancers?project_id=6e39099cccde4f809b003d9e0dd09304'
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
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_loadbalancers_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
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
