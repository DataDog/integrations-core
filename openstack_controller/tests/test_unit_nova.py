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
from tests.common import (
    CONFIG_REST,
    CONFIG_REST_NOVA_MICROVERSION_2_93,
    CONFIG_SDK,
    CONFIG_SDK_NOVA_MICROVERSION_2_93,
    remove_service_from_catalog,
)

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize(
    ('mock_http_post', 'connection_session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['compute'])}},
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
        'openstack.nova.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://10.164.0.11/compute/v2.1') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 3
    elif api_type == ApiType.SDK:
        assert connection_session_auth.get_access.call_count == 3
    assert '`compute` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1': MockResponse(status_code=500)}},
            CONFIG_REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/compute/v2.1': MockResponse(status_code=500)}},
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
        'openstack.nova.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://10.164.0.11/compute/v2.1') == 2


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
        'openstack.nova.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.nova.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://10.164.0.11/compute/v2.1') == 1


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/limits': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'limits': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_limits_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_total_instances',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_total_cores',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_total_ram_size',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_server_meta',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/compute/v2.1/limits') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.get_limits.call_count == 2


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_limits_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_total_instances',
        value=10,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_total_cores',
        value=20,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_total_ram_size',
        value=51200,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_metric(
        'openstack.nova.limits.absolute.max_server_meta',
        value=128,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_image_meta',
    #     value=128,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_personality',
    #     value=5,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_personality_size',
    #     value=10240,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_total_keypairs',
    #     value=100,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_server_groups',
    #     value=10,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_server_group_members',
    #     value=10,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_total_floating_ips',
    #     value=-1,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_security_groups',
    #     value=-1,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.max_security_group_rules',
    #     value=-1,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.total_ram_used',
    #     value=2048,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.total_cores_used',
    #     value=8,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.total_instances_used',
    #     value=8,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.total_floating_ips_used',
    #     value=0,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.total_security_groups_used',
    #     value=0,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )
    # aggregator.assert_metric(
    #     'openstack.nova.limits.absolute.total_server_groups_used',
    #     value=0,
    #     tags=['keystone_server:http://127.0.0.1:8080/identity'],
    # )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/os-services': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'services': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_services_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.service.up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/compute/v2.1/os-services') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.services.call_count == 2


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_services_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    #     for metric in metrics:
    #         aggregator.assert_metric(
    #             metric['name'],
    #             count=metric['count'],
    #             value=metric['value'],
    #             tags=metric['tags'],
    #         )
    aggregator.assert_metric(
        'openstack.nova.service.count',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'service_host:agent-integrations-openstack-default',
            'service_id:1',
            'service_name:nova-conductor',
            'service_state:up',
            'service_status:enabled',
            'service_zone:internal',
        ],
    )


#     # aggregator.assert_metric(
#     #     'openstack.nova.service.up',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:1',
#     #         'service_name:nova-conductor',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:internal',
#     #     ],
#     # )
#     # aggregator.assert_metric(
#     #     'openstack.nova.service.count',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:2',
#     #         'service_name:nova-scheduler',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:internal',
#     #     ],
#     # )
#     # aggregator.assert_metric(
#     #     'openstack.nova.service.up',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:2',
#     #         'service_name:nova-scheduler',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:internal',
#     #     ],
#     # )
#     # aggregator.assert_metric(
#     #     'openstack.nova.service.count',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:3',
#     #         'service_name:nova-compute',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:availability-zone',
#     #     ],
#     # )
#     # aggregator.assert_metric(
#     #     'openstack.nova.service.up',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:3',
#     #         'service_name:nova-compute',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:availability-zone',
#     #     ],
#     # )
#     # aggregator.assert_metric(
#     #     'openstack.nova.service.count',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:5',
#     #         'service_name:nova-conductor',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:internal',
#     #     ],
#     # )
#     # aggregator.assert_metric(
#     #     'openstack.nova.service.up',
#     #     value=1,
#     #     tags=[
#     #         'keystone_server:http://127.0.0.1:8080/identity',
#     #         'service_host:agent-integrations-openstack-default',
#     #         'service_id:5',
#     #         'service_name:nova-conductor',
#     #         'service_state:up',
#     #         'service_status:enabled',
#     #         'service_zone:internal',
#     #     ],
#     # )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/flavors/detail': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'flavors': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_flavors_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/compute/v2.1/flavors/detail') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.flavors.call_count == 2


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_flavors_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:1',
            'flavor_name:m1.tiny',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:2',
            'flavor_name:m1.small',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=2,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:3',
            'flavor_name:m1.medium',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=4,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:4',
            'flavor_name:m1.large',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:42',
            'flavor_name:m1.nano',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=8,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:5',
            'flavor_name:m1.xlarge',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:84',
            'flavor_name:m1.micro',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:c1',
            'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d1',
            'flavor_name:ds512M',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d2',
            'flavor_name:ds1G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=2,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d3',
            'flavor_name:ds2G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.vcpus',
        value=4,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d4',
            'flavor_name:ds4G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:1',
            'flavor_name:m1.tiny',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:2',
            'flavor_name:m1.small',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:3',
            'flavor_name:m1.medium',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:4',
            'flavor_name:m1.large',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:42',
            'flavor_name:m1.nano',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:5',
            'flavor_name:m1.xlarge',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:84',
            'flavor_name:m1.micro',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:c1',
            'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d1',
            'flavor_name:ds512M',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d2',
            'flavor_name:ds1G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d3',
            'flavor_name:ds2G',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.flavor.swap',
        value=0,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'flavor_id:d4',
            'flavor_name:ds4G',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/os-hypervisors/detail': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'hypervisors': MockResponse(status_code=500)}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_hypervisors_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.hypervisor.up',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/compute/v2.1/os-hypervisors/detail') == 2
    if api_type == ApiType.SDK:
        assert connection_compute.hypervisors.call_count == 2


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {'http_error': {'/compute/v2.1/os-hypervisors/1/uptime': MockResponse(status_code=500)}},
            None,
            CONFIG_REST,
            ApiType.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            {'http_error': {'hypervisor_uptime': {1: MockResponse(status_code=500)}}},
            CONFIG_SDK,
            ApiType.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_hypervisor_uptime_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.hypervisor.up',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_1',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_5',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_15',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/compute/v2.1/os-hypervisors/1/uptime') == 1
    if api_type == ApiType.SDK:
        assert connection_compute.get_hypervisor_uptime.call_count == 1
        assert connection_compute.get_hypervisor_uptime.call_args_list.count(mock.call(1, microversion=None)) == 1


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_hypervisors_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.hypervisor.up',
        value=1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_1',
        value=0.29,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_5',
        value=0.36,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.hypervisor.load_15',
        value=0.35,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'hypervisor_id:1',
            'hypervisor_name:agent-integrations-openstack-default',
            'hypervisor_state:up',
            'hypervisor_status:enabled',
            'hypervisor_type:QEMU',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/os-quota-sets/1e6e233e637d4d55a50a62b63398ad15': MockResponse(status_code=500),
                    '/compute/v2.1/os-quota-sets/6e39099cccde4f809b003d9e0dd09304': MockResponse(status_code=500),
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
                    'quota_sets': {
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
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quota_sets_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.quota_set.cores',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://10.164.0.11/compute/v2.1/os-quota-sets/1e6e233e637d4d55a50a62b63398ad15') == 1
        assert args_list.count('http://10.164.0.11/compute/v2.1/os-quota-sets/6e39099cccde4f809b003d9e0dd09304') == 1
    if api_type == ApiType.SDK:
        assert connection_compute.get_quota_set.call_count == 2
        assert (
            connection_compute.get_quota_set.call_args_list.count(
                mock.call('1e6e233e637d4d55a50a62b63398ad15', microversion=None)
            )
            == 1
        )
        assert (
            connection_compute.get_quota_set.call_args_list.count(
                mock.call('6e39099cccde4f809b003d9e0dd09304', microversion=None)
            )
            == 1
        )


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_quota_sets_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.quota_set.cores',
        value=20,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.fixed_ips',
        value=-1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.floating_ips',
        value=-1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.injected_file_content_bytes',
        value=10240,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.injected_file_path_bytes',
        value=255,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.injected_files',
        value=5,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'quota_id:6e39099cccde4f809b003d9e0dd09304',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.cores',
        value=20,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'quota_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.fixed_ips',
        value=-1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'quota_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.floating_ips',
        value=-1,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'quota_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.injected_file_content_bytes',
        value=10240,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'quota_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.injected_file_path_bytes',
        value=255,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'quota_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.quota_set.injected_files',
        value=5,
        tags=[
            'keystone_server:http://127.0.0.1:8080/identity',
            'domain_id:default',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'quota_id:1e6e233e637d4d55a50a62b63398ad15',
        ],
    )


@pytest.mark.parametrize(
    ('mock_http_get', 'connection_compute', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'http_error': {
                    '/compute/v2.1/servers/detail?project_id=1e6e233e637d4d55a50a62b63398ad15': MockResponse(
                        status_code=500
                    ),
                    '/compute/v2.1/servers/detail?project_id=6e39099cccde4f809b003d9e0dd09304': MockResponse(
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
                    'servers': {
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
    indirect=['mock_http_get', 'connection_compute'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_exception(aggregator, dd_run_check, instance, mock_http_get, connection_compute, api_type):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.server.count',
        count=0,
    )
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_get.call_args_list:
            args, _ = call
            args_list += list(args)
        assert (
            args_list.count(
                'http://10.164.0.11/compute/v2.1/servers/detail?project_id=1e6e233e637d4d55a50a62b63398ad15'
            )
            == 1
        )
        assert (
            args_list.count(
                'http://10.164.0.11/compute/v2.1/servers/detail?project_id=6e39099cccde4f809b003d9e0dd09304'
            )
            == 1
        )
    if api_type == ApiType.SDK:
        assert connection_compute.servers.call_count == 2
        assert (
            connection_compute.servers.call_args_list.count(
                mock.call(details=True, project_id='1e6e233e637d4d55a50a62b63398ad15', microversion=None)
            )
            == 1
        )
        assert (
            connection_compute.servers.call_args_list.count(
                mock.call(details=True, project_id='6e39099cccde4f809b003d9e0dd09304', microversion=None)
            )
            == 1
        )


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            CONFIG_REST,
            id='api rest no microversion',
        ),
        pytest.param(
            CONFIG_REST_NOVA_MICROVERSION_2_93,
            id='api rest microversion 2.93',
        ),
        pytest.param(
            CONFIG_SDK,
            id='api sdk no microversion',
        ),
        pytest.param(
            CONFIG_SDK_NOVA_MICROVERSION_2_93,
            id='api sdk microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_servers_metrics(aggregator, dd_run_check, instance):
    check = OpenStackControllerCheck('test', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.nova.server.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.disk_details.read_bytes',
        value=23407104,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.disk_details.read_requests',
        value=861,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.disk_details.write_bytes',
        value=42684416,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.disk_details.write_requests',
        value=302,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.disk_details.errors_count',
        value=-1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.cpu_details.time',
        value=7211680000000,
        tags=[
            'cpu_id:0',
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.diagnostic.nic_details.rx_octets',
        value=73838,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'mac_address:fa:16:3e:06:5c:6f',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_driver:libvirt',
            'server_id:5102fbbf-7156-48dc-8355-af7ab992266f',
            'server_name:a',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:2c653a68-b520-4582-a05d-41a68067d76c',
            'server_name:server',
            'server_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:6e39099cccde4f809b003d9e0dd09304',
            'project_name:admin',
            'server_id:2c653a68-b520-4582-a05d-41a68067d76c',
            'server_name:server',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:a',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.count',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:67ca710a-e73f-4801-a12f-d0c55ccb8955',
            'server_name:demo-1',
            'server_status:ACTIVE',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:67ca710a-e73f-4801-a12f-d0c55ccb8955',
            'server_name:demo-1',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-1',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.error',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:3b27b706-c0ad-4528-a865-7afaf7712130',
            'server_name:demo-2',
            'server_status:ERROR',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-2',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:97dec705-edab-4b3a-bbe6-b2121a85a603',
            'server_name:demo-3',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-3',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:cca55639-448f-44cc-ae6a-150afe0fa6b3',
            'server_name:demo-4',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-4',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:4caf78dc-2e5d-40a7-8d56-1c2f7f664283',
            'server_name:demo-5',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-5',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:7994720d-62a5-4b48-9158-f941d98db5c1',
            'server_name:demo-6',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-6',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:d34c4531-7cd1-4454-b39e-356463af7700',
            'server_name:demo-7',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-7',
            # 'flavor_name:cirros256',
        ],
    )
    aggregator.assert_metric(
        'openstack.nova.server.active',
        value=1,
        tags=[
            'domain_id:default',
            'keystone_server:http://127.0.0.1:8080/identity',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'project_name:demo',
            'server_id:9e80aa16-5a28-4ec0-bfce-f83bf56d0c86',
            'server_name:demo-8',
            'server_status:ACTIVE',
            # 'hypervisor:agent-integrations-openstack-default',
            # 'instance_hostname:demo-8',
            # 'flavor_name:cirros256',
        ],
    )
