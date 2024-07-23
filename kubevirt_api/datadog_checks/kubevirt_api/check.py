# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2

from .metrics import METRICS_MAP

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class KubevirtApiCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "kubevirt_api"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubevirtApiCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        # type: (Any) -> None
        if self.health_url:
            url = self.health_url
            try:
                response = self.http.get(url)
                response.raise_for_status()
                self.gauge("can_connect", 1)
            except Exception as e:
                self.log.error(
                    "Cannot connect to KubeVirt API HTTP  endpoint '%s': %s.\n",
                    url,
                    str(e),
                )
                self.gauge("can_connect", 0)
                raise
        super().check(_)

    def _parse_config(self):
        self.kubevirt_api_url = self.instance.get("kubevirt_api_url")
        self.health_url = self.instance.get("health_url")

        if "/metrics" not in self.kubevirt_api_url:
            self.kubevirt_api_url = "{}/metrics".format(self.kubevirt_api_url)

        self.instance.setdefault("openmetrics_endpoint", self.kubevirt_api_url)
        self.instance.setdefault("enable_health_service_check", False)
        self.instance.setdefault("metrics", [METRICS_MAP])
        self.instance.setdefault("rename_labels", {"version": "kubevirt_api_version", "host": "kubevirt_host"})
