# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import AUTH_METRICS_MAP, COMMON_METRICS_MAP, PROXY_METRICS_MAP

METRIC_MAP = {**COMMON_METRICS_MAP, **PROXY_METRICS_MAP, **AUTH_METRICS_MAP}


class TeleportCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'teleport'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        try:
            super().check(_)
            response = self.http.get(self.diagnostic_url + "/healthz")
            response.raise_for_status()
            self.service_check("health.up", self.OK)
        except Exception as e:
            self.service_check("health.up", self.CRITICAL, message=str(e))
        finally:
            pass

    def _parse_config(self):
        self.diagnostic_url = self.instance.get("diagnostic_url")
        if self.diagnostic_url:
            self.instance.setdefault("openmetrics_endpoint", self.diagnostic_url + "/metrics")
            self.instance.setdefault("metrics", [METRIC_MAP])
            self.instance.setdefault("rename_labels", {'version': "teleport_version"})
