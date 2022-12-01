import cm_client

from datadog_checks.base import AgentCheck
from datadog_checks.cloudera.api_client import ApiClient
from datadog_checks.cloudera.entity_status import ENTITY_STATUS
from datadog_checks.cloudera.metrics import TIMESERIES_METRICS

from .common import CLUSTER_HEALTH, HOST_HEALTH


# TODO: Refactor this to abstract out timeseries queries using composite pattern
class ApiClientV7(ApiClient):
    def __init__(self, check, api_client):
        super(ApiClientV7, self).__init__(check, api_client)

    def collect_data(self):
        self._collect_clusters()
        self._collect_events()

    def _collect_clusters(self):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        read_clusters_response = clusters_resource_api.read_clusters(cluster_type='any', view='full')
        self._log.debug("Full clusters response:")
        self._log.debug(read_clusters_response)
        for cluster in read_clusters_response.items:
            self._collect_cluster_metrics_and_service_check(cluster)

    def _collect_cluster_metrics_and_service_check(self, cluster):
        self._log.debug('cluster: %s', cluster)
        cluster_entity_status = ENTITY_STATUS[cluster.entity_status]
        cluster_name = cluster.name
        cluster_tags = cluster.tags
        self._log.debug('cluster_entity_status: %s', cluster_entity_status)
        self._log.debug('cluster_name: %s', cluster_name)
        self._log.debug('cluster_tags: %s', cluster_tags)

        if cluster_name:
            tags = [f'cloudera_cluster:{cluster_name}']

        if cluster_tags:
            for cluster_tag in cluster_tags:
                tags.append(f"{cluster_tag.name}:{cluster_tag.value}")

        message = cluster.entity_status if cluster_entity_status != AgentCheck.OK else None
        self._check.service_check(CLUSTER_HEALTH, cluster_entity_status, tags=tags, message=message)

        if cluster_name:
            self._collect_cluster_metrics(cluster_name, tags)
            self._collect_hosts_metrics_and_service_check(cluster_name)

    def _collect_cluster_metrics(self, cluster_name, tags):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        metric_names = ','.join(f'last({metric})' for metric in TIMESERIES_METRICS['cluster'])
        query = f'SELECT {metric_names} WHERE clusterName="{cluster_name}" AND category=CLUSTER'
        self._log.debug('query: %s', query)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug("Full timeseries response:")
        self._log.debug(query_time_series_response)
        self._collect_query_time_series(query_time_series_response, 'cluster', [])

    def _collect_hosts_metrics_and_service_check(self, cluster_name):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        list_hosts_response = clusters_resource_api.list_hosts(cluster_name, view='full')
        self._log.debug("Full hosts response:")
        self._log.debug(list_hosts_response)

        for host in list_hosts_response.items:
            self._collect_host_metrics_and_service_check(host)

    def _collect_host_metrics_and_service_check(self, host):
        self._log.debug('host: %s', host)
        host_entity_status = ENTITY_STATUS[host.entity_status] if host.entity_status else None

        host_id = host.host_id
        self._log.debug('host_entity_status: %s', host_entity_status)
        self._log.debug('host_id: %s', host_id)

        if host_id:
            tags = [f"{tag.name}:{tag.value}" for tag in host.tags] if host.tags else []
            self._collect_host_metrics(host_id, tags)
            self._collect_role_metrics(host_id, tags)
            self._collect_host_disks(host_id)
            self._log.debug('host tags: %s', tags)
            self._check.service_check(HOST_HEALTH, host_entity_status, tags=tags)

    def _collect_host_metrics(self, host_id, tags):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        metric_names = ','.join(f'last({metric})' for metric in TIMESERIES_METRICS['host'])
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=HOST'
        self._log.debug('query: %s', query)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug("Full timeseries response:")
        self._log.debug(query_time_series_response)

        self._collect_query_time_series(query_time_series_response, 'host', tags)

    def _collect_role_metrics(self, host_id, tags):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        metric_names = ','.join(f'last({metric})' for metric in TIMESERIES_METRICS['role'])
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=ROLE'
        self._log.debug('query: %s', query)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug("Full timeseries response:")
        self._log.debug(query_time_series_response)
        self._collect_query_time_series(query_time_series_response, 'role', [])

    def _collect_host_disks(self, host_id):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        metric_names = ','.join(f'last({metric})' for metric in TIMESERIES_METRICS['disk'])
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=DISK'
        self._log.debug('query: %s', query)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug('query_time_series_response: %s', query_time_series_response)
        self._collect_query_time_series(query_time_series_response, 'disk', [])

    def _collect_query_time_series(self, query_time_series_response, category, tags):
        for item in query_time_series_response.items:
            last_metadata_metric_name = None
            for ts in item.time_series:
                self._log.debug('ts: %s', ts)
                if last_metadata_metric_name is None:
                    index = 0
                elif last_metadata_metric_name != ts.metadata.metric_name:
                    index += 1
                last_metadata_metric_name = ts.metadata.metric_name
                metric_name = TIMESERIES_METRICS[category][index]
                metric_tags = tags + [f'cloudera_{category}:{ts.metadata.entity_name}']
                full_metric_name = f'{category}.{metric_name}'
                new_tag = f'cloudera_{category}:{ts.metadata.entity_name}'
                if new_tag not in tags:
                    tags.append(new_tag)
                new_tag = f'cloudera_{category}:{ts.metadata.entity_name}'
                if new_tag not in tags:
                    tags.append(new_tag)
                for d in ts.data:
                    value = d.value
                    self._log.debug('full_metric_name: %s', full_metric_name)
                    self._log.debug('value: %s', value)
                    self._log.debug('metric_tags: %s', metric_tags)
                    self._check.gauge(full_metric_name, value, tags=metric_tags)
