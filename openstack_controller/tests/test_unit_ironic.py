# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging

import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.api.type import ApiType
from tests.common import (
    CONFIG_REST,
    CONFIG_REST_IRONIC_MICROVERSION_1_80,
    CONFIG_SDK,
    CONFIG_SDK_IRONIC_MICROVERSION_1_80,
    remove_service_from_catalog,
)
from tests.metrics import (
    CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
    CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
    NODES_METRICS_IRONIC_MICROVERSION_1_80,
    NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
)

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['baremetal'])}},
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
        'openstack.ironic.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://10.164.0.11/baremetal') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 3
    elif api_type == ApiType.SDK:
        assert connection_session_auth.get_access.call_count == 3
    assert '`baremetal` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/baremetal': MockResponse(status_code=500)}},
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/baremetal': MockResponse(status_code=500)}},
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
        'openstack.ironic.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://10.164.0.11/baremetal') == 2


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
        'openstack.ironic.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://10.164.0.11/baremetal') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_baremetal', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/baremetal/v1/nodes/detail': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'nodes': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_baremetal'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_nodes_exception(aggregator, dd_run_check, instance, mock_http_get, connection_baremetal, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.ironic.node.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.ironic.node.up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/baremetal/v1/nodes/detail') == 2
    elif api_type == ApiType.SDK:
        assert connection_baremetal.nodes.call_count == 2


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            CONFIG_REST,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            CONFIG_SDK,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_nodes_metrics(aggregator, dd_run_check, metrics, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
        )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_baremetal', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/baremetal/v1/conductors': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'conductors': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_baremetal'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_conductors_exception(aggregator, dd_run_check, instance, mock_http_get, connection_baremetal, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.ironic.conductor.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.ironic.conductor.up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/baremetal/v1/conductors') == 2
    elif api_type == ApiType.SDK:
        assert connection_baremetal.conductors.call_count == 2


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            CONFIG_REST,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            CONFIG_SDK,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_conductors_metrics(aggregator, dd_run_check, metrics, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
        )
