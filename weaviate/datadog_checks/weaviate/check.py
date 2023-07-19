# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import time
from urllib.parse import urljoin

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.utils.common import round_value
from datadog_checks.weaviate.config_models import ConfigMixin

from .metrics import METRICS

DEFAULT_METADATA_ENDPOINT = '/v1/meta'
DEFAULT_NODE_METRICS_ENDPOINT = '/v1/nodes'
DEFAULT_LIVENESS_ENDPOINT = '/v1/.well-known/live'

# Mapping service checks to HEALTHY = Ok, UNHEALTHY = Warning, UNAVAILABLE = Critical.
# Defaults to unknown if not of the above (3).
NODE_STATUS_VALUES = {'HEALTHY': 0, 'UNHEALTHY': 1, 'UNAVAILABLE': 2, 'UNKNOWN': 3}


class WeaviateCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'weaviate'

    def __init__(self, name, init_config, instances=None):
        super(WeaviateCheck, self).__init__(
            name,
            init_config,
            instances,
        )
        self.tags = self.instance.get('tags', [])
        self.api_url = self.instance.get('weaviate_api_endpoint')

    def get_default_config(self):
        return {'metrics': [METRICS]}

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = urljoin(self.api_url, DEFAULT_METADATA_ENDPOINT)
        response = self.http.get(endpoint)

        if response.ok:
            data = response.json()
            version = data.get("version", "")
            version_split = version.split(".")
            if len(version_split) >= 3:
                major = version_split[0]
                minor = version_split[1]
                patch = version_split[2]

                version_raw = f'{major}.{minor}.{patch}'

                version_parts = {
                    'major': major,
                    'minor': minor,
                    'patch': patch,
                }
                self.set_metadata('version', version_raw, scheme='semver', part_map=version_parts)
            else:
                self.log.debug("Invalid Weaviate version format: %s", version)
        else:
            self.log.debug("Could not retrieve version metadata from host.")

    def _submit_liveness_metrics(self):
        endpoint = urljoin(self.api_url, DEFAULT_LIVENESS_ENDPOINT)
        tags = copy.deepcopy(self.tags)
        tags.append(f"weaviate_liveness_url:{endpoint}")

        start_time = time.time()
        response = self.http.get(endpoint)
        end_time = time.time()

        if response.ok:
            latency = round_value((end_time - start_time) * 1000, 2)
            self.service_check('liveness.status', AgentCheck.OK, tags)
            self.gauge('http.latency_ms', latency, tags=tags)
        else:
            self.service_check('liveness.status', AgentCheck.CRITICAL, tags)

    def _submit_node_metrics(self):
        endpoint = urljoin(self.api_url, DEFAULT_NODE_METRICS_ENDPOINT)
        response = self.http.get(endpoint)
        if not response.ok:
            self.log.error("Could not retrieve Node metrics. Request returned a: %s", str(response.status_code))
            return

        data = response.json()

        for node in data.get('nodes', []):
            tags = copy.deepcopy(self.tags)

            tags.append(f"weaviate_node:{node.get('name', '')}")
            tags.append(f"weaviate_version:{node.get('version', '')}")
            tags.append(f"weaviate_githash:{node.get('gitHash', '')}")

            if status := node.get('status'):
                tags.append(f"weaviate_node_status:{status.lower()}")
                self.gauge('node.status', NODE_STATUS_VALUES.get(status, NODE_STATUS_VALUES['UNKNOWN']), tags=tags)
                self.service_check(
                    'node.status', NODE_STATUS_VALUES.get(status, NODE_STATUS_VALUES['UNKNOWN']), tags=tags
                )

            if stats := node.get('stats'):
                self.gauge('node.stats.shards', stats.get('shardCount', 0), tags=tags)
                self.gauge('node.stats.objects', stats.get('objectCount', 0), tags=tags)

            if shards := node.get('shards'):
                for shard in shards:
                    tags.append(f"shard_name:{shard.get('name', '')}")
                    tags.append(f"class_name:{shard.get('class', '')}")
                    self.gauge('node.shard.objects', shard.get('objectCount', 0), tags=tags)

    def check(self, instance):
        if self.instance.get("openmetrics_endpoint"):
            super().check(instance)
        if self.api_url:
            self._submit_liveness_metrics()
            self._submit_version_metadata()
            self._submit_node_metrics()
