# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .config_models import ConfigMixin
from .metrics import METRIC_MAP, construct_metrics_config


class CockroachdbCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'cockroachdb'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.check_initializations.append(self.configure_additional_transformers)

    def get_default_config(self):
        return {
            'openmetrics_endpoint': 'http://localhost:8080/_status/vars',
            'metrics': construct_metrics_config(METRIC_MAP, {}),
        }

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def configure_transformer_build_timestamp(self, metric_name):
        def build_timestamp_transformer(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                self.gauge(metric_name, sample.value, tags=tags, hostname=hostname)
                self.set_metadata('version', sample.labels['tag'])

        return build_timestamp_transformer

    def configure_additional_transformers(self):
        self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
            'build_timestamp', self.configure_transformer_build_timestamp('build.timestamp')
        )
