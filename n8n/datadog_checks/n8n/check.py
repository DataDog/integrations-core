# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import urljoin, urlparse  # noqa: F401

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.n8n.metrics import METRIC_MAP

DEFAULT_READY_ENDPOINT = '/healthz/readiness'
DEFAULT_HEALTH_ENDPOINT = '/healthz'
DEFAULT_VERSION_ENDPOINT = '/rest/settings'


class N8nCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'n8n'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):
        super(N8nCheck, self).__init__(
            name,
            init_config,
            instances,
        )
        self.openmetrics_endpoint = self.instance["openmetrics_endpoint"]
        self.tags = self.instance.get('tags', [])
        self._ready_endpoint = DEFAULT_READY_ENDPOINT
        self._health_endpoint = DEFAULT_HEALTH_ENDPOINT
        self._version_endpoint = DEFAULT_VERSION_ENDPOINT
        # Get the N8N API port if specified, otherwise use the default 5678.
        self.server_port = str(self.instance.get('server_port', 5678))
        self.raw_metric_prefix = self.instance.get('raw_metric_prefix', 'n8n')

    def get_default_config(self):
        # If raw_metric_prefix is 'n8n', metrics start with 'n8n'
        if self.raw_metric_prefix == 'n8n':
            namespace = 'n8n'
        else:
            namespace = f'n8n.{self.raw_metric_prefix}'

        return {'namespace': namespace, 'metrics': [METRIC_MAP]}
    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._version_endpoint)
        response = self.http.get(endpoint)

        if response.ok:
            data = response.json()
            version = data.get("versionCli", "")
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
                self.log.debug("Malformed N8N Server version format: %s", version)
        else:
            self.log.debug("Could not retrieve version metadata.")

    def _check_n8n_health(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._health_endpoint)
        response = self.http.get(endpoint)

        # Any 4xx or 5xx response from the API endpoint (/healthz) means the n8n process is not responding
        if 400 <= response.status_code and response.status_code < 600:
            self.service_check('health.status', AgentCheck.CRITICAL, self.tags)
        if response.status_code == 200:
            self.service_check('health.status', AgentCheck.OK, self.tags)
        else:
            self.service_check('health.status', AgentCheck.UNKNOWN, self.tags)

    def _check_n8n_readiness(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._ready_endpoint)
        response = self.http.get(endpoint)

        # Any 4xx or 5xx response from the API endpoint (/healthz/readiness)
        # means the n8n is not ready to accept requests
        if 400 <= response.status_code and response.status_code < 600:
            self.service_check('health.status', AgentCheck.CRITICAL, self.tags)
        if response.status_code == 200:
            self.service_check('health.status', AgentCheck.OK, self.tags)
        else:
            self.service_check('health.status', AgentCheck.UNKNOWN, self.tags)

    def check(self, instance):
        super().check(instance)
        self._submit_version_metadata()
        self._check_n8n_health()
        self._check_n8n_readiness()

