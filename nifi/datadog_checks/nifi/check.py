# ABOUTME: Datadog Agent check for Apache NiFi.
# ABOUTME: Polls the NiFi REST API to collect JVM, flow, queue, processor, and bulletin data.

# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import AgentCheck

from .api import NiFiApi


class NifiCheck(AgentCheck):
    __NAMESPACE__ = 'nifi'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self._api = None

    def _get_api(self):
        if self._api is None:
            self._api = NiFiApi(
                api_url=self.instance['api_url'],
                http=self.http,
                log=self.log,
                username=self.instance.get('username'),
                password=self.instance.get('password'),
            )
        return self._api

    def check(self, _):
        api = self._get_api()
        try:
            api._ensure_auth()
            version = api.get_about()
            base_tags = [f'nifi_version:{version}'] + self.instance.get('tags', [])

            self._collect_cluster_health(api, base_tags)

            self.gauge('can_connect', 1, tags=base_tags)
        except Exception:
            self.gauge('can_connect', 0, tags=self.instance.get('tags', []))
            raise

    def _collect_cluster_health(self, api, base_tags):
        data = api.get_cluster_summary()
        summary = data.get('clusterSummary', {})
        if not summary.get('clustered', False):
            return

        connected = summary.get('connectedNodeCount', 0)
        total = summary.get('totalNodeCount', 0)
        self.gauge('cluster.connected_node_count', connected, tags=base_tags)
        self.gauge('cluster.total_node_count', total, tags=base_tags)
        is_healthy = 1 if connected == total and total > 0 else 0
        self.gauge('cluster.is_healthy', is_healthy, tags=base_tags)
