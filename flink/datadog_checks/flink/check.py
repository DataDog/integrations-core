# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import COUNTER_METRICS, METRIC_MAP


class FlinkCheck(OpenMetricsBaseCheckV2):
    """
    Collects Flink metrics by scraping the OpenMetrics/Prometheus endpoint
    exposed by Flink's `flink-metrics-prometheus` reporter.

    This is an alternative to configuring Flink's native Datadog HTTP
    Reporter; see the README for guidance on which collection mode to use.
    """

    __NAMESPACE__ = 'flink'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.append(self._configure_counter_transformers)

    def get_default_config(self):
        # Flink's Prometheus reporter labels every series with `host` to
        # identify the source JobManager/TaskManager. That label collides
        # with Datadog's reserved hostname tag, so we promote it to the
        # metric's hostname and exclude it from the tag set.
        return {
            'hostname_label': 'host',
            'exclude_labels': ['host'],
            # Counters are handled separately below: Flink's Prometheus reporter
            # always describes them as `# TYPE ... gauge`, so the default
            # (payload-trusting) transform would submit them as gauges.
            'metrics': [{k: v for k, v in METRIC_MAP.items() if k not in COUNTER_METRICS}],
        }

    def _configure_counter_transformers(self):
        # Registered as a custom transformer (rather than a `metrics` config entry)
        # because forcing OpenMetricsBaseCheckV2's built-in `counter` type would
        # append a `.count` suffix to the metric name, breaking parity with the
        # names Flink's legacy DatadogHttpReporterFactory-based reporter already
        # uses. Fully anchored: e.g. `numRecordsIn` is a substring of
        # `numRecordsInPerSecond`, which must stay a gauge.
        pattern = r'^(?:{})$'.format('|'.join(re.escape(name) for name in COUNTER_METRICS))
        for scraper in self.scrapers.values():
            scraper.metric_transformer.add_custom_transformer(pattern, self._transform_counter, pattern=True)

    def _transform_counter(self, metric, sample_data, runtime_data):
        metric_name = METRIC_MAP[metric.name]
        flush_first_value = runtime_data['flush_first_value']
        for sample, tags, hostname in sample_data:
            self.monotonic_count(
                metric_name, sample.value, tags=tags, hostname=hostname, flush_first_value=flush_first_value
            )
