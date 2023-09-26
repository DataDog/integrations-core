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
from tests.common import CONFIG_REST, CONFIG_SDK

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: {**d, **{'token': {**d['token'], **{'catalog': []}}}}}},
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
    assert args_list.count('http://10.164.0.11/networking') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 3
    elif api_type == ApiType.SDK:
        assert connection_session_auth.get_access.call_count == 3
    assert '`network` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/networking': MockResponse(status_code=500)}},
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/networking': MockResponse(status_code=500)}},
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
    assert args_list.count('http://10.164.0.11:9696/networking') == 2


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
    assert args_list.count('http://10.164.0.11:9696/networking') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_network', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/networking/v2.0/agents': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'agents': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_network'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_agents_exception(aggregator, dd_run_check, instance, mock_http_get, connection_network, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.agents.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11:9696/networking/v2.0/agents') == 2
    if api_type == ApiType.SDK:
        assert connection_network.agents.call_count == 2


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
def test_agents_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.agents.count',
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
        'openstack.neutron.agents.alive',
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
        'openstack.neutron.agents.admin_state_up',
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
        'openstack.neutron.agents.count',
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
        'openstack.neutron.agents.alive',
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
        'openstack.neutron.agents.admin_state_up',
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
            CONFIG_REST,
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
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_network'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quotas_exception(aggregator, dd_run_check, instance, mock_http_get, connection_network, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.quotas.floatingip',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.quotas.network',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.quotas.port',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11:9696/networking/v2.0/quotas/1e6e233e637d4d55a50a62b63398ad15') == 1
        assert args_list.count('http://10.164.0.11:9696/networking/v2.0/quotas/6e39099cccde4f809b003d9e0dd09304') == 1
    if api_type == ApiType.SDK:
        assert connection_network.get_quota.call_count == 2
        assert (
            connection_network.get_quota.call_args_list.count(
                mock.call(details=True, project_id='1e6e233e637d4d55a50a62b63398ad15')
            )
            == 1
        )
        assert (
            connection_network.get_quota.call_args_list.count(
                mock.call(details=True, project_id='6e39099cccde4f809b003d9e0dd09304')
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
    indirect=[],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quotas_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.neutron.quotas.floatingip',
        value=50,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.network',
        value=100,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.port',
        value=500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.rbac_policy',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.floatingip',
        value=50,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.network',
        value=100,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.port',
        value=500,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
    aggregator.assert_metric(
        'openstack.neutron.quotas.rbac_policy',
        value=10,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
        ],
    )
