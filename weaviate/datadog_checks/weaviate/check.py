# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import time
from urllib.parse import urljoin  # urlparse

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.utils.common import round_value

from .metrics import METRICS

DEFAULT_METADATA_ENDPOINT = '/v1/meta'
DEFAULT_NODE_METRICS_ENDPOINT = '/v1/nodes'
DEFAULT_LIVENESS_ENDPOINT = '/v1/.well-known/live'


class WeaviateCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'weaviate'

    def __init__(self, name, init_config, instances=None):
        super(WeaviateCheck, self).__init__(
            name,
            init_config,
            instances,
        )
        self.tags = self.instance.get('tags', [])

        self.api_url = self.instance.get('weaviate_api')

    def get_default_config(self):
        return {'metrics': [METRICS]}

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = urljoin(self.api_url, DEFAULT_METADATA_ENDPOINT)
        response = self.http.get(endpoint)

        if response.status_code == 200:
            try:
                data = response.json()
                version = data["version"]
                version_split = version.split(".")
                if len(version_split) >= 3:
                    major = version_split[0]
                    minor = version_split[1]
                    patch = version_split[2]

                    version_raw = '{}.{}.{}'.format(major, minor, patch)

                    version_parts = {
                        'major': major,
                        'minor': minor,
                        'patch': patch,
                    }
                    self.set_metadata('version', version_raw, scheme='semver', part_map=version_parts)
                else:
                    self.log.debug("Invalid Weaviate version format: %s", version)
            except Exception as e:
                self.log.debug("Error while parsing Weaviate version: %s", str(e))
        else:
            self.log.debug("Could not retrieve version metadata from host.")

    def _submit_liveness_metrics(self):
        endpoint = urljoin(self.api_url, DEFAULT_LIVENESS_ENDPOINT)
        start_time = time.time()
        response = self.http.get(endpoint)
        end_time = time.time()
        if response.status_code == 200:
            tags = self.tags
            latency = round_value((end_time - start_time) * 1000, 2)
            self.service_check('liveness.status', 0)
            tags.append(f"weaviate_liveness_url:{endpoint}")
            self.gauge('http.latency_ms', latency, tags=tags)
        else:
            self.service_check('liveness.status', 2)

    def _submit_node_metrics(self):
        endpoint = urljoin(self.api_url, DEFAULT_NODE_METRICS_ENDPOINT)
        response = self.http.get(endpoint)
        if response.status_code != 200:
            self.log.debug("Could not retrieve Node metrics. Request returned a: %s", str(response.status_code))
            return
        try:
            data = response.json()
            status_values = {'HEALTHY': 0, 'UNHEALTHY': 1, 'UNAVAILABLE': 2}

            for node in data.get('nodes', []):
                tags = self.tags

                tags.append(f"weaviate_node:{node.get('name')}")
                tags.append(f"weaviate_version:{node.get('version')}")
                tags.append(f"weaviate_githash:{node.get('gitHash')}")

                if 'status' in node:
                    status = node.get('status')
                    tags.append(f"weaviate_node_status:{status.lower()}")
                    self.gauge('node.status', status_values.get(status, 3), tags=tags)
                    self.service_check('node.status', status_values.get(status, 3), tags=tags)

                if 'stats' in node:
                    stats = node['stats']
                    self.gauge('node.stats.shards', stats.get('shardCount', 0), tags=tags)
                    self.gauge('node.stats.objects', stats.get('objectCount', 0), tags=tags)

                if 'shards' in node:
                    for shard in node['shards']:
                        tags.append(f"weaviate_shard_name:{shard.get('name')}")
                        tags.append(f"weaviate_shard_class:{shard.get('class')}")
                        self.gauge('node.shard.objects', shard.get('objectCount', 0), tags=tags)

        except Exception as e:
            self.log.debug("Error occurred during node metrics submission: %s", str(e))

    def check(self, _):
        try:
            if self.instance.get("weaviate_api"):
                self._submit_version_metadata()
                self._submit_liveness_metrics()
                self._submit_node_metrics()
        except Exception as e:
            self.log.error("Error while collecting Weaviate metrics from API: %s", str(e))
        try:
            if self.instance.get("openmetrics_endpoint"):
                super().check(_)
        except Exception as e:
            self.log.error("Error while collecting Weaviate metrics from OpenMetrics endpoint: %s", str(e))
