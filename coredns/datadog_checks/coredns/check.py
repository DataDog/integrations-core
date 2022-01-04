from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .common import DEFAULT_METRICS, GO_METRICS


class CoreDNS(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'coredns'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        metrics = [DEFAULT_METRICS, GO_METRICS]
        return {'metrics': metrics}

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
