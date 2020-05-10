# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from six import iteritems
from pprint import pprint

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.marklogic.api import MarkLogicApi


class MarklogicCheck(AgentCheck):
    __NAMESPACE__ = 'marklogic'

    def __init__(self, name, init_config, instances):
        super(MarklogicCheck, self).__init__(name, init_config, instances)

        url = self.instance.get('url')
        if not url:
            raise ConfigurationError("url is a required configuration.")

        self.api = MarkLogicApi(self.http, url)

        self._tags = tuple(self.instance.get('tags', []))

    def check(self, _):
        # type: (Any) -> None
        pprint(self.api.get_status())
        self.process_base_status(self.api.get_status())
        # pprint(self.api.get_status('hosts'))
        # pprint(self.api.get_status('forests'))
        # pprint(self.api.get_status('servers'))

    def process_base_status(self, data):
        relations = data['local-cluster-status']['status-relations']
        for key, resource_data in iteritems(relations):
            if not key.endswith('-status'):
                continue
            resource_type = resource_data['typeref']
            metrics = resource_data['{}-status-summary'.format(resource_type)]
            tags = ['resource:{}'.format(resource_type)]
            self.process_status_metrics(resource_type, metrics, tags=tags)

    def process_status_metrics(self, metric_prefix, metrics, tags):
        pprint(tags)
        pprint(metrics)
        for key, data in iteritems(metrics):
            if key in ['rate-properties', 'load-properties']:
                prop_type = key[:key.index('-properties')]
                total_key = 'total-'+prop_type
                self.submit_metric(metric_prefix, total_key, data[total_key], tags)
                self.process_status_metrics(metric_prefix, data[prop_type+'-detail'], tags)
            elif key == 'load-properties':
                self.submit_metric(metric_prefix, 'total-load', data['total-load'], tags)
                self.process_status_metrics(metric_prefix, data['load-detail'], tags)
            elif self.is_metric(data):
                self.submit_metric(metric_prefix, key, data, tags)

    @staticmethod
    def is_metric(data):
        return (isinstance(data, (int, float))) or ('units' in data and 'value' in data)

    def submit_metric(self, suffix, prefix, value_data, tags=None):
        metric_name = "{}.{}".format(suffix, prefix)
        if isinstance(value_data, (int, float)):
            self.gauge(metric_name, value_data, tags=tags)
        elif 'units' in value_data and 'value' in value_data:
            units = value_data['units']
            value = value_data['value']
            if units in GAUGE_UNITS:
                self.gauge(metric_name, value, tags=tags)
        else:
            self.log.warning("Invalid metric: metric_suffix={}, metric_data={}".format(prefix, value_data))


GAUGE_UNITS = [
    '%',
    'hits/sec',
    'locks/sec',
    'MB/sec',
    'misses/sec',
    'quantity',
    'quantity/sec',
    'sec',
    'sec/sec',
]

"""
Design

Metric naming

marklogic.status.<METRIC_NAME> e.g. marklogic.status.backup-read-bytes

tags by object type:
    - cluster
    - hosts
    - database
    - forest
    - groups

Query Metrics
    - http://localhost:8002/dashboard/query
    - Example queries:
        - http://localhost:8002/manage/v2/requests?format=json (cluster level)
        - http://localhost:8002/manage/v2/requests?format=json&server-id=Admin&group-id=Default
        - http://localhost:8002/manage/v2/requests?format=json&group-id=Default
        - http://localhost:8002/manage/v2/requests?format=json&host-id=2871b05b4bdc
    - metric name: marklogic.query_summary.<METRIC_NAME>
    - metric name: marklogic.query.<METRIC_NAME>

Rates & Loads Metrics aka Status metrics (view=status)
    - http://localhost:8002/dashboard/load/
    - Example queries:
        - http://localhost:8002/manage/v2/hosts?view=status
        - http://localhost:8002/manage/v2/hosts?view=status&format=json (cluster level)
        - http://localhost:8002/manage/v2/forests/Security?view=status&format=json
        - http://localhost:8002/manage/v2/databases/Extensions?view=status&format=json
        - http://localhost:8002/manage/v2/hosts/2871b05b4bdc?view=status&format=json
        - http://localhost:8002/manage/v2/transactions?format=json (already in http://localhost:8002/manage/v2/hosts?view=status)
        - http://localhost:8002/manage/v2/servers?view=status&format=json (already in http://localhost:8002/manage/v2/hosts?view=status)
    - metric name: marklogic.status_summary.<METRIC_NAME>
    - metric name: marklogic.status.<METRIC_NAME>

Storage Metrics
    - http://localhost:8002/dashboard/disk-space/
    - Example queries:
        - http://localhost:8002/manage/v2/forests?format=json&view=storage
        - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Last-Login
        - http://localhost:8002/manage/v2/forests?format=json&view=storage&forest-id=Last-Login
        - http://localhost:8002/manage/v2/forests?format=json&view=storage&database-id=Security
    - metric name: marklogic.storage_summary.<METRIC_NAME>
    - metric name: marklogic.storage.<METRIC_NAME>

"""
