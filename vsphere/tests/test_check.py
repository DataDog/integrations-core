# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt
import json
import logging
import os
import time

import mock
import pytest
from mock import MagicMock
from pyVmomi import vim, vmodl

from datadog_checks.base import to_string
from datadog_checks.base.utils.time import get_current_datetime
from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.api import APIConnectionError
from datadog_checks.vsphere.config import VSphereConfig
from tests.legacy.utils import mock_alarm_event

from .common import HERE, VSPHERE_VERSION, build_rest_api_client
from .mocked_api import MockedAPI


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api")
def test_realtime_metrics(aggregator, dd_run_check, realtime_instance):
    """This test asserts that the same api content always produces the same metrics."""
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    fixture_file = os.path.join(HERE, 'fixtures', 'metrics_realtime_values.json')
    with open(fixture_file, 'r') as f:
        data = json.load(f)
        for metric in data:
            aggregator.assert_metric(
                metric['name'], metric.get('value'), hostname=metric.get('hostname'), tags=metric.get('tags')
            )

    aggregator.assert_metric('datadog.vsphere.collect_events.time', metric_type=aggregator.GAUGE, count=1)
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api")
def test_historical_metrics(aggregator, dd_run_check, historical_instance):
    """This test asserts that the same api content always produces the same metrics."""
    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)

    fixture_file = os.path.join(HERE, 'fixtures', 'metrics_historical_values.json')
    with open(fixture_file, 'r') as f:
        data = json.load(f)
        for metric in data:
            aggregator.assert_metric(metric['name'], metric.get('value'), tags=metric.get('tags'))

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api")
def test_historical_metrics_no_dsc_folder(aggregator, dd_run_check, historical_instance):
    """This test does the same check than test_historical_events, but deactivate the option to get datastore cluster
    folder in metrics tags"""
    check = VSphereCheck('vsphere', {}, [historical_instance])
    check._config.include_datastore_cluster_folder_tag = False
    dd_run_check(check)

    fixture_file = os.path.join(HERE, 'fixtures', 'metrics_historical_values.json')

    with open(fixture_file, 'r') as f:
        data = json.load(f)
        for metric in data:
            all_tags = metric.get('tags')
            if all_tags is not None:
                # The tag 'vsphere_folder:Datastores' is not supposed to be there anymore!
                all_tags = [tag for tag in all_tags if tag != 'vsphere_folder:Datastores']
            aggregator.assert_metric(metric['name'], metric.get('value'), tags=all_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_events_only(aggregator, events_only_instance):
    check = VSphereCheck('vsphere', {}, [events_only_instance])
    check.initiate_api_connection()

    time1 = dt.datetime.now()
    event1 = mock_alarm_event(from_status='green', key=10, created_time=time1)

    check.api.mock_events = [event1]
    check.check(None)
    aggregator.assert_event("vCenter monitor status changed on this alarm, it was green and it's now red.", count=1)

    aggregator.assert_metric('datadog.vsphere.collect_events.time')

    # assert all metrics will check that we are not collecting historical and realtime metrics
    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("mock_type", 'mock_rest_api')
def test_external_host_tags(aggregator, realtime_instance):
    realtime_instance['collect_tags'] = True
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    config = VSphereConfig(realtime_instance, {}, MagicMock())
    check.api = MockedAPI(config)
    check.api_rest = build_rest_api_client(config, MagicMock())

    with check.infrastructure_cache.update():
        check.refresh_infrastructure_cache()

    fixture_file = os.path.join(HERE, 'fixtures', 'host_tags_values.json')
    with open(fixture_file, 'r') as f:
        expected_tags = json.load(f)

    check.set_external_tags = MagicMock()
    check.submit_external_host_tags()
    submitted_tags = check.set_external_tags.mock_calls[0].args[0]
    submitted_tags.sort(key=lambda x: x[0])
    for ex, sub in zip(expected_tags, submitted_tags):
        ex_host, sub_host = ex[0], sub[0]
        ex_tags, sub_tags = ex[1]['vsphere'], sub[1]['vsphere']
        ex_tags = [to_string(t) for t in ex_tags]  # json library loads data in unicode, let's convert back to native
        assert ex_host == sub_host
        assert sorted(ex_tags) == sorted(sub_tags)

    check._config.excluded_host_tags = ['vsphere_host']
    check.set_external_tags = MagicMock()
    check.submit_external_host_tags()
    submitted_tags = check.set_external_tags.mock_calls[0].args[0]
    submitted_tags.sort(key=lambda x: x[0])
    for ex, sub in zip(expected_tags, submitted_tags):
        ex_host, sub_host = ex[0], sub[0]
        ex_tags, sub_tags = ex[1]['vsphere'], sub[1]['vsphere']
        ex_tags = [to_string(t) for t in ex_tags if 'vsphere_host:' not in t]
        assert ex_host == sub_host
        assert sorted(ex_tags) == sorted(sub_tags)

    check.set_external_tags = MagicMock()
    check.submit_external_host_tags()


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_collect_metric_instance_values(aggregator, dd_run_check, realtime_instance):
    realtime_instance.update(
        {
            'collect_per_instance_filters': {
                'vm': [r'cpu\.usagemhz\.avg', r'disk\..*'],
                'host': [r'cpu\.coreUtilization\..*', r'sys\.uptime\..*', r'disk\..*'],
            }
        }
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    # Following metrics should match and have instance value tag
    aggregator.assert_metric('vsphere.cpu.usagemhz.avg', tags=['cpu_core:6', 'vcenter_server:FAKE'])
    aggregator.assert_metric(
        'vsphere.cpu.coreUtilization.avg', hostname='10.0.0.104', tags=['cpu_core:16', 'vcenter_server:FAKE']
    )

    # Following metrics should NOT match and do NOT have instance value tag
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'])
    aggregator.assert_metric('vsphere.cpu.totalCapacity.avg', tags=['vcenter_server:FAKE'])

    # None of `vsphere.disk.usage.avg` metrics have instance values for specific metric+resource_type
    # Hence the aggregated metric IS collected
    aggregator.assert_metric('vsphere.disk.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-1', count=1)

    # Some of `vsphere.disk.read.avg` metrics have instance values for specific metric+resource_type
    # Hence the aggregated metric IS NOT collected
    aggregator.assert_metric('vsphere.disk.read.avg', tags=['vcenter_server:FAKE'], hostname='VM4-1', count=0)
    for instance_tag in ['device_path:value-aa', 'device_path:value-bb']:
        aggregator.assert_metric(
            'vsphere.disk.read.avg', tags=['vcenter_server:FAKE'] + [instance_tag], hostname='VM4-1', count=1
        )


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_collect_metric_instance_values_historical(aggregator, dd_run_check, historical_instance):

    historical_instance.update(
        {
            'collect_per_instance_filters': {
                'datastore': [r'disk\..*'],
                # datacenter metric group doesn't have any instance tags so this has no effect
                'datacenter': [r'cpu\.usagemhz\.avg'],
                'cluster': [r'cpu\.usagemhz\.avg'],
            }
        }
    )

    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'vsphere.cpu.usagemhz.avg',
        tags=[
            'cpu_core:16',
            'vcenter_server:FAKE',
            'vsphere_cluster:Cluster2',
            'vsphere_datacenter:Datacenter2',
            'vsphere_folder:Datacenters',
            'vsphere_folder:host',
            'vsphere_type:cluster',
        ],
    )

    aggregator.assert_metric(
        'vsphere.disk.used.latest',
        tags=[
            'device_path:value-aa',
            'vcenter_server:FAKE',
            'vsphere_datacenter:Datacenter2',
            'vsphere_datastore:NFS Share',
            'vsphere_folder:Datacenters',
            'vsphere_folder:datastore',
            'vsphere_type:datastore',
        ],
    )

    # Following metrics should NOT match and do NOT have instance value tag
    aggregator.assert_metric(
        'vsphere.cpu.usage.avg',
        tags=[
            'vcenter_server:FAKE',
            'vsphere_cluster:Cluster2',
            'vsphere_datacenter:Datacenter2',
            'vsphere_folder:Datacenters',
            'vsphere_folder:host',
            'vsphere_type:cluster',
        ],
    )


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_collect_tags(aggregator, dd_run_check, realtime_instance):
    realtime_instance.update({'collect_tags': True, 'excluded_host_tags': ['my_cat_name_1', 'my_cat_name_2']})
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'vsphere.cpu.usage.avg',
        tags=['my_cat_name_1:my_tag_name_1', 'my_cat_name_2:my_tag_name_2', 'vcenter_server:FAKE'],
        hostname='VM4-4',
    )
    aggregator.assert_metric(
        'vsphere.rescpu.samplePeriod.latest',
        tags=['my_cat_name_2:my_tag_name_2', 'vcenter_server:FAKE'],
        hostname='10.0.0.104',
    )
    aggregator.assert_metric(
        'vsphere.datastore.maxTotalLatency.latest',
        tags=['my_cat_name_2:my_tag_name_2', 'vcenter_server:FAKE'],
        hostname='10.0.0.104',
    )
    aggregator.assert_metric('datadog.vsphere.query_tags.time', tags=['vcenter_server:FAKE'])


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_tag_prefix(aggregator, dd_run_check, realtime_instance):
    realtime_instance.update(
        {'collect_tags': True, 'tags_prefix': 'ABC_', 'excluded_host_tags': ['ABC_my_cat_name_1', 'ABC_my_cat_name_2']}
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    aggregator.assert_metric(
        'vsphere.cpu.usage.avg',
        tags=['ABC_my_cat_name_1:my_tag_name_1', 'ABC_my_cat_name_2:my_tag_name_2', 'vcenter_server:FAKE'],
        hostname='VM4-4',
    )


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_continue_if_tag_collection_fail(aggregator, dd_run_check, realtime_instance):
    realtime_instance.update({'collect_tags': True})
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.log = MagicMock()

    with mock.patch('requests.post', side_effect=Exception, autospec=True):
        dd_run_check(check)

    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='10.0.0.104')

    check.log.error.assert_called_once_with(
        "Cannot connect to vCenter REST API. Tags won't be collected. Error: %s", mock.ANY
    )


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_refresh_tags_cache_should_not_raise_exception(aggregator, dd_run_check, realtime_instance):
    realtime_instance.update({'collect_tags': True})
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.log = MagicMock()
    check.api_rest = MagicMock()
    check.api_rest.get_resource_tags_for_mors.side_effect = APIConnectionError("Some error")

    check.collect_tags({})

    # Error logged, but `refresh_tags_cache` should NOT raise any exception
    check.log.error.assert_called_once_with("Failed to collect tags: %s", mock.ANY)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_renew_rest_api_session_on_failure(aggregator, dd_run_check, realtime_instance):
    realtime_instance.update({'collect_tags': True})
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    config = VSphereConfig(realtime_instance, {}, MagicMock())
    check.api_rest = build_rest_api_client(config, MagicMock())
    check.api_rest.make_batch = MagicMock(side_effect=[Exception, []])
    check.api_rest.smart_connect = MagicMock()

    tags = check.collect_tags({})
    assert tags
    assert check.api_rest.make_batch.call_count == 2
    assert check.api_rest.smart_connect.call_count == 1


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_tags_filters_integration_tags(aggregator, dd_run_check, historical_instance):
    historical_instance['collect_tags'] = True
    historical_instance['resource_filters'] = [
        {
            'resource': 'cluster',
            'property': 'tag',
            'patterns': [
                r'vsphere_datacenter:Datacenter2',
            ],
        },
        {
            'resource': 'datastore',
            'property': 'tag',
            'patterns': [
                r'vsphere_datastore:Datastore 1',
            ],
        },
    ]

    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)

    aggregator.assert_metric('vsphere.cpu.usage.avg', count=1)
    aggregator.assert_metric_has_tag('vsphere.cpu.usage.avg', 'vsphere_datacenter:Datacenter2', count=1)
    aggregator.assert_metric_has_tag('vsphere.cpu.usage.avg', 'vsphere_datacenter:Dätacenter', count=0)

    aggregator.assert_metric('vsphere.disk.used.latest', count=1)
    aggregator.assert_metric_has_tag('vsphere.disk.used.latest', 'vsphere_datastore:Datastore 1', count=1)
    aggregator.assert_metric_has_tag('vsphere.disk.used.latest', 'vsphere_datastore:Datastore 2', count=0)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_tags_filters_when_tags_are_not_yet_collected(aggregator, dd_run_check, realtime_instance):
    realtime_instance['collect_tags'] = True
    realtime_instance['resource_filters'] = [
        {'resource': 'vm', 'property': 'tag', 'patterns': [r'my_cat_name_1:my_tag_name_1']},
        {'resource': 'host', 'property': 'name', 'type': 'blacklist', 'patterns': [r'.*']},
    ]

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    # Assert that only a single resource was collected
    aggregator.assert_metric('vsphere.cpu.usage.avg', count=1)
    # Assert that the resource that was collected is the one with the correct tag
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-4')


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_tags_filters_with_prefix_when_tags_are_not_yet_collected(aggregator, dd_run_check, realtime_instance):
    realtime_instance['collect_tags'] = True
    realtime_instance['resource_filters'] = [
        {'resource': 'vm', 'property': 'tag', 'patterns': [r'foo_my_cat_name_1:my_tag_name_1']},
        {'resource': 'host', 'property': 'name', 'type': 'blacklist', 'patterns': [r'.*']},
    ]
    realtime_instance['tags_prefix'] = 'foo_'

    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    # Assert that only a single resource was collected
    aggregator.assert_metric('vsphere.cpu.usage.avg', count=1)
    # Assert that the resource that was collected is the one with the correct tag
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-4')


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api')
def test_attributes_filters(aggregator, dd_run_check, realtime_instance):
    realtime_instance['collect_attributes'] = True
    realtime_instance['attributes_prefix'] = 'vattr_'
    realtime_instance['resource_filters'] = [
        {'resource': 'vm', 'property': 'attribute', 'patterns': [r'vattr_foo:bar\d']},
        {'resource': 'host', 'property': 'name', 'type': 'blacklist', 'patterns': [r'.*']},
    ]
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    # Assert that only a single resource was collected
    aggregator.assert_metric('vsphere.cpu.usage.avg', count=2)
    # Assert that the resource that was collected is the one with the correct tag
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-15')
    # Assert that the resource that was collected is the one with the correct tag
    aggregator.assert_metric('vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'], hostname='VM4-9')


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_version_metadata(aggregator, dd_run_check, realtime_instance, datadog_agent):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    major, minor, patch = VSPHERE_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.build': '123456789',
        'version.raw': '{}+123456789'.format(VSPHERE_VERSION),
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.usefixtures('mock_type', 'mock_threadpool', 'mock_api', 'mock_rest_api')
def test_specs_start_time(aggregator, dd_run_check, historical_instance):
    mock_time = dt.datetime.now()

    check = VSphereCheck('vsphere', {}, [historical_instance])
    dd_run_check(check)

    check.api.server_time = mock_time

    start_times = []
    for specs in check.make_query_specs():
        for spec in specs:
            start_times.append(spec.startTime)

    assert len(start_times) != 0
    for start_time in start_times:
        assert start_time == (mock_time - dt.timedelta(hours=2))


@pytest.mark.parametrize(
    'test_timeout, expected_result',
    [
        (1, False),
        (2, False),
        (20, True),
    ],
)
@pytest.mark.usefixtures('mock_type', 'mock_api')
def test_connection_refresh(aggregator, dd_run_check, realtime_instance, test_timeout, expected_result):
    # This test is to ensure that the connection is refreshed after a specified period of time.
    # We run the check initially to get a connection object, sleep for a period of time, and then
    # rerun the check and compare and see if the connection objects are the same.
    realtime_instance['connection_reset_timeout'] = test_timeout
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)
    first_connection = check.api

    time.sleep(2)

    dd_run_check(check)

    same_object = False
    if first_connection == check.api:
        same_object = True

    assert same_object == expected_result


def test_no_infra_cache(aggregator, realtime_instance, dd_run_check, caplog):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = None

        mock_connect.return_value = mock_si
        caplog.set_level(logging.WARNING)
        check = VSphereCheck('vsphere', {}, [realtime_instance])

        dd_run_check(check)
        assert "Did not retrieve any properties from the vCenter. "
        "Metric collection cannot continue. Ensure your user has correct permissions." in caplog.text

        aggregator.assert_metric('datadog.vsphere.collect_events.time')
        aggregator.assert_metric('datadog.vsphere.refresh_metrics_metadata_cache.time')
        aggregator.assert_metric('datadog.vsphere.refresh_infrastructure_cache.time')

        aggregator.assert_all_metrics_covered()


def test_no_infra_cache_events(aggregator, realtime_instance, dd_run_check, caplog):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:
        event = vim.event.VmReconfiguredEvent()
        event.userName = "datadog"
        event.createdTime = get_current_datetime()
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.configSpec = vim.vm.ConfigSpec()

        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = None

        mock_connect.return_value = mock_si
        caplog.set_level(logging.WARNING)
        check = VSphereCheck('vsphere', {}, [realtime_instance])

        dd_run_check(check)
        assert "Did not retrieve any properties from the vCenter. "
        "Metric collection cannot continue. Ensure your user has correct permissions." in caplog.text

        aggregator.assert_metric('datadog.vsphere.collect_events.time')
        aggregator.assert_metric('datadog.vsphere.refresh_metrics_metadata_cache.time')
        aggregator.assert_metric('datadog.vsphere.refresh_infrastructure_cache.time')

        aggregator.assert_event(
            """datadog saved the new configuration:\n@@@\n""",
            exact_match=False,
            msg_title="VM vm1 configuration has been changed",
            host="vm1",
        )

        aggregator.assert_all_metrics_covered()


def test_no_infra_cache_no_perf_values(aggregator, realtime_instance, dd_run_check, caplog):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:

        event = vim.event.VmReconfiguredEvent()
        event.userName = "datadog"
        event.createdTime = get_current_datetime()
        event.vm = vim.event.VmEventArgument()
        event.vm.name = "vm1"
        event.configSpec = vim.vm.ConfigSpec()

        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = [event]
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = []
        mock_si.content.perfManager.QueryPerf.return_value = []
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = None

        mock_connect.return_value = mock_si
        caplog.set_level(logging.WARNING)
        check = VSphereCheck('vsphere', {}, [realtime_instance])

        dd_run_check(check)
        assert "Did not retrieve any properties from the vCenter. "
        "Metric collection cannot continue. Ensure your user has correct permissions." in caplog.text

        aggregator.assert_metric('datadog.vsphere.collect_events.time')
        aggregator.assert_metric('datadog.vsphere.refresh_metrics_metadata_cache.time')
        aggregator.assert_metric('datadog.vsphere.refresh_infrastructure_cache.time')

        aggregator.assert_event(
            """datadog saved the new configuration:\n@@@\n""",
            exact_match=False,
            msg_title="VM vm1 configuration has been changed",
            host="vm1",
        )

        aggregator.assert_all_metrics_covered()


def test_vm_property_metrics(aggregator, realtime_instance, dd_run_check, caplog):
    with mock.patch('pyVim.connect.SmartConnect') as mock_connect, mock.patch(
        'pyVmomi.vmodl.query.PropertyCollector'
    ) as mock_property_collector:

        realtime_instance['collect_property_metrics'] = True

        # VM 1 disk
        disk = vim.vm.GuestInfo.DiskInfo()
        disk.diskPath = '\\'
        disk.capacity = 2064642048
        disk.freeSpace = 1270075392
        disk.filesystemType = 'ext4'
        disks = vim.ArrayOfAnyType()
        disks.append(disk)

        # VM 1 net
        ip_address = vim.net.IpConfigInfo.IpAddress()
        ip_address.ipAddress = 'fe70::150:46ff:fe47:6311'
        ip_config = vim.net.IpConfigInfo()
        ip_config.ipAddress = vim.ArrayOfAnyType()
        ip_config.ipAddress.append(ip_address)
        net = vim.vm.GuestInfo.NicInfo()
        net.macAddress = '00:61:58:72:53:13'
        net.ipConfig = ip_config
        nets = vim.ArrayOfAnyType()
        nets.append(net)

        # VM 1 ip stack
        dns_config = vim.net.DnsConfigInfo()
        dns_config.hostName = 'test-hostname'
        dns_config.domainName = 'example.com'
        gateway = vim.net.IpRouteConfigInfo.Gateway()
        gateway.device = '0'
        gateway.ipAddress = None
        ip_route = vim.net.IpRouteConfigInfo.IpRoute()
        ip_route.prefixLength = 64
        ip_route.network = 'fe83::'
        ip_route.gateway = gateway
        ip_route_config = vim.net.IpRouteConfigInfo()
        ip_route_config.ipRoute = vim.ArrayOfAnyType()
        ip_route_config.ipRoute.append(ip_route)
        ip_stack = vim.vm.GuestInfo.StackInfo()
        ip_stack.dnsConfig = dns_config
        ip_stack.ipRouteConfig = ip_route_config
        ip_stacks = vim.ArrayOfAnyType()
        ip_stacks.append(ip_stack)

        # VM 3 disk
        disks3 = vim.ArrayOfAnyType()

        # VM 3 net
        ip_address3 = vim.net.IpConfigInfo.IpAddress()
        ip_address3.ipAddress = 'fe70::150:46ff:fe47:6311'
        ip_address4 = vim.net.IpConfigInfo.IpAddress()
        ip_address4.ipAddress = 'fe80::170:46ff:fe27:6311'
        ip_config3 = vim.net.IpConfigInfo()
        ip_config3.ipAddress = vim.ArrayOfAnyType()
        ip_config3.ipAddress.append(ip_address3)
        ip_config3.ipAddress.append(ip_address4)
        net3 = vim.vm.GuestInfo.NicInfo()
        net3.macAddress = None
        net3.ipConfig = ip_config3
        nets3 = vim.ArrayOfAnyType()
        nets3.append(net3)

        # VM 3 ip stack
        gateway3 = vim.net.IpRouteConfigInfo.Gateway()
        gateway3.device = '0'
        gateway3.ipAddress = '0.0.0.0'
        ip_route3 = vim.net.IpRouteConfigInfo.IpRoute()
        ip_route3.prefixLength = 32
        ip_route3.network = 'fe83::'
        ip_route3.gateway = gateway3
        ip_route_config3 = vim.net.IpRouteConfigInfo()
        ip_route_config3.ipRoute = vim.ArrayOfAnyType()
        ip_route_config3.ipRoute.append(ip_route3)
        ip_stack3 = vim.vm.GuestInfo.StackInfo()
        ip_stack3.dnsConfig = None
        ip_stack3.ipRouteConfig = ip_route_config3
        ip_stacks3 = vim.ArrayOfAnyType()
        ip_stacks3.append(ip_stack3)

        mock_si = mock.MagicMock()
        mock_si.content.eventManager.QueryEvents.return_value = []
        mock_si.content.perfManager.QueryPerfCounterByLevel.return_value = [
            vim.PerformanceManager.CounterInfo(
                key=100,
                groupInfo=vim.ElementDescription(key='cpu'),
                nameInfo=vim.ElementDescription(key='costop'),
                rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            )
        ]
        mock_si.content.perfManager.QueryPerf.return_value = [
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm1"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[47, 52],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm2"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
            vim.PerformanceManager.EntityMetric(
                entity=vim.VirtualMachine(moId="vm3"),
                value=[
                    vim.PerformanceManager.IntSeries(
                        value=[30, 11],
                        id=vim.PerformanceManager.MetricId(counterId=100),
                    )
                ],
            ),
        ]
        mock_property_collector.ObjectSpec.return_value = vmodl.query.PropertyCollector.ObjectSpec()
        mock_si.content.viewManagerCreateContainerView.return_value = vim.view.ContainerView(moId="cv1")
        mock_si.content.propertyCollector.RetrievePropertiesEx.return_value = vim.PropertyCollector.RetrieveResult(
            objects=[
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm1"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm1',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.numCpu',
                            val=2,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.memorySizeMB',
                            val=2048,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.numVirtualDisks',
                            val=1,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.numEthernetCards',
                            val=1,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.quickStats.uptimeSeconds',
                            val=12184573,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.quickStats.uptimeSeconds',
                            val=12184573,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.guestFullName',
                            val='Debian GNU/Linux 11 (32-bit)',
                        ),
                        vmodl.DynamicProperty(
                            name='guest.disk',
                            val=disks,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.net',
                            val=nets,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.ipStack',
                            val=ip_stacks,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.toolsRunningStatus',
                            val='guestToolsRunning',
                        ),
                        vmodl.DynamicProperty(
                            name='guest.toolsVersion',
                            val='11296',
                        ),
                        vmodl.DynamicProperty(
                            name='config.hardware.numCoresPerSocket',
                            val='2',
                        ),
                        vmodl.DynamicProperty(
                            name='config.cpuAllocation.limit',
                            val='-1',
                        ),
                        vmodl.DynamicProperty(
                            name='config.cpuAllocation.overheadLimit',
                            val=None,
                        ),
                        vmodl.DynamicProperty(
                            name='config.memoryAllocation.limit',
                            val='-1',
                        ),
                        vmodl.DynamicProperty(
                            name='config.memoryAllocation.overheadLimit',
                            val=None,
                        ),
                    ],
                ),
                vim.ObjectContent(
                    obj=vim.VirtualMachine(moId="vm3"),
                    propSet=[
                        vmodl.DynamicProperty(
                            name='name',
                            val='vm3',
                        ),
                        vmodl.DynamicProperty(
                            name='runtime.powerState',
                            val=vim.VirtualMachinePowerState.poweredOn,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.numCpu',
                            val=1,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.memorySizeMB',
                            val=None,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.numVirtualDisks',
                            val=3,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.config.numEthernetCards',
                            val=3,
                        ),
                        vmodl.DynamicProperty(
                            name='summary.quickStats.uptimeSeconds',
                            val=1218453,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.guestFullName',
                            val='Debian GNU/Linux 12 (32-bit)',
                        ),
                        vmodl.DynamicProperty(name='guest.disk', val=disks3),
                        vmodl.DynamicProperty(
                            name='guest.net',
                            val=nets3,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.ipStack',
                            val=ip_stacks3,
                        ),
                        vmodl.DynamicProperty(
                            name='guest.toolsRunningStatus',
                            val='guestToolsRunning',
                        ),
                        vmodl.DynamicProperty(
                            name='guest.toolsVersion',
                            val='11296',
                        ),
                        vmodl.DynamicProperty(
                            name='config.hardware.numCoresPerSocket',
                            val='2',
                        ),
                        vmodl.DynamicProperty(
                            name='config.cpuAllocation.limit',
                            val='10',
                        ),
                        vmodl.DynamicProperty(
                            name='config.cpuAllocation.overheadLimit',
                            val='24',
                        ),
                        vmodl.DynamicProperty(
                            name='config.memoryAllocation.limit',
                            val='-1',
                        ),
                        vmodl.DynamicProperty(
                            name='config.memoryAllocation.overheadLimit',
                            val='59',
                        ),
                    ],
                ),
            ],
            token='123',
        )
        mock_si.content.propertyCollector.ContinueRetrievePropertiesEx.return_value = (
            vim.PropertyCollector.RetrieveResult(
                objects=[
                    vim.ObjectContent(
                        obj=vim.VirtualMachine(moId="vm2"),
                        propSet=[
                            vmodl.DynamicProperty(
                                name='name',
                                val='vm2',
                            ),
                            vmodl.DynamicProperty(
                                name='runtime.powerState',
                                val=vim.VirtualMachinePowerState.poweredOff,
                            ),
                            vmodl.DynamicProperty(
                                name='summary.config.numCpu',
                                val=2,
                            ),
                            vmodl.DynamicProperty(
                                name='summary.config.memorySizeMB',
                                val=2048,
                            ),
                            vmodl.DynamicProperty(
                                name='summary.config.numVirtualDisks',
                                val=1,
                            ),
                            vmodl.DynamicProperty(
                                name='summary.config.numEthernetCards',
                                val=1,
                            ),
                            vmodl.DynamicProperty(
                                name='summary.quickStats.uptimeSeconds',
                                val=12184573,
                            ),
                            vmodl.DynamicProperty(
                                name='guest.guestFullName',
                                val='Debian GNU/Linux 12 (32-bit)',
                            ),
                            vmodl.DynamicProperty(name='guest.disk', val=disks),
                            vmodl.DynamicProperty(
                                name='guest.net',
                                val=nets,
                            ),
                            vmodl.DynamicProperty(
                                name='guest.ipStack',
                                val=ip_stacks,
                            ),
                            vmodl.DynamicProperty(
                                name='guest.toolsRunningStatus',
                                val='guestToolsRunning',
                            ),
                            vmodl.DynamicProperty(
                                name='guest.toolsVersion',
                                val='11296',
                            ),
                            vmodl.DynamicProperty(
                                name='config.hardware.numCoresPerSocket',
                                val='2',
                            ),
                            vmodl.DynamicProperty(
                                name='config.cpuAllocation.limit',
                                val='-1',
                            ),
                            vmodl.DynamicProperty(
                                name='config.cpuAllocation.overheadLimit',
                                val=None,
                            ),
                            vmodl.DynamicProperty(
                                name='config.memoryAllocation.limit',
                                val='-1',
                            ),
                            vmodl.DynamicProperty(
                                name='config.memoryAllocation.overheadLimit',
                                val=None,
                            ),
                        ],
                    )
                ],
            )
        )
        mock_connect.return_value = mock_si
        check = VSphereCheck('vsphere', {}, [realtime_instance])
        dd_run_check(check)
        aggregator.assert_metric(
            'vsphere.vm.count',
            value=2,
            count=2,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
        )

        # VM 1
        aggregator.assert_metric(
            'vsphere.vm.uptime',
            count=1,
            value=12184573.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.numCpu',
            count=1,
            value=2.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.numEthernetCards',
            count=1,
            value=1.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )

        aggregator.assert_metric(
            'vsphere.vm.numVirtualDisks',
            count=1,
            value=1.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.memorySizeMB',
            count=1,
            value=2048,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.hardware.numCoresPerSocket',
            count=1,
            value=2.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.guest.toolsVersion',
            count=1,
            value=11296.0,
            tags=[
                'tools_status:guestToolsRunning',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.net.ipConfig.address',
            count=1,
            value=1,
            tags=[
                'nic_ip_address:fe70::150:46ff:fe47:6311',
                'nic_mac_address:00:61:58:72:53:13',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.ipStack.ipRoute',
            count=1,
            value=1,
            tags=[
                'device:0',
                'network_dest_ip:fe83::',
                'route_domain_name:example.com',
                'route_hostname:test-hostname',
                'prefix_length:64',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.disk.freeSpace',
            count=1,
            value=1270075392,
            tags=[
                'disk_path:\\',
                'file_system_type:ext4',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.disk.capacity',
            count=1,
            value=2064642048,
            tags=[
                'disk_path:\\',
                'file_system_type:ext4',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm1',
        )
        aggregator.assert_metric(
            'vsphere.vm.numCpu',
            value=1,
            count=1,
            hostname='vm3',
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
        )

        aggregator.assert_metric(
            'vsphere.vm.numEthernetCards',
            count=1,
            value=3.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm3',
        )

        aggregator.assert_metric(
            'vsphere.vm.numVirtualDisks',
            count=1,
            value=3.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm3',
        )
        aggregator.assert_metric(
            'vsphere.vm.memorySizeMB',
            count=0,
            hostname='vm3',
        )
        aggregator.assert_metric(
            'vsphere.vm.hardware.numCoresPerSocket',
            count=1,
            value=2.0,
            tags=[
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm3',
        )
        aggregator.assert_metric(
            'vsphere.vm.guest.toolsVersion',
            count=1,
            value=11296.0,
            tags=[
                'tools_status:guestToolsRunning',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm3',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.net.ipConfig.address',
            count=1,
            value=1,
            tags=[
                'nic_ip_address:fe70::150:46ff:fe47:6311',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm3',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.ipStack.ipRoute',
            count=1,
            value=1,
            tags=[
                'device:0',
                'gateway_address:0.0.0.0',
                'network_dest_ip:fe83::',
                'prefix_length:32',
                'vcenter_server:FAKE',
                'vsphere_host:unknown',
                'vsphere_type:vm',
            ],
            hostname='vm3',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.disk.freeSpace',
            count=0,
            hostname='vm3',
        )

        aggregator.assert_metric(
            'vsphere.vm.guest.disk.capacity',
            count=0,
            hostname='vm3',
        )
        # assert we still get VM performance counter metrics
        aggregator.assert_metric('vsphere.cpu.costop.sum', count=1, hostname='vm1')
        aggregator.assert_metric('vsphere.cpu.costop.sum', count=1, hostname='vm3')
