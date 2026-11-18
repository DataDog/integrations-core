# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging
import os

import pytest

import tests.configs as configs
from datadog_checks.base import AgentCheck
from datadog_checks.dev.http import MockResponse
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
            id='clouds.yaml',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('mock_http_post', 'instance'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['object-store'])}},
            configs.REST,
            id='api rest',
        ),
    ],
    indirect=['mock_http_post'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_not_in_catalog(aggregator, check, dd_run_check, caplog, mock_http_post):
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
    args_list = []
    for call in mock_http_post.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    assert '`swift` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {
                'http_error': {
                    '/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/v1/AUTH_6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                }
            },
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {
                'http_error': {
                    '/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/v1/AUTH_6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                }
            },
            configs.SDK,
            id='clouds.yaml',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'elapsed_total_seconds': {'/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': 0.30706}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'elapsed_total_seconds': {'/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': 0.30706}},
            configs.SDK,
            id='clouds.yaml',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_response_time(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_service_check(
        'openstack.swift.api.up',
        status=AgentCheck.UNKNOWN,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.swift.api.up',
        status=AgentCheck.CRITICAL,
        count=0,
    )
    aggregator.assert_metric(
        'openstack.swift.response_time',
        value=307.06,
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
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {
                'http_error': {
                    '/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/v1/AUTH_6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
                },
            },
            configs.REST,
            id='api rest',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_containers_exception(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.swift.container.count',
        count=0,
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += [(list(args), kwargs.get('params', None))]
    assert (
        args_list.count((['http://127.0.0.1:6002/v1/AUTH_6e39099cccde4f809b003d9e0dd09304'], {'format': 'json'})) == 1
    )
    assert (
        args_list.count((['http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15'], {'format': 'json'})) == 1
    )


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
            id='clouds.yaml',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            CONTAINERS_METRICS_SWIFT,
            id='api rest limit 1',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_containers_pagination_limit_1(
    aggregator,
    instance,
    openstack_controller_check,
    dd_run_check,
    mock_http_get,
    metrics,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = 1
    dd_run_check(openstack_controller_check(paginated_instance))
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
    assert args_list.count(('http://127.0.0.1:6002/v1/AUTH_6e39099cccde4f809b003d9e0dd09304', 1)) == 2
    assert args_list.count(('http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15', 1)) == 3
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            CONTAINERS_METRICS_SWIFT,
            id='api rest limit 1000',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_containers_pagination_limit_1000(
    aggregator,
    instance,
    openstack_controller_check,
    dd_run_check,
    mock_http_get,
    metrics,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = 1000
    dd_run_check(openstack_controller_check(paginated_instance))
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
    assert args_list.count(('http://127.0.0.1:6002/v1/AUTH_6e39099cccde4f809b003d9e0dd09304', 1000)) == 2
    assert args_list.count(('http://127.0.0.1:6002/v1/AUTH_1e6e233e637d4d55a50a62b63398ad15', 1000)) == 2
    for metric in metrics:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )
