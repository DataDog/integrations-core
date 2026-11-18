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
from tests.common import remove_service_from_catalog
from tests.metrics import (
    ALLOCATIONS_METRICS_IRONIC_MICROVERSION_1_80,
    CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
    CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
    DRIVERS_METRICS_IRONIC_MICROVERSION_1_80,
    IRONIC_NODE_COUNT,
    NODES_METRICS_IRONIC_MICROVERSION_1_80,
    NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
    PORT_METRICS_IRONIC_MICROVERSION_DEFAULT,
    PORTGROUPS_METRICS_IRONIC,
    VOLUME_CONNECTOR_METRICS_IRONIC_MICROVERSION_1_80,
    VOLUME_TARGET_METRICS_IRONIC_MICROVERSION_1_80,
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
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_disable_ironic_node_portgroup_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "nodes": {
                    "portgroups": False,
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.node.portgroup.')


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK,
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_disable_ironic_ports_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "ports": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.port.')


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST,
            PORT_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api rest no microversion',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            PORT_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK,
            PORT_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            PORT_METRICS_IRONIC_MICROVERSION_DEFAULT,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_ports_metrics(aggregator, check, dd_run_check, metrics):
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
    ('instance', 'paginated_limit', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            2,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            1,
            id='api rest high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_ports_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    dd_run_check,
    mock_http_get,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
    assert args_list.count(('http://127.0.0.1:6385/baremetal/v1/ports/detail', paginated_limit)) == expected_api_calls
    for metric in PORT_METRICS_IRONIC_MICROVERSION_DEFAULT:
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
            configs.REST_IRONIC_MICROVERSION_1_80,
            PORTGROUPS_METRICS_IRONIC,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            PORTGROUPS_METRICS_IRONIC,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_nodes_portgroups_metrics(aggregator, check, dd_run_check, metrics):
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
    ('instance', 'paginated_limit', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            5,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            4,
            id='api rest high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_portgroups_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    dd_run_check,
    mock_http_get,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    count = 0
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
        if (
            'http://127.0.0.1:6385/baremetal/v1/nodes' in args[0]
            and 'portgroups/detail' in args[0]
            and limit == paginated_limit
        ):
            count += 1
    assert count == expected_api_calls
    for metric in PORTGROUPS_METRICS_IRONIC:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('instance'),
    [
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_disable_ironic_driver_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "drivers": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.driver.')


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            DRIVERS_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            DRIVERS_METRICS_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_drivers_metrics(aggregator, check, dd_run_check, metrics):
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
    ('instance'),
    [
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_disable_ironic_allocation_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "allocations": False,
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.allocation.')


@pytest.mark.parametrize(
    ('instance', 'metrics'),
    [
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            ALLOCATIONS_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            ALLOCATIONS_METRICS_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_allocations_metrics(aggregator, check, dd_run_check, metrics):
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
    ('instance', 'paginated_limit', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            1,
            2,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            1000,
            1,
            id='api rest high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_allocation_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    dd_run_check,
    mock_http_get,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
    assert args_list.count(('http://127.0.0.1:6385/baremetal/v1/allocations', paginated_limit)) == expected_api_calls
    for metric in ALLOCATIONS_METRICS_IRONIC_MICROVERSION_1_80:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )


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
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 2.93',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('mock_http_post', 'instance'),
    [
        pytest.param(
            {'replace': {'/identity/v3/auth/tokens': lambda d: remove_service_from_catalog(d, ['baremetal'])}},
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
    args_list = []
    for call in mock_http_post.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:8080/identity/v3/auth/tokens') == 4
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
            id='clouds.yaml',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'elapsed_total_seconds': {'/baremetal': 0.30706}},
            configs.REST,
            id='api rest',
        ),
        pytest.param(
            {'elapsed_total_seconds': {'/baremetal': 0.30706}},
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
        'openstack.ironic.api.up',
        status=AgentCheck.UNKNOWN,
        count=0,
    )
    aggregator.assert_service_check(
        'openstack.ironic.api.up',
        status=AgentCheck.CRITICAL,
        count=0,
    )
    aggregator.assert_metric(
        'openstack.ironic.response_time',
        value=307.06,
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
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/baremetal/v1/nodes/detail': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_nodes_exception(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.ironic.node.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.ironic.node.up',
        count=0,
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:6385/baremetal/v1/nodes/detail') == 2


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
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('instance'),
    [
        pytest.param(
            configs.REST_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_disable_ironic_volume_metrics(aggregator, dd_run_check, instance, openstack_controller_check):
    instance = instance | {
        "components": {
            "baremetal": {
                "volumes": {
                    "connectors": False,
                    "targets": False,
                },
            },
        },
    }
    check = openstack_controller_check(instance)
    dd_run_check(check)
    for metric in aggregator.metric_names:
        assert not metric.startswith('openstack.ironic.volume.connector.')
        assert not metric.startswith('openstack.ironic.volume.target.')


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            2,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            1,
            id='api rest high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_volume_connector_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    dd_run_check,
    mock_http_get,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
    assert (
        args_list.count(('http://127.0.0.1:6385/baremetal/v1/volume/connectors', paginated_limit)) == expected_api_calls
    )
    for metric in VOLUME_CONNECTOR_METRICS_IRONIC_MICROVERSION_1_80:
        aggregator.assert_metric(
            metric['name'],
            count=metric['count'],
            value=metric['value'],
            tags=metric['tags'],
            hostname=metric.get('hostname'),
        )


@pytest.mark.parametrize(
    ('instance', 'paginated_limit', 'expected_api_calls'),
    [
        pytest.param(
            configs.REST,
            1,
            2,
            id='api rest small limit',
        ),
        pytest.param(
            configs.REST,
            1000,
            1,
            id='api rest high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_volume_target_pagination(
    aggregator,
    instance,
    openstack_controller_check,
    paginated_limit,
    expected_api_calls,
    dd_run_check,
    mock_http_get,
):
    paginated_instance = copy.deepcopy(instance)
    paginated_instance['paginated_limit'] = paginated_limit
    dd_run_check(openstack_controller_check(paginated_instance))
    args_list = []
    for call in mock_http_get.call_args_list:
        args, kwargs = call
        args_list += list(args)
        params = kwargs.get('params', {})
        limit = params.get('limit')
        args_list += [(args[0], limit)]
    assert args_list.count(('http://127.0.0.1:6385/baremetal/v1/volume/targets', paginated_limit)) == expected_api_calls
    for metric in VOLUME_TARGET_METRICS_IRONIC_MICROVERSION_1_80:
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
            configs.REST_IRONIC_MICROVERSION_1_80,
            VOLUME_CONNECTOR_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            VOLUME_CONNECTOR_METRICS_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_volumes_connectors_metrics(aggregator, check, dd_run_check, metrics):
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
            configs.REST_IRONIC_MICROVERSION_1_80,
            VOLUME_TARGET_METRICS_IRONIC_MICROVERSION_1_80,
            id='api rest microversion 1.80',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            VOLUME_TARGET_METRICS_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_volumes_targets_metrics(aggregator, check, dd_run_check, metrics):
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
    ('paginated_limit', 'instance', 'metrics', 'expected_api_call_count'),
    [
        pytest.param(
            1,
            configs.REST,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            4,
            id='api rest no microversion',
        ),
        pytest.param(
            1000,
            configs.REST,
            NODES_METRICS_IRONIC_MICROVERSION_DEFAULT,
            1,
            id='api rest no microversion',
        ),
        pytest.param(
            1,
            configs.REST_IRONIC_MICROVERSION_1_80,
            NODES_METRICS_IRONIC_MICROVERSION_1_80,
            4,
            id='api rest microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_ironic_nodes_pagination(
    aggregator,
    dd_run_check,
    instance,
    openstack_controller_check,
    paginated_limit,
    metrics,
    expected_api_call_count,
    mock_http_get,
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
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_pagination_invalid_no_exception(aggregator, openstack_controller_check, dd_run_check, paginated_limit):
    paginated_instance = copy.deepcopy(configs.REST)
    paginated_instance['paginated_limit'] = paginated_limit
    check = openstack_controller_check(paginated_instance)
    dd_run_check(check)
    aggregator.assert_metric(IRONIC_NODE_COUNT, count=0)


@pytest.mark.parametrize(
    ('mock_http_get', 'instance'),
    [
        pytest.param(
            {'http_error': {'/baremetal/v1/conductors': MockResponse(status_code=500)}},
            configs.REST,
            id='api rest',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_conductors_exception(aggregator, check, dd_run_check, mock_http_get):
    dd_run_check(check)
    aggregator.assert_metric(
        'openstack.ironic.conductor.count',
        count=0,
    )
    aggregator.assert_metric(
        'openstack.ironic.conductor.up',
        count=0,
    )
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)
    assert args_list.count('http://127.0.0.1:6385/baremetal/v1/conductors') == 2


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
            id='clouds.yaml no microversion',
        ),
        pytest.param(
            configs.SDK_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            id='clouds.yaml microversion 1.80',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
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
    ('paginated_limit', 'instance', 'metrics', 'expected_api_call_count'),
    [
        pytest.param(
            1,
            configs.REST,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            2,
            id='api rest no microversion low limit',
        ),
        pytest.param(
            1000,
            configs.REST,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_DEFAULT,
            1,
            id='api rest no microversion high limit',
        ),
        pytest.param(
            1,
            configs.REST_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            2,
            id='api rest microversion 1.80 low limit',
        ),
        pytest.param(
            1000,
            configs.REST_IRONIC_MICROVERSION_1_80,
            CONDUCTORS_METRICS_IRONIC_MICROVERSION_1_80,
            1,
            id='api rest microversion 1.80 high limit',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get', 'mock_http_post')
def test_conductors_pagination(
    aggregator,
    dd_run_check,
    instance,
    openstack_controller_check,
    paginated_limit,
    metrics,
    expected_api_call_count,
    mock_http_get,
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
    args_list = []
    for call in mock_http_get.call_args_list:
        args, _ = call
        args_list += list(args)

    baremetal_url = 'http://127.0.0.1:6385/baremetal/v1/conductors'
    assert args_list.count(baremetal_url) == expected_api_call_count
