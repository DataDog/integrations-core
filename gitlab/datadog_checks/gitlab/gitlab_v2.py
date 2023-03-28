# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

import requests

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.gitlab.config_models import ConfigMixin

from ..base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper
from .common import get_gitlab_version, get_tags
from .metrics import METRICS_MAP, construct_metrics_config


class GitlabCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    ALLOWED_SERVICE_CHECKS = ['readiness', 'liveness', 'health']
    __NAMESPACE__ = 'gitlab'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self.parse_config)

    def check(self, _):
        super().check(_)

        # Service check to check GitLab's health endpoints
        if self.config.gitlab_url is not None:
            for check_type in self.ALLOWED_SERVICE_CHECKS:
                self._check_health_endpoint(check_type)
        else:
            self.log.debug("gitlab_url not configured, service checks are skipped")

        self._submit_version()

    def get_default_config(self):
        return {
            "metrics": construct_metrics_config(METRICS_MAP),
        }

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, ChainMap({"tags": self._tags}, config, self.get_default_config()))

    @AgentCheck.metadata_entrypoint
    def _submit_version(self):
        if version := get_gitlab_version(self.http, self.log, self.config.gitlab_url, self.config.api_token):
            self.log.debug("Set version %s for GitLab", version)
            self.set_metadata("version", version)

    def _check_health_endpoint(self, check_type):
        # These define which endpoint is hit and which type of check is actually performed
        check_url = f'{self.config.gitlab_url}/-/{check_type}'

        try:
            self.log.debug("checking %s against %s", check_type, check_url)
            r = self.http.get(check_url)
            if r.status_code != 200:
                self.service_check(
                    check_type,
                    OpenMetricsBaseCheckV2.CRITICAL,
                    message=f"Got {r.status_code} when hitting {check_url}",
                    tags=self._tags,
                )
        except requests.exceptions.Timeout:
            self.service_check(
                check_type,
                OpenMetricsBaseCheckV2.CRITICAL,
                message=f"Timeout when hitting {check_url}",
                tags=self._tags,
            )
        except Exception as e:
            self.service_check(
                check_type,
                OpenMetricsBaseCheckV2.CRITICAL,
                message=f"Error hitting {check_url}. Error: {e}",
                tags=self._tags,
            )
        else:
            self.service_check(check_type, OpenMetricsBaseCheckV2.OK, self._tags)

        self.log.debug("GitLab check `%s` done", check_type)

    def parse_config(self):
        self._tags = get_tags(self.instance)

        if self.is_metadata_collection_enabled() and not self.instance.get("api_token"):
            self.warning("GitLab token not found; please add one in your config to enable version metadata collection.")
