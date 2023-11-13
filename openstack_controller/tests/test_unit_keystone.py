# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


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
def test_disable_keystone_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.')


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
def test_disable_keystone_region_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "regions": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.region')


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
def test_disable_keystone_domain_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "domains": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.domain')


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
def test_disable_keystone_project_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "projects": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.project')


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
def test_disable_keystone_user_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "users": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.user')


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
def test_disable_keystone_group_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "groups": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.group')


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
def test_disable_keystone_service_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "services": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.service')


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
def test_disable_keystone_limit_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "identity": {
                "limits": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.keystone.limit')


@pytest.mark.parametrize(
    ('mock_http_post', 'session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['identity'])}},
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
        'openstack.keystone.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.CRITICAL,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8080/identity') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert session_auth.get_access.call_count == 4
    assert '`identity` component not found in catalog' in caplog.text


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
def test_region_id_in_tags(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "endpoint_region_id": "RegionOne",
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.response_time',
        count=1,
        tags=[
            'region_id:RegionOne',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        tags=[
            'region_id:RegionOne',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/identity': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/identity': MockResponse(status_code=500)}},
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
        'openstack.keystone.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.UNKNOWN,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8080/identity') == 2


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
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.UNKNOWN,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.CRITICAL,
        count=0,
    )
    aggregator.assert_metric(
        'openstack.keystone.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.keystone.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8080/identity') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/regions': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'regions': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_regions_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.region.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.keystone.region.enabled',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/regions') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.regions.call_count == 2


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
def test_regions_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.region.count',
        value=1,
        tags=[
            'region_id:RegionOne',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.region.count',
        value=1,
        tags=[
            'region_id:my-region',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/domains': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'domains': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_domains_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.domain.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.keystone.domain.enabled',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/domains') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.domains.call_count == 2


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
def test_domains_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.domain.count',
        value=1,
        tags=[
            'domain_id:default',
            'domain_name:Default',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domain.count',
        value=1,
        tags=[
            'domain_id:03e40b01788d403e98e4b9a20210492e',
            'domain_name:New domain',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domain.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'domain_name:Default',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.domain.enabled',
        value=1,
        tags=[
            'domain_id:03e40b01788d403e98e4b9a20210492e',
            'domain_name:New domain',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/projects': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'projects': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_projects_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.project.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.keystone.project.enabled',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/projects') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.projects.call_count == 2


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
def test_projects_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.project.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:b0700d860b244dcbb038541976cd8f32',
            'project_name:alt_demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:b0700d860b244dcbb038541976cd8f32',
            'project_name:alt_demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:c1147335eac0402ea9cabaae59c267e1',
            'project_name:invisible_to_admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.enabled',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:c1147335eac0402ea9cabaae59c267e1',
            'project_name:invisible_to_admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:e9e405ed5811407db982e3113e52d26b',
            'project_name:service',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.project.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:e9e405ed5811407db982e3113e52d26b',
            'project_name:service',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/users': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'users': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_users_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.user.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/users') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.users.call_count == 2


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
def test_users_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.user.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:78205c506b534738bc851d3e189a00c3',
            'user_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:78205c506b534738bc851d3e189a00c3',
            'user_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:2059bc7347c94546bef812b1092cc5cf',
            'user_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:e3e3e90d24b34e52970a54c9e8656778',
            'user_name:demo_reader',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:3472440960de4595be3b975d230979d3',
            'user_name:alt_demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:87e289ddac6d4dce8626a659c5ea88ae',
            'user_name:alt_demo_member',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:61f0cd4dec604f968ff6cc92d4c1c278',
            'user_name:alt_demo_reader',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:5d0c9a6896c9430b8a1528424c9ee6f6',
            'user_name:system_member',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:aeaa8e9835284e4380583e10bb2575fd',
            'user_name:system_reader',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:bc603ecd6ed940119be9a3a933c39509',
            'user_name:nova',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:ad9f72f911744acbbf69379e45a3ef37',
            'user_name:glance',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:94fb5df1e547496894f9304a9b4a06d4',
            'user_name:neutron',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:af4653d4f2dc4a38b8af36cbd3993d5a',
            'user_name:cinder',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.user.enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'user_id:fc7c3571bed548e98e7df266f57a50f7',
            'user_name:placement',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/groups': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'groups': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_groups_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.group.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/groups') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.groups.call_count == 2


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/identity/v3/groups/89b36a4c32c44b0ea8856b6357f101ea/users': MockResponse(status_code=500)
                }
            },
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'group_users': {'89b36a4c32c44b0ea8856b6357f101ea': MockResponse(status_code=500)}}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_group_users_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.group.count',
        value=1,
        tags=[
            'domain_id:default',
            'group_id:89b36a4c32c44b0ea8856b6357f101ea',
            'group_name:admins',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.group.count',
        value=1,
        tags=[
            'domain_id:default',
            'group_id:9acda6caf16e4828935f4f681ee8b3e5',
            'group_name:nonadmins',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.group.users',
        count=0,
        tags=[
            'domain_id:default',
            'group_id:89b36a4c32c44b0ea8856b6357f101ea',
            'group_name:admins',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.group.users',
        value=0,
        tags=[
            'domain_id:default',
            'group_id:9acda6caf16e4828935f4f681ee8b3e5',
            'group_name:nonadmins',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/groups/89b36a4c32c44b0ea8856b6357f101ea/users') == 1
        assert args_list.count('http://127.0.0.1:8080/identity/v3/groups/9acda6caf16e4828935f4f681ee8b3e5/users') == 1
    if api_type == ApiType.SDK:
        assert connection_identity.group_users.call_count == 2
        assert connection_identity.group_users.call_args_list.count(mock.call('89b36a4c32c44b0ea8856b6357f101ea')) == 1
        assert connection_identity.group_users.call_args_list.count(mock.call('9acda6caf16e4828935f4f681ee8b3e5')) == 1


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
def test_groups_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.group.count',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'group_id:89b36a4c32c44b0ea8856b6357f101ea',
            'group_name:admins',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.group.users',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'group_id:89b36a4c32c44b0ea8856b6357f101ea',
            'group_name:admins',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.group.count',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'group_id:9acda6caf16e4828935f4f681ee8b3e5',
            'group_name:nonadmins',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.group.users',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'group_id:9acda6caf16e4828935f4f681ee8b3e5',
            'group_name:nonadmins',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/services': MockResponse(status_code=500)}},
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
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_services_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.service.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/services') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.services.call_count == 2


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
def test_services_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.service.count',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:9aca42df11e84366924013b2f1a1259b',
            'service_name:nova',
            'service_type:compute',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:155d28a57a054d5fae86410b566ffca1',
            'service_name:placement',
            'service_type:placement',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:17d8088bf93b41b19ae971eb6f2aa7a5',
            'service_name:nova_legacy',
            'service_type:compute_legacy',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:271afc4cc62e493592b6be9b87bfb108',
            'service_name:keystone',
            'service_type:identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:3ef836a26c2c40acabb07a6415384f20',
            'service_name:cinderv3',
            'service_type:volumev3',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:55b21161725a461793a2222749229306',
            'service_name:cinder',
            'service_type:block-storage',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:7dca0a2e55d74d66995f3105ed69608f',
            'service_name:neutron',
            'service_type:network',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:82624ab61fb04f058d043facf315fa3c',
            'service_name:glance',
            'service_type:image',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.service.enabled',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_id:9aca42df11e84366924013b2f1a1259b',
            'service_name:nova',
            'service_type:compute',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/registered_limits': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'registered_limits': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_registered_limits_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        count=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:dd4fefa5602a4414b1c0a01ac7514b97',
            'resource_name:image_size_total',
            'region_id:RegionOne',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/registered_limits') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.registered_limits.call_count == 2


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_identity', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/identity/v3/limits': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'limits': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_identity'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_limits_exception(aggregator, check, dd_run_check, mock_http_get, connection_identity, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        count=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:25a04c7a065c430590881c646cdcdd58',
            "project_id:3a705b9f56bb439381b43c4fe59dccce",
            'resource_name:volume',
            'service_id:9408080f1970482aa0e38bc2d4ea34b7',
        ],
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/limits') == 2
    if api_type == ApiType.SDK:
        assert connection_identity.limits.call_count == 2


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
def test_limits_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        value=1000,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:dd4fefa5602a4414b1c0a01ac7514b97',
            'resource_name:image_size_total',
            'region_id:RegionOne',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        value=1000,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:5e7d44c9d30d47919187a5c1a58a8885',
            'resource_name:image_stage_total',
            'region_id:RegionOne',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        value=100,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:9f489d63900841f4a70fe58036c81339',
            'resource_name:image_count_total',
            'region_id:RegionOne',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        value=100,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:5d26b57b414c4e25848cd34b38f56606',
            'resource_name:image_count_uploading',
            'region_id:RegionOne',
            'service_id:82624ab61fb04f058d043facf315fa3c',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        value=11,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:25a04c7a065c430590881c646cdcdd58',
            "project_id:3a705b9f56bb439381b43c4fe59dccce",
            'resource_name:volume',
            'service_id:9408080f1970482aa0e38bc2d4ea34b7',
        ],
    )
    aggregator.assert_metric(
        'openstack.keystone.limit.limit',
        value=5,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'limit_id:3229b3849f584faea483d6851f7aab05',
            "project_id:3a705b9f56bb439381b43c4fe59dccce",
            'region_id:RegionOne',
            'resource_name:snapshot',
            'service_id:9408080f1970482aa0e38bc2d4ea34b7',
        ],
    )
