# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer

from .metrics import METRICS_MAP


class KubevirtControllerCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = "kubevirt_controller"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubevirtControllerCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)
        self.check_initializations.append(self._configure_additional_transformers)

    def check(self, _):
        self.base_tags = [
            "pod_name:{}".format(self.pod_name),
            "kube_namespace:{}".format(self.kube_namespace),
        ]

        if self.kube_cluster_name:
            self.base_tags.append("kube_cluster_name:{}".format(self.kube_cluster_name))

        self.kubevirt_controller_healthz_endpoint = self.instance.get("kubevirt_controller_healthz_endpoint")

        try:
            self.log.debug("Checking health status at %s", self.kubevirt_controller_healthz_endpoint)
            response = self.http.get(self.kubevirt_controller_healthz_endpoint)
            response.raise_for_status()
            self.gauge(
                "can_connect", 1, tags=[f"endpoint:{self.kubevirt_controller_healthz_endpoint}", *self.base_tags]
            )
        except Exception as e:
            self.log.error(
                "Cannot connect to KubeVirt Controller HTTP endpoint '%s': %s.\n",
                self.kubevirt_controller_healthz_endpoint,
                str(e),
            )
            self.gauge(
                "can_connect", 0, tags=[f"endpoint:{self.kubevirt_controller_healthz_endpoint}", *self.base_tags]
            )
            raise

        super().check(_)

    def _parse_config(self):
        self.kubevirt_controller_metrics_endpoint = self.instance.get("kubevirt_controller_metrics_endpoint")
        self.kubevirt_controller_healthz_endpoint = self.instance.get("kubevirt_controller_healthz_endpoint")
        self.kube_cluster_name = self.instance.get("kube_cluster_name")
        self.kube_namespace = self.instance.get("kube_namespace")
        self.pod_name = self.instance.get("kube_pod_name")

        self.scraper_configs = []

        instance = {
            "openmetrics_endpoint": self.kubevirt_controller_metrics_endpoint,
            "namespace": self.__NAMESPACE__,
            "enable_health_service_check": False,
            "tls_verify": False,
        }

        self.scraper_configs.append(instance)

    def _configure_additional_transformers(self):
        metric_transformer = self.scrapers[self.kubevirt_controller_metrics_endpoint].metric_transformer
        metric_transformer.add_custom_transformer(r".*", self.configure_transformer_kubevirt_metrics(), pattern=True)

    def configure_transformer_kubevirt_metrics(self):
        def transform(_metric, sample_data, _runtime_data):
            for sample, tags, hostname in sample_data:
                metric_name = _metric.name
                metric_type = _metric.type

                # ignore metrics we don't collect
                if metric_name not in METRICS_MAP:
                    continue

                # add tags
                tags = tags + self.base_tags

                # get mapped metric name
                new_metric_name = METRICS_MAP[metric_name]
                if isinstance(new_metric_name, dict) and "name" in new_metric_name:
                    new_metric_name = new_metric_name["name"]

                # send metric
                metric_transformer = self.scrapers[self.kubevirt_controller_metrics_endpoint].metric_transformer

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

                    modified_sample_data = (add_tag_to_sample(x, self.base_tags) for x in sample_data)
                    native_transformer(_metric, modified_sample_data, _runtime_data)

        return transform
