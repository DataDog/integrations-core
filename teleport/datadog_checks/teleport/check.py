# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.transform import get_native_dynamic_transformer

from .metrics import METRIC_MAP, METRIC_MAP_BY_SERVICE


class TeleportCheck(OpenMetricsBaseCheckV2):
    __NAMESPACE__ = 'teleport'
    DEFAULT_METRIC_LIMIT = 0
    DEFAULT_DIAG_PORT = 3000

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)
        self.check_initializations.appendleft(self._parse_config)
        self.check_initializations.append(self._configure_additional_transformers)

    def check(self, _):
        try:
            health_endpoint = f"{self.diag_addr}/healthz"
            response = self.http.get(health_endpoint)
            response.raise_for_status()
            self.count("health.up", 1, tags=["teleport_status:ok"])
        except Exception as e:
            self.log.error(
                "Cannot connect to Teleport HTTP diagnostic health endpoint '%s': %s.\nPlease make sure to enable Teleport's diagnostic HTTP endpoints.",  # noqa: E501
                health_endpoint,
                str(e),
            )  # noqa: E501
            self.count("health.up", 0, tags=["teleport_status:unreachable"])
            raise

        super().check(_)

    def _parse_config(self):
        self.teleport_url = self.instance.get("teleport_url")
        self.diag_port = self.instance.get("diag_port", self.DEFAULT_DIAG_PORT)
        if self.teleport_url:
            self.diag_addr = "{}:{}".format(self.teleport_url, self.diag_port)
            self.instance.setdefault("openmetrics_endpoint", "{}/metrics".format(self.diag_addr))
            self.instance.setdefault("rename_labels", {'version': "teleport_version"})

    def _configure_additional_transformers(self):
        metric_transformer = self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer
        metric_transformer.add_custom_transformer(r'.*', self.configure_transformer_teleport_metrics(), pattern=True)

    def configure_transformer_teleport_metrics(self):
        def transform(_metric, sample_data, _runtime_data):
            for sample, tags, hostname in sample_data:
                metric_name = _metric.name
                metric_type = _metric.type

                # ignore metrics we don't collect
                if metric_name not in METRIC_MAP:
                    continue

                # extract `teleport_service` tag
                service = METRIC_MAP_BY_SERVICE.get(metric_name, "teleport")
                tags = tags + [f"teleport_service:{service}"]

                # get mapped metric name
                new_metric_name = METRIC_MAP[metric_name]
                if isinstance(new_metric_name, dict) and "name" in new_metric_name:
                    new_metric_name = new_metric_name["name"]

                # send metric
                metric_transformer = self.scrapers[self.instance['openmetrics_endpoint']].metric_transformer

                if metric_type == "counter":
                    self.count(new_metric_name + ".count", sample.value, tags=tags, hostname=hostname)
                elif metric_type == "gauge":
                    self.gauge(new_metric_name, sample.value, tags=tags, hostname=hostname)
                else:
                    native_transformer = get_native_dynamic_transformer(
                        self, new_metric_name, None, metric_transformer.global_options
                    )

                    def add_tag_to_sample(sample, service):
                        [sample, tags, hostname] = sample
                        return [sample, tags + [f"teleport_service:{service}"], hostname]

                    modified_sample_data = (add_tag_to_sample(x, service) for x in sample_data)
                    native_transformer(_metric, modified_sample_data, _runtime_data)

        return transform
