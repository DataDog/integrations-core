# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import logging
from datetime import datetime, timezone

import mock
import pytest

from datadog_checks.dev.http import MockResponse
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.proxmox import ProxmoxCheck

from .common import (
    ALL_EVENTS,
    ALL_METRICS,
    CONTAINER_PERF_METRICS,
    NO_CONTAINER_EVENTS,
    NODE_PERF_METRICS,
    NODE_RESOURCE_METRICS,
    PERF_METRICS,
    RESOURCE_METRICS,
    START_UPDATE_EVENTS,
    STORAGE_PERF_METRICS,
    STORAGE_RESOURCE_METRICS,
    VM_PERF_METRICS,
)


@pytest.mark.usefixtures('mock_http_get')
def test_api_up(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "proxmox.api.up", 1, tags=['proxmox_server:http://localhost:8006/api2/json', 'proxmox_status:up', 'testing']
    )
    for metric in ALL_METRICS:
        aggregator.assert_metric(metric, at_least=1)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures('mock_http_get')
def test_no_tags(dd_run_check, aggregator, instance):
    new_instance = copy.deepcopy(instance)
    del new_instance['tags']
    check = ProxmoxCheck('proxmox', {}, [new_instance])
    dd_run_check(check)
    aggregator.assert_metric(
        "proxmox.api.up", 1, tags=['proxmox_server:http://localhost:8006/api2/json', 'proxmox_status:up']
    )


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {'http_error': {'/api2/json/version': MockResponse(status_code=500)}},
            id='500',
        ),
        pytest.param(
            {'http_error': {'/api2/json/version': MockResponse(status_code=404)}},
            id='404',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_api_down(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    with pytest.raises(Exception, match=r'requests.exceptions.HTTPError'):
        dd_run_check(check)

    aggregator.assert_metric(
        "proxmox.api.up", 0, tags=['proxmox_server:http://localhost:8006/api2/json', 'proxmox_status:down', 'testing']
    )


@pytest.mark.usefixtures('mock_http_get')
def test_version_metadata(dd_run_check, datadog_agent, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    version_metadata = {
        'version.scheme': 'semver',
        'version.major': '8',
        'version.minor': '4',
        'version.patch': '1',
        'version.raw': '8.4.1',
    }
    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.usefixtures('mock_http_get')
def test_resource_count_metrics(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    aggregator.assert_metric(
        "proxmox.vm.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:vm',
            'proxmox_name:VM 100',
            'proxmox_id:qemu/100',
            'proxmox_node:ip-122-82-3-112',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.node.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:node',
            'proxmox_type:host',
            'proxmox_name:ip-122-82-3-112',
            'proxmox_id:node/ip-122-82-3-112',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.container.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:container',
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'proxmox_node:ip-122-82-3-112',
            'tag1',
            'test',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.container.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'proxmox_type:container',
            'proxmox_name:test-container',
            'proxmox_id:lxc/101',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_pool:pool-1',
            'test',
            'testing',
            'testtag',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.storage.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:storage',
            'proxmox_name:local',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_id:storage/ip-122-82-3-112/local',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.pool.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:pool',
            'proxmox_name:pool-1',
            'proxmox_id:/pool/pool-1',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.sdn.count",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:sdn',
            'proxmox_name:localnetwork',
            'proxmox_id:sdn/ip-122-82-3-112/localnetwork',
            'proxmox_node:ip-122-82-3-112',
        ],
        hostname='',
    )


@pytest.mark.usefixtures('mock_http_get')
def test_resource_up_metrics(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    aggregator.assert_metric("proxmox.vm.up", 1, tags=[], hostname="debian")
    aggregator.assert_metric("proxmox.node.up", 1, tags=[], hostname='ip-122-82-3-112')
    aggregator.assert_metric(
        "proxmox.container.up",
        0,
        tags=[
            'proxmox_name:test-container',
            'proxmox_id:lxc/101',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_pool:pool-1',
            'proxmox_server:http://localhost:8006/api2/json',
            'proxmox_type:container',
            'test',
            'testing',
            'testtag',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.container.up",
        0,
        tags=[
            'proxmox_name:CT111',
            'proxmox_id:lxc/111',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_server:http://localhost:8006/api2/json',
            'proxmox_type:container',
            'tag1',
            'test',
            'testing',
        ],
        hostname='',
    )
    aggregator.assert_metric(
        "proxmox.storage.up",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:storage',
            'proxmox_name:local',
            'proxmox_node:ip-122-82-3-112',
            'proxmox_id:storage/ip-122-82-3-112/local',
        ],
        hostname='',
    )
    aggregator.assert_metric("proxmox.pool.up", count=0, hostname='')
    aggregator.assert_metric(
        "proxmox.sdn.up",
        1,
        tags=[
            'proxmox_server:http://localhost:8006/api2/json',
            'testing',
            'proxmox_type:sdn',
            'proxmox_name:localnetwork',
            'proxmox_id:sdn/ip-122-82-3-112/localnetwork',
            'proxmox_node:ip-122-82-3-112',
        ],
        hostname='',
    )


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/nodes/ip-122-82-3-112/qemu/100/agent/get-host-name': MockResponse(status_code=500)
                }
            },
            id='500',
        ),
        pytest.param(
            {
                'http_error': {
                    '/api2/json/nodes/ip-122-82-3-112/qemu/100/agent/get-host-name': MockResponse(status_code=404)
                }
            },
            id='404',
        ),
        pytest.param(
            {
                'http_error': {
                    '/api2/json/nodes/ip-122-82-3-112/qemu/100/agent/get-host-name': MockResponse(
                        status_code=200, json_data={"data": None, "message": "No QEMU guest agent configured\n"}
                    )
                }
            },
            id='qemu_agent_not_configured',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_get_hostname_error(dd_run_check, aggregator, instance, caplog):
    check = ProxmoxCheck('proxmox', {}, [instance])
    check.check_id = 'test:123'
    caplog.set_level(logging.INFO)
    dd_run_check(check)

    aggregator.assert_metric("proxmox.vm.up", 1, tags=[], hostname="VM 100")
    assert (
        "Failed to get hostname for vm 100 on node ip-122-82-3-112; endpoint: http://localhost:8006/api2/json;"
        in caplog.text
    )


@pytest.mark.usefixtures('mock_http_get')
def test_external_tags(dd_run_check, aggregator, instance, datadog_agent):
    check = ProxmoxCheck('proxmox', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)
    aggregator.assert_metric("proxmox.vm.up", 1, tags=[], hostname="debian")
    aggregator.assert_metric("proxmox.node.up", 1, tags=[], hostname='ip-122-82-3-112')
    datadog_agent.assert_external_tags(
        "debian",
        {
            'proxmox': [
                'proxmox_id:qemu/100',
                'proxmox_node:ip-122-82-3-112',
                'proxmox_server:http://localhost:8006/api2/json',
                'proxmox_type:vm',
                'proxmox_name:VM 100',
                'testing',
            ]
        },
    )
    datadog_agent.assert_external_tags(
        "ip-122-82-3-112",
        {
            'proxmox': [
                'proxmox_server:http://localhost:8006/api2/json',
                'testing',
                'proxmox_id:node/ip-122-82-3-112',
                'proxmox_name:ip-122-82-3-112',
                'proxmox_type:node',
                'proxmox_type:host',
            ]
        },
    )


@pytest.mark.usefixtures('mock_http_get')
def test_resource_metrics(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    for metric in RESOURCE_METRICS:
        aggregator.assert_metric(metric, hostname="debian", tags=[])

    for metric in NODE_RESOURCE_METRICS:
        aggregator.assert_metric(metric, hostname="ip-122-82-3-112", tags=[])

    container1_tags = [
        'proxmox_name:CT111',
        'proxmox_id:lxc/111',
        'proxmox_node:ip-122-82-3-112',
        'proxmox_server:http://localhost:8006/api2/json',
        'proxmox_type:container',
        'tag1',
        'test',
        'testing',
    ]
    container2_tags = [
        'proxmox_name:test-container',
        'proxmox_id:lxc/101',
        'proxmox_node:ip-122-82-3-112',
        'proxmox_pool:pool-1',
        'proxmox_server:http://localhost:8006/api2/json',
        'proxmox_type:container',
        'test',
        'testing',
        'testtag',
    ]
    for metric in RESOURCE_METRICS:
        aggregator.assert_metric(metric, hostname="", tags=container1_tags)
        aggregator.assert_metric(metric, hostname="", tags=container2_tags)

    storage_tags = [
        'proxmox_server:http://localhost:8006/api2/json',
        'testing',
        'proxmox_type:storage',
        'proxmox_name:local',
        'proxmox_node:ip-122-82-3-112',
        'proxmox_id:storage/ip-122-82-3-112/local',
    ]

    for metric in STORAGE_RESOURCE_METRICS:
        aggregator.assert_metric(metric, hostname="", tags=storage_tags)

    sdn_tags = [
        'proxmox_server:http://localhost:8006/api2/json',
        'testing',
        'proxmox_type:sdn',
        'proxmox_name:localnetwork',
        'proxmox_id:sdn/ip-122-82-3-112/localnetwork',
        'proxmox_node:ip-122-82-3-112',
    ]

    pool_tags = [
        'proxmox_server:http://localhost:8006/api2/json',
        'testing',
        'proxmox_type:pool',
        'proxmox_name:pool-1',
        'proxmox_id:/pool/pool-1',
    ]

    for metric in RESOURCE_METRICS:
        aggregator.assert_metric(metric, count=0, tags=sdn_tags)
        aggregator.assert_metric(metric, count=0, tags=pool_tags)


@pytest.mark.usefixtures('mock_http_get')
def test_perf_metrics(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    for metric in VM_PERF_METRICS:
        aggregator.assert_metric(metric, hostname="debian", tags=[])

    for metric in NODE_PERF_METRICS:
        aggregator.assert_metric(metric, hostname="ip-122-82-3-112", tags=[])

    container1_tags = [
        'proxmox_name:CT111',
        'proxmox_id:lxc/111',
        'proxmox_node:ip-122-82-3-112',
        'proxmox_server:http://localhost:8006/api2/json',
        'proxmox_type:container',
        'tag1',
        'test',
        'testing',
    ]
    container2_tags = [
        'proxmox_name:test-container',
        'proxmox_id:lxc/101',
        'proxmox_node:ip-122-82-3-112',
        'proxmox_pool:pool-1',
        'proxmox_server:http://localhost:8006/api2/json',
        'proxmox_type:container',
        'test',
        'testing',
        'testtag',
    ]

    for metric in CONTAINER_PERF_METRICS:
        aggregator.assert_metric(metric, hostname='', tags=container1_tags)
        aggregator.assert_metric(metric, hostname='', tags=container2_tags)

    storage_tags = [
        'proxmox_server:http://localhost:8006/api2/json',
        'testing',
        'proxmox_type:storage',
        'proxmox_name:local',
        'proxmox_node:ip-122-82-3-112',
        'proxmox_id:storage/ip-122-82-3-112/local',
    ]

    for metric in STORAGE_PERF_METRICS:
        aggregator.assert_metric(metric, hostname="", tags=storage_tags)

    sdn_tags = [
        'proxmox_server:http://localhost:8006/api2/json',
        'testing',
        'proxmox_type:sdn',
        'proxmox_name:localnetwork',
        'proxmox_id:sdn/ip-122-82-3-112/localnetwork',
        'proxmox_node:ip-122-82-3-112',
    ]

    pool_tags = [
        'proxmox_server:http://localhost:8006/api2/json',
        'testing',
        'proxmox_type:pool',
        'proxmox_name:pool-1',
        'proxmox_id:/pool/pool-1',
    ]

    for metric in PERF_METRICS:
        aggregator.assert_metric(metric, count=0, tags=sdn_tags)
        aggregator.assert_metric(metric, count=0, tags=pool_tags)


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {'http_error': {'/api2/json/cluster/metrics/export': MockResponse(status_code=501)}},
            id='501',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_performance_metrics_endpoint_unavailable(dd_run_check, aggregator, instance, mock_http_get):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric(
        "proxmox.api.up", 1, tags=['proxmox_server:http://localhost:8006/api2/json', 'proxmox_status:up', 'testing']
    )
    aggregator.assert_metric("proxmox.node.up", 1, tags=[], hostname='ip-122-82-3-112')
    aggregator.assert_metric("proxmox.vm.up", 1, tags=[], hostname="debian")
    aggregator.assert_metric("proxmox.ha.quorum", hostname='ip-122-82-3-112', tags=['node_status:OK'])


@pytest.mark.usefixtures('mock_http_get')
def test_perf_metrics_error(dd_run_check, caplog, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    caplog.set_level(logging.DEBUG)
    dd_run_check(check)
    assert "Invalid metric entry found; metric name: disk.used, resource id: storage/ip-122-82-3-112" in caplog.text


@pytest.mark.usefixtures('mock_http_get')
def test_ha_metrics(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('proxmox.ha.quorum', hostname='ip-122-82-3-112', tags=['node_status:OK'])
    aggregator.assert_metric('proxmox.ha.quorate', hostname='ip-122-82-3-112', tags=['node_status:OK'])


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/ha/status/current': MockResponse(
                        status_code=200,
                        json_data={'data': None},
                    )
                }
            },
            id='ha-disabled',
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures('mock_http_get')
def test_ha_metrics_null_data(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('proxmox.ha.quorum', count=0)
    aggregator.assert_metric('proxmox.ha.quorate', count=0)


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/metrics/export': MockResponse(
                        status_code=200,
                        json_data={'data': {'data': None}},
                    )
                }
            },
            id='no-exported-metrics',
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures('mock_http_get')
def test_performance_metrics_null_data(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    for metric in {'proxmox.cpu.current', 'proxmox.disk.total', 'proxmox.mem.total'}:
        aggregator.assert_metric(metric, count=0)


# Proxmox returns API errors with an HTTP error status and, on current versions, the reason in `message`.
PERMISSION_DENIED_RESPONSE = {'data': None, 'message': 'Permission check failed (/ , Sys.Audit)\n'}
TWO_NODE_RESOURCES = {
    'data': [
        {'id': 'node/node-1', 'node': 'node-1', 'status': 'online', 'type': 'node'},
        {'id': 'node/node-2', 'node': 'node-2', 'status': 'online', 'type': 'node'},
    ]
}


def task_calls(mock_http_get):
    return [call for call in mock_http_get.call_args_list if call.args[0].endswith('/tasks')]


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_error'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(status_code=403, json_data=PERMISSION_DENIED_RESPONSE)
                }
            },
            r'HTTP 403 for .*/cluster/resources: Permission check failed \(/ , Sys.Audit\)',
            id='with-message',
        ),
        pytest.param(
            {'http_error': {'/api2/json/cluster/resources': MockResponse(status_code=403, json_data={'data': None})}},
            r'HTTP 403 for .*/cluster/resources',
            id='without-message',
        ),
        pytest.param(
            {'http_error': {'/api2/json/cluster/resources': MockResponse(status_code=502, content='Bad Gateway')}},
            r'HTTP 502 for .*/cluster/resources',
            id='non-json-body',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_resources_api_error_response(dd_run_check, instance, expected_error):
    check = ProxmoxCheck('proxmox', {}, [instance])

    with pytest.raises(Exception, match=expected_error):
        dd_run_check(check, extract_message=True)


@pytest.mark.parametrize(
    ('mock_http_get', 'failed_collection', 'failed_endpoint', 'collected_metric'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/metrics/export': MockResponse(
                        status_code=403, json_data=PERMISSION_DENIED_RESPONSE
                    )
                }
            },
            'performance metrics',
            '/cluster/metrics/export',
            'proxmox.ha.quorum',
            id='performance-metrics',
        ),
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/ha/status/current': MockResponse(
                        status_code=403, json_data=PERMISSION_DENIED_RESPONSE
                    )
                }
            },
            'HA metrics',
            '/cluster/ha/status/current',
            'proxmox.cpu.current',
            id='ha',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.proxmox.check.get_current_datetime")
def test_optional_collection_error_does_not_block_other_collectors(
    get_current_datetime, dd_run_check, aggregator, instance, failed_collection, failed_endpoint, collected_metric
):
    get_current_datetime.return_value = datetime.fromtimestamp(1752552000, timezone.utc)
    new_instance = copy.deepcopy(instance)
    new_instance['collect_tasks'] = True
    check = ProxmoxCheck('proxmox', {}, [new_instance])

    dd_run_check(check)

    assert check.warnings == [
        f"Skipping Proxmox {failed_collection} collection: Proxmox API returned HTTP 403 for "
        f"http://localhost:8006/api2/json{failed_endpoint}: Permission check failed (/ , Sys.Audit)"
    ]
    aggregator.assert_metric(
        "proxmox.api.up", 1, tags=['proxmox_server:http://localhost:8006/api2/json', 'proxmox_status:up', 'testing']
    )
    aggregator.assert_metric("proxmox.node.up", 1, tags=[], hostname='ip-122-82-3-112')
    aggregator.assert_metric(collected_metric, at_least=1)
    assert len(aggregator.events) == len(ALL_EVENTS)


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(
                        status_code=200,
                        json_data={'data': None},
                    )
                }
            },
            id='resources',
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures('mock_http_get')
def test_required_null_data(dd_run_check, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])

    with pytest.raises(Exception, match=r'Proxmox API returned null data for .*/cluster/resources'):
        dd_run_check(check, extract_message=True)


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/nodes/ip-122-82-3-112/tasks': MockResponse(
                        status_code=200,
                        json_data={'data': None},
                    )
                }
            },
            id='no-tasks',
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures('mock_http_get')
def test_tasks_null_data(dd_run_check, aggregator, instance):
    new_instance = copy.deepcopy(instance)
    new_instance['collect_tasks'] = True
    check = ProxmoxCheck('proxmox', {}, [new_instance])

    dd_run_check(check)
    assert aggregator.events == []


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/nodes/ip-122-82-3-112/tasks': MockResponse(
                        status_code=403,
                        json_data=PERMISSION_DENIED_RESPONSE,
                    )
                }
            },
            id='tasks',
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures('mock_http_get')
def test_tasks_api_error_response(dd_run_check, instance):
    new_instance = copy.deepcopy(instance)
    new_instance['collect_tasks'] = True
    check = ProxmoxCheck('proxmox', {}, [new_instance])

    dd_run_check(check)

    endpoint = 'http://localhost:8006/api2/json/nodes/ip-122-82-3-112/tasks'
    assert check.warnings == [
        f"Failed to collect tasks for node ip-122-82-3-112; endpoint: {endpoint}; "
        f"Proxmox API returned HTTP 403 for {endpoint}: Permission check failed (/ , Sys.Audit)"
    ]


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(status_code=200, json_data=TWO_NODE_RESOURCES)
                }
            },
            id='two-nodes',
        ),
    ],
    indirect=True,
)
def test_failed_node_retries_from_last_successful_collection(
    dd_run_check, aggregator, instance, mock_http_get, monkeypatch, caplog
):
    # One timestamp for check initialization, then one per node and check run.
    collect_times = [datetime.fromtimestamp(ts, timezone.utc) for ts in (100, 200, 300, 400, 500)]
    monkeypatch.setattr('datadog_checks.proxmox.check.get_current_datetime', mock.MagicMock(side_effect=collect_times))

    def tasks_response(endtime):
        return MockResponse(status_code=200, json_data={'data': [{'type': 'aptupdate', 'endtime': endtime}]})

    # node-1 is unavailable on the first run while it runs a task, then recovers; node-2 always succeeds.
    task_responses = {
        '/nodes/node-1/tasks': iter(
            [
                MockResponse(status_code=500, json_data={'data': None, 'message': 'node unavailable'}),
                tasks_response(150),
            ]
        ),
        '/nodes/node-2/tasks': iter([tasks_response(150), tasks_response(350)]),
    }
    default_get = mock_http_get.side_effect

    def get(url, *args, **kwargs):
        for suffix, responses in task_responses.items():
            if url.endswith(suffix):
                return next(responses)
        return default_get(url, *args, **kwargs)

    mock_http_get.side_effect = get
    new_instance = copy.deepcopy(instance)
    new_instance['collect_tasks'] = True
    check = ProxmoxCheck('proxmox', {}, [new_instance])

    dd_run_check(check)
    assert "Failed to collect tasks for node node-1" in caplog.text
    assert [(event['host'], event['timestamp']) for event in aggregator.events] == [('node-2', 150)]

    dd_run_check(check)
    assert [(call.args[0].split('/')[-2], call.kwargs['params']['since']) for call in task_calls(mock_http_get)] == [
        ('node-1', 100),
        ('node-2', 100),
        # node-1 retries from its last successful collection; node-2 moves on.
        ('node-1', 100),
        ('node-2', 300),
    ]
    # The node-1 task missed while the node was unavailable is emitted once it recovers.
    assert [(event['host'], event['timestamp']) for event in aggregator.events] == [
        ('node-2', 150),
        ('node-1', 150),
        ('node-2', 350),
    ]


@pytest.mark.parametrize(
    'mock_http_get',
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(status_code=200, json_data=TWO_NODE_RESOURCES),
                    '/api2/json/nodes/node-1/tasks': MockResponse(
                        status_code=200, json_data={'data': [{'type': 'vzstart'}, {'type': 'vzstop'}]}
                    ),
                    '/api2/json/nodes/node-2/tasks': MockResponse(
                        status_code=200, json_data={'data': [{'type': 'vzstart'}]}
                    ),
                }
            },
            id='node-1-reaches-limit',
        ),
    ],
    indirect=True,
)
def test_tasks_warn_when_limit_reached(dd_run_check, instance, mock_http_get, monkeypatch, caplog):
    monkeypatch.setattr('datadog_checks.proxmox.check.TASK_COLLECTION_LIMIT', 2)
    new_instance = copy.deepcopy(instance)
    new_instance['collect_tasks'] = True
    new_instance['collected_task_types'] = []
    check = ProxmoxCheck('proxmox', {}, [new_instance])

    dd_run_check(check)

    assert [call.kwargs['params']['limit'] for call in task_calls(mock_http_get)] == [2, 2]
    assert "Node node-1 returned 2 tasks since" in caplog.text
    assert "Node node-2 returned" not in caplog.text


@pytest.mark.parametrize(
    ('collect_tasks, task_types, expected_events'),
    [
        pytest.param(
            False,
            [],
            [],
            id='collect_tasks disabled and task_types empty',
        ),
        pytest.param(
            False,
            ['startall'],
            [],
            id='collect_tasks disabled and task_types contains one event',
        ),
        pytest.param(
            True,
            None,
            ALL_EVENTS,
            id='collect_tasks enabled and task_types not set',
        ),
        pytest.param(
            True,
            [],
            [],
            id='collect_tasks enabled and task_types empty',
        ),
        pytest.param(
            True,
            ['vzstart', 'aptupdate'],
            START_UPDATE_EVENTS,
            id='collect_tasks enabled and task_types contains two events',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.proxmox.check.get_current_datetime")
def test_events(get_current_datetime, dd_run_check, aggregator, instance, collect_tasks, task_types, expected_events):
    instance = copy.deepcopy(instance)
    instance['collect_tasks'] = collect_tasks
    if task_types is not None:
        instance['collected_task_types'] = task_types
    get_current_datetime.return_value = datetime.fromtimestamp(1752552000, timezone.utc)
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    for event in expected_events:
        aggregator.assert_event(**event)

    assert len(aggregator.events) == len(expected_events)


@pytest.mark.parametrize(
    ('infrastructure_mode', 'expected_count'),
    [
        pytest.param('basic', 2, id='basic mode adds infra_mode tag'),
        pytest.param('full', 0, id='full mode does not add infra_mode tag'),
        pytest.param(None, 0, id='unset mode does not add infra_mode tag'),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_infra_mode_tag(dd_run_check, aggregator, instance, infrastructure_mode, expected_count):
    instance = copy.deepcopy(instance)
    if infrastructure_mode is not None:
        instance['infrastructure_mode'] = infrastructure_mode
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric_has_tag_prefix('proxmox.cpu', 'infra_mode:', count=expected_count)

    # assert that no container metrics have an infra_mode tag
    for metric in aggregator.metrics('proxmox.cpu'):
        if 'proxmox_type:container' in metric.tags:
            assert not any(t.startswith('infra_mode:') for t in metric.tags)
    # assert only the cpu metric has an infra_mode tag
    for metric_name in ALL_METRICS:
        if metric_name != 'proxmox.cpu':
            aggregator.assert_metric_has_tag_prefix(metric_name, 'infra_mode:', count=0)


@pytest.mark.parametrize(
    ('resource_filters, expected_vms, expected_nodes'),
    [
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'resource_name',
                    'patterns': [
                        'test.*',
                    ],
                }
            ],
            [],
            ['ip-122-82-3-112'],
            id='vm include list- name- no match',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'resource_name',
                    'patterns': [
                        'VM.*',
                    ],
                }
            ],
            ['debian'],
            ['ip-122-82-3-112'],
            id='vm include list- name- match',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'hi',
                    ],
                }
            ],
            [],
            ['ip-122-82-3-112'],
            id='vm include list- hostname- no match',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'deb.*',
                    ],
                }
            ],
            ['debian'],
            ['ip-122-82-3-112'],
            id='vm include list- hostname- match',
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'deb.*',
                    ],
                }
            ],
            [],
            ['ip-122-82-3-112'],
            id='vm exclude list- hostname- match',
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'el.*',
                        'node.*',
                    ],
                }
            ],
            ['debian'],
            ['ip-122-82-3-112'],
            id='vm exclude list- hostname- no match',
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [
                        'el.*',
                    ],
                },
                {
                    'type': 'exclude',
                    'resource': 'node',
                    'property': 'hostname',
                    'patterns': [
                        'node.*',
                    ],
                },
            ],
            ['debian'],
            ['ip-122-82-3-112'],
            id='node exclude list- hostname- no match',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'node',
                    'property': 'resource_name',
                    'patterns': [
                        'ip.*',
                    ],
                }
            ],
            ['debian'],
            ['ip-122-82-3-112'],
            id='node include list- name- match',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'node',
                    'property': 'resource_name',
                    'patterns': [
                        'test.*',
                    ],
                }
            ],
            ['debian'],
            [],
            id='node include list- name- no match',
        ),
        pytest.param(
            [
                {
                    'resource': 'node',
                    'property': 'resource_name',
                    'patterns': [
                        'test.*',
                    ],
                }
            ],
            ['debian'],
            [],
            id='node include list- no type- no match',
        ),
        pytest.param(
            [
                {
                    'resource': 'node',
                    'type': 'include',
                    'patterns': [
                        'test.*',
                    ],
                }
            ],
            ['debian'],
            [],
            id='node include list- no property- no match',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_host_resource_filters(
    dd_run_check, resource_filters, aggregator, datadog_agent, expected_vms, expected_nodes, instance
):
    instance = copy.deepcopy(instance)
    instance['resource_filters'] = resource_filters
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    for host in expected_vms:
        aggregator.assert_metric("proxmox.vm.up", hostname=host)

    for host in expected_nodes:
        aggregator.assert_metric("proxmox.node.up", hostname=host)

    aggregator.assert_metric("proxmox.vm.up", count=len(expected_vms))
    aggregator.assert_metric("proxmox.node.up", count=len(expected_nodes))

    num_xpected_hosts = len(expected_vms) + len(expected_nodes)
    datadog_agent.assert_external_tags_count(num_xpected_hosts)


@pytest.mark.parametrize(
    ('resource_filters, expected_containers, expected_storages, expected_pools, expected_sdns'),
    [
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'container',
                    'property': 'resource_name',
                    'patterns': [
                        'none.*',
                    ],
                }
            ],
            [],
            ['local'],
            ['pool-1'],
            ['localnetwork'],
            id='container include list- no match',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'container',
                    'property': 'resource_name',
                    'patterns': [
                        '.*',
                    ],
                },
                {
                    'type': 'include',
                    'resource': 'pool',
                    'property': 'resource_name',
                    'patterns': [
                        'pool.*',
                    ],
                },
                {
                    'type': 'include',
                    'resource': 'sdn',
                    'property': 'resource_name',
                    'patterns': [
                        'local.*',
                    ],
                },
            ],
            ['test-container', 'CT111'],
            ['local'],
            ['pool-1'],
            ['localnetwork'],
            id='include list- name- all match',
        ),
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'container',
                    'property': 'resource_name',
                    'patterns': [
                        '.*',
                    ],
                },
                {
                    'type': 'include',
                    'resource': 'pool',
                    'property': 'resource_name',
                    'patterns': [
                        'test.*',
                    ],
                },
                {
                    'type': 'include',
                    'resource': 'storage',
                    'property': 'resource_name',
                    'patterns': [
                        'test.*',
                    ],
                },
                {
                    'type': 'exclude',
                    'resource': 'sdn',
                    'property': 'resource_name',
                    'patterns': [
                        'local.*',
                    ],
                },
            ],
            [],
            [],
            [],
            [],
            id='no matches',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_additional_resource_filters(
    dd_run_check,
    resource_filters,
    aggregator,
    expected_containers,
    expected_storages,
    expected_pools,
    expected_sdns,
    instance,
):
    instance = copy.deepcopy(instance)
    instance['resource_filters'] = resource_filters
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    for container in expected_containers:
        aggregator.assert_metric_has_tag("proxmox.container.count", f"proxmox_name:{container}")

    for storage in expected_storages:
        aggregator.assert_metric_has_tag("proxmox.storage.count", f"proxmox_name:{storage}")

    for pool in expected_pools:
        aggregator.assert_metric_has_tag("proxmox.pool.count", f"proxmox_name:{pool}")

    for sdn in expected_sdns:
        aggregator.assert_metric_has_tag("proxmox.sdn.count", f"proxmox_name:{sdn}")

    aggregator.assert_metric("proxmox.container.count", count=len(expected_containers))
    aggregator.assert_metric("proxmox.storage.count", count=len(expected_storages))
    aggregator.assert_metric("proxmox.pool.count", count=len(expected_pools))
    aggregator.assert_metric("proxmox.sdn.count", count=len(expected_sdns))


@pytest.mark.parametrize(
    ('resource_filters, expected_message'),
    [
        pytest.param(
            [
                {
                    'type': 'includes',
                    'resource': 'container',
                    'property': 'resource_name',
                    'patterns': [
                        'none.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'includes', 'resource': 'container', 'property': 'resource_name', "
            "'patterns': ['none.*']} because type 'includes' is not valid. Should be one of ['include', 'exclude'].",
            id='invalid type',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'containers',
                    'property': 'resource_name',
                    'patterns': [
                        'none.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'include', 'resource': 'containers', 'property': 'resource_name', 'patterns': "
            "['none.*']} because resource containers is not a supported resource",
            id='invalid resource',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'property': 'resource_name',
                    'patterns': [
                        'none.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'include', 'property': 'resource_name', 'patterns': "
            "['none.*']} because it doesn't contain a resource field",
            id='missing resource',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'pool',
                    'property': 'hostname',
                    'patterns': [
                        'none.*',
                    ],
                }
            ],
            "Ignoring filter {'type': 'include', 'resource': 'pool', 'property': 'hostname', 'patterns': "
            "['none.*']} because property 'hostname' is not valid for resource type pool. "
            "Should be one of ['resource_name'].",
            id='invalid property',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': [],
                },
                {
                    'type': 'include',
                    'resource': 'vm',
                    'property': 'hostname',
                    'patterns': ['test'],
                },
            ],
            "Ignoring filter {'type': 'include', 'resource': 'vm', 'property': 'hostname', 'patterns': ['test']} "
            "because you already have a `include` filter for resource type vm and property hostname.",
            id='duplocate filter',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_resource_filters_errors(dd_run_check, resource_filters, expected_message, caplog, instance):
    instance = copy.deepcopy(instance)
    instance['resource_filters'] = resource_filters
    caplog.set_level(logging.WARNING)
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    assert expected_message in caplog.text


@pytest.mark.parametrize(
    ('resource_filters, expected_events'),
    [
        pytest.param(
            [
                {
                    'type': 'exclude',
                    'resource': 'container',
                    'property': 'resource_name',
                    'patterns': [
                        '.*',
                    ],
                }
            ],
            NO_CONTAINER_EVENTS,
            id='no container events',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'container',
                    'property': 'resource_name',
                    'patterns': [
                        '.*',
                    ],
                },
                {
                    'type': 'exclude',
                    'resource': 'vm',
                    'property': 'resource_name',
                    'patterns': [
                        'test',
                    ],
                },
            ],
            ALL_EVENTS,
            id='all events, some filters',
        ),
        pytest.param(
            [
                {
                    'type': 'include',
                    'resource': 'node',
                    'property': 'resource_name',
                    'patterns': [
                        'hello',
                    ],
                }
            ],
            [],
            id='node filtered, no events',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
@mock.patch("datadog_checks.proxmox.check.get_current_datetime")
def test_resource_filters_events(
    get_current_datetime, aggregator, dd_run_check, resource_filters, expected_events, instance
):
    instance = copy.deepcopy(instance)
    instance['collect_tasks'] = True
    instance['resource_filters'] = resource_filters
    get_current_datetime.return_value = datetime.fromtimestamp(1752552000, timezone.utc)
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)

    for event in expected_events:
        aggregator.assert_event(**event)

    assert len(aggregator.events) == len(expected_events)
