# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base.checks.openmetrics import OpenMetricsBaseCheck

from .metrics import METRIC_MAP, TYPE_OVERRIDES


class LinkerdCheck(OpenMetricsBaseCheck):
    """
    Collect linkerd metrics from Prometheus
    """

    DEFAULT_METRIC_LIMIT = 0
    HEALTH_METRIC = 'linkerd.prometheus.health'

    def __init__(self, name, init_config, instances):
        labels_mapper = {'rt': 'linkerd_router', 'client': 'linkerd_client', 'service': 'linkerd_service'}

        default_config = {
            'linkerd': {'labels_mapper': labels_mapper, 'metrics': [METRIC_MAP], 'type_overrides': TYPE_OVERRIDES}
        }
        super(LinkerdCheck, self).__init__(
            name, init_config, instances, default_instances=default_config, default_namespace='linkerd'
        )

    def process(self, scraper_config, metric_transformers=None):
        # Override the process method to send the health metric, as service checks can be disabled.
        endpoint = scraper_config.get('prometheus_url')
        tags = ['endpoint:{}'.format(endpoint)]
        tags.extend(scraper_config['custom_tags'])
        try:
            super(LinkerdCheck, self).process(scraper_config, metric_transformers=metric_transformers)
        except Exception:
            self.gauge(self.HEALTH_METRIC, 1, tags=tags)
            raise
        else:
            self.gauge(self.HEALTH_METRIC, 0, tags=tags)
