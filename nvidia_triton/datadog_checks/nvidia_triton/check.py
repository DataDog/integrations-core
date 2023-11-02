# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from urllib.parse import urljoin, urlparse  # noqa: F401

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2

from .metrics import METRICS_MAP

DEFAULT_METADATA_ENDPOINT = '/v2'
DEFAULT_HEALTH_ENDPOINT = DEFAULT_METADATA_ENDPOINT + '/health/ready'


class NvidiaTritonCheck(OpenMetricsBaseCheckV2):

    # This will be the prefix of every metric and service check the integration sends
    DEFAULT_METRIC_LIMIT = 0
    __NAMESPACE__ = 'nvidia_triton'

    def __init__(self, name, init_config, instances=None):
        super(NvidiaTritonCheck, self).__init__(name, init_config, instances)
        self.openmetrics_endpoint = self.instance["openmetrics_endpoint"]
        self.tags = self.instance.get('tags', [])
        self._metadata_endpoint = DEFAULT_METADATA_ENDPOINT
        self._health_endpoint = DEFAULT_HEALTH_ENDPOINT

        # Get the API server port if specified, otherwise use the default 8000.
        self.server_port = str(self.instance.get('server_port', 8000))

        self.collect_server_info = self.instance.get('collect_server_info', True)

        # Get the base url from the openmetrics endpoint and construct the server info API endpoint.
        if self.collect_server_info:
            parts = urlparse(self.openmetrics_endpoint)
            # Delete the /metrics from the url
            self.base_url = parts._replace(path="")
            # Replace the openmetrics port by the server port
            self.server_info_api = self.base_url._replace(netloc=parts.hostname + ':' + self.server_port).geturl()
        else:
            self.log.debug("Collecting server info through API is disabled.")
            return

    def get_default_config(self):
        return {
            "metrics": [METRICS_MAP],
            # Rename labels that are reserved in datadog.
            "rename_labels": {
                "version": "triton_model_version",
            },
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = urljoin(self.server_info_api, self._metadata_endpoint)
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

    def _check_server_health(self):
        endpoint = urljoin(self.server_info_api, self._health_endpoint)
        response = self.http.get(endpoint)

        # Any 4xx or 5xx response from the API endpoint (/v2/health/ready) means the server is not ready
        if 400 <= response.status_code and response.status_code < 600:
            self.service_check('health.status', AgentCheck.CRITICAL, self.tags)
        if response.status_code == 200:
            self.service_check('health.status', AgentCheck.OK, self.tags)
        else:
            self.service_check('health.status', AgentCheck.UNKNOWN, self.tags)

    def check(self, instance):
        super().check(instance)
        if self.collect_server_info:
            self._submit_version_metadata()
            self._check_server_health()
