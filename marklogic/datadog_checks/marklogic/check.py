# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict

from six import iteritems
from pprint import pprint

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.marklogic.api import MarkLogicApi
from .constants import RESOURCE_TYPES


class MarklogicCheck(AgentCheck):
    __NAMESPACE__ = 'marklogic'

    def __init__(self, name, init_config, instances):
        super(MarklogicCheck, self).__init__(name, init_config, instances)

        url = self.instance.get('url')
        if not url:
            raise ConfigurationError("url is a required configuration.")

        self.api = MarkLogicApi(self.http, url)

        self._tags = self.instance.get('tags', [])

        # TODO: Need cache with regular refresh
        self.resources = self.api.get_resources()

    def check(self, _):
        # type: (Any) -> None
        # TODO: Handle errors:
        #       - Continue if one of the processor fail
        #       - Add service check (can connect, status service check)
        self.collect_base_status_metrics()
        self.collect_resource_status()

        # No need to query base requests metrics, they are already collect in by process_base_status
        # self.process_requests_metrics_by_resource()
        self.collect_base_storage_metrics()

    def collect_resource_status(self):
        """
        Collect Extra Metrics.
        Only necessary for forest.
        For other resources, all metrics are already collected via `process_base_status`
        """
        for resource_type in ['forest']:
            res_meta = RESOURCE_TYPES[resource_type]
            data = self.api.get_status_data(res_meta['plural'])
            metrics = data['{}-status-list'.format(resource_type)]['status-list-summary']
            self._collect_status_metrics(res_meta['plural'], metrics)

    def collect_base_status_metrics(self):
        """
        Collect Status Metrics
        """
        data = self.api.get_status_data()
        relations = data['local-cluster-status']['status-relations']
        for key, resource_data in iteritems(relations):
            if not key.endswith('-status'):
                continue
            resource_type = resource_data['typeref']
            metrics = resource_data['{}-status-summary'.format(resource_type)]
            # TODO: Ignore already collected metrics
            #       - forests-status-summary
            #       - hosts-status-summary
            #       - servers-status-summary
            self._collect_status_metrics(resource_type, metrics)

    def _collect_status_metrics(self, metric_prefix, metrics):
        tags = self._tags
        for key, data in iteritems(metrics):
            if key in ['rate-properties', 'load-properties']:
                prop_type = key[:key.index('-properties')]
                total_key = 'total-'+prop_type
                self.submit_metric("{}.{}".format(metric_prefix, total_key), data[total_key], tags)
                self._collect_status_metrics(metric_prefix, data[prop_type + '-detail'])
            elif key == 'load-properties':
                self.submit_metric("{}.total-load".format(metric_prefix), data['total-load'], tags)
                self._collect_status_metrics(metric_prefix, data['load-detail'])
            elif self.is_metric(data):
                self.submit_metric("{}.{}".format(metric_prefix, key), data, tags)

    def collect_requests_metrics_by_resource(self):
        """
        Collect Base Query Metrics
        """
        data = self.api.get_requests_data()
        metrics_data = data['request-default-list']['list-summary']
        for metric_name, value_data in iteritems(metrics_data):
            self.submit_metric("requests.{}".format(metric_name), value_data)

    def collect_base_storage_metrics(self):
        """
        Collect Base Storage Metrics
        """

        data = self.api.get_forest_storage_data()
        locations_data = data['forest-storage-list']['storage-list-items']['storage-host']

        for location_data in locations_data:
            tags = self._tags[:]
            tags.append('host_id:{}'.format(location_data['relation-id']))
            # tags.append('host_name:{}'.format(sub_locations['relation-id']))  # TODO: get host name too
            for sub_location_data in location_data['locations']['location']:
                tags += ['storage_path:{}'.format(sub_location_data['path'])]
                for host_key, host_value in iteritems(sub_location_data):
                    if host_key == 'location-forests':
                        location_value = host_value['location-forest']
                        for forest_data in location_value:
                            tags += [
                                "forest_id:{}".format(forest_data['idref']),
                                "forest_name:{}".format(forest_data['nameref']),
                            ]
                            for forest_key, forest_value in iteritems(forest_data):
                                if forest_key == 'disk-size':
                                    self.submit_metric("forests.storage.forest.{}".format(forest_key), forest_value,
                                                       tags=tags)
                    elif self.is_metric(host_value):
                        self.submit_metric("forests.storage.host.{}".format(host_key), host_value, tags=tags)

    @staticmethod
    def is_metric(data):
        return (isinstance(data, (int, float))) or ('units' in data and 'value' in data)

    def submit_metric(self, metric_name, value_data, tags=None):
        if isinstance(value_data, (int, float)):
            self.gauge(metric_name, value_data, tags=tags)
        elif 'units' in value_data and 'value' in value_data:
            units = value_data['units']
            value = value_data['value']
            if units in GAUGE_UNITS:
                self.gauge(metric_name, value, tags=tags)
        else:
            self.log.warning("Invalid metric: metric_suffix={}, metric_data={}".format(metric_name, value_data))


GAUGE_UNITS = [
    '%',
    'hits/sec',
    'locks/sec',
    'MB',
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
