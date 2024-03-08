# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import AUTH_METRICS_MAP, COMMON_METRICS_MAP, PROXY_METRICS_MAP, SSH_METRICS_MAP

METRIC_MAP = {**COMMON_METRICS_MAP, **PROXY_METRICS_MAP, **AUTH_METRICS_MAP, **SSH_METRICS_MAP}


class TeleportCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'teleport'
    DEFAULT_DIAG_PORT = 3000

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        try:
            response = self.http.get("{}/healthz".format(self.diag_addr))
            response.raise_for_status()
            self.service_check("health.up", self.OK)
        except Exception as e:
            self.service_check("health.up", self.CRITICAL, message=str(e))

        super().check(_)

    def _parse_config(self):
        self.teleport_url = self.instance.get("teleport_url")
        self.diag_port = self.instance.get("diag_port", self.DEFAULT_DIAG_PORT)
        if self.teleport_url:
            self.diag_addr = "{}:{}".format(self.teleport_url, self.diag_port)
            self.instance.setdefault("openmetrics_endpoint", "{}/metrics".format(self.diag_addr))
            self.instance.setdefault("metrics", [METRIC_MAP])
            self.instance.setdefault("rename_labels", {'version': "teleport_version"})
