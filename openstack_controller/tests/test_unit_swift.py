# (C) Datadog, Inc. 2024-present
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
from tests.metrics import (
    CONTAINERS_METRICS_SWIFT,
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
            id='api rest',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_swift_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "swift": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.swift')


@pytest.mark.parametrize(
    ('mock_http_post', 'openstack_v3_password', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['object-store'])}},
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
    indirect=['mock_http_post', 'openstack_v3_password'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_not_in_catalog(aggregator, check, dd_run_check, caplog, mock_http_post, openstack_connection, api_type):
    with caplog.at_level(logging.DEBUG):
        dd_run_check(check)

    aggregator.assert_metric(
        'openstack.swift.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.swift.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:6002/v1') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert openstack_connection.call_count == 4
    assert '`swift` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500)}},
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
        'openstack.swift.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.swift.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:6002/v1') == 0


@pytest.mark.parametrize(
    ('instance', 'api_type'),
    [
        pytest.param(
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time(aggregator, check, dd_run_check, mock_http_get, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.swift.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.swift.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += [(list(args), kwargs.get('params', None))]
    assert args_list.count((['http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15'], None)) == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_swift', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {
                'http_error': {
                    'containers': {
                        '1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    }
                }
            },
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_swift'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_containers_exception(aggregator, check, dd_run_check, mock_http_get, connection_swift, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.swift.container.count',
        count=0,
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += [(list(args), kwargs.get('params', None))]
    if api_type == ApiType.REST:
        assert (
            args_list.count((['http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15'], {'format': 'json'}))
            == 1
        )
    else:
        assert connection_swift.containers.call_count == 1
        assert (
            connection_swift.containers.call_args_list.count(mock.call(account_id='1e6e233e637d4d55a50a62b63398ad15'))
            == 1
        )
    assert args_list.count((['http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15'], None)) == 1


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            CONTAINERS_METRICS_SWIFT,
            id='api rest',
        ),
        pytest.param(
            configs.SDK,
            CONTAINERS_METRICS_SWIFT,
            id='api sdk',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_containers_metrics(aggregator, check, dd_run_check, metrics):
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
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls', 'metrics'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            1,
            CONTAINERS_METRICS_SWIFT,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            1,
            CONTAINERS_METRICS_SWIFT,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            1,
            CONTAINERS_METRICS_SWIFT,
            id='api sdk small limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            CONTAINERS_METRICS_SWIFT,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'connection_swift', 'mock_http_post', 'openstack_connection')
def test_containers_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    api_type,
    dd_run_check,
    mock_http_get,
    connection_swift,
    metrics,
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
            args_list.count(('http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15', None))
            == expected_api_calls
        )
    else:
        assert connection_swift.containers.call_count == expected_api_calls
        assert (
            connection_swift.containers.call_args_list.count(
                mock.call(account_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == expected_api_calls
        )
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )
