# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os

import mock
import pytest
from mock import MagicMock

from datadog_checks.base import to_string
from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.api import APIConnectionError
from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.config import VSphereConfig

from .common import HERE
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


@pytest.mark.usefixtures("mock_type", 'mock_rest_api')
def test_external_host_tags(aggregator, realtime_instance):
    realtime_instance['collect_tags'] = True
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    config = VSphereConfig(realtime_instance, MagicMock())
    check.api = MockedAPI(config)
    check.api_rest = VSphereRestAPI(config, MagicMock())
    with check.tags_cache.update():
        check.refresh_tags_cache()
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
        assert ex_tags == sub_tags

    check.config.excluded_host_tags = ['vsphere_host']
    check.set_external_tags = MagicMock()
    check.submit_external_host_tags()
    submitted_tags = check.set_external_tags.mock_calls[0].args[0]
    submitted_tags.sort(key=lambda x: x[0])
    for ex, sub in zip(expected_tags, submitted_tags):
        ex_host, sub_host = ex[0], sub[0]
        ex_tags, sub_tags = ex[1]['vsphere'], sub[1]['vsphere']
        ex_tags = [to_string(t) for t in ex_tags if 'vsphere_host:' not in t]
        assert ex_host == sub_host
        assert ex_tags == sub_tags

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
    aggregator.assert_metric(
        'vsphere.cpu.usagemhz.avg', tags=['cpu_core:6', 'vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.coreUtilization.avg', hostname='10.0.0.104', tags=['cpu_core:16', 'vcenter_server:FAKE'],
    )

    # Following metrics should NOT match and do NOT have instance value tag
    aggregator.assert_metric(
        'vsphere.cpu.usage.avg', tags=['vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.totalCapacity.avg', tags=['vcenter_server:FAKE'],
    )

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
    check.api_rest.get_resource_tags.side_effect = APIConnectionError("Some error")

    check.refresh_tags_cache()

    # Error logged, but `refresh_tags_cache` should NOT raise any exception
    check.log.error.assert_called_once_with("Failed to collect tags: %s", mock.ANY)
