# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2

from .config_models import ConfigMixin
from .metrics import COUNTER_METRICS, HISTOGRAM_METRICS, METRIC_MAP, QUANTILE_SUFFIXES


class HivemqCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    """
    Collect HiveMQ metrics from the HiveMQ Prometheus extension
    (https://github.com/hivemq/hivemq-prometheus-extension), as an alternative to
    this integration's default JMX collection. The Agent only loads this check when
    `use_openmetrics: true` is set on the instance; otherwise JMXFetch handles
    collection directly and this class is never instantiated.
    """

    __NAMESPACE__ = 'hivemq'
    DEFAULT_METRIC_LIMIT = 0

    def get_default_config(self):
        return {'metrics': [METRIC_MAP]}

    def configure_scrapers(self):
        super().configure_scrapers()

        metric_transformer = self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer
        for wire_name in COUNTER_METRICS:
            metric_transformer.add_custom_transformer(wire_name, self._transform_counter)
        for wire_name in HISTOGRAM_METRICS:
            metric_transformer.add_custom_transformer(wire_name, self._transform_histogram)

    def _transform_counter(self, metric, sample_data, _runtime_data):
        """
        HiveMQ's Dropwizard Counters are exposed as Prometheus gauges (not counters --
        see metrics.py), carrying the raw count. Submit them as a monotonic_count to
        match JMX's `Count` attribute handling, using our own naming: the native
        `counter` metric type always appends `.count`, which would double up with our
        target names that already end in `.count`.
        """
        target_name = COUNTER_METRICS[metric.name]

        for sample, tags, hostname in sample_data:
            self.monotonic_count(target_name, sample.value, tags=tags, hostname=hostname)

    def _transform_histogram(self, metric, sample_data, _runtime_data):
        """
        HiveMQ's histograms are exposed as Prometheus summaries (quantiles + a count
        sample). Split them back into the discrete `<name>.<Nth>_percentile` gauges
        and `<name>.count` monotonic_count already used by JMX collection (see
        data/metrics.yaml), instead of the native tag-based summary shape, so
        dashboards/monitors work the same way regardless of collection method.

        Note: unlike JMX, this does not have Max/Mean/Min/StdDev/SnapshotSize --
        DropwizardExports does not expose them (see metrics.py for details).
        """
        base_name = HISTOGRAM_METRICS[metric.name]

        for sample, tags, hostname in sample_data:
            if sample.name.endswith('_count'):
                self.monotonic_count(f'{base_name}.count', sample.value, tags=tags, hostname=hostname)
            elif sample.name == metric.name:
                quantile_tag = next((tag for tag in tags if tag.startswith('quantile:')), None)
                if quantile_tag is None:
                    continue

                suffix = QUANTILE_SUFFIXES.get(quantile_tag.split(':', 1)[1])
                if suffix is None:
                    continue

                remaining_tags = [tag for tag in tags if tag != quantile_tag]
                self.gauge(f'{base_name}.{suffix}', sample.value, tags=remaining_tags, hostname=hostname)
