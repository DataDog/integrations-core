# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
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
def test_disable_neutron_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "network": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.neutron.')


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
def test_disable_neutron_agent_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "network": {
                "agents": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.neutron.agent.')


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
def test_disable_neutron_quota_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "network": {
                "quotas": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.neutron.quota.')


@pytest.mark.parametrize(
    ('mock_http_post', 'session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['network'])}},
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
        'openstack.neutron.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:9696/networking') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert session_auth.get_access.call_count == 4
    assert '`network` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/networking': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/networking': MockResponse(status_code=500)}},
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
        'openstack.neutron.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:9696/networking') == 2


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
        'openstack.neutron.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.neutron.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:9696/networking') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_network', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/networking/v2.0/agents': MockResponse(status_code=500)}},
            None,
            configs.REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'agents': MockResponse(status_code=500)}},
            configs.SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_network'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_agents_exception(aggregator, check, dd_run_check, mock_http_get, connection_network, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.agent.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:9696/networking/v2.0/agents') == 2
    if api_type == ApiType.SDK:
        assert connection_network.agents.call_count == 2


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
def test_agents_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.agent.count',
        value=1,
        tags=[
            'agent_availability_zone:',
            'agent_host:agent-integrations-openstack-default',
            'agent_id:2f4eba9c-8c8a-5836-b0d7-85d6eb176f20',
            'agent_name:neutron-ovn-metadata-agent',
            'agent_type:OVN Metadata agent',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.agent.alive',
        value=1,
        tags=[
            'agent_availability_zone:',
            'agent_host:agent-integrations-openstack-default',
            'agent_id:2f4eba9c-8c8a-5836-b0d7-85d6eb176f20',
            'agent_name:neutron-ovn-metadata-agent',
            'agent_type:OVN Metadata agent',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.agent.admin_state_up',
        value=1,
        tags=[
            'agent_availability_zone:',
            'agent_host:agent-integrations-openstack-default',
            'agent_id:2f4eba9c-8c8a-5836-b0d7-85d6eb176f20',
            'agent_name:neutron-ovn-metadata-agent',
            'agent_type:OVN Metadata agent',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.agent.count',
        value=1,
        tags=[
            'agent_availability_zone:',
            'agent_host:agent-integrations-openstack-default',
            'agent_id:203083d6-ddae-4023-aa83-ab679c9f4d2d',
            'agent_name:ovn-controller',
            'agent_type:OVN Controller Gateway agent',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.agent.alive',
        value=1,
        tags=[
            'agent_availability_zone:',
            'agent_host:agent-integrations-openstack-default',
            'agent_id:203083d6-ddae-4023-aa83-ab679c9f4d2d',
            'agent_name:ovn-controller',
            'agent_type:OVN Controller Gateway agent',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.agent.admin_state_up',
        value=1,
        tags=[
            'agent_availability_zone:',
            'agent_host:agent-integrations-openstack-default',
            'agent_id:203083d6-ddae-4023-aa83-ab679c9f4d2d',
            'agent_name:ovn-controller',
            'agent_type:OVN Controller Gateway agent',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
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
def test_disable_network_collect_for_all_projects(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "projects": {
            "include": [
                {
                    "name": ".*",
                    "network": False,
                },
            ],
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NEUTRON_PROJECT_METRICS:
        aggregator.assert_metric(metric, count=0)


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
def test_disable_networks_collect_for_all_projects(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "projects": {
            "include": [
                {
                    "name": ".*",
                    "network": {
                        "networks": False,
                    },
                },
            ],
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NEUTRON_NETWORK_METRICS:
        aggregator.assert_metric(metric, count=0)


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
def test_disable_quotas_collect_for_all_projects(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "projects": {
            "include": [
                {
                    "name": ".*",
                    "network": {
                        "quotas": False,
                    },
                },
            ],
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in metrics.NEUTRON_QUOTA_METRICS:
        aggregator.assert_metric(metric, count=0)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_network', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/networking/v2.0/networks': MockResponse(status_code=500),
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
                    'networks': {
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
    indirect=['mock_http_get', 'connection_network'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_networks_exception(aggregator, check, dd_run_check, mock_http_get, connection_network, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, kwargs = call
            project_id = kwargs.get('params', {}).get('project_id')
            args_list += [(list(args), project_id)]

        assert (
            args_list.count((['http://127.0.0.1:9696/networking/v2.0/networks'], '1e6e233e637d4d55a50a62b63398ad15'))
            == 1
        )
        assert (
            args_list.count((['http://127.0.0.1:9696/networking/v2.0/networks'], '6e39099cccde4f809b003d9e0dd09304'))
            == 1
        )

    if api_type == ApiType.SDK:
        assert connection_network.networks.call_count == 2
        assert (
            connection_network.networks.call_args_list.count(mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15'))
            == 1
        )
        assert (
            connection_network.networks.call_args_list.count(mock.call(project_id='6e39099cccde4f809b003d9e0dd09304'))
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
def test_networks_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        value=1500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.is_default',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        value=1442,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        value=1442,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
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
def test_networks_metrics_with_include(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "projects": {
            "include": [
                {
                    "name": ".*",
                    "network": {
                        "networks": {
                            "include": [
                                {
                                    "name": "^public.*",
                                },
                            ],
                        },
                    },
                },
            ],
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        value=1500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.is_default',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
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
def test_networks_metrics_with_exclude(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "projects": {
            "include": [
                {
                    "name": ".*",
                    "network": {
                        "networks": {
                            "include": [
                                {
                                    "name": "^.*",
                                },
                            ],
                            "exclude": ["^private.*"],
                        },
                    },
                },
            ],
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        value=1500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        value=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.is_default',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ec38babc-37e8-4bd7-9de0-03009304b2e4',
            'network_name:public',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        value=1442,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:f7b6adc8-24ea-490c-9537-5c4eae015cd8',
            'network_name:shared',
            'network_status:ACTIVE',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.count',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.admin_state_up',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.mtu',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.port_security_enabled',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.network.shared',
        count=0,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'network_id:ebdfddd9-14b8-46bd-98d6-10205d13038c',
            'network_name:private',
            'network_status:ACTIVE',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
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
def test_networks_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    api_type,
    dd_run_check,
    mock_http_get,
    connection_network,
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
            args_list.count(('http://127.0.0.1:9696/networking/v2.0/networks', paginated_limit)) == expected_api_calls
        )

    else:
        assert connection_network.networks.call_count == 2
        assert (
            connection_network.networks.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_network.networks.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )
    test_networks_metrics(aggregator, openstack_controller_check(paginated_instance), dd_run_check)


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_network', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/networking/v2.0/quotas/1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/networking/v2.0/quotas/6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
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
    indirect=['mock_http_get', 'connection_network'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quotas_exception(aggregator, check, dd_run_check, mock_http_get, connection_network, api_type):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.quota.floatingip',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.quota.network',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.quota.port',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:9696/networking/v2.0/quotas/1e6e233e637d4d55a50a62b63398ad15') == 1
        assert args_list.count('http://127.0.0.1:9696/networking/v2.0/quotas/6e39099cccde4f809b003d9e0dd09304') == 1
    if api_type == ApiType.SDK:
        assert connection_network.get_quota.call_count == 2
        assert (
            connection_network.get_quota.call_args_list.count(
                mock.call('1e6e233e637d4d55a50a62b63398ad15', details=True)
            )
            == 1
        )
        assert (
            connection_network.get_quota.call_args_list.count(
                mock.call('6e39099cccde4f809b003d9e0dd09304', details=True)
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
    indirect=[],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quotas_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.quota.floatingip',
        value=50,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.network',
        value=100,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.port',
        value=500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.rbac_policy',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.floatingip',
        value=50,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.network',
        value=100,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.port',
        value=500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quota.rbac_policy',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
