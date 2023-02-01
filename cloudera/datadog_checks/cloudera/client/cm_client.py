# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import cm_client
from cm_client.rest import RESTClientObject
from packaging.version import Version, parse

from datadog_checks.cloudera.client.client import Client


class CmClient(Client):
    def __init__(self, log, **kwargs):
        self._log = log
        self._log.debug("creating CmClient object with parameters: %s", kwargs)
        cm_client.configuration.username = kwargs.get('username')
        cm_client.configuration.password = kwargs.get('password')
        self._client = cm_client.ApiClient(kwargs.get('url'))
        self._client.rest_client = RESTClientObject(maxsize=kwargs.get('max_parallel_requests'))

    def get_version(self) -> Version:
        self._log.debug('getting version from cloudera')
        cloudera_manager_resource_api = cm_client.ClouderaManagerResourceApi(self._client)
        get_version_response = cloudera_manager_resource_api.get_version()
        self._log.debug('get_version_response: %s', get_version_response)
        return parse(get_version_response.version)

    def read_clusters(self) -> list:
        return [
            {
                'name': cluster.name,
                'entity_status': cluster.entity_status,
                'tags': [{'name': tag.name, 'value': tag.value} for tag in cluster.tags],
            }
            for cluster in cm_client.ClustersResourceApi(self._client)
            .read_clusters(cluster_type='any', view='full')
            .items
        ]

    def query_time_series(self, _1, _2, query) -> list:
        items = []
        for item in cm_client.TimeSeriesResourceApi(self._client).query_time_series(query=query).items:
            for ts in item.time_series:
                if len(ts.data) > 0:
                    value = ts.data[0].value
                    timestamp = ts.data[0].timestamp
                    for d in ts.data:
                        current_timestamp = d.timestamp
                        if current_timestamp > timestamp:
                            value = d.value
                    category = ts.metadata.attributes['category'].lower()
                    name = ts.metadata.alias if ts.metadata.alias else ts.metadata.metric_name
                    items.append(
                        {
                            'metric': f"{category}.{name}",
                            'value': value,
                            'tags': [f'cloudera_{category}:{ts.metadata.entity_name}'],
                        }
                    )
        return items

    def list_hosts(self, cluster_name) -> list:
        return [
            {
                'host_id': host.host_id,
                'name': host.hostname,
                'entity_status': host.entity_status,
                'num_cores': host.num_cores,
                'num_physical_cores': host.num_physical_cores,
                'total_phys_mem_bytes': host.total_phys_mem_bytes,
                'rack_id': host.rack_id,
                'tags': [{'name': tag.name, 'value': tag.value} for tag in host.tags],
            }
            for host in cm_client.ClustersResourceApi(self._client).list_hosts(cluster_name, view='full').items
        ]
