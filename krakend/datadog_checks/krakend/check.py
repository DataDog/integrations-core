# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.metrics_file import ConfigOptionTruthy, MetricsFile
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.base.types import InstanceType

from .metrics import RENAME_LABELS_MAP

if TYPE_CHECKING:
    from collections.abc import Mapping

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

    METRICS_FILES = [
        MetricsFile(Path("metrics/default.yaml")),
        MetricsFile(Path("metrics/go.yaml"), predicate=ConfigOptionTruthy("go_metrics")),
        MetricsFile(Path("metrics/process.yaml"), predicate=ConfigOptionTruthy("process_metrics")),
    ]

    def create_scraper(self, config: InstanceType):
        return HttpCodeClassScraper(self, self.get_config_with_defaults(config))

    def get_default_config(self):
        return {"target_info": True}

    def get_config_with_defaults(self, config: InstanceType) -> Mapping:
        result = super().get_config_with_defaults(config)

        go_metrics = config.get("go_metrics", True)

        rename_labels = RENAME_LABELS_MAP.copy()
        if go_metrics:
            # Only rename the version label if go_metrics are enabled
            # This is explained in the tile
            rename_labels["version"] = "go_version"

        result.maps[-1]["rename_labels"] = rename_labels

        return result
