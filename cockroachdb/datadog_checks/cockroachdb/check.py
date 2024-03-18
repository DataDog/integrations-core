# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper

from .config_models import ConfigMixin
from .metrics import METRIC_MAP, OMV2_METRIC_MAP, construct_metrics_config

METRIC_WITH_LABEL_NAME = {
    r'^distsender_rpc_err_errordetailtype_(\d+)_$': {
        'label_name': 'error_type',
        'metric_type': 'monotonic_count',
        'new_name': 'distsender.rpc.err.errordetailtype.count',
    },
}


class CockroachdbCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'cockroachdb'

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self.check_initializations.append(self.configure_additional_transformers)

    def get_default_config(self):
        return {
            'openmetrics_endpoint': 'http://localhost:8080/_status/vars',
            'metrics': construct_metrics_config(METRIC_MAP | OMV2_METRIC_MAP, {}),
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

        for metric, data in METRIC_WITH_LABEL_NAME.items():
            self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer.add_custom_transformer(
                metric, self.configure_transformer_label_in_name(metric, **data), pattern=True
            )

    def configure_transformer_label_in_name(self, metric_pattern, new_name, label_name, metric_type):
        method = getattr(self, metric_type)
        cached_patterns = defaultdict(lambda: re.compile(metric_pattern))

        def transform(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                parsed_sample_name = sample.name
                if sample.name.endswith("_total"):
                    parsed_sample_name = re.match("(.*)_total$", sample.name).groups()[0]
                label_value = cached_patterns[metric_pattern].match(parsed_sample_name).groups()[0]
                tags.append('{}:{}'.format(label_name, label_value))
                method(new_name, sample.value, tags=tags, hostname=hostname)

        return transform
