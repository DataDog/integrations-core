# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .metrics import METRIC_MAP, TYPE_OVERRIDES, construct_metrics_config


class LinkerdCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'linkerd'

    DEFAULT_METRIC_LIMIT = 0

    def check(self, instance):
        # Override the check method to send the health metric, as service checks can be disabled.
        scraper = self.scrapers[self.instance['openmetrics_endpoint']]

        try:
            super().check(instance)
        except Exception:
            self.gauge(scraper.SERVICE_CHECK_HEALTH, 1, tags=scraper.static_tags)
            raise
        else:
            self.gauge(scraper.SERVICE_CHECK_HEALTH, 0, tags=scraper.static_tags)

    def get_default_config(self):
        return {
            'metrics': construct_metrics_config(METRIC_MAP, TYPE_OVERRIDES),
            'rename_labels': {'rt': 'linkerd_router', 'client': 'linkerd_client', 'service': 'linkerd_service'},
        }

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
