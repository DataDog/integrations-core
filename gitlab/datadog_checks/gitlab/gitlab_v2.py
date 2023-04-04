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
    READINESS_SERVICE_CHECKS = {
        'master_check': 'master',
        'db_check': 'database',
        'cache_check': 'cache',
        'db_load_balancing_check': 'database_load_balancing',
        'queues_check': 'queues',
        'rate_limiting_check': 'rate_limiting',
        'repository_cache_check': 'repository_cache',
        'cluster_rate_limiting_check': 'cluster_rate_limiting',
        'sessions_check': 'sessions',
        'shared_state_check': 'shared_state',
        'trace_chunks_check': 'trace_chunks',
        'gitaly_check': 'gitaly',
        'redis_check': 'redis',
    }
    __NAMESPACE__ = 'gitlab'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.ALLOWED_SERVICE_CHECKS = {
            'readiness': {
                'response_handler': self.parse_readiness_service_checks,
                'extra_params': '?all=1',
            },
            'liveness': {},
            'health': {},
        }

        self.check_initializations.appendleft(self.parse_config)

    def check(self, _):
        try:
            super().check(_)
        finally:
            # Service check to check GitLab's health endpoints
            if self.config.gitlab_url is not None:
                for check_type, options in self.ALLOWED_SERVICE_CHECKS.items():
                    self._check_health_endpoint(check_type, **options)
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

    def _check_health_endpoint(self, check_type, extra_params=None, response_handler=None):
        # These define which endpoint is hit and which type of check is actually performed
        check_url = f'{self.config.gitlab_url}/-/{check_type}'

        if extra_params:
            check_url = f'{check_url}{extra_params}'

        try:
            self.log.debug("checking %s against %s", check_type, check_url)
            r = self.http.get(check_url)

            if response_handler:
                response_handler(r)

            if r.status_code != 200:
                self.service_check(
                    check_type,
                    OpenMetricsBaseCheckV2.CRITICAL,
                    message=f"Got {r.status_code} when hitting {check_url}",
                    tags=self._tags,
                )
            else:
                self.service_check(check_type, OpenMetricsBaseCheckV2.OK, self._tags)
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

        self.log.debug("GitLab check `%s` done", check_type)

    def parse_config(self):
        self._tags = get_tags(self.instance)

        if self.is_metadata_collection_enabled() and not self.instance.get("api_token"):
            self.warning("GitLab token not found; please add one in your config to enable version metadata collection.")

    def parse_readiness_service_checks(self, response):
        self.log.debug("Parsing readiness output")
        service_checks_sent = set()

        if response is not None:
            for key, value in response.json().items():
                self.log.trace("Reading key %s", key)

                # Format:
                # {
                #     "master_check": [
                #         {
                #             "status": "ok"
                #         }
                #     ]
                # }
                if (
                    not key.endswith("_check")
                    or not isinstance(value, list)
                    or len(value) == 0
                    or not value[0].get("status")
                ):
                    continue

                if check := self.READINESS_SERVICE_CHECKS.get(key):
                    gitlab_status = value[0].get("status")

                    if gitlab_status == "ok":
                        self.service_check(f"readiness.{check}", OpenMetricsBaseCheckV2.OK, self._tags)
                    elif gitlab_status is None:
                        self.service_check(f"readiness.{check}", OpenMetricsBaseCheckV2.UNKNOWN, self._tags)
                    else:
                        self.service_check(f"readiness.{check}", OpenMetricsBaseCheckV2.CRITICAL, self._tags)

                    service_checks_sent.add(key)
                else:
                    self.log.debug("Unknown service check %s", check)

        # Handle all the declared checks that we did not get from the endpoint
        for missing_service_check in set(self.READINESS_SERVICE_CHECKS.keys()).difference(service_checks_sent):
            self.service_check(
                f"readiness.{self.READINESS_SERVICE_CHECKS[missing_service_check]}",
                OpenMetricsBaseCheckV2.UNKNOWN,
                self._tags,
            )
