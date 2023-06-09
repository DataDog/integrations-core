# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests
import json
from datadog_checks.base import OpenMetricsBaseCheckV2, AgentCheck

from .metrics import METRICS
DEFAULT_METADATA_ENDPOINT = '/v1/meta'
DEFAULT_NODE_METRICS_ENDPOINT = '/v1/nodes'

class WeaviateCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):

        super(WeaviateCheck, self).__init__(
            name,
            init_config,
            instances,
        )

    def get_default_config(self):
        return {'namespace': 'weaviate', 'metrics': [METRICS]}

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
    
        endpoint = f"{self.instance.get('weaviate_api')}{DEFAULT_METADATA_ENDPOINT}"
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            data = json.loads(response.text)
            version = data["version"]
            try:
                version_split = version.split(".")
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
            except Exception as e:
                self.log.error("Error while parsing Weaviate version: %s", str(e))
                return
        else:
            self.log.debug("Could not submit version metadata.")

    def _submit_node_metrics:
    

    def check(self, _):
        try:
            self._submit_version_metadata()
        except Exception as e:
            self.log.error("Error while collecting Weaviate metrics: %s", str(e))
            raise