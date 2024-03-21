# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging
import os

import pytest

import tests.configs as configs
from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
from datadog_checks.openstack_controller.api.type import ApiType
from tests.common import remove_service_from_catalog
from tests.metrics import (
    CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
    CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
    IRONIC_NODE_COUNT,
    NODES_METRICS_IRONIC_MICROVERSION_1_80,
    NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
)

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
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_ironic_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_ironic_node_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "nodes": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.node.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_ironic_conductor_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "conductors": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.conductor.')


@pytest.mark.parametrize(
    ('mock_http_post', 'session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['baremetal'])}},
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
    assert args_list.count('http://127.0.0.1:6385/baremetal') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert session_auth.get_access.call_count == 4
    assert '`baremetal` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/baremetal': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/baremetal': MockResponse(status_code=500)}},
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
    assert args_list.count('http://127.0.0.1:6385/baremetal') == 2


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
    assert args_list.count('http://127.0.0.1:6385/baremetal') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_baremetal', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/baremetal/v1/nodes/detail': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'nodes': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_baremetal'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_nodes_exception(aggregator, check, dd_run_check, mock_http_get, connection_baremetal, api_type):
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
        assert args_list.count('http://127.0.0.1:6385/baremetal/v1/nodes/detail') == 2
    if api_type == ApiType.SDK:
        assert connection_baremetal.nodes.call_count == 2


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_nodes_metrics(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('connection_baremetal', 'paginated_limit', 'instance', 'metrics', 'api_type', 'expected_api_call_count'),
    [
        pytest.param(
            None,
            1,
            configs.REST,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.REST,
            4,
            id='api rest no microversion',
        ),
        pytest.param(
            None,
            1000,
            configs.REST,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.REST,
            1,
            id='api rest no microversion',
        ),
        pytest.param(
            None,
            1,
            configs.REST_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.REST,
            4,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            None,
            1,
            configs.SDK,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.SDK,
            1,
            id='api sdk no microversion',
        ),
        pytest.param(
            None,
            1,
            configs.SDK_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.SDK,
            1,
            id='api sdk microversion 1.80',
        ),
        pytest.param(
            None,
            1000,
            configs.SDK_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.SDK,
            1,
            id='api sdk microversion 1.80',
        ),
    ],
    indirect=['connection_baremetal'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_ironic_nodes_pagination(
    aggregator,
    dd_run_check,
    instance,
    openstack_controller_check,
    paginated_limit,
    metrics,
    api_type,
    expected_api_call_count,
    mock_http_get,
    connection_baremetal,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)

        baremetal_url = (
            'http://127.0.0.1:6385/baremetal/v1/nodes/detail'
            if instance.get("ironic_microversion", None) != "1.80"
            else 'http://127.0.0.1:6385/baremetal/v1/nodes'
        )
        assert args_list.count(baremetal_url) == expected_api_call_count
    if api_type == ApiType.SDK:
        assert connection_baremetal.nodes.call_count == expected_api_call_count


@pytest.mark.parametrize(
    ('mock_http_get', 'paginated_limit'),
    [
        pytest.param(
            {
                'mock_data': {
                    '/baremetal/v1/nodes/detail': {"nodes": []},
                }
            },
            1,
            id='api empty nodes',
        ),
        pytest.param(
            {
                'mock_data': {
                    '/baremetal/v1/nodes/detail': {"node": [{"test": "attr"}]},
                }
            },
            1,
            id='api no nodes ',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_pagination_invalid_no_exception(aggregator, openstack_controller_check, dd_run_check, paginated_limit):
    paginated_instance = copy.deepcopy(configs.REST)
    paginated_instance['paginated_limit'] = paginated_limit
    check = openstack_controller_check(paginated_instance)
    dd_run_check(check)
    aggregator.assert_metric(IRONIC_NODE_COUNT, count=0)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_baremetal', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/baremetal/v1/conductors': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'conductors': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_baremetal'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_conductors_exception(aggregator, check, dd_run_check, mock_http_get, connection_baremetal, api_type):
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
        assert args_list.count('http://127.0.0.1:6385/baremetal/v1/conductors') == 2
    if api_type == ApiType.SDK:
        assert connection_baremetal.conductors.call_count == 2


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api sdk no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            id='api sdk microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_conductors_metrics(aggregator, check, dd_run_check, metrics):
    dd_run_check(check)
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
        )


@pytest.mark.parametrize(
    ('connection_baremetal', 'paginated_limit', 'instance', 'metrics', 'api_type', 'expected_api_call_count'),
    [
        pytest.param(
            None,
            1,
            configs.REST,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.REST,
            2,
            id='api rest no microversion low limit',
        ),
        pytest.param(
            None,
            1000,
            configs.REST,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.REST,
            1,
            id='api rest no microversion high limit',
        ),
        pytest.param(
            None,
            1,
            configs.REST_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.REST,
            2,
            id='api rest microversion 1.80 low limit',
        ),
        pytest.param(
            None,
            1000,
            configs.REST_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.REST,
            1,
            id='api rest microversion 1.80 high limit',
        ),
        pytest.param(
            None,
            1,
            configs.SDK,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.SDK,
            1,
            id='api sdk no microversion low limit',
        ),
        pytest.param(
            None,
            1000,
            configs.SDK,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            ApiType.SDK,
            1,
            id='api sdk no microversion high limit',
        ),
        pytest.param(
            None,
            1,
            configs.SDK_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.SDK,
            1,
            id='api sdk microversion 1.80 low limit',
        ),
        pytest.param(
            None,
            1000,
            configs.SDK_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            ApiType.SDK,
            1,
            id='api sdk microversion 1.80 high limit',
        ),
    ],
    indirect=['connection_baremetal'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_conductors_pagination(
    aggregator,
    dd_run_check,
    instance,
    openstack_controller_check,
    paginated_limit,
    metrics,
    api_type,
    expected_api_call_count,
    mock_http_get,
    connection_baremetal,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)

        baremetal_url = 'http://127.0.0.1:6385/baremetal/v1/conductors'
        assert args_list.count(baremetal_url) == expected_api_call_count
    if api_type == ApiType.SDK:
        assert connection_baremetal.conductors.call_count == expected_api_call_count
