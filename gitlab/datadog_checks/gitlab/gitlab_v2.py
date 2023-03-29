# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
from urllib.parse import urlparse

import requests

from datadog_checks.base import AgentCheck, OpenMetricsBaseCheckV2
from datadog_checks.gitlab.config_models import ConfigMixin

from .common import get_gitlab_version, get_tags
from .metrics import METRICS_MAP
from ..base.errors import CheckException


class GitlabCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    ALLOWED_SERVICE_CHECKS = ['readiness', 'liveness', 'health']
    __NAMESPACE__ = CHECK_NAME = 'gitlab'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.metric_url = None
        self.gitlab_url = None
        self.token = None

        self.scraper_configs.clear()
        # Should be done before `load_configuration_models`
        self.check_initializations.appendleft(self.remap_options)
        # Before scrapers are configured
        self.check_initializations.insert(-1, self.parse_config)

    def check(self, _):
        # super().check(_)

        # Service check to check GitLab's health endpoints
        if self.gitlab_url is not None:
            for check_type in self.ALLOWED_SERVICE_CHECKS:
                self._check_health_endpoint(check_type)
        else:
            self.log.debug("gitlab_url not configured, service checks are skipped")

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

    def _check_health_endpoint(self, check_type):
        # These define which endpoint is hit and which type of check is actually performed
        check_url = f'{self.gitlab_url}/-/{check_type}'

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
                raise CheckException(f"Http status code {r.status_code} on check_url {check_url}")
            else:
                r.raise_for_status()
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

    def remap_options(self):
        if not self.instance.get("prometheus_url") and self.instance.get("prometheus_endpoint"):
            self.warning('`prometheus_endpoint` is deprecated and will be removed in a future release. '
                         'Please use `prometheus_url` instead.')
            self.instance["prometheus_url"] = self.instance["prometheus_endpoint"]

    def parse_config(self):
        self.gitlab_url = self.config.gitlab_url
        self.api_token = self.config.api_token
        self.prometheus_url = self.config.prometheus_url
        self._tags = get_tags(self.instance)

    def configure_scrapers(self):
        config = copy.deepcopy(self.instance)

        config['openmetrics_endpoint'] = self.prometheus_url

        self.scraper_configs.clear()
        self.scraper_configs.append(config)

        super().configure_scrapers()
