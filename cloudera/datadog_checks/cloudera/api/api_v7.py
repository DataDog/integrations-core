# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.discovery import Discovery
from datadog_checks.base.utils.time import get_timestamp
from datadog_checks.cloudera.api.api import Api
from datadog_checks.cloudera.common import CLUSTER_HEALTH, HOST_HEALTH
from datadog_checks.cloudera.config import normalize_discover_config_include
from datadog_checks.cloudera.entity_status import ENTITY_STATUS
from datadog_checks.cloudera.metrics import NATIVE_METRICS, TIMESERIES_METRICS


class ApiV7(Api):
    def __init__(self, check, api_client):
        super(ApiV7, self).__init__(check, api_client)
        self._log.debug("clusters config: %s", self._check.config.clusters)
        config_clusters_include = normalize_discover_config_include(self._log, self._check.config.clusters)
        self._log.debug("config_clusters_include: %s", config_clusters_include)
        if config_clusters_include:
            self._clusters_discovery = Discovery(
                lambda: self._api_client.read_clusters(),
                limit=self._check.config.clusters.limit,
                include=config_clusters_include,
                exclude=self._check.config.clusters.exclude,
                interval=self._check.config.clusters.interval,
                key=lambda cluster: cluster.get('name'),
            )
        else:
            self._clusters_discovery = None
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
                (None, cluster.get('name'), cluster, None) for cluster in self._api_client.read_clusters()
            ]
        self._log.trace("Discovered clusters raw response:\n%s", discovered_clusters)
        # Use len(read_clusters_response.items) * 2 workers since
        # for each cluster, we are executing 2 tasks in parallel.
        if len(discovered_clusters) > 0:
            with ThreadPoolExecutor(max_workers=len(discovered_clusters) * 3) as executor, raising_submitter(
                executor
            ) as submit:
                for pattern, cluster_name, item, cluster_config in discovered_clusters:
                    self._log.debug(
                        "Discovered cluster: [pattern:%s, cluster_name:%s, config:%s]",
                        pattern,
                        cluster_name,
                        cluster_config,
                    )
                    self._log.trace(
                        "Discovered cluster raw response: [pattern:%s, key:%s, item:%s, config:%s]",
                        pattern,
                        cluster_name,
                        item,
                        cluster_config,
                    )
                    tags = self._collect_cluster_tags(item)
                    submit(self._collect_cluster_metrics, cluster_name, tags)
                    submit(self._collect_hosts, cluster_name, cluster_config)
                    submit(self._collect_cluster_service_check, item, tags)

    def _collect_events(self):
        now_utc = get_timestamp()
        start_time_iso = datetime.utcfromtimestamp(self._check.latest_event_query_utc).isoformat()
        end_time_iso = datetime.utcfromtimestamp(now_utc).isoformat()
        query = f"timeOccurred=ge={start_time_iso};timeOccurred=le={end_time_iso}"
        self._log.debug("Cloudera event query: %s", query)
        try:
            events = self._api_client.read_events(query)
            self._log.debug("Events: %s", events)
            for event in events:
                self._check.event(event)
        except Exception as e:
            self._log.error("Cloudera unable to process event collection: %s", e)
        self._check.latest_event_query_utc = now_utc

    def _collect_cluster_tags(self, cluster):
        cluster_tags = [f"cloudera_cluster:{cluster.get('name')}"]
        cluster_tags.extend(
            [f"{cluster_tag['name']}:{cluster_tag['value']}" for cluster_tag in cluster.get('tags', [])]
        )
        if self._check.config.tags is not None:
            cluster_tags.extend(self._check.config.tags)
        return cluster_tags

    def _collect_cluster_service_check(self, cluster, tags):
        entity_status = cluster['entity_status']
        cluster_entity_status = ENTITY_STATUS[entity_status]
        message = entity_status if cluster_entity_status != AgentCheck.OK else None
        self._check.service_check(CLUSTER_HEALTH, cluster_entity_status, tags=tags, message=message)

    def _collect_cluster_metrics(self, cluster_name, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['cluster'])
        query = f'SELECT {metric_names} WHERE clusterName="{cluster_name}" AND category=CLUSTER'
        self._query_time_series('cluster', cluster_name, query, tags)

    def _collect_hosts(self, cluster_name, config):
        self._log.debug("self._hosts_discovery: %s", self._hosts_discovery)
        if cluster_name not in self._hosts_discovery:
            self._log.debug("Collecting hosts from '%s' cluster with config: %s", cluster_name, config)
            config_hosts_include = normalize_discover_config_include(self._log, config.get('hosts') if config else None)
            self._log.trace("config_hosts_include: %s", config_hosts_include)
            if config_hosts_include:
                self._hosts_discovery[cluster_name] = Discovery(
                    lambda: self._api_client.list_hosts(cluster_name),
                    limit=config.get('hosts').get('limit') if config else None,
                    include=config_hosts_include,
                    exclude=config.get('hosts').get('exclude') if config else None,
                    interval=config.get('hosts').get('interval') if config else None,
                    key=lambda host: host.get('name'),
                )
            else:
                self._hosts_discovery[cluster_name] = None
        if self._hosts_discovery[cluster_name]:
            discovered_hosts = list(self._hosts_discovery[cluster_name].get_items())
        else:
            discovered_hosts = [
                (None, host.get('name'), host, None) for host in self._api_client.list_hosts(cluster_name)
            ]
        self._log.debug("Discovered hosts: %s", discovered_hosts)
        # Use len(discovered_hosts) * 4 workers since
        # for each host, we are executing 4 tasks in parallel.
        if len(discovered_hosts) > 0:
            with ThreadPoolExecutor(max_workers=len(discovered_hosts) * 4) as executor, raising_submitter(
                executor
            ) as submit:
                for pattern, key, item, config in discovered_hosts:
                    self._log.debug(
                        "discovered host: [pattern:%s, key:%s, item:%s, config:%s]", pattern, key, item, config
                    )
                    tags = self._collect_host_tags(item) + [f'cloudera_cluster:{cluster_name}']
                    submit(self._collect_host_service_check, item, tags)
                    submit(self._collect_host_metrics, item, tags)
                    submit(self._collect_role_metrics, item, tags)
                    submit(self._collect_disk_metrics, item, tags)

    def _collect_host_tags(self, host):
        host_tags = [f"cloudera_hostname:{host['name']}", f"cloudera_rack_id:{host['rack_id']}"]
        host_tags.extend([f"{host_tag['name']}:{host_tag['value']}" for host_tag in host['tags'] or []])
        if self._check.config.tags is not None:
            host_tags.extend(self._check.config.tags)
        return host_tags

    def _collect_host_service_check(self, host, tags):
        entity_status = host['entity_status']
        host_entity_status = ENTITY_STATUS[entity_status]
        message = entity_status if host_entity_status != AgentCheck.OK else None
        self._check.service_check(HOST_HEALTH, host_entity_status, tags=tags, message=message)

    def _collect_host_metrics(self, host, tags):
        # Use 2 workers since we are executing 2 tasks in parallel.
        with ThreadPoolExecutor(max_workers=2) as executor, raising_submitter(executor) as submit:
            submit(self._collect_host_native_metrics, host, tags)
            submit(self._collect_host_timeseries_metrics, host, tags)

    def _collect_host_native_metrics(self, host, tags):
        for metric in NATIVE_METRICS['host']:
            self._check.gauge(f"host.{metric}", host[metric], tags)

    def _collect_host_timeseries_metrics(self, host, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['host'])
        host_id = host['host_id']
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=HOST'
        self._query_time_series('host', host['name'], query, tags=tags)

    def _collect_role_metrics(self, host, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['role'])
        host_id = host['host_id']
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=ROLE'
        self._query_time_series('role', f"role_{host['name']}", query, tags=tags)

    def _collect_disk_metrics(self, host, tags):
        metric_names = ','.join(f'last({metric}) AS {metric}' for metric in TIMESERIES_METRICS['disk'])
        host_id = host['host_id']
        query = f'SELECT {metric_names} WHERE hostId="{host_id}" AND category=DISK'
        self._query_time_series('disk', f"disk_{host['name']}", query, tags=tags)

    def _query_time_series(self, category, name, query, tags):
        self._log.debug(
            'Cloudera timeseries query: category[%s], name[%s], query[%s], tags[%s]', category, name, query, tags
        )
        items = self._api_client.query_time_series(query, category, name)
        self._log.trace('query_time_series response: %s', items)
        for item in items:
            self._log.debug('item: %s', item)
            metric = item.get('metric')
            item_tags = [*tags]
            item_tags.extend([tag for tag in item.get('tags') if tag not in item_tags])
            value = item.get('value')
            self._log.debug('metric: %s', metric)
            self._check.gauge(metric, value, tags=[*item_tags])

    def _collect_custom_queries(self):
        if self._check.config.custom_queries is None:
            return

        for custom_query in self._check.config.custom_queries:
            try:
                tags = custom_query.tags if custom_query.tags else []
                self._run_custom_query(custom_query.query, tags)
            except Exception as e:
                self._log.error("Skipping custom query %s due to the following exception: %s", custom_query, e)

    def _run_custom_query(self, custom_query, tags):
        self._log.debug('Running Cloudera custom query: %s', custom_query)
        items = self._api_client.query_time_series(custom_query)
        self._log.trace('query_time_series response: %s', items)

        for item in items:
            self._log.debug('item: %s', item)
            metric = item.get('metric')
            item_tags = [*tags]
            item_tags.extend([tag for tag in item.get('tags') if tag not in item_tags])
            value = item.get('value')
            self._log.debug('metric: %s', metric)
            self._check.gauge(metric, value, tags=[*item_tags])


@contextlib.contextmanager
def raising_submitter(executor):
    """Provides a `submit` function that wraps `executor.submit` in such a way that it
    will cause the first exception found in the resulting _futures_ to be raised in the
    parent thread at the point where the context is exited.
    """
    futures = []

    def submit_and_maybe_raise(*args, **kwargs):
        future = executor.submit(*args, **kwargs)
        futures.append(future)

    yield submit_and_maybe_raise

    # Calling the `result` method on futures causes exceptions that happened during the
    # execution to be raised in the current thread.
    for future in futures:
        future.result()
