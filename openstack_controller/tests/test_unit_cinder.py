# (C) Datadog, Inc. 2023-present
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
def test_disable_block_storage_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "block-storage": False,
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.cinder.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.SDK,
            id='api sdk no microversion',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_disable_block_storage_components_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "block-storage": {
                "volumes": False,
                "transfers": False,
                "snapshots": False,
                "pools": False,
                "clusters": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.cinder.volume.count')
        assert not metric.startswith('openstack.cinder.volume.transfer.count')
        assert not metric.startswith('openstack.cinder.snapshot.count')
        assert not metric.startswith('openstack.cinder.pool.count')
        assert not metric.startswith('openstack.cinder.cluster.count')


@pytest.mark.parametrize(
    ('mock_http_post', 'session_auth', 'instance', 'api_type'),
    [
        pytest.param(
            {
                'replace': {
                    '/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['block-storage', 'volumev3'])
                }
            },
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
        'openstack.cinder.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.cinder.api.up',
        status=AgentCheck.UNKNOWN,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_post.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8776/volume/v3/') == 0
    if api_type == ApiType.REST:
        args_list = []
        for call in mock_http_post.call_args_list:
            args, _ = call
            args_list += list(args)
        assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
    if api_type == ApiType.SDK:
        assert session_auth.get_access.call_count == 4
    assert '`block-storage` component not found in catalog' in caplog.text


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/volume/v3/': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'http_error': {'/volume/v3/': MockResponse(status_code=500)}},
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
        'openstack.cinder.response_time',
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.cinder.api.up',
        status=AgentCheck.CRITICAL,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8776/volume/v3/') == 2


@pytest.mark.parametrize(
    ('mock_http_post', 'instance'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['volumev3'])}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            configs.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time_block_storage(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.cinder.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.cinder.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8776/volume/v3/') == 1


@pytest.mark.parametrize(
    ('mock_http_post', 'instance'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['block-storage'])}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            None,
            configs.SDK,
            id='api sdk',
        ),
    ],
    indirect=['mock_http_post'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_response_time_volumev3(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.cinder.response_time',
        count=1,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    aggregator.assert_service_check(
        'openstack.cinder.api.up',
        status=AgentCheck.OK,
        tags=['keystone_server:http://127.0.0.1:8080/identity'],
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8776/volume/v3/') == 1


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
def test_block_storage_metrics(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.cinder.volume.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:9c762008-d70f-44d1-af02-98e1da79ee4b',
            'volume_name:first_volume',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:259b16de-727f-4011-8388-84d17a9ae594',
            'volume_name:',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:9c762008-d70f-44d1-af02-98e1da79ee4b',
            'volume_name:first_volume',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:259b16de-727f-4011-8388-84d17a9ae594',
            'volume_name:',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.transfer.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:acb5a860-3f17-4c35-9484-394a12dd7dfc',
            'volume_name:first volume',
            'transfer_id:1b3f7d49-8fd8-41b8-b2a5-859c5fe71a20',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:6e099852-b540-48ad-b01b-92fa6daed7ff',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:b6fedd82-b518-4a69-b25f-68a00a6b8492',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:6e099852-b540-48ad-b01b-92fa6daed7ff',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:b6fedd82-b518-4a69-b25f-68a00a6b8492',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool1',
            'pool_volume_backend_name:volume_pool1',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool2',
            'pool_volume_backend_name:volume_pool2',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.capabilities.free_capacity_gb',
        count=1,
        value=100,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool1',
            'pool_volume_backend_name:volume_pool1',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.capabilities.total_capacity_gb',
        count=1,
        value=1024,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool1',
            'pool_volume_backend_name:volume_pool1',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.capabilities.free_capacity_gb',
        count=1,
        value=200,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool2',
            'pool_volume_backend_name:volume_pool2',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.capabilities.total_capacity_gb',
        count=1,
        value=512,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool2',
            'pool_volume_backend_name:volume_pool2',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.capabilities.reserved_percentage',
        count=1,
        value=0,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool1',
            'pool_volume_backend_name:volume_pool1',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.pool.capabilities.reserved_percentage',
        count=1,
        value=0,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'pool_name:pool2',
            'pool_volume_backend_name:volume_pool2',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST_MICROVERSION_3_70,
            id='api rest microversion 3.70',
        ),
        pytest.param(
            configs.SDK_MICROVERSION_3_70,
            id='api sdk microversion 3.70',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_block_storage_metrics_microversion_3_70(aggregator, check, dd_run_check):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.cinder.cluster.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'cluster-name:first_cluster',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.cluster.num_hosts',
        count=1,
        value=0,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'cluster-name:first_cluster',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.cluster.num_down_hosts',
        count=1,
        value=0,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'cluster-name:first_cluster',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls_proj_1', 'expected_api_calls_proj_2'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            2,
            1,
            id='api rest low limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            1,
            1,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            2,
            1,
            id='api sdk low limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            1,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_block_storage_volumes_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls_proj_1,
    expected_api_calls_proj_2,
    api_type,
    dd_run_check,
    connection_block_storage,
    mock_http_get,
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
            args_list.count(
                ('http://127.0.0.1:8776/volume/v3/1e6e233e637d4d55a50a62b63398ad15/volumes/detail', paginated_limit)
            )
            == expected_api_calls_proj_1
        )
        assert (
            args_list.count(
                ('http://127.0.0.1:8776/volume/v3/6e39099cccde4f809b003d9e0dd09304/volumes/detail', paginated_limit)
            )
            == expected_api_calls_proj_2
        )
    else:
        assert connection_block_storage.volumes.call_count == 2
        assert (
            connection_block_storage.volumes.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_block_storage.volumes.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )
    aggregator.assert_metric(
        'openstack.cinder.volume.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:9c762008-d70f-44d1-af02-98e1da79ee4b',
            'volume_name:first_volume',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:259b16de-727f-4011-8388-84d17a9ae594',
            'volume_name:',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:9c762008-d70f-44d1-af02-98e1da79ee4b',
            'volume_name:first_volume',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.volume.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'volume_id:259b16de-727f-4011-8388-84d17a9ae594',
            'volume_name:',
            'volume_status:in-use',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'api_type', 'expected_api_calls_proj_1', 'expected_api_calls_proj_2'),
    [
        pytest.param(
            configs.REST,
            1,
            ApiType.REST,
            2,
            1,
            id='api rest low limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            ApiType.REST,
            1,
            1,
            id='api rest high limit',
        ),
        pytest.param(
            configs.SDK,
            1,
            ApiType.SDK,
            2,
            1,
            id='api sdk low limit',
        ),
        pytest.param(
            configs.SDK,
            1000,
            ApiType.SDK,
            1,
            1,
            id='api sdk high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post', 'openstack_connection')
def test_block_storage_snapshots_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls_proj_1,
    expected_api_calls_proj_2,
    api_type,
    dd_run_check,
    connection_block_storage,
    mock_http_get,
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
            args_list.count(
                ('http://127.0.0.1:8776/volume/v3/1e6e233e637d4d55a50a62b63398ad15/snapshots/detail', paginated_limit)
            )
            == expected_api_calls_proj_1
        )
        assert (
            args_list.count(
                ('http://127.0.0.1:8776/volume/v3/6e39099cccde4f809b003d9e0dd09304/snapshots/detail', paginated_limit)
            )
            == expected_api_calls_proj_2
        )
    else:
        assert connection_block_storage.snapshots.call_count == 2
        assert (
            connection_block_storage.snapshots.call_args_list.count(
                mock.call(project_id='1e6e233e637d4d55a50a62b63398ad15', limit=paginated_limit)
            )
            == 1
        )
        assert (
            connection_block_storage.snapshots.call_args_list.count(
                mock.call(project_id='6e39099cccde4f809b003d9e0dd09304', limit=paginated_limit)
            )
            == 1
        )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:6e099852-b540-48ad-b01b-92fa6daed7ff',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.count',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:b6fedd82-b518-4a69-b25f-68a00a6b8492',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:6e099852-b540-48ad-b01b-92fa6daed7ff',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
    aggregator.assert_metric(
        'openstack.cinder.snapshot.size',
        count=1,
        value=1,
        tags=[
            'domain_id:default',
            'project_name:demo',
            'project_id:1e6e233e637d4d55a50a62b63398ad15',
            'snapshot_id:b6fedd82-b518-4a69-b25f-68a00a6b8492',
            'volume_id:2c5d27f7-6f96-4913-81f6-3ab9bd755c51',
            'keystone_server:http://127.0.0.1:8080/identity',
        ],
    )
