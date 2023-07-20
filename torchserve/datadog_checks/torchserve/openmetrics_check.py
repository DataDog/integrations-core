# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.torchserve.config_models import ConfigMixin
from datadog_checks.torchserve.metrics import OPENMETRICS_METRIC_MAP


class TorchserveOpenMetricsCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'torchserve.openmetrics'
    DEFAULT_METRIC_LIMIT = 0

    def create_scraper(self, config):
        # All metrics are prefixed with their endpoint.
        # When default scraper (`OpenMetricsScraper`) is used, the service checks will have duplicates,
        # for eg. `torchserve.openmetrics.health` would be `torchserve.openmetrics.openmetrics.health`
        # There isn't a mechanism to dynamically override service check names,
        # hence `TorchServeOpenMetricsScraper` is derived from `OpenMetricsScraper`
        # to override `SERVICE_CHECK_HEALTH` value
        scraper = OpenMetricsScraper(self, self.get_config_with_defaults(config))
        scraper.SERVICE_CHECK_HEALTH = "health"
        return scraper

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
