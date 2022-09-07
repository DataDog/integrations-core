# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy
from urllib.parse import urlparse

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative

from .metrics import METRIC_MAP, SUMMARY_METRICS, construct_metrics_config


class TeamCityCheckV2(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'teamcity'
    DEFAULT_METRIC_LIMIT = 0

    DEFAULT_METRICS_URL = "/{}/app/metrics"
    EXPERIMENTAL_METRICS_URL = "/{}/app/metrics?experimental=true"

    def __init__(self, name, init_config, instances):
        super(TeamCityCheckV2, self).__init__(name, init_config, instances)
        self.basic_http_auth = is_affirmative(self.instance.get('basic_http_authentication'))
        self.auth_type = 'httpAuth' if self.basic_http_auth else 'guestAuth'
        parsed_endpoint = urlparse(self.instance.get('server'))
        self.server_url = "{}://{}".format(parsed_endpoint.scheme, parsed_endpoint.netloc)
        self.metrics_endpoint = ''

        experimental_metrics = is_affirmative(self.instance.get('experimental_metrics', True))

        if experimental_metrics:
            self.metrics_endpoint = self.EXPERIMENTAL_METRICS_URL.format(self.auth_type)
        else:
            self.metrics_endpoint = self.DEFAULT_METRICS_URL.format(self.auth_type)

        self.scraper_configs.clear()
        self.check_initializations.append(self.configure_additional_transformers)

    def configure_scrapers(self):
        config = deepcopy(self.instance)
        config['openmetrics_endpoint'] = "{}{}".format(self.server_url, self.metrics_endpoint)
        config['metrics'] = construct_metrics_config(METRIC_MAP)
        self.scraper_configs.clear()
        self.scraper_configs.append(config)

        super().configure_scrapers()

    def configure_transformer_summary_metric(self, new_name):
        gauge_method = self.gauge
        monotonic_count_method = self.monotonic_count
        sum_metric = f'{new_name}.total'
        count_metric = f'{new_name}.count'
        quantile_metric = f'{new_name}.quantile'

        def transform(metric, sample_data, runtime_data):
            flush_first_value = runtime_data['flush_first_value']
            for sample, tags, hostname in sample_data:
                if sample.name.endswith('_total'):
                    monotonic_count_method(
                        sum_metric, sample.value, tags=tags, hostname=hostname, flush_first_value=flush_first_value
                    )
                if sample.name.endswith('_count'):
                    monotonic_count_method(
                        count_metric, sample.value, tags=tags, hostname=hostname, flush_first_value=flush_first_value
                    )
                elif sample.name == metric.name:
                    gauge_method(quantile_metric, sample.value, tags=tags, hostname=hostname)

        return transform

    def configure_additional_transformers(self):
        if not self.scrapers:
            return
        for raw_metric_name, new_metric_name in SUMMARY_METRICS.items():
            self.scrapers[
                "{}{}".format(self.server_url, self.metrics_endpoint)
            ].metric_transformer.add_custom_transformer(
                raw_metric_name, self.configure_transformer_summary_metric(new_metric_name)
            )
