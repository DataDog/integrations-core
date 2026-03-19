# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.temporal.config_models import ConfigMixin
from datadog_checks.temporal.metrics import METRIC_MAP, SECONDS_TO_MILLISECONDS_METRICS

SECONDS_TO_MS = 1000


class TemporalCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'temporal.server'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
        }

    def configure_scrapers(self):
        super().configure_scrapers()

        scraper = self.scrapers[self.instance['openmetrics_endpoint']]

        scraper.metric_transformer.add_custom_transformer(
            "build_information",
            self._transform_build_information,
        )

        # Add transformer for metrics that report in seconds but need to be converted to milliseconds
        for raw_metric_name, dd_metric_name in SECONDS_TO_MILLISECONDS_METRICS.items():
            scraper.metric_transformer.add_custom_transformer(
                raw_metric_name,
                self._create_seconds_to_ms_histogram_transformer(dd_metric_name),
            )

    def _create_seconds_to_ms_histogram_transformer(self, metric_name: str):
        """
        Creates a transformer that converts histogram sum values from seconds to milliseconds.

        Temporal emits timing metrics with a `_milliseconds` suffix by default (older versions
        omit the suffix but still use milliseconds). Users can configure Temporal with
        `recordTimerInSeconds` to emit metrics with a `_seconds` suffix instead. To maintain
        compatibility with existing dashboards and monitors that expect millisecond values,
        we convert the sum from seconds to milliseconds.
        """
        monotonic_count = self.monotonic_count

        def histogram_seconds_to_ms(metric, sample_data, runtime_data):
            flush_first_value = runtime_data['flush_first_value']

            for sample, tags, hostname in sample_data:
                sample_name = sample.name

                # Skip infinity buckets (similar to count)
                if sample_name.endswith('_bucket') and sample.labels.get('le', '').endswith('inf'):
                    continue

                # Only sum needs conversion
                if sample_name.endswith('_sum'):
                    suffix, value = 'sum', sample.value * SECONDS_TO_MS
                elif sample_name.endswith('_count'):
                    suffix, value = 'count', sample.value
                elif sample_name.endswith('_bucket'):
                    suffix, value = 'bucket', sample.value
                else:
                    continue

                monotonic_count(
                    f'{metric_name}.{suffix}',
                    value,
                    tags=tags,
                    hostname=hostname,
                    flush_first_value=flush_first_value,
                )

        return histogram_seconds_to_ms

    def _transform_build_information(self, metric, sample_data, runtime_data):
        for sample, *_ in sample_data:
            self.set_metadata('version', sample.labels['build_version'].replace('_', '.'))
