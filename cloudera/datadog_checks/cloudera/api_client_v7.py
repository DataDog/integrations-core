# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import cm_client

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.cloudera.api_client import ApiClient
from datadog_checks.cloudera.entity_status import ENTITY_STATUS
from datadog_checks.cloudera.event import ClouderaEvent
from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS

from .common import CLUSTER_HEALTH, HOST_HEALTH
from .config import normalize_discover_config_include


class ApiClientV7(ApiClient):
    def __init__(self, check, api_client):
        super(ApiClientV7, self).__init__(check, api_client)
        self._log.debug("clusters config: %s", self._check.config.clusters)
        config_clusters_include = normalize_discover_config_include(self._log, self._check.config.clusters)
        self._log.debug("config_clusters_include: %s", config_clusters_include)
        if config_clusters_include:
            self._clusters_discovery = Discovery(
                lambda: cm_client.ClustersResourceApi(self._api_client)
                .read_clusters(cluster_type='any', view='full')
                .items,
                limit=self._check.config.clusters.limit,
                include=config_clusters_include,
                exclude=self._check.config.clusters.exclude,
                interval=self._check.config.clusters.interval,
                key=lambda cluster: cluster.name,
            )
        else:
            self._clusters_discovery = None
        self._log.debug("_clusters_discovery: %s", self._clusters_discovery)
        self._hosts_discovery = {}

    def collect_data(self):
        self._collect_clusters()
        self._collect_events()
        if self._check.config.custom_queries:
            self._collect_custom_queries()

    def _collect_clusters(self):
        if self._clusters_discovery:
            discovered_clusters = list(self._clusters_discovery.get_items())
        else:
            discovered_clusters = [
                (None, cluster.name, cluster, None)
                for cluster in cm_client.ClustersResourceApi(self._api_client)
                .read_clusters(cluster_type='any', view='full')
                .items
            ]
        self._log.debug("discovered clusters:\n%s", discovered_clusters)
        # Use len(read_clusters_response.items) * 2 workers since
        # for each cluster, we are executing 2 tasks in parallel.
        if len(discovered_clusters) > 0:
            futures = []
            with ThreadPoolExecutor(max_workers=len(discovered_clusters) * 3) as executor:
                for pattern, key, item, config in discovered_clusters:
                    self._log.debug(
                        "discovered cluster: [pattern:%s, key:%s, item:%s, config:%s]", pattern, key, item, config
                    )
                    cluster_name = key
                    cloudera_cluster_tag, cluster_tags = self._collect_cluster_tags(item, config)
                    futures.append(executor.submit(self._collect_cluster_metrics, cluster_name, cluster_tags))
                    futures.append(executor.submit(self._collect_hosts, cloudera_cluster_tag, cluster_name, config))
                    futures.append(executor.submit(self._collect_cluster_service_check, item, cluster_tags))
            for future in futures:
                future.result()

    def _collect_events(self):
        events_resource_api = cm_client.EventsResourceApi(self._api_client)
        now_utc = get_timestamp()

        start_time_iso = datetime.utcfromtimestamp(self._check.latest_event_query_utc).isoformat()
        end_time_iso = datetime.utcfromtimestamp(now_utc).isoformat()

        query = f"timeOccurred=ge={start_time_iso};timeOccurred=le={end_time_iso}"
        self._log.info("Cloudera event query: %s", query)
        try:
            event_resource_response = events_resource_api.read_events(query=query)
            for item in event_resource_response.items:
                self._log.debug('content: %s', item.content)
                self._log.debug('timestamp: %s', item.time_occurred)
                self._log.debug('id: %s', item.id)
                self._log.debug('category: %s', item.category)
                event_payload = ClouderaEvent(item).get_event()
                self._check.event(event_payload)
            self._check.latest_event_query_utc = now_utc
        except Exception as e:
            self._log.error("Cloudera unable to process event collection: %s", e)

    def _collect_cluster_tags(self, cluster, config):
        cloudera_cluster_tag = f"cloudera_cluster:{cluster.name}" if cluster.name else None
        cluster_tags = [f"{cluster_tag.name}:{cluster_tag.value}" for cluster_tag in cluster.tags]
        cluster_tags.extend([tag for tag in self._check.config.tags])
        cluster_tags.extend([tag for tag in config.get('tags', [])] if config else [])
        cluster_tags.append(cloudera_cluster_tag)
        return cloudera_cluster_tag, cluster_tags

    def _collect_cluster_service_check(self, cluster, tags):
        cluster_entity_status = ENTITY_STATUS[cluster.entity_status]
        message = cluster.entity_status if cluster_entity_status != AgentCheck.OK else None
        self._check.service_check(CLUSTER_HEALTH, cluster_entity_status, tags=tags, message=message)

    def _collect_cluster_metrics(self, cluster_name, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['cluster'])
        query = f'SELECT {metric_names} WHERE clusterName="{cluster_name}" AND category=CLUSTER'
        self._query_time_series(query, tags=tags)

    def _collect_hosts(self, cloudera_cluster_tag, cluster_name, config):
        self._log.debug("self._hosts_discovery: %s", self._hosts_discovery)
        if cluster_name not in self._hosts_discovery:
            self._log.debug("Collecting hosts from '%s' cluster with config: %s", cluster_name, config)
            config_hosts_include = normalize_discover_config_include(self._log, config.get('hosts') if config else None)
            self._log.debug("config_hosts_include: %s", config_hosts_include)
            if config_hosts_include:
                self._hosts_discovery[cluster_name] = Discovery(
                    lambda: cm_client.ClustersResourceApi(self._api_client).list_hosts(cluster_name, view='full').items,
                    limit=config.get('hosts').get('limit') if config else None,
                    include=config_hosts_include,
                    exclude=config.get('hosts').get('exclude') if config else None,
                    interval=config.get('hosts').get('interval') if config else None,
                    key=lambda host: host.host_id,
                )
            else:
                self._hosts_discovery[cluster_name] = None

        if self._hosts_discovery[cluster_name]:
            discovered_hosts = list(self._hosts_discovery[cluster_name].get_items())
        else:
            discovered_hosts = [
                (None, host.host_id, host, None)
                for host in cm_client.ClustersResourceApi(self._api_client).list_hosts(cluster_name, view='full').items
            ]
        self._log.debug("discovered hosts:\n%s", discovered_hosts)
        # Use len(list_hosts_response.items) * 4 workers since
        # for each host, we are executing 4 tasks in parallel.
        if len(discovered_hosts) > 0:
            futures = []
            with ThreadPoolExecutor(max_workers=len(discovered_hosts) * 4) as executor:
                for pattern, key, item, config in discovered_hosts:
                    self._log.debug(
                        "discovered host: [pattern:%s, key:%s, item:%s, config:%s]", pattern, key, item, config
                    )
                    cloudera_hostname_tag, host_tags = self._collect_host_tags(item, config)
                    futures.append(
                        executor.submit(self._collect_host_metrics, item, [cloudera_cluster_tag] + host_tags)
                    )
                    futures.append(
                        executor.submit(self._collect_role_metrics, item, [cloudera_cluster_tag] + host_tags)
                    )
                    futures.append(
                        executor.submit(self._collect_disk_metrics, item, [cloudera_cluster_tag] + host_tags)
                    )
                    futures.append(
                        executor.submit(self._collect_host_service_check, item, [cloudera_cluster_tag] + host_tags)
                    )
            for future in futures:
                future.result()

    def _collect_host_tags(self, host, config):
        cloudera_hostname_tag = f'cloudera_hostname:{host.hostname}' if host.hostname else None
        host_tags = [f"{host_tag.name}:{host_tag.value}" for host_tag in host.tags] if host.tags else []
        host_tags.extend([tag for tag in self._check.config.tags])
        host_tags.extend([tag for tag in config.get('tags', [])] if config else [])
        host_tags.append(cloudera_hostname_tag)
        host_tags.append(f'cloudera_rack_id:{host.rack_id}' if host.rack_id else None)
        return cloudera_hostname_tag, host_tags

    def _collect_host_service_check(self, host, tags):
        host_entity_status = ENTITY_STATUS[host.entity_status] if host.entity_status else None
        self._log.debug('Cloudera host_entity_status: %s', host_entity_status)
        self._check.service_check(HOST_HEALTH, host_entity_status, tags=tags)

    def _collect_host_metrics(self, host, tags):
        # Use 2 workers since we are executing 2 tasks in parallel.
        futures = []
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures.append(executor.submit(self._collect_host_native_metrics, host, tags))
            futures.append(executor.submit(self._collect_host_timeseries_metrics, host, tags))
        for future in futures:
            future.result()

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
                entity_tag = f'cloudera_{category_name}:{ts.metadata.entity_name}' if ts.metadata.entity_name else None
                for d in ts.data:
                    value = d.value
                    self._check.gauge(
                        full_metric_name, value, tags=[entity_tag if entity_tag not in tags else None, *tags]
                    )

    def _collect_custom_queries(self):
        for custom_query in self._check.config.custom_queries:
            try:
                tags = custom_query.tags if custom_query.tags else []
                self._run_custom_query(custom_query.query, tags)
            except Exception as e:
                self._log.error("Skipping custom query %s due to the following exception: %s", custom_query, e)

    def _run_custom_query(self, custom_query, tags):
        self._log.debug('Running Cloudera custom query: %s', custom_query)
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        query_time_series_response = time_series_resource_api.query_time_series(query=custom_query)
        self._log.debug('Cloudera custom query result: %s', query_time_series_response)
        for item in query_time_series_response.items:
            for ts in item.time_series:
                if ts.metadata.alias:
                    metric_name = ts.metadata.alias
                else:
                    metric_name = ts.metadata.metric_name

                category_name = ts.metadata.attributes['category'].lower()
                full_metric_name = f'{category_name}.{metric_name}'
                entity_tag = f'cloudera_{category_name}:{ts.metadata.entity_name}'

                value = ts.data[0].value
                timestamp = ts.data[0].timestamp
                for d in ts.data:
                    current_timestamp = d.timestamp
                    if current_timestamp > timestamp:
                        value = d.value

                self._check.gauge(full_metric_name, value, tags=[entity_tag, *tags])
