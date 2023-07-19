# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import re

from pyVmomi import vim, vmodl
from six.moves.urllib.parse import urlparse

from datadog_checks.base.utils.time import get_current_datetime
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

LEGACY_DEFAULT_INSTANCE = {
    'use_legacy_check_version': True,
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
}

LEGACY_REALTIME_INSTANCE = {
    'use_legacy_check_version': True,
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
    'collect_realtime_only': True,
}

LEGACY_HISTORICAL_INSTANCE = {
    'use_legacy_check_version': True,
    'name': 'vsphere_mock',
    'empty_default_hostname': True,
    'event_config': {
        'collect_vcenter_alarms': True,
    },
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
    'collect_historical_only': True,
}

DEFAULT_INSTANCE = {
    'use_legacy_check_version': False,
    'empty_default_hostname': True,
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
    'ssl_verify': False,
}

REALTIME_INSTANCE = {
    'use_legacy_check_version': False,
    'empty_default_hostname': True,
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
    'ssl_verify': False,
    'collection_level': 4,
    'rest_api_options': None,
}

HISTORICAL_INSTANCE = {
    'use_legacy_check_version': False,
    'empty_default_hostname': True,
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
    'ssl_verify': False,
    'collection_level': 4,
    'collection_type': 'historical',
}

EVENTS_ONLY_INSTANCE = {
    'empty_default_hostname': True,
    'use_legacy_check_version': False,
    'host': os.environ.get('VSPHERE_URL', 'FAKE'),
    'username': os.environ.get('VSPHERE_USERNAME', 'FAKE'),
    'password': os.environ.get('VSPHERE_PASSWORD', 'FAKE'),
    'ssl_verify': False,
    'collect_events_only': True,
}


def build_rest_api_client(config, logger):
    if VSPHERE_VERSION.startswith('7.'):
        return VSphereRestAPI(config, logger, False)
    return VSphereRestAPI(config, logger, True)


EVENTS = [
    vim.event.VmMessageEvent(
        createdTime=get_current_datetime(),
        vm=vim.event.VmEventArgument(name="vm1"),
        fullFormattedMessage="First event in time",
    ),
    vim.event.VmMessageEvent(
        createdTime=get_current_datetime(),
        vm=vim.event.VmEventArgument(name="vm2"),
        fullFormattedMessage="Second event in time",
    ),
]


PERF_METRIC_ID = [
    vim.PerformanceManager.MetricId(counterId=100),
    vim.PerformanceManager.MetricId(counterId=101),
    vim.PerformanceManager.MetricId(counterId=102),
    vim.PerformanceManager.MetricId(counterId=103),
]


PERF_COUNTER_INFO = [
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
    vim.PerformanceManager.CounterInfo(
        key=104,
        groupInfo=vim.ElementDescription(key='mem'),
        nameInfo=vim.ElementDescription(key='active'),
        rollupType=vim.PerformanceManager.CounterInfo.RollupType.average,
        unitInfo=vim.ElementDescription(key='kibibyte'),
    ),
]


PERF_ENTITY_METRICS = [
    vim.PerformanceManager.EntityMetric(
        entity=vim.VirtualMachine(moId="vm1"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[47, 52],
                id=vim.PerformanceManager.MetricId(counterId=103),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.VirtualMachine(moId="vm2"),
        value=[
            vim.PerformanceManager.IntSeries(
                value=[30, 11],
                id=vim.PerformanceManager.MetricId(counterId=103),
            )
        ],
    ),
    vim.PerformanceManager.EntityMetric(
        entity=vim.Datastore(moId="ds1"),
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
                    # instance='dc2',
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
                    # instance='host1',
                ),
            )
        ],
    ),
]


PROPERTIES_EX_VM_OFF = vim.PropertyCollector.RetrieveResult(
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
                    val=vim.VirtualMachinePowerState.poweredOff,
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.VirtualMachine(moId="vm2"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='vm2',
                ),
                vmodl.DynamicProperty(
                    name='runtime.powerState',
                    val=vim.VirtualMachinePowerState.poweredOn,
                ),
            ],
        ),
    ]
)

PROPERTIES_EX = vim.PropertyCollector.RetrieveResult(
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
            ],
        ),
        vim.ObjectContent(
            obj=vim.VirtualMachine(moId="vm2"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='vm2',
                ),
                vmodl.DynamicProperty(
                    name='runtime.powerState',
                    val=vim.VirtualMachinePowerState.poweredOn,
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Datastore(moId="ds1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='ds1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.ClusterComputeResource(moId="c1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='c1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Folder(moId="folder_1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='folder_1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Datacenter(moId="dc1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='dc1',
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.Datacenter(moId="dc2"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='dc2',
                ),
                vmodl.DynamicProperty(
                    name='parent',
                    val=vim.Folder(moId="folder_1"),
                ),
            ],
        ),
        vim.ObjectContent(
            obj=vim.HostSystem(moId="host1"),
            propSet=[
                vmodl.DynamicProperty(
                    name='name',
                    val='host1',
                ),
            ],
        ),
    ],
)


class MockHttpV6:
    def __init__(self):
        self.exceptions = {}

    def get(self, url, *args, **kwargs):
        if '/api/' in url:
            return MockResponse({}, 404)
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/category/id:.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    "value": {
                        "name": "my_cat_name_{}".format(num),
                        "description": "",
                        "id": "cat_id_{}".format(num),
                        "used_by": [],
                        "cardinality": "SINGLE",
                    }
                },
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag/id:.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    "value": {
                        "category_id": "cat_id_{}".format(num),
                        "name": "my_tag_name_{}".format(num),
                        "description": "",
                        "id": "xxx",
                        "used_by": [],
                    }
                },
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('get', url))

    def post(self, url, *args, **kwargs):
        if '/api/' in url:
            return MockResponse({}, 404)
        assert kwargs['headers']['Content-Type'] == 'application/json'
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/session$', url):
            return MockResponse(
                json_data={"value": "dummy-token"},
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag-association\?~action=list-attached-tags-on-objects$', url):
            return MockResponse(
                json_data={
                    "value": [
                        {"object_id": {"id": "vm1", "type": "VirtualMachine"}, "tag_ids": ["tag_id_1", "tag_id_2"]},
                        {"object_id": {"id": "host1", "type": "HostSystem"}, "tag_ids": ["tag_id_2"]},
                        {"object_id": {"id": "ds1", "type": "Datastore"}, "tag_ids": ["tag_id_2"]},
                    ]
                },
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('post', url))


class MockHttpV7:
    def __init__(self):
        self.exceptions = []

    def get(self, url, *args, **kwargs):
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/category/.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    'name': 'my_cat_name_{}'.format(num),
                    'description': 'VM category description',
                    'id': 'cat_id_{}'.format(num),
                    'used_by': [],
                    'cardinality': 'SINGLE',
                },
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag/.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                json_data={
                    'category_id': 'cat_id_{}'.format(num),
                    'name': 'my_tag_name_{}'.format(num),
                    'description': '',
                    'id': 'tag_id_{}'.format(num),
                    'used_by': [],
                },
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('get', url))

    def post(self, url, *args, **kwargs):
        assert kwargs['headers']['Content-Type'] == 'application/json'
        parsed_url = urlparse(url)
        path_and_args = parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path
        path_parts = path_and_args.split('/')
        subpath = os.path.join(*path_parts)
        if subpath in self.exceptions:
            raise self.exceptions[subpath]
        if re.match(r'.*/session$', url):
            return MockResponse(
                json_data="dummy-token",
                status_code=200,
            )
        elif re.match(r'.*/tagging/tag-association\?action=list-attached-tags-on-objects$', url):
            return MockResponse(
                json_data=[
                    {'tag_ids': ['tag_id_1', 'tag_id_2'], 'object_id': {'id': 'vm1', 'type': 'VirtualMachine'}},
                    {'tag_ids': ['tag_id_2'], 'object_id': {'id': 'ds1', 'type': 'Datastore'}},
                    {'tag_ids': ['tag_id_2'], 'object_id': {'id': 'host1', 'type': 'HostSystem'}},
                ],
                status_code=200,
            )
        raise Exception("Rest api mock request not matched: method={}, url={}".format('post', url))
