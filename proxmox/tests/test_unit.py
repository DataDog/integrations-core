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
