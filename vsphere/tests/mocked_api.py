# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import datetime as dt
import json
import os
import re

from mock import MagicMock
from pyVmomi import vim
from requests import Response
from six import iteritems

from datadog_checks.vsphere.api import VersionInfo
from tests.common import HERE, VSPHERE_VERSION


class MockedCounter(object):
    def __init__(self, counter):
        self.key = counter['key']
        self.groupInfo = MagicMock(key=counter['groupInfo.key'])
        self.nameInfo = MagicMock(key=counter['nameInfo.key'])
        self.rollupType = counter['rollup']


class MockedAPI(object):
    def __init__(self, config, _=None):
        self.config = config
        self.infrastructure_data = {}
        self.metrics_data = []
        self.mock_events = []
        self.server_time = dt.datetime.now()

    def get_current_time(self):
        return self.server_time

    def get_version(self):
        about = MagicMock(
            version=VSPHERE_VERSION,
            build='123456789',
            fullName='VMware vCenter Server {} build-14792544'.format(VSPHERE_VERSION),
            apiType='VirtualCenter',
        )
        return VersionInfo(about)

    def recursive_parse_topology(self, subtree, parent=None):
        current_mor = MagicMock(spec=getattr(vim, subtree['spec']), _moId=subtree['mo_id'])
        children = subtree.get('children', [])
        self.infrastructure_data[current_mor] = {'name': subtree['name'], 'parent': parent}
        if subtree.get('runtime.powerState') == 'on':
            self.infrastructure_data[current_mor]['runtime.powerState'] = vim.VirtualMachinePowerState.poweredOn
        if 'runtime.host' in subtree:
            # Temporary setting 'runtime.host_moId' to the host _moId
            # This will be used later to make 'runtime.host' a pointer to the runtime.host mor instance.
            self.infrastructure_data[current_mor]['runtime.host_moid'] = subtree['runtime.host']
        if 'guest.hostName' in subtree:
            self.infrastructure_data[current_mor]['guest.hostName'] = subtree['guest.hostName']
        if self.config.should_collect_attributes and 'customValue' in subtree:
            mor_attr = []
            for key_name, value in iteritems(subtree['customValue']):
                mor_attr.append('{}{}:{}'.format(self.config.attr_prefix, key_name, value))
            self.infrastructure_data[current_mor]['attributes'] = mor_attr

        for c in children:
            self.recursive_parse_topology(c, parent=current_mor)

        if parent is not None:
            return

        # Resolve the runtime.host_moId into pointers to the mocked mors.
        for _, props in iteritems(self.infrastructure_data):
            if 'runtime.host_moid' in props:
                hosts = [m for m, p in iteritems(self.infrastructure_data) if p['name'] == props['runtime.host_moid']]
                props['runtime.host'] = hosts[0] if hosts else object()
                del props['runtime.host_moid']

    def smart_connect(self):
        pass

    def get_perf_counter_by_level(self, _):
        with open(os.path.join(HERE, 'fixtures', 'counters.json')) as f:
            file_data = json.load(f)
            return [MockedCounter(m) for m in file_data]

    def get_infrastructure(self):
        if not self.infrastructure_data:
            with open(os.path.join(HERE, 'fixtures', 'topology.json')) as f:
                file_data = json.load(f)
                self.recursive_parse_topology(file_data)

        return self.infrastructure_data

    def query_metrics(self, query_specs):
        if not self.metrics_data:
            metrics_filename = 'metrics_{}.json'.format(self.config.collection_type)
            with open(os.path.join(HERE, 'fixtures', metrics_filename)) as f:
                file_data = json.load(f)
                for el in file_data:
                    mocked = MagicMock(
                        entity=el['entity'], value=el['value'], counterId=el['counterId'], instance=el['instance']
                    )
                    self.metrics_data.append(mocked)

        data = []
        for spec in query_specs:
            entity_name = self.infrastructure_data.get(spec.entity)['name']
            counter_ids = [i.counterId for i in spec.metricId]
            results = [m for m in self.metrics_data if m.entity == entity_name and m.counterId in counter_ids]
            values = []
            for r in results:
                values.append(MagicMock(id=MagicMock(counterId=r.counterId, instance=r.instance), value=r.value))

            if results:
                data.append(MagicMock(entity=spec.entity, value=values))

        return data

    def get_max_query_metrics(self):
        return 256

    def get_new_events(self, start_time):
        return self.mock_events


class MockResponse(Response):
    def __init__(self, json_data, status_code):
        super(MockResponse, self).__init__()
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


def mock_http_rest_api_v6(method, url, *args, **kwargs):
    if '/api/' in url:
        return MockResponse({}, 404)
    if method == 'get':
        if re.match(r'.*/category/id:.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                {
                    "value": {
                        "name": "my_cat_name_{}".format(num),
                        "description": "",
                        "id": "cat_id_{}".format(num),
                        "used_by": [],
                        "cardinality": "SINGLE",
                    }
                },
                200,
            )
        elif re.match(r'.*/tagging/tag/id:.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                {
                    "value": {
                        "category_id": "cat_id_{}".format(num),
                        "name": "my_tag_name_{}".format(num),
                        "description": "",
                        "id": "xxx",
                        "used_by": [],
                    }
                },
                200,
            )
    elif method == 'post':
        assert kwargs['headers']['Content-Type'] == 'application/json'
        if re.match(r'.*/session$', url):
            return MockResponse(
                {"value": "dummy-token"},
                200,
            )
        elif re.match(r'.*/tagging/tag-association\?~action=list-attached-tags-on-objects$', url):
            return MockResponse(
                {
                    "value": [
                        {"object_id": {"id": "VM4-4-1", "type": "VirtualMachine"}, "tag_ids": ["tag_id_1", "tag_id_2"]},
                        {"object_id": {"id": "10.0.0.104-1", "type": "HostSystem"}, "tag_ids": ["tag_id_2"]},
                        {"object_id": {"id": "NFS-Share-1", "type": "Datastore"}, "tag_ids": ["tag_id_2"]},
                    ]
                },
                200,
            )
    raise Exception("Rest api mock request not matched: method={}, url={}".format(method, url))


def mock_http_rest_api_v7(method, url, *args, **kwargs):
    if method == 'get':
        if re.match(r'.*/category/.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                {
                    'name': 'my_cat_name_{}'.format(num),
                    'description': 'VM category description',
                    'id': 'cat_id_{}'.format(num),
                    'used_by': [],
                    'cardinality': 'SINGLE',
                },
                200,
            )

        elif re.match(r'.*/tagging/tag/.*$', url):
            parts = url.split('_')
            num = parts[len(parts) - 1]
            return MockResponse(
                {
                    'category_id': 'cat_id_{}'.format(num),
                    'name': 'my_tag_name_{}'.format(num),
                    'description': '',
                    'id': 'tag_id_{}'.format(num),
                    'used_by': [],
                },
                200,
            )
    elif method == 'post':
        assert kwargs['headers']['Content-Type'] == 'application/json'
        if re.match(r'.*/session$', url):
            return MockResponse(
                "dummy-token",
                200,
            )
        elif re.match(r'.*/tagging/tag-association\?action=list-attached-tags-on-objects$', url):
            return MockResponse(
                [
                    {'tag_ids': ['tag_id_1', 'tag_id_2'], 'object_id': {'id': 'VM4-4-1', 'type': 'VirtualMachine'}},
                    {'tag_ids': ['tag_id_2'], 'object_id': {'id': 'NFS-Share-1', 'type': 'Datastore'}},
                    {'tag_ids': ['tag_id_2'], 'object_id': {'id': '10.0.0.104-1', 'type': 'HostSystem'}},
                ],
                200,
            )

    raise Exception("Rest api mock request not matched: method={}, url={}".format(method, url))
