# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheckV2  # noqa: F401

from .config_models import ConfigMixin
from .metrics import RENAME_LABELS_MAP, STORAGE_API_METRICS, SUPABASE_METRICS

(
    PRIVILEGED_METRICS_NAMESPACE,
    STORAGE_API_METRICS_NAMESPACE,
) = [
    'supabase',
    'supabase.storage_api',
]


class SupabaseCheck(OpenMetricsBaseCheckV2, ConfigMixin):

    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances=None):
        super(SupabaseCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self.parse_config)
        # Use self.instance to read the check configuration
        # self.url = self.instance.get("url")

    def parse_config(self):
        self.scraper_configs = []
        privileged_metrics_endpoint = self.instance.get("privileged_metrics_endpoint")
        storage_api_endpoint = self.instance.get("storage_api_endpoint")

        if not privileged_metrics_endpoint and not storage_api_endpoint:
            raise ConfigurationError(
                "Must specify at least one of the following:" "`privileged_metrics_endpoint` or `storage_api_endpoint`."
            )

        if privileged_metrics_endpoint:
            self.scraper_configs.append(
                self.generate_config(privileged_metrics_endpoint, PRIVILEGED_METRICS_NAMESPACE, SUPABASE_METRICS)
            )
        if storage_api_endpoint:
            self.scraper_configs.append(
                self.generate_config(storage_api_endpoint, STORAGE_API_METRICS_NAMESPACE, STORAGE_API_METRICS)
            )

    def generate_config(self, endpoint, namespace, metrics):
        config = {
            'openmetrics_endpoint': endpoint,
            'metrics': metrics,
            'namespace': namespace,
            'rename_labels': RENAME_LABELS_MAP,
        }
        config.update(self.instance)
        return config
