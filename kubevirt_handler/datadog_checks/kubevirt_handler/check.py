# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import AgentCheck  # noqa: F401

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError


class KubevirtHandlerCheck(AgentCheck):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "kubevirt_handler"

    def __init__(self, name, init_config, instances):
        super(KubevirtHandlerCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        # type: (Any) -> None

        if self.kubevirt_handler_healthz_endpoint:
            self._report_health_check(self.kubevirt_handler_healthz_endpoint)
        else:
            self.log.warning(
                "Skipping health check. Please provide a `kubevirt_handler_healthz_endpoint` to ensure the health of the KubeVirt Handler."  # noqa: E501
            )

    def _report_health_check(self, health_endpoint):
        try:
            self.log.debug("Checking health status at %s", health_endpoint)
            response = self.http.get(health_endpoint)
            response.raise_for_status()
            self.gauge("can_connect", 1, tags=[f"endpoint:{health_endpoint}", *self.base_tags])
        except Exception as e:
            self.log.error(
                "Cannot connect to KubeVirt Handler HTTP endpoint '%s': %s.\n",
                health_endpoint,
                str(e),
            )
            self.gauge("can_connect", 0, tags=[f"endpoint:{health_endpoint}", *self.base_tags])
            raise

    def _parse_config(self):
        self.kubevirt_handler_healthz_endpoint = self.instance.get("kubevirt_handler_healthz_endpoint")
        self.kube_cluster_name = self.instance.get("kube_cluster_name")
        self.kube_namespace = self.instance.get("kube_namespace")
        self.pod_name = self.instance.get("kube_pod_name")

        self.base_tags = [
            "pod_name:{}".format(self.pod_name),
            "kube_namespace:{}".format(self.kube_namespace),
        ]

        if self.kube_cluster_name:
            self.base_tags.append("kube_cluster_name:{}".format(self.kube_cluster_name))
