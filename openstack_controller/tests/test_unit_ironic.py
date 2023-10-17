# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

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
def test_disable_baremetal_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
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
    ('mock_http_post', 'connection_session_auth', 'instance', 'api_type'),
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
    indirect=['mock_http_post', 'connection_session_auth'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_not_in_catalog(aggregator, check, dd_run_check, caplog, mock_http_post, connection_session_auth, api_type):
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
        assert connection_session_auth.get_access.call_count == 4
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
        )


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
