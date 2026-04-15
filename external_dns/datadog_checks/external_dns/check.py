# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .metrics import METRIC_MAP, construct_metrics_config


class ExternalDNS(OpenMetricsBaseCheckV2):
    """
    Collect external DNS metrics from its Prometheus endpoint using OpenMetricsBaseCheckV2.
    """

    __NAMESPACE__ = 'external_dns'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'metrics': construct_metrics_config(METRIC_MAP),
            # Rename 'host' label to 'http_host' since 'host' is a reserved Datadog tag
            'rename_labels': {'host': 'http_host'},
        }

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
