import cm_client

from datadog_checks.cloudera.api_client import ApiClient
from datadog_checks.cloudera.entity_status import ENTITY_STATUS
from datadog_checks.cloudera.metrics import METRICS

from .common import CLUSTER_HEALTH, HOST_HEALTH


class ApiClientV7(ApiClient):
    def __init__(self, check, api_client):
        super(ApiClientV7, self).__init__(check, api_client)

    def collect_data(self):
        self._collect_clusters()

    def _collect_clusters(self):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        read_clusters_response = clusters_resource_api.read_clusters(cluster_type='any', view='full')
        for cluster in read_clusters_response.items:
            self._collect_cluster(cluster)

    def _collect_cluster(self, cluster):
        self._log.debug('cluster: %s', cluster)
        cluster_entity_status = ENTITY_STATUS[cluster.entity_status] if cluster.entity_status else None
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
        self._check.service_check(CLUSTER_HEALTH, cluster_entity_status, tags=tags)

        if cluster_name:
            self._collect_cluster_metrics(cluster_name, tags)
            self._collect_cluster_hosts(cluster_name)

    def _collect_cluster_metrics(self, cluster_name, tags):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        metric_names = ','.join(f'last({metric})' for metric in METRICS['cluster'])
        query = f'SELECT {metric_names} WHERE clusterName="{cluster_name}" AND category=CLUSTER'
        self._log.debug('query: %s', query)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        index = 0
        while index < len(query_time_series_response.items[0].time_series):
            metric_name = METRICS['cluster'][index]
            value = query_time_series_response.items[0].time_series[index].data[0].value
            self._log.debug('metric_name: %s', f'cluster.{metric_name}')
            self._log.debug('value: %s', value)
            self._log.debug('tags: %s', tags)
            self._check.gauge(f'cluster.{metric_name}', value, tags=tags)
            index += 1

    def _collect_cluster_hosts(self, cluster_name):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        list_hosts_response = clusters_resource_api.list_hosts(cluster_name, view='full')
        for host in list_hosts_response.items:
            self._collect_cluster_host(host)

    def _collect_cluster_host(self, host):
        self._log.debug('host: %s', host)
        host_health_summary = ENTITY_STATUS[host.entity_status] if host.entity_status else None

        host_id = host.host_id
        host_name = host.hostname
        host_ip_address = host.ip_address
        host_tags = host.tags
        self._log.debug('host_status: %s', host_health_summary)
        self._log.debug('host_id: %s', host_id)
        self._log.debug('host_tags: %s', host_tags)
        tags = []

        if host_id:
            tags.append(f'cloudera_host_id:{host_id}')
        if host_name:
            tags.append(f'cloudera_host_name:{host_name}')
        if host_ip_address:
            tags.append(f'cloudera_host_ip_address:{host_ip_address}')
        if host_tags:
            tags.extend([f"{host_tag.name}:{host_tag.value}" for host_tag in host_tags])

        self._log.debug('host_tags: %s', tags)
        self._check.service_check(HOST_HEALTH, host_health_summary, tags=tags)
        if host_id:
            self._collect_host_metrics(host_id, tags)

    def _collect_host_metrics(self, host_id, tags):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        metric_names = ','.join(f'last({metric})' for metric in METRICS['host'])
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=HOST'
        self._log.debug('query: %s', query)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug('query_time_series_response: %s', query_time_series_response)
        index = 0
        while index < len(query_time_series_response.items[0].time_series):
            metric_name = METRICS['host'][index]
            value = query_time_series_response.items[0].time_series[index].data[0].value
            self._log.debug('metric_name: %s', f'host.{metric_name}')
            self._log.debug('value: %s', value)
            self._log.debug('tags: %s', tags)
            self._check.gauge(f'host.{metric_name}', value, tags=tags)
            index += 1
