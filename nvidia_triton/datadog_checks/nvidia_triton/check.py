# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any
from urllib.parse import urljoin  # noqa: F401
from six.moves.urllib.parse import urlparse, urlunparse

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.base.errors import ConfigurationError

from .metrics import METRICS_MAP


DEFAULT_METADATA_ENDPOINT = '/v2'
DEFAULT_HEALTH_ENDPOINT = '/health/ready'
DEFAULT_ERROR_CODE = r'(4|5)\d\d'

class NvidiaTritonCheck(OpenMetricsBaseCheckV2):

    # This will be the prefix of every metric and service check the integration sends
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'nvidia_triton'

    def __init__(self, name, init_config, instances=None):
        super(NvidiaTritonCheck, self).__init__(name, init_config, instances)
        if 'openmetrics_endpoint' not in self.instance:
            raise ConfigurationError("Missing 'openmetrics url' in nvidia triton config")
        self.openmetrics_endpoint = self.instance["openmetrics_endpoint"]
        self.tags = self.instance.get('tags', [])

        # Get the API server port if specified, otherwise use the default 8000.
        self.server_port = self.instance.get('server_port', "8000")

        # Get the base url from the openmetrics endpoint and construct the server info API endpoint.
        self.server_info_api = None
        self.base_url = None
        try:
            parts = urlparse(self.openmetrics_endpoint)
            # Delete the /metrics from the url
            self.base_url=parts._replace(path="")
            # Replace the openmetrics port by the server port
            self.server_info_api= self.base_url._replace(netloc=parts.hostname+':'+self.server_port).geturl()
            
        except Exception as e:
            self.log.debug("Unable to determine the base url for server info collection: %s", str(e))

        # Wheather to collect the server info through the API or not
        self.collect_server_info = self.instance.get('collect_server_info', True)

        if self.collect_server_info == True :
            self._submit_version_metadata()
            self._check_server_health()

    def get_default_config(self):
        return {
            "metrics": [METRICS_MAP],
            # Rename labels that are reserved in datadog.
            "rename_labels": {
                "version": "model_version",
            },
        }
    
        
    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        if self.collect_server_info == False :
            self.log.warning("Collecting server info through API is disabled.")

        endpoint = urljoin(self.server_info_api, DEFAULT_METADATA_ENDPOINT)
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

        
    def _check_server_health(self, response_handler=None):
        if self.collect_server_info == False :
            self.log.warning("Collecting server info through API is disabled.")

        endpoint = urljoin(self.server_info_api, DEFAULT_METADATA_ENDPOINT, DEFAULT_HEALTH_ENDPOINT)
        response = self.http.get(endpoint)
        
        if response.status_code == DEFAULT_ERROR_CODE:
            self.service_check('health.status', AgentCheck.CRITICAL, self.tags)
        if response.status_code == 200:
            self.service_check('health.status', AgentCheck.OK, self.tags)
        else:
            self.service_check('health.status', AgentCheck.UNKNOWN, self.tags)

    def check(self, instance):
        if instance['openmetrics_endpoint']:
            super().check(instance)
