# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRICS_MAP


class KubevirtControllerCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "kubevirt_controller"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubevirtControllerCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        self.kubevirt_controller_healthz_endpoint = self.instance.get("kubevirt_controller_healthz_endpoint")

        try:
            self.log.debug("Checking health status at %s", self.kubevirt_controller_healthz_endpoint)
            response = self.http.get(self.kubevirt_controller_healthz_endpoint)
            response.raise_for_status()
            self.gauge("can_connect", 1, tags=[f"endpoint:{self.kubevirt_controller_healthz_endpoint}"])
        except Exception as e:
            self.log.error(
                "Cannot connect to KubeVirt Controller HTTP endpoint '%s': %s.\n",
                self.kubevirt_controller_healthz_endpoint,
                str(e),
            )
            self.gauge("can_connect", 0, tags=[f"endpoint:{self.kubevirt_controller_healthz_endpoint}"])
            raise

        super().check(_)

    def _parse_config(self):
        self.kubevirt_controller_metrics_endpoint = self.instance.get("kubevirt_controller_metrics_endpoint")
        self.kubevirt_controller_healthz_endpoint = self.instance.get("kubevirt_controller_healthz_endpoint")
        self.scraper_configs = []

        instance = {
            "openmetrics_endpoint": self.kubevirt_controller_metrics_endpoint,
            "namespace": self.__NAMESPACE__,
            "enable_health_service_check": False,
            "metrics": [METRICS_MAP],
        }

        self.scraper_configs.append(instance)
