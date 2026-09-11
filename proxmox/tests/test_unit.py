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
    BASE_TAGS,
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
    cluster_resources_with_offline_node,
    cluster_resources_with_vm_maxcpu,
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
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), check_symmetric_inclusion=True)


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


@pytest.mark.parametrize(
    ('metric', 'value', 'hostname', 'resource_tags'),
    [
        pytest.param(
            'proxmox.vm.cpu.max',
            2,
            'debian',
            [
                'proxmox_type:vm',
                'proxmox_name:VM 100',
                'proxmox_id:qemu/100',
                'proxmox_node:ip-122-82-3-112',
            ],
            id='vm',
        ),
        pytest.param(
            'proxmox.node.cpu.max',
            72,
            'ip-122-82-3-112',
            [
                'proxmox_type:node',
                'proxmox_type:host',
                'proxmox_name:ip-122-82-3-112',
                'proxmox_id:node/ip-122-82-3-112',
            ],
            id='node',
        ),
    ],
)
@pytest.mark.usefixtures('mock_http_get')
def test_vcpu_metering_metric(dd_run_check, aggregator, instance, metric, value, hostname, resource_tags):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    # `proxmox_type` has to be on the point itself: for VMs and nodes the check routes the
    # resource tags to external host tags, which never reach the payload at metering ingest.
    aggregator.assert_metric(metric, value, hostname=hostname, tags=BASE_TAGS + resource_tags)


@pytest.mark.usefixtures('mock_http_get')
def test_metering_metrics_skip_containers(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    # A default-configured container reports its host's entire thread count as `maxcpu`
    # (lxc/111 reports 72 on a 72-thread node), so metering containers would bill each one
    # at full host CPU.
    aggregator.assert_metric('proxmox.container.cpu.max', count=0)
    # Containers are still collected — the assertion above is about the vCPU point, not the
    # resource, and would also pass if containers stopped being collected altogether.
    aggregator.assert_metric('proxmox.container.count', at_least=1)


@pytest.mark.usefixtures('mock_http_get')
def test_metering_metrics_skip_powered_off_vm(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    # qemu/101 is stopped but still carries maxcpu=2.
    aggregator.assert_metric(
        'proxmox.vm.cpu.max',
        count=0,
        tags=BASE_TAGS
        + [
            'proxmox_type:vm',
            'proxmox_name:VM 101',
            'proxmox_id:qemu/101',
            'proxmox_node:ip-122-82-3-112',
        ],
    )
    aggregator.assert_metric('proxmox.vm.cpu.max', count=1)


@pytest.mark.parametrize(
    ('mock_http_get'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(
                        status_code=200,
                        json_data=cluster_resources_with_offline_node(),
                    )
                }
            },
            id='offline_node',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_metering_metrics_skip_offline_node(dd_run_check, aggregator, instance):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    aggregator.assert_metric('proxmox.node.cpu.max', count=0)
    # The rest of the inventory still emits, so the assertion above fails if the node really
    # is skipped and not merely because the payload override stopped matching.
    aggregator.assert_metric('proxmox.vm.cpu.max', count=1)


@pytest.mark.parametrize(
    ('mock_http_get', 'expected_count', 'expected_value'),
    [
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(
                        status_code=200,
                        json_data=cluster_resources_with_vm_maxcpu(None),
                    )
                }
            },
            0,
            None,
            id='maxcpu_absent',
        ),
        pytest.param(
            {
                'http_error': {
                    '/api2/json/cluster/resources': MockResponse(
                        status_code=200,
                        json_data=cluster_resources_with_vm_maxcpu(0),
                    )
                }
            },
            1,
            0,
            id='maxcpu_zero',
        ),
    ],
    indirect=['mock_http_get'],
)
@pytest.mark.usefixtures('mock_http_get')
def test_metering_metrics_distinguish_absent_maxcpu_from_zero(
    dd_run_check, aggregator, instance, expected_count, expected_value
):
    check = ProxmoxCheck('proxmox', {}, [instance])
    dd_run_check(check)
    # An absent `maxcpu` is skipped; a zero one is a real value and must still be emitted. A
    # truthiness check instead of `is not None` would silently drop the zero.
    if expected_value is None:
        aggregator.assert_metric('proxmox.vm.cpu.max', count=expected_count)
    else:
        aggregator.assert_metric('proxmox.vm.cpu.max', expected_value, count=expected_count)
    # The VM itself is still collected either way, so neither assertion above can pass merely
    # because the payload override dropped the resource.
    aggregator.assert_metric('proxmox.vm.count', at_least=1)


@pytest.mark.usefixtures('mock_http_get')
def test_metering_metrics_respect_resource_filters(dd_run_check, aggregator, instance):
    new_instance = copy.deepcopy(instance)
    new_instance['resource_filters'] = [
        {'type': 'exclude', 'resource': 'vm', 'property': 'resource_name', 'patterns': ['VM 100']},
    ]
    check = ProxmoxCheck('proxmox', {}, [new_instance])
    dd_run_check(check)
    aggregator.assert_metric('proxmox.vm.cpu.max', count=0)
    aggregator.assert_metric('proxmox.node.cpu.max', count=1)


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
