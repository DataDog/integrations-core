# (C) Datadog, Inc. 2026-present
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
        self.raw_metric_prefix = self.instance.get('raw_metric_prefix', 'n8n_')

    def get_default_config(self):
        return {
            'metrics': [METRIC_MAP],
            'rename_labels': {
                'version': 'n8n_version',
            },
            'exclude_metrics': [
                'nodejs_version_info',
                'version_info',
            ],
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._version_endpoint)
        version_submitted = False
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
                    self.set_metadata('version', version_raw, scheme='parts', final_scheme='semver', part_map=version_parts)
                    version_submitted = True
                else:
                    self.log.debug("Malformed N8N Server version format: %s, will try to parse from metrics", version)
            else:
                self.log.debug(
                    "Could not retrieve version metadata; code %s: %s", response.status_code, response.reason
                )
        except Exception as e:
            self.log.debug("Error retrieving version metadata: %s", e)

        # Fallback: try to parse version from metrics endpoint if not submitted yet
        if not version_submitted:
            self._submit_version_from_metrics()

    def _submit_version_from_metrics(self):
        """Fallback method to parse n8n version from the metrics endpoint"""
        try:
            response = self.http.get(self.openmetrics_endpoint)

            if response.ok:
                lines = response.text.splitlines()
                for line in lines:
                    # Look for the version_info metric with the raw prefix
                    if line.startswith(f'{self.raw_metric_prefix}version_info{{'):
                        # n8n_version_info{version="v1.117.2",major="1",minor="117",patch="2"} 1
                        if 'major=' in line and 'minor=' in line and 'patch=' in line:
                            # Extract the label values
                            import re

                            major_match = re.search(r'major="([^"]+)"', line)
                            minor_match = re.search(r'minor="([^"]+)"', line)
                            patch_match = re.search(r'patch="([^"]+)"', line)

                            if major_match and minor_match and patch_match:
                                major = major_match.group(1)
                                minor = minor_match.group(1)
                                patch = patch_match.group(1)

                                version_raw = f'{major}.{minor}.{patch}'
                                version_parts = {
                                    'major': major,
                                    'minor': minor,
                                    'patch': patch,
                                }
                                self.set_metadata('version', version_raw, scheme='parts', final_scheme='semver', part_map=version_parts)
                                self.log.debug("Submitted n8n version metadata from metrics: %s", version_raw)
                                break
            else:
                self.log.debug(
                    "Could not retrieve n8n version from metrics; code %s: %s", response.status_code, response.reason
                )
        except Exception as e:
            self.log.debug("Error retrieving n8n version from metrics: %s", e)

    @AgentCheck.metadata_entrypoint
    def _submit_nodejs_version_metadata(self):
        """Parse Node.js version from the metrics endpoint"""
        try:
            response = self.http.get(self.openmetrics_endpoint)

            if response.ok:
                lines = response.text.splitlines()
                for line in lines:
                    # Look for the nodejs_version_info metric with the raw prefix
                    if line.startswith(f'{self.raw_metric_prefix}nodejs_version_info{{'):
                        # n8n_nodejs_version_info{version="v22.18.0",major="22",minor="18",patch="0"} 1
                        if 'major=' in line and 'minor=' in line and 'patch=' in line:
                            # Extract the label values
                            import re

                            major_match = re.search(r'major="([^"]+)"', line)
                            minor_match = re.search(r'minor="([^"]+)"', line)
                            patch_match = re.search(r'patch="([^"]+)"', line)

                            if major_match and minor_match and patch_match:
                                major = major_match.group(1)
                                minor = minor_match.group(1)
                                patch = patch_match.group(1)

                                version_raw = f'{major}.{minor}.{patch}'
                                
                                # Manually submit each metadata field
                                self.set_metadata('nodejs.version.major', major)
                                self.set_metadata('nodejs.version.minor', minor)
                                self.set_metadata('nodejs.version.patch', patch)
                                self.set_metadata('nodejs.version.raw', version_raw)
                                self.set_metadata('nodejs.version.scheme', 'semver')
                                self.log.debug("Submitted Node.js version metadata: %s", version_raw)
                                break
            else:
                self.log.debug(
                    "Could not retrieve Node.js version from metrics; code %s: %s",
                    response.status_code,
                    response.reason,
                )
        except Exception as e:
            self.log.debug("Error retrieving Node.js version metadata: %s", e)

    def _check_n8n_readiness(self):
        endpoint = urljoin(self.openmetrics_endpoint, self._ready_endpoint)
        response = self.http.get(endpoint)

        # Determine metric value and status_code tag
        if response.status_code is None:
            self.log.warning("The readiness endpoint did not return a status code")
            metric_value = 0
            metric_tags = self.tags + ['status_code:null']
        elif response.status_code == 200:
            # Ready - submit 1
            metric_value = 1
            metric_tags = self.tags + [f'status_code:{response.status_code}']
        else:
            # Not ready - submit 0
            metric_value = 0
            metric_tags = self.tags + [f'status_code:{response.status_code}']

        # Submit metric with appropriate value and status_code tag
        self.gauge('readiness.check', metric_value, tags=metric_tags)

    def check(self, instance):
        super().check(instance)
        self._submit_version_metadata()
        self._submit_nodejs_version_metadata()
        self._check_n8n_readiness()
