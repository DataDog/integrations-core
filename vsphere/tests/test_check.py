# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os

import pytest
from mock import MagicMock
from tests.common import HERE
from tests.mocked_api import MockedAPI

from datadog_checks.base import to_string
from datadog_checks.vsphere import VSphereCheck
from datadog_checks.vsphere.config import VSphereConfig


@pytest.mark.usefixtures("mock_type", "mock_threadpool", "mock_api")
def test_realtime_metrics(aggregator, dd_run_check, realtime_instance):
    """This test asserts that the same api content always produces the same metrics."""
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    fixture_file = os.path.join(HERE, 'fixtures', 'metrics_realtime_values.json')
    with open(fixture_file, 'r') as f:
        data = json.load(f)
        for metric in data:
            aggregator.assert_metric(metric['name'], metric.get('value'), hostname=metric.get('hostname'))

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


@pytest.mark.usefixtures("mock_type")
def test_external_host_tags(aggregator, realtime_instance):
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    config = VSphereConfig(realtime_instance, MagicMock())
    check.api = MockedAPI(config)
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
                'vm': [r'cpu\.usage\.raw', r'disk\..*'],
                'host': [r'cpu\.coreUtilization\..*', r'sys\.uptime\..*', r'disk\..*'],
            }
        }
    )
    check = VSphereCheck('vsphere', {}, [realtime_instance])
    dd_run_check(check)

    # Following metrics should match and have instance value tag
    aggregator.assert_metric(
        'vsphere.cpu.usage.raw', tags=['cpu_core:4', 'vcenter_server:FAKE'],
    )
    for suffix in ['min', 'max', 'raw', 'avg']:
        aggregator.assert_metric(
            'vsphere.cpu.coreUtilization.{}'.format(suffix),
            hostname='10.0.0.104',
            tags={'cpu_core:16', 'vcenter_server:FAKE'},
        )

    # Following metrics should NOT match and do NOT have instance value tag
    aggregator.assert_metric(
        'vsphere.cpu.usage.min', tags=['vcenter_server:FAKE'],
    )
    aggregator.assert_metric(
        'vsphere.cpu.totalCapacity.avg', tags=['vcenter_server:FAKE'],
    )

    # `vsphere.disk.read.avg` is available per instance but the instance values are empty, hence no metric submitted.
    aggregator.assert_metric('vsphere.disk.read.avg', tags=['vcenter_server:FAKE'], hostname='VM4-1', count=0)
