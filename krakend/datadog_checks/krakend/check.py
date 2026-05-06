# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from collections import ChainMap
from typing import TYPE_CHECKING

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsScraper
from datadog_checks.base.types import InstanceType

from .metrics import METRICS_MAP, RENAME_LABELS_MAP

if TYPE_CHECKING:
    from typing import Mapping

    from prometheus_client.metrics_core import Metric

    from datadog_checks.base.checks.base import AgentCheck

HTTP_STATUS_CODE_TAG = "http_response_status_code"

DISCOVERY_PORT_HINTS = [9090]
DISCOVERY_METRICS_PATH = "/metrics"


class HttpCodeClassScraper(OpenMetricsScraper):
    def __init__(self, check: AgentCheck, config: Mapping):
        super().__init__(check, config)

    def consume_metrics_w_target_info(self, runtime_data: dict):
        metrics = super().consume_metrics(runtime_data)
        for metric in metrics:
            yield HttpCodeClassScraper.inject_code_class(metric)

    @staticmethod
    def inject_code_class(metric: Metric):
        # Patch all samples to add the code_class tag if 'code' is a 3-digit HTTP code
        for sample in metric.samples:
            if (
                (code := sample.labels.get(HTTP_STATUS_CODE_TAG))
                and isinstance(code, str)
                and len(code) == 3
                and code.isdigit()
            ):
                sample.labels['code_class'] = f"{code[0]}XX"

        return metric


class KrakendCheck(OpenMetricsBaseCheckV2):
    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = "krakend.api"
    DEFAULT_METRIC_LIMIT = 0

    DISCOVERY_PORT_HINTS = DISCOVERY_PORT_HINTS
    DISCOVERY_METRICS_PATH = DISCOVERY_METRICS_PATH

    def __init__(self, name: str, init_config: dict, instances: list) -> None:
        # When a discovery instance arrives without openmetrics_endpoint the parent's
        # configure_scrapers (run before check()) would raise ConfigurationError.
        # Inject a placeholder so the parent init succeeds; _configure_from_discovery
        # replaces it with the real endpoint on the first check() call.
        if instances:
            for inst in instances:
                if inst.get("__discovery_service__") is not None and not inst.get("openmetrics_endpoint"):
                    inst["openmetrics_endpoint"] = "http://discovery-pending.invalid/metrics"
        super().__init__(name, init_config, instances)
        self._discovery_endpoint: str | None = None

    def check(self, _: InstanceType) -> None:
        instance = self.instance
        if instance.get("__discovery_service__") is not None and self._discovery_endpoint is None:
            self._configure_from_discovery(instance["__discovery_service__"])
        super().check(_)

    def _configure_from_discovery(self, service_dict: dict) -> None:
        import datadog_checks.base.utils.discovery.http as http_mod
        from datadog_checks.base.utils.discovery import Port, Service, candidate_ports, is_prometheus_exposition

        service = Service(
            id=service_dict["id"],
            host=service_dict["host"],
            ports=tuple(Port(number=p["number"], name=p.get("name", "")) for p in service_dict["ports"]),
        )

        endpoint = None
        for port in candidate_ports(service, self.DISCOVERY_PORT_HINTS):
            if http_mod.http_probe(
                service.host, port.number, self.DISCOVERY_METRICS_PATH, verifier=is_prometheus_exposition()
            ):
                endpoint = f"http://{service.host}:{port.number}{self.DISCOVERY_METRICS_PATH}"
                break

        if endpoint is None:
            tried = [p.number for p in candidate_ports(service, self.DISCOVERY_PORT_HINTS)]
            raise Exception(
                f"krakend discovery: no responding /metrics endpoint on host {service.host} (ports tried: {tried})"
            )

        self.instance["openmetrics_endpoint"] = endpoint
        self.scraper_configs = [self.instance]
        self.configure_scrapers()
        self._discovery_endpoint = endpoint

    def create_scraper(self, config: InstanceType):
        return HttpCodeClassScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config: InstanceType) -> Mapping:
        # If the user does not provide a value for go_metrics or process_metrics,
        # assume they want whatever behvaior has been set in KrakenD
        go_metrics = config.get("go_metrics", True)
        process_metrics = config.get("process_metrics", True)

        def accept_metric(metric_name):
            if metric_name.startswith("go_") and not go_metrics:
                return False
            if metric_name.startswith("process_") and not process_metrics:
                return False
            return True

        metrics = {
            original_name: new_name for original_name, new_name in METRICS_MAP.items() if accept_metric(original_name)
        }

        rename_labels = RENAME_LABELS_MAP.copy()
        if go_metrics:
            # Only rename the version label if go_metrics are enabled
            # This is explained in the tile
            rename_labels["version"] = "go_version"

        default_configs = {
            "metrics": [metrics],
            "rename_labels": rename_labels,
            "target_info": True,
        }

        return ChainMap(config, default_configs)
