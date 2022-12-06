import cm_client

from datadog_checks.base import AgentCheck
from datadog_checks.cloudera.api_client import ApiClient
from datadog_checks.cloudera.entity_status import ENTITY_STATUS
from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS

from .common import CLUSTER_HEALTH, HOST_HEALTH


class ApiClientV7(ApiClient):
    def __init__(self, check, api_client):
        super(ApiClientV7, self).__init__(check, api_client)

    def collect_data(self):
        self._collect_clusters()

    def _collect_clusters(self):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        read_clusters_response = clusters_resource_api.read_clusters(cluster_type='any', view='full')
        self._log.debug("Full clusters response:")
        self._log.debug(read_clusters_response)
        for cluster in read_clusters_response.items:
            self._log.debug('cluster: %s', cluster)
            cluster_name = cluster.name
            cluster_tags = cluster.tags
            self._log.debug('cluster_name: %s', cluster_name)

            if cluster_name:
                tags = [f'cloudera_cluster:{cluster_name}']

            if cluster_tags:
                for cluster_tag in cluster_tags:
                    tags.append(f"{cluster_tag.name}:{cluster_tag.value}")

            self._collect_cluster_metrics(cluster_name, tags)
            self._collect_cluster_service_check(cluster, tags)

            # host metrics will have different tags than the cluster metrics
            self._collect_hosts(cluster_name)

    def _collect_cluster_service_check(self, cluster, tags):
        cluster_entity_status = ENTITY_STATUS[cluster.entity_status]
        message = cluster.entity_status if cluster_entity_status != AgentCheck.OK else None
        self._check.service_check(CLUSTER_HEALTH, cluster_entity_status, tags=tags, message=message)

    def _collect_cluster_metrics(self, cluster_name, tags):
        metric_names = ','.join(f'last({metric})' for metric in TIMESERIES_METRICS['cluster'])
        query = f'SELECT {metric_names} WHERE clusterName="{cluster_name}" AND category=CLUSTER'
        self._query_time_series(query, category='cluster', tags=tags)

    def _collect_hosts(self, cluster_name):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        list_hosts_response = clusters_resource_api.list_hosts(cluster_name, view='full')
        self._log.debug("Full hosts response:")
        self._log.debug(list_hosts_response)
        for host in list_hosts_response.items:
            tags = [
                f'cloudera_hostname:{host.hostname}',
                f'cloudera_rack_id:{host.rack_id}',
                f'cloudera_host_id:{host.host_id}',
                f'cloudera_cluster:{host.cluster_ref.cluster_name}',
            ]

            host_tags = host.tags
            if host_tags:
                for host_tag in host_tags:
                    tags.append(f"{host_tag.name}:{host_tag.value}")

            self._collect_host_native_metrics(host, tags)

            if host.host_id:
                self._collect_host_metrics(host, tags)
                self._collect_host_service_check(host, tags)

    def _collect_host_native_metrics(self, host, tags):
        for metric in NATIVE_METRICS['host']:
            self._check.gauge(f"host.{metric}", getattr(host, metric), tags)

    def _collect_host_service_check(self, host, tags):
        host_entity_status = ENTITY_STATUS[host.entity_status] if host.entity_status else None
        self._log.debug('host_entity_status: %s', host_entity_status)
        self._check.service_check(HOST_HEALTH, host_entity_status, tags=tags)

    def _collect_host_metrics(self, host, tags):
        categories = TIMESERIES_METRICS.keys()
        for category in categories:
            metric_names = ','.join(f'last({metric})' for metric in TIMESERIES_METRICS[category])
            query = f'SELECT {metric_names} WHERE hostId="{host.host_id}" AND category={category.upper()}'
            self._query_time_series(query, category=category, tags=tags)

    def _query_time_series(self, query, category, tags):
        self._log.debug('query: %s', query)
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug('query_time_series_response: %s', query_time_series_response)
        for item in query_time_series_response.items:
            for ts in item.time_series:
                self._log.debug('ts: %s', ts)
                raw_metric_name = ts.metadata.metric_name
                metric_name = raw_metric_name[5:-1]
                full_metric_name = f'{category}.{metric_name}'
                for d in ts.data:
                    value = d.value
                    self._log.debug('full_metric_name: %s', full_metric_name)
                    self._log.debug('value: %s', value)
                    self._check.gauge(full_metric_name, value, tags=tags)
