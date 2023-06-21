# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.torchserve.config_models import ConfigMixin
from datadog_checks.torchserve.metrics import OPENMETRICS_METRIC_MAP


class TorchServeOpenMetricsScraper(OpenMetricsScraper):
    SERVICE_CHECK_HEALTH = "health"


class TorchserveOpenMetricsCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'torchserve.openmetrics'
    DEFAULT_METRIC_LIMIT = 0

    def create_scraper(self, config):
        # We prefix all the metrics with their endpoint. If we use the default scraper, we will emit the service check
        # `torchserve.openmetrics.openmetrics.health`. It seems we can't override it dynamically.
        # I prefer overriding the service check over manually adding `openmetrics.` to every single metrics.
        return TorchServeOpenMetricsScraper(self, self.get_config_with_defaults(config))

    def get_default_config(self):
        return {
            "metrics": [OPENMETRICS_METRIC_MAP],
            # TorchServe is not consistent with the labels, sometimes it's UpperCamelCase, sometimes snake_case
            "exclude_labels": ["hostname", "Hostname"],
            # Let's keep everything snake_case
            "rename_labels": {
                "Level": "level",
                "ModelName": "model_name",
                "WorkerName": "worker_name",
            },
        }
