# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os
from datetime import datetime

from mock import MagicMock
from pyVmomi import vim
from six import iteritems
from tests.common import HERE


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

    def check_health(self):
        return True

    def recursive_parse_topology(self, subtree, parent=None):
        current_mor = MagicMock(spec=getattr(vim, subtree['spec']))
        children = subtree.get('children', [])
        self.infrastructure_data[current_mor] = {'name': subtree['name'], 'parent': parent}
        if subtree.get('runtime.powerState') == 'on':
            self.infrastructure_data[current_mor]['runtime.powerState'] = vim.VirtualMachinePowerState.poweredOn
        if 'runtime.host' in subtree:
            self.infrastructure_data[current_mor]['runtime.host'] = subtree['runtime.host']
        if 'guest.hostName' in subtree:
            self.infrastructure_data[current_mor]['guest.hostName'] = subtree['guest.hostName']

        for c in children:
            self.recursive_parse_topology(c, parent=current_mor)

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

            for _, props in iteritems(self.infrastructure_data):
                if 'runtime.host' in props:
                    hosts = [m for m, p in iteritems(self.infrastructure_data) if p['name'] == props['runtime.host']]
                    assert len(hosts) == 1
                    props['runtime.host'] = hosts[0]

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

    def get_latest_event_timestamp(self):
        return datetime.now()
