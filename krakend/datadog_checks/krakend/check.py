# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import ChainMap
from typing import TYPE_CHECKING

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.base.types import InstanceType

from .metrics import METRICS_MAP, RENAME_LABELS_MAP

if TYPE_CHECKING:
    from typing import Mapping

    from prometheus_client.metrics_core import Metric

    from datadog_checks.base.checks.base import AgentCheck

HTTP_STATUS_CODE_TAG = "http_response_status_code"


class HttpCodeClassScraper(OpenMetricsScraper):
    def __init__(self, check: AgentCheck, config: Mapping):
        super().__init__(check, config)

    def consume_metrics_w_target_info(self, runtime_data: dict):
        metrics = super().consume_metrics(runtime_data)
        for metric in metrics:
            yield HttpCodeClassScraper.inject_code_class(metric)

    @staticmethod
    def inject_code_class(metric: Metric):
        # Patch all samples to add the code_class tag if 'code' is a 3-digit HTTP code
        for sample in metric.samples:
            if (
                (code := sample.labels.get(HTTP_STATUS_CODE_TAG))
                and isinstance(code, str)
                and len(code) == 3
                and code.isdigit()
            ):
                sample.labels['code_class'] = f"{code[0]}XX"

        return metric


class KrakendCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "krakend.api"
    DEFAULT_METRIC_LIMIT = 0

    def create_scraper(self, config: InstanceType):
        return HttpCodeClassScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config: InstanceType) -> Mapping:
        # If the user does not provide a value for go_metrics or process_metrics,
        # assume they want whatever behvaior has been set in KrakenD
        go_metrics = config.get("go_metrics", True)
        process_metrics = config.get("process_metrics", True)

        def accept_metric(metric_name):
            if metric_name.startswith("go_") and not go_metrics:
                return False
            if metric_name.startswith("process_") and not process_metrics:
                return False
            return True

        metrics = {
            original_name: new_name for original_name, new_name in METRICS_MAP.items() if accept_metric(original_name)
        }

        rename_labels = RENAME_LABELS_MAP.copy()
        if go_metrics:
            # Only rename the version label if go_metrics are enabled
            # This is explained in the tile
            rename_labels["version"] = "go_version"

        default_configs = {
            "metrics": [metrics],
            "rename_labels": rename_labels,
            "target_info": True,
        }

        return ChainMap(config, default_configs)
