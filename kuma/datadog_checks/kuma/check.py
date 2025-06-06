# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap
from typing import Any  # noqa: F401

from datadog_checks.base.checks.openmetrics.v2.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.kuma.metrics import METRIC_MAP, RENAME_LABELS_MAP


class KumaOpenMetricsScraper(OpenMetricsScraper):
    def __init__(self, check, config):
        super().__init__(check, config)

    def consume_metrics_w_target_info(self, runtime_data):
        metrics = super().consume_metrics_w_target_info(runtime_data)
        for metric in metrics:
            yield KumaOpenMetricsScraper.inject_code_class(metric)

    @staticmethod
    def inject_code_class(metric):
        # Patch all samples to add the code_class tag if 'code' is a 3-digit HTTP code
        for sample in metric.samples:
            code = sample.labels.get('code')
            if code and isinstance(code, str) and len(code) == 3 and code.isdigit():
                code_class = f"{code[0]}XX"
                sample.labels['code_class'] = code_class
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
            "target_info": True,
            "target_info_metric_name": "cp_info",
        }

    def get_config_with_defaults(self, config):
        merged = ChainMap(config, self.get_default_config())
        # Only set histogram_buckets_as_distributions to True if not set by the user (None or missing)
        if merged.get('histogram_buckets_as_distributions') is None:
            merged = merged.new_child({'histogram_buckets_as_distributions': True})
        return merged

    def create_scraper(self, config):
        return KumaOpenMetricsScraper(self, self.get_config_with_defaults(config))
