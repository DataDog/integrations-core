# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.gitlab.config_models import ConfigMixin

from .common import get_gitlab_version


class GitlabCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = CHECK_NAME = 'gitlab'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        # Should be done before `load_configuration_models`
        self.check_initializations.appendleft(self.remap_options)

    def check(self, _):
        # super().check(_)
        self._submit_version()

    def get_default_config(self):
        return {
            "metrics": [],
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version(self):
        if version := get_gitlab_version(self.http, self.log, self.config.gitlab_url, self.config.api_token):
            self.log.debug("Set version %s for GitLab", version)
            self.set_metadata("version", version)

    def remap_options(self):
        if not self.instance.get("prometheus_url") and self.instance.get("prometheus_endpoint"):
            self.warning(
                '`prometheus_endpoint` is deprecated and will be removed in a future release. '
                'Please use `prometheus_url` instead.'
            )
            self.instance["prometheus_url"] = self.instance["prometheus_endpoint"]

        if self.instance.get("openmetrics_endpoint") and self.instance.get("prometheus_url"):
            self.warning(
                "`openmetrics_endpoint` and `prometheus_url` are both defined using OpenMetricsV2. "
                "Only `openmetrics_endpoint` will be used"
            )

        if not self.instance.get("openmetrics_endpoint") and self.instance.get("prometheus_url"):
            self.instance['openmetrics_endpoint'] = self.instance.get("prometheus_url")
