# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.utils.http_exceptions import HTTPClientError

from .metrics import GPU_METRIC_MAP, METRIC_MAP, RAY_GPU_METRIC_MAP, RAY_METRIC_MAP, RENAME_LABELS_MAP


class vLLMCheck(OpenMetricsBaseCheckV2):
    DEFAULT_METRIC_LIMIT = 0
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'vllm'

    def get_default_config(self):
        metrics = [METRIC_MAP, RAY_METRIC_MAP]
        if is_affirmative(datadog_agent.get_config('gpu.enabled')):
            metrics.extend([GPU_METRIC_MAP, RAY_GPU_METRIC_MAP])

        return {
            'metrics': metrics,
            "rename_labels": RENAME_LABELS_MAP,
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self):
        endpoint = self.instance["openmetrics_endpoint"].replace("/metrics", "/version")
        try:
            response = self.http.get(endpoint)
            response.raise_for_status()
            data = response.json()
        except (HTTPClientError, ValueError) as e:
            self.log.debug("Could not retrieve vLLM version metadata: %s", e)
            return

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
            self.log.debug("Invalid vLLM version format: %s", version)

    def check(self, instance):
        super().check(instance)
        self._submit_version_metadata()
