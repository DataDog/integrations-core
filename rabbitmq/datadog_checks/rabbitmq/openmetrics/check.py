# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from . import metrics


class RabbitMQOpenMetrics(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "rabbitmq"

    DEFAULT_METRIC_LIMIT = 0

    def configure_scrapers(self):
        base_url = self.instance['prometheus_plugin']['url']
        self.scraper_configs.clear()
        endpoints = []
        unagg_ep = self.instance['prometheus_plugin'].get('unaggregated_endpoint', '')
        exclude_from_agg = set()
        if unagg_ep:
            renames, exclude_from_agg = metrics.unaggregated_renames_and_exclusions(unagg_ep)
            endpoints.append((f"/metrics/{unagg_ep}", {"metrics": [renames]}))
        if self.instance['prometheus_plugin'].get('include_aggregated_endpoint', True):
            endpoints.append(("/metrics", {'metrics': [metrics.aggregated_renames(exclude_from_agg)]}))
        for ep, ep_config in endpoints:
            self.scraper_configs.append(
                {
                    **self.instance,
                    'openmetrics_endpoint': base_url + ep,
                    **ep_config,
                    # Due to performance considerations, shared labels may not be applied to all metrics in the very
                    # first run of the check after an agent (re)start. This is not a problem for subsequent runs
                    # of the check as long as `cache_shared_labels` is True.
                    'share_labels': {'rabbitmq_identity_info': True},
                }
            )
        super().configure_scrapers()
