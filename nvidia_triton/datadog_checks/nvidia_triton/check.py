# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any
from urllib.parse import urljoin  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2

from .metrics import METRICS_MAP


DEFAULT_METADATA_ENDPOINT = '/v2'
DEFAULT_SERVER_STATS_ENDPOINT = '/v2/models/stats'
DEFAULT_HEALTH_ENDPOINT = 'v2/health/ready'

class NvidiaTritonCheck(AgentCheck , OpenMetricsBaseCheckV2):

    # This will be the prefix of every metric and service check the integration sends
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'nvidia_triton'

    def __init__(self, name, init_config, instances=None):
        super(NvidiaTritonCheck, self).__init__(name, init_config, instances)
        self.tags = self.instance.get('tags', [])
        self.api_url = self.instance.get('nvidia_triton_api_endpoint')

    def get_default_config(self):
        return {'metrics': [METRICS_MAP]}
        
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
                self.log.debug("Malformed Triton Server version format: %s", version)
        else:
            self.log.debug("Could not retrieve version metadata.")

    
    def _submit_server_metrics(self):
        endpoint = self.openmetrics_endpoint
        response = self.http.get(endpoint)
        
        if not response.ok:
            self.log.error("Unable to get a valid response from url: %s with status code: %s", str(endpoint), str(response.status_code))
            return
        
        #TO DO : add the code to parse the endpoint metrics
        
    def _check_server_health(self, check_type, extra_params=None, response_handler=None):

        endpoint = urljoin(self.api_url, DEFAULT_HEALTH_ENDPOINT)
        response = self.http.get(endpoint)
        #The helath endpoint only exposes the status code in verbose mode, so we need to check we can properly retrieve it from the response

        if response.status_code != 200:
            self.service_check('health.status', AgentCheck.CRITICAL, self._tags)
        if response.status_code == 200:
            self.service_check('health.status', AgentCheck.OK, self._tags)
        else:
            self.service_check('health.status', AgentCheck.UNKNOWN, self._tags)

    def check(self, instance):
        if self.instance.get("openmetrics_endpoint"):
            super().check(instance)
        if self.api_url:
            self._check_server_health()
            self._submit_version_metadata()
            self._submit_server_metrics()
