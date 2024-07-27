# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import ipaddress
from typing import Any  # noqa: F401
from urllib.parse import urlparse

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer

from .kube_client import KubernetesAPIClient
from .metrics import METRICS_MAP


class KubevirtApiCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "kubevirt_api"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubevirtApiCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)
        self.check_initializations.append(self._configure_additional_transformers)

    def _setup(self):
        self.kube_client = KubernetesAPIClient(tls_verify=self.tls_verify, kube_config_dict=self.kube_config_dict)

    def check(self, _):
        # type: (Any) -> None

        self._setup()

        target_ip, _ = self._extract_host_port(self.kubevirt_api_metrics_endpoint)
        target_pod = self.kube_client.get_pods(self.kube_namespace, ip=target_ip)

        if len(target_pod) == 0:
            target_pod = self.kube_client.get_pods(namespace="kubevirt")
            virt_api_pods = [pod for pod in target_pod if "virt-api" in pod.metadata.name]
            if len(virt_api_pods) == 0:
                raise ValueError(
                    f"There are no pods with 'virt-api' in their name in the '{self.kube_namespace}' namespace"
                )
            target_pod = virt_api_pods[0]
        elif len(target_pod) > 0:
            target_pod = target_pod[0]
        else:
            raise ValueError(f"Target pod with ip: '{target_ip}' not found")

        self.target_pod = target_pod
        self.pod_tags = self._extract_pod_tags(self.target_pod)

        if self.kubevirt_api_healthz_endpoint:
            url = self.kubevirt_api_healthz_endpoint
            try:
                response = self.http.get(url, verify=is_affirmative(self.tls_verify))
                response.raise_for_status()
                self.gauge("can_connect", 1, tags=[f"endpoint:{self.kubevirt_api_healthz_endpoint}"])
            except Exception as e:
                self.log.error(
                    "Cannot connect to KubeVirt API HTTP endpoint '%s': %s.\n",
                    url,
                    str(e),
                )
                self.gauge("can_connect", 0, tags=[f"endpoint:{self.kubevirt_api_healthz_endpoint}"])
                raise

        super().check(_)

    def _extract_host_port(self, url):
        parsed_url = urlparse(url)

        host = parsed_url.hostname
        port = parsed_url.port

        if host and port:
            try:
                host = ipaddress.ip_address(host)
                return host, port
            except Exception as e:
                raise ValueError(f"Host '{host}' must be a valid ip address: {str(e)}")
        else:
            raise ValueError(f"URL '{url}' does not match the expected format `https://<host_ip>:<port>/<path>`")

    def _extract_pod_tags(self, pod):
        tags = []
        tags.append(f"pod_name:{pod.metadata.name}")
        tags.append(f"kube_namespace:{pod.metadata.namespace}")

        if self.kube_cluster_name:
            tags.append(f"kube_cluster_name:{self.kube_cluster_name}")

        return tags

    def _parse_config(self):
        self.kubevirt_api_metrics_endpoint = self.instance.get("kubevirt_api_metrics_endpoint")
        self.kubevirt_api_healthz_endpoint = self.instance.get("kubevirt_api_healthz_endpoint")
        self.kube_cluster_name = self.instance.get("kube_cluster_name")
        self.kube_namespace = self.instance.get("kube_namespace")
        self.kube_config_dict = self.instance.get("kube_config_dict")
        self.tls_verify = self.instance.get("tls_verify")

        if "/metrics" not in self.kubevirt_api_metrics_endpoint:
            self.kubevirt_api_metrics_endpoint = "{}/metrics".format(self.kubevirt_api_metrics_endpoint)

        self.scraper_configs = []

        instance = {
            "openmetrics_endpoint": self.kubevirt_api_metrics_endpoint,
            "namespace": self.__NAMESPACE__,
            "enable_health_service_check": False,
            "rename_labels": {"version": "kubevirt_api_version", "host": "kubevirt_host"},
            "tls_verify": self.tls_verify,
        }

        self.scraper_configs.append(instance)

    def _configure_additional_transformers(self):
        metric_transformer = self.scrapers[self.kubevirt_api_metrics_endpoint].metric_transformer
        metric_transformer.add_custom_transformer(r".*", self.configure_transformer_kubevirt_metrics(), pattern=True)

    def configure_transformer_kubevirt_metrics(self):
        def transform(_metric, sample_data, _runtime_data):
            # print("_metric: ", _metric.name)

            for sample, tags, hostname in sample_data:
                metric_name = _metric.name
                metric_type = _metric.type

                # ignore metrics we don't collect
                if metric_name not in METRICS_MAP:
                    continue

                # print("metric_name: ", metric_name, "metric_type: ", metric_type)

                # add tags
                tags = tags + self.pod_tags

                # get mapped metric name
                new_metric_name = METRICS_MAP[metric_name]
                if isinstance(new_metric_name, dict) and "name" in new_metric_name:
                    new_metric_name = new_metric_name["name"]

                # send metric
                metric_transformer = self.scrapers[self.kubevirt_api_metrics_endpoint].metric_transformer

                print("new_metric_name: ", new_metric_name, "metric_type: ", metric_type)
                if metric_type == "counter":
                    self.count(new_metric_name + ".count", sample.value, tags=tags, hostname=hostname)
                elif metric_type == "gauge":
                    self.gauge(new_metric_name, sample.value, tags=tags, hostname=hostname)
                else:
                    native_transformer = get_native_dynamic_transformer(
                        self, new_metric_name, None, metric_transformer.global_options
                    )

                    def add_tag_to_sample(sample, pod_tags):
                        [sample, tags, hostname] = sample
                        return [sample, tags + pod_tags, hostname]

                    modified_sample_data = (add_tag_to_sample(x, self.pod_tags) for x in sample_data)
                    native_transformer(_metric, modified_sample_data, _runtime_data)

        return transform
