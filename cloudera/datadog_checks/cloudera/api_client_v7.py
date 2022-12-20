from concurrent.futures import ThreadPoolExecutor

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
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        read_clusters_response = clusters_resource_api.read_clusters(cluster_type='any', view='full')
        self._log.debug("Cloudera full clusters response:\n%s", read_clusters_response)

        # Use len(read_clusters_response.items) * 3 workers since
        # for each cluster, we are executing 3 tasks in parallel.
        with ThreadPoolExecutor(max_workers=len(read_clusters_response.items) * 3) as executor:
            for cluster in read_clusters_response.items:
                cluster_name = cluster.name

                tags = self._collect_cluster_tags(cluster, self._check.config.tags)

                executor.submit(self._collect_cluster_metrics, cluster_name, tags)
                executor.submit(self._collect_cluster_service_check, cluster, tags)
                executor.submit(self._collect_hosts, cluster_name)

    @staticmethod
    def _collect_cluster_tags(cluster, custom_tags):
        cluster_tags = [f"{cluster_tag.name}:{cluster_tag.value}" for cluster_tag in cluster.tags]

        cluster_tags.extend(custom_tags)

        return cluster_tags

    def _collect_cluster_service_check(self, cluster, tags):
        cluster_entity_status = ENTITY_STATUS[cluster.entity_status]
        message = cluster.entity_status if cluster_entity_status != AgentCheck.OK else None
        self._check.service_check(
            CLUSTER_HEALTH, cluster_entity_status, tags=[f'cloudera_cluster:{cluster.name}', *tags], message=message
        )

    def _collect_cluster_metrics(self, cluster_name, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['cluster'])
        query = f'SELECT {metric_names} WHERE clusterName="{cluster_name}" AND category=CLUSTER'
        self._query_time_series(query, tags=tags)

    def _collect_hosts(self, cluster_name):
        clusters_resource_api = cm_client.ClustersResourceApi(self._api_client)
        list_hosts_response = clusters_resource_api.list_hosts(cluster_name, view='full')
        self._log.debug("Cloudera full hosts response:\n%s", list_hosts_response)

        # Use len(list_hosts_response.items) * 4 workers since
        # for each host, we are executing 4 tasks in parallel.
        with ThreadPoolExecutor(max_workers=len(list_hosts_response.items) * 4) as executor:
            for host in list_hosts_response.items:
                tags = self._collect_host_tags(host, self._check.config.tags)
                executor.submit(self._collect_host_metrics, host, tags)
                executor.submit(self._collect_role_metrics, host, tags)
                executor.submit(self._collect_disk_metrics, host, tags)
                executor.submit(self._collect_host_service_check, host, tags)

    @staticmethod
    def _collect_host_tags(host, custom_tags):
        tags = [
            f'cloudera_hostname:{host.hostname}',
            f'cloudera_rack_id:{host.rack_id}',
            f'cloudera_cluster:{host.cluster_ref.cluster_name}',
        ]

        host_tags = host.tags
        if host_tags:
            for host_tag in host_tags:
                tags.append(f"{host_tag.name}:{host_tag.value}")

        tags.extend(custom_tags)

        return tags

    def _collect_host_service_check(self, host, tags):
        host_entity_status = ENTITY_STATUS[host.entity_status] if host.entity_status else None
        self._log.debug('Cloudera host_entity_status: %s', host_entity_status)
        self._check.service_check(HOST_HEALTH, host_entity_status, tags=tags)

    def _collect_host_metrics(self, host, tags):
        # Use 2 workers since we are executing 2 tasks in parallel.
        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(self._collect_host_native_metrics, host, tags)
            executor.submit(self._collect_host_timeseries_metrics, host, tags)

    def _collect_host_native_metrics(self, host, tags):
        for metric in NATIVE_METRICS['host']:
            self._check.gauge(f"host.{metric}", getattr(host, metric), tags)

    def _collect_host_timeseries_metrics(self, host, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['host'])
        query = f'SELECT {metric_names} WHERE hostId="{host.host_id}" AND category=HOST'
        self._query_time_series(query, tags=tags)

    def _collect_role_metrics(self, host, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['role'])
        query = f'SELECT {metric_names} WHERE hostId="{host.host_id}" AND category=ROLE'
        self._query_time_series(query, tags=tags)

    def _collect_disk_metrics(self, host, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['disk'])
        query = f'SELECT {metric_names} WHERE hostId="{host.host_id}" AND category=DISK'
        self._query_time_series(query, tags=tags)

    def _query_time_series(self, query, tags):
        self._log.debug('Cloudera timeseries query: %s', query)
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        self._log.debug('Cloudera query_time_series_response: %s', query_time_series_response)
        for item in query_time_series_response.items:
            for ts in item.time_series:
                self._log.debug('ts: %s', ts)
                metric_name = ts.metadata.alias
                category_name = ts.metadata.attributes['category'].lower()
                full_metric_name = f'{category_name}.{metric_name}'
                for d in ts.data:
                    value = d.value
                    self._check.gauge(
                        full_metric_name, value, tags=[f'cloudera_{category_name}:{ts.metadata.entity_name}', *tags]
                    )
