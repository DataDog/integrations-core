# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base.checks.openmetrics.v2.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.kuma.metrics import METRIC_MAP, RENAME_LABELS_MAP


class KumaOpenMetricsScraper(OpenMetricsScraper):
    def __init__(self, check, config):
        super().__init__(check, config)

    def consume_metrics(self, runtime_data):
        metrics = super().consume_metrics(runtime_data)
        for metric in metrics:
            yield KumaOpenMetricsScraper.inject_code_class(metric)

    @staticmethod
    def inject_code_class(metric):
        # Patch all samples to add the code_class tag if 'code' is a 3-digit HTTP code
        for sample in metric.samples:
            if (code := sample.labels.get('code')) and isinstance(code, str) and len(code) == 3 and code.isdigit():
                sample.labels['code_class'] = f"{code[0]}XX"
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
            "share_labels": {"cp_info": {"labels": ["instance_id", "version"]}},
        }

    def create_scraper(self, config):
        return KumaOpenMetricsScraper(self, self.get_config_with_defaults(config))
