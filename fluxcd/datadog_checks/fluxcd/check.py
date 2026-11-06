# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.fluxcd.config_models import ConfigMixin
from datadog_checks.fluxcd.metrics import KSM_METRICS, METRIC_MAP


class FluxcdCheck(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = "fluxcd"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def _parse_config(self):
        ksm_endpoint = self.instance.get("kube_state_metrics_endpoint")
        if ksm_endpoint:
            self.scraper_configs.append(
                {**self.instance, "openmetrics_endpoint": ksm_endpoint, "metrics": [KSM_METRICS]}
            )

    def get_default_config(self):
        return {"metrics": [METRIC_MAP]}
