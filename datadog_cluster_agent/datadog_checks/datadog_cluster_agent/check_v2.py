# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .config_models import ConfigMixin
from .metrics import METRICS_MAP, construct_metrics_config


class DatadogClusterAgentCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'datadog.cluster_agent'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            'openmetrics_endpoint': 'http://localhost:5000/metrics',
            'metrics': construct_metrics_config(METRICS_MAP, {}),
            'share_labels': {
                'leader_election_is_leader': {
                    'labels': ['is_leader'],
                    'values': [1]
                }
            },
            'histogram_buckets_as_distributions': True,
        }

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
