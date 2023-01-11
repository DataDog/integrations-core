from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRICS_RENAMES


class RabbitMQOpenMetrics(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "rabbitmq"

    def configure_scrapers(self):
        self.instance['openmetrics_endpoint'] = self.instance['prometheus_plugin']['url'] + "/metrics"
        self.scraper_configs.clear()
        self.scraper_configs.append({**self.instance, 'metrics': [METRICS_RENAMES]})
        super().configure_scrapers()
