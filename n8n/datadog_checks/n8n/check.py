# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from urllib.parse import urljoin, urlparse  # noqa: F401

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.n8n.metrics import METRIC_MAP

DEFAULT_READY_ENDPOINT = '/healthz/readiness'
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
        self._version_endpoint = DEFAULT_VERSION_ENDPOINT
        # Get the N8N API port if specified, otherwise use the default 5678.
        self.server_port = str(self.instance.get('server_port', 5678))
        self.raw_metric_prefix = self.instance.get('raw_metric_prefix', 'n8n')

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': {
                'version': 'n8n_version',
            },
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._version_endpoint)
        try:
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
                self.log.debug("Could not retrieve version metadata; code %s: %s", response.status_code response.reason)
        except Exception as e:
            self.log.debug("Error retrieving version metadata: %s", e)

    def _check_n8n_readiness(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._ready_endpoint)
        response = self.http.get(endpoint)

        # Check if status_code is available
        if response.status_code is None:
            self.log.warning("The readiness endpoint did not return a status code")
        else:
            metric_tags = self.tags + [f'status_code:{response.status_code}']

        # Submit metric with value 1 and status_code as tag
        self.gauge('readiness.check', 1, tags=metric_tags)

    def check(self, instance):
        super().check(instance)
        self._submit_version_metadata()
        self._check_n8n_readiness()
