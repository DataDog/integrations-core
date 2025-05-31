# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401
from collections import ChainMap

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.kuma.metrics import METRIC_MAP, RENAME_LABELS_MAP
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper

class KumaOpenMetricsScraper(OpenMetricsScraper):
    def __init__(self, check, config):
        super().__init__(check, config)
        self._instance_id = None

    def consume_metrics(self, runtime_data):
        # First, find cp_info and extract instance_id
        metrics = list(super().consume_metrics(runtime_data))
        for metric in metrics:
            if metric.name == 'cp_info':
                for sample in metric.samples:
                    if 'instance_id' in sample.labels:
                        self._instance_id = sample.labels['instance_id']
                        break
        # Now yield metrics, injecting instance_id as a tag
        for metric in metrics:
            yield self._inject_instance_id(metric)

    def _inject_instance_id(self, metric):
        if self._instance_id is None or metric.name == 'cp_info':
            return metric
        # Patch all samples to add the instance_id tag
        for sample in metric.samples:
            sample.labels['instance_id'] = self._instance_id
        return metric

class KumaCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "kuma"

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):
        super(KumaCheck, self).__init__(name, init_config, instances)

    def get_default_config(self):
        return {
            "metrics": [METRIC_MAP],
            "rename_labels": RENAME_LABELS_MAP,
        }

    def get_config_with_defaults(self, config):
        merged = ChainMap(config, self.get_default_config())
        # Only set histogram_buckets_as_distributions to True if not set by the user (None or missing)
        if merged.get('histogram_buckets_as_distributions') is None:
            merged = merged.new_child({'histogram_buckets_as_distributions': True})
        return merged

    def create_scraper(self, config):
        return KumaOpenMetricsScraper(self, self.get_config_with_defaults(config))