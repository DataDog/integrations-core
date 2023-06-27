# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
from urllib.parse import urlparse

from pyVmomi import vim

from datadog_checks.dev.http import MockResponse
from datadog_checks.vsphere.api_rest import VSphereRestAPI

HERE = os.path.abspath(os.path.dirname(__file__))

VSPHERE_VERSION = os.environ.get('VSPHERE_VERSION')

LAB_USERNAME = os.environ.get('TEST_VSPHERE_USER')
LAB_PASSWORD = os.environ.get('TEST_VSPHERE_PASS')

LAB_INSTANCE = {
    'host': 'aws.vcenter.localdomain',
    'username': LAB_USERNAME,
    'password': LAB_PASSWORD,
    'collection_level': 4,
    'collection_type': 'both',
    'use_legacy_check_version': False,
    'collect_metric_instance_values': True,
    'empty_default_hostname': True,
    'ssl_verify': False,
    'collect_tags': True,
    'collect_events': True,
    'use_collect_events_fallback': True,
}

legacy_default_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
}

legacy_realtime_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'collect_realtime_only': True,
}

legacy_realtime_host_include_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'collect_realtime_only': True,
    'host_include_only_regex': "host1",
}

legacy_realtime_host_exclude_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'collect_realtime_only': True,
    'host_include_only_regex': "host[2-9]",
}

legacy_historical_instance = {
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'use_legacy_check_version': True,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'collect_historical_only': True,
}

default_instance = {
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
}

realtime_instance = {
    'collection_level': 4,
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'ssl_verify': False,
    'rest_api_options': None,
}

realtime_blacklist_instance = {
    'collection_level': 4,
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'ssl_verify': False,
    'rest_api_options': None,
    'resource_filters': [
        {
            'type': 'blacklist',
            'resource': 'host',
            'property': 'name',
            'patterns': [
                'host.*',
            ],
        }
    ],
}

realtime_whitelist_instance = {
    'collection_level': 4,
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'ssl_verify': False,
    'rest_api_options': None,
    'resource_filters': [
        {
            'type': 'whitelist',
            'resource': 'host',
            'property': 'name',
            'patterns': [
                'host.*',
            ],
        }
    ],
}

historical_instance = {
    'collection_level': 1,
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': 'vsphere_host',
    'username': 'vsphere_username',
    'password': 'vsphere_password',
    'ssl_verify': False,
    'collection_type': 'historical',
}


def build_rest_api_client(config, logger):
    if VSPHERE_VERSION.startswith('7.'):
        return VSphereRestAPI(config, logger, False)
    return VSphereRestAPI(config, logger, True)


def QueryPerfCounterByLevel(collection_level):
    return [
        vim.PerformanceManager.CounterInfo(
            key=100,
            groupInfo=vim.ElementDescription(key='datastore'),
            nameInfo=vim.ElementDescription(key='busResets'),
            rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            unitInfo=vim.ElementDescription(key='command'),
        ),
        vim.PerformanceManager.CounterInfo(
            key=101,
            groupInfo=vim.ElementDescription(key='cpu'),
            nameInfo=vim.ElementDescription(key='totalmhz'),
            rollupType=vim.PerformanceManager.CounterInfo.RollupType.average,
            unitInfo=vim.ElementDescription(key='megahertz'),
        ),
        vim.PerformanceManager.CounterInfo(
            key=102,
            groupInfo=vim.ElementDescription(key='vmop'),
            nameInfo=vim.ElementDescription(key='numChangeDS'),
            rollupType=vim.PerformanceManager.CounterInfo.RollupType.latest,
            unitInfo=vim.ElementDescription(key='operation'),
        ),
        vim.PerformanceManager.CounterInfo(
            key=103,
            groupInfo=vim.ElementDescription(key='cpu'),
            nameInfo=vim.ElementDescription(key='costop'),
            rollupType=vim.PerformanceManager.CounterInfo.RollupType.summation,
            unitInfo=vim.ElementDescription(key='millisecond'),
        ),
    ]


entity_metrics = [
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datastore(moId="NFS-Share-1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[2, 5],
                id=vim.PerformanceManager.MetricId(
                    counterId=100,
                    instance='ds1',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.ClusterComputeResource(moId="c1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[2, 5],
                id=vim.PerformanceManager.MetricId(
                    counterId=101,
                    instance='c1',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datacenter(moId="dc1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[1, 7],
                id=vim.PerformanceManager.MetricId(
                    counterId=102,
                    instance='dc1',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datacenter(moId="dc2"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[1, 3],
                id=vim.PerformanceManager.MetricId(
                    counterId=102,
                    instance='dc2',
                ),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.HostSystem(moId="host1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[34, 61],
                id=vim.PerformanceManager.MetricId(
                    counterId=103,
                    instance='host1',
                ),
            )
        ],
    ),
]


def QueryPerf(query_specs):
    result = []
    for query_spec in query_specs:
        for entity_metric in entity_metrics:
            if query_spec.entity == entity_metric.entity:
                value = []
                for metric_id in query_spec.metricId:
                    for metric_value in entity_metric.value:
                        if metric_id.counterId == metric_value.id.counterId:
                            value.append(metric_value)
                result.append(
                    vim.PerformanceManager.EntityMetric(
                        entity=entity_metric.entity,
                        value=value,
                    )
                )
    return result


class MockHttp:
    def __init__(self, **kwargs):
        self._exceptions = kwargs.get('exceptions')
        self._defaults = kwargs.get('defaults')

    def get(self, url, *args, **kwargs):
        return MockResponse(json_data={}, status_code=200)

    def post(self, url, *args, **kwargs):
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(
            *path_parts,
        )
        if self._exceptions and subpath in self._exceptions:
            raise self._exceptions[subpath]
        elif self._defaults and subpath in self._defaults:
            return self._defaults[subpath]
