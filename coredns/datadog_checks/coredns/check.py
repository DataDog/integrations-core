# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .metrics import METRIC_MAP, construct_metrics_config


class CoreDNS(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'coredns'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        return {'metrics': construct_metrics_config(METRIC_MAP)}

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
