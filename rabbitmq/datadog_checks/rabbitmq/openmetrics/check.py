import re

from datadog_checks.base import OpenMetricsBaseCheckV2

from . import metrics


class RabbitMQOpenMetrics(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "rabbitmq"

    def configure_scrapers(self):
        base_url = self.instance['prometheus_plugin']['url']
        self.scraper_configs.clear()
        endpoints = []
        if self.instance['prometheus_plugin'].get('include_aggregated_endpoint', False):
            endpoints.append(
                (
                    "/metrics",
                    {
                        'metrics': [metrics.RENAME_RABBITMQ_TO_DATADOG],
                    },
                )
            )
        unagg_ep = self.instance['prometheus_plugin'].get('unaggregated_endpoint', '')
        if 'detailed' in unagg_ep:
            endpoints.append(
                (
                    f"/metrics/{unagg_ep}",
                    {
                        "metrics": [
                            {
                                (
                                    re.sub("^rabbitmq_", "rabbitmq_detailed_", k)
                                    if k not in ['rabbitmq_build_info', 'rabbitmq_identity_info']
                                    else k
                                ): v
                                for k, v in metrics.RENAME_RABBITMQ_TO_DATADOG.items()
                            }
                        ],
                    },
                )
            )
        for ep, ep_config in endpoints:
            self.scraper_configs.append(
                {
                    **self.instance,
                    'openmetrics_endpoint': base_url + ep,
                    **ep_config,
                }
            )
        super().configure_scrapers()
