# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.gitlab.config_models import ConfigMixin

from .common import get_gitlab_version
from .metrics import METRICS_MAP


class GitlabCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = CHECK_NAME = 'gitlab'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.metric_url = None
        self.gitlab_url = None
        self.token = None

        self.scraper_configs.clear()
        # Before scrapers are configured
        self.check_initializations.insert(-1, self.parse_config)

    def check(self, _):
        super().check(_)
        self._submit_version()

    def get_default_config(self):
        return {
            "metrics": [METRICS_MAP],
        }

    @AgentCheck.metadata_entrypoint
    def _submit_version(self):
        version = get_gitlab_version(self.http, self.log, self.gitlab_url, self.api_token)

        if version:
            self.log.debug("Set version %s for GitLab", version)
            self.set_metadata("version", version)

    def parse_config(self):
        if not self.config.prometheus_url and self.config.prometheus_endpoint:
            self.config.prometheus_url = self.config.prometheus_endpoint

        self.gitlab_url = self.config.gitlab_url
        self.api_token = self.config.api_token
        self.prometheus_url = self.config.prometheus_url

    def configure_scrapers(self):
        config = copy.deepcopy(self.instance)

        config['openmetrics_endpoint'] = self.prometheus_url

        self.scraper_configs.clear()
        self.scraper_configs.append(config)

        super().configure_scrapers()
