# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from kubernetes import config, dynamic
from kubernetes.client import api_client

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative

from .metrics import METRICS_MAP


class KubevirtApiCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'kubevirt_api'
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubevirtApiCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)

    def check(self, _):
        # type: (Any) -> None
        if self.kubevirt_api_healthz_endpoint:
            url = self.kubevirt_api_healthz_endpoint
            try:
                response = self.http.get(url, verify=is_affirmative(self.tls_verify))
                response.raise_for_status()
                self.gauge("can_connect", 1)
            except Exception as e:
                self.log.error(
                    "Cannot connect to KubeVirt API HTTP endpoint '%s': %s.\n",
                    url,
                    str(e),
                )
                self.gauge("can_connect", 0)
                raise

        """ TODO: Use The KubeAPI client to get tags from the following endpoints:
        GET /apis/kubevirt.io/v1/namespaces/{namespace}/virtualmachineinstances
        GET /apis/kubevirt.io/v1/virtualmachineinstances
        GET /apis/kubevirt.io/v1/namespaces/{namespace}/virtualmachine
        GET /apis/kubevirt.io/v1/virtualmachine
        """

        # Creating a dynamic client
        client = dynamic.DynamicClient(api_client.ApiClient(configuration=config.load_kube_config()))
        api = client.resources.get(api_version="v1", kind="Node")

        print("%s\t\t%s\t\t%s" % ("NAME", "STATUS", "VERSION"))
        for item in api.get().items:
            node = api.get(name=item.metadata.name)
            print(
                "%s\t%s\t\t%s\n"
                % (
                    node.metadata.name,
                    node.status.conditions[3]["type"],
                    node.status.nodeInfo.kubeProxyVersion,
                )
            )

        super().check(_)

    def _parse_config(self):
        self.kubevirt_api_metrics_endpoint = self.instance.get("kubevirt_api_metrics_endpoint")
        self.kubevirt_api_healthz_endpoint = self.instance.get("kubevirt_api_healthz_endpoint")
        self.tls_verify = self.instance.get("tls_verify")

        if "/metrics" not in self.kubevirt_api_metrics_endpoint:
            self.kubevirt_api_metrics_endpoint = "{}/metrics".format(self.kubevirt_api_metrics_endpoint)

        self.scraper_configs = []

        instance = {
            "openmetrics_endpoint": self.kubevirt_api_metrics_endpoint,
            "metrics": [METRICS_MAP],
            "namespace": self.__NAMESPACE__,
            "enable_health_service_check": False,
            "rename_labels": {"version": "kubevirt_api_version", "host": "kubevirt_host"},
            "tls_verify": self.tls_verify,
        }

        self.scraper_configs.append(instance)
