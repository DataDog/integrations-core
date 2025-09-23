# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any  # noqa: F401

from datadog_checks.base import OpenMetricsBaseCheckV2, is_affirmative
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer

from .metrics import METRICS_MAP


class KubeVirtHandlerCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "kubevirt_handler"
    DEFAULT_METRIC_LIMIT = 0

    def __init__(self, name, init_config, instances):
        super(KubeVirtHandlerCheck, self).__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)
        self.check_initializations.append(self._init_base_tags)
        self.check_initializations.append(self._configure_additional_transformers)

    def check(self, _):
        # type: (Any) -> None

        if self.kubevirt_handler_healthz_endpoint:
            self._report_health_check(self.kubevirt_handler_healthz_endpoint)
        else:
            self.log.warning(
                "Skipping health check. Please provide a `kubevirt_handler_healthz_endpoint` to ensure the health of the KubeVirt Handler."  # noqa: E501
            )

        super().check(_)

    def _report_health_check(self, health_endpoint):
        try:
            self.log.debug("Checking health status at %s", health_endpoint)
            response = self.http.get(health_endpoint, verify=self.tls_verify)
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
        self.kubevirt_handler_metrics_endpoint = self.instance.get("kubevirt_handler_metrics_endpoint")
        self.kube_namespace = self.instance.get("kube_namespace")
        self.pod_name = self.instance.get("kube_pod_name")
        self.tls_verify = is_affirmative(self.instance.get("tls_verify"))

        self.scraper_configs = []

        instance = {
            "openmetrics_endpoint": self.kubevirt_handler_metrics_endpoint,
            "namespace": self.__NAMESPACE__,
            "enable_health_service_check": False,
            "tls_verify": self.tls_verify,
            "rename_labels": {
                "namespace": "vm_namespace",
            },
        }

        self.scraper_configs.append(instance)

    def _init_base_tags(self):
        self.base_tags = [
            "pod_name:{}".format(self.pod_name),
            "kube_namespace:{}".format(self.kube_namespace),
        ]

    def _configure_additional_transformers(self):
        metric_transformer = self.scrapers[self.kubevirt_handler_metrics_endpoint].metric_transformer
        metric_transformer.add_custom_transformer("kubevirt_info", self.configure_metadata_transformer)
        metric_transformer.add_custom_transformer(r".*", self.configure_transformer_kubevirt_metrics(), pattern=True)

    def configure_metadata_transformer(self, metric, sample_data, runtime_data):
        """
        Parse the kubevirt_info metric to extract the kubevirt version.
        """
        for sample, *_ in sample_data:
            kubeversion = sample.labels["kubeversion"]
            version_split = kubeversion[1:].split(".")

            major = version_split[0]
            minor = version_split[1]
            patch = version_split[2]

            version_raw = kubeversion

            version_parts = {
                "major": major,
                "minor": minor,
                "patch": patch,
            }

            self.set_metadata("version", version_raw, scheme="semver", part_map=version_parts)

    def configure_transformer_kubevirt_metrics(self):
        """
        Return a metrics transformer that adds tags to all the collected metrics.
        """

        def transform(_metric, sample_data, _runtime_data):
            for sample, tags, hostname in sample_data:
                metric_name = _metric.name
                metric_type = _metric.type

                # ignore metrics we don't collect
                if metric_name not in METRICS_MAP:
                    continue

                # attach tags to the metric
                tags = tags + self.base_tags

                # apply the METRICS_MAP mapping for the metric name
                new_metric_name = METRICS_MAP[metric_name]
                if isinstance(new_metric_name, dict) and "name" in new_metric_name:
                    new_metric_name = new_metric_name["name"]

                # call the correct metric submission method based on the metric type
                if metric_type == "counter":
                    self.count(new_metric_name + ".count", sample.value, tags=tags, hostname=hostname)
                elif metric_type == "gauge":
                    self.gauge(new_metric_name, sample.value, tags=tags, hostname=hostname)
                else:
                    metric_transformer = self.scrapers[self.kubevirt_handler_metrics_endpoint].metric_transformer

                    native_transformer = get_native_dynamic_transformer(
                        self, new_metric_name, None, metric_transformer.global_options
                    )

                    def add_tag_to_sample(sample, pod_tags):
                        [sample, tags, hostname] = sample
                        return [sample, tags + pod_tags, hostname]

                    modified_sample_data = (add_tag_to_sample(x, self.base_tags) for x in sample_data)
                    native_transformer(_metric, modified_sample_data, _runtime_data)

        return transform
