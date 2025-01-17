# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

import requests

from datadog_checks.base import AgentCheck

from . import constants
from .api_client import SonatypeNexusClient


class SonatypeNexusCheck(AgentCheck):
    __NAMESPACE__ = "sonatype_nexus"

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self._username = (self.instance.get("username") or "").strip()
        self._password = (self.instance.get("password") or "").strip()
        self._sonatype_nexus_server_url = self.instance.get("sonatype_nexus_server_url")
        self.min_collection_interval = self.instance.get("min_collection_interval")
        self.sonatype_nexus_client = SonatypeNexusClient(self)
        self.custom_tags = self.instance.get("tags")

    def check(self, _):
        self.generate_and_yield_status_metrics()
        self.generate_and_yield_analytics_metrics()

    def extract_ip_from_url(self) -> str | None:
        pattern = r"http[s]?://([\d\.]+)"
        match = re.search(pattern, self._sonatype_nexus_server_url)
        return match.group(1) if match else None

    def generate_and_yield_status_metrics(self):
        url = f"{self._sonatype_nexus_server_url}{constants.STATUS_ENDPOINT}"
        try:
            response_json = self.sonatype_nexus_client.call_sonatype_nexus_api(url).json()
        except requests.exceptions.JSONDecodeError as ex:
            self.log.error("Can't decode API response to json, Error: %s", str(ex))
            return {"message": "Can't decode API response to json", "error": str(ex)}
        for key, metric_name in constants.STATUS_METRICS_MAP.items():
            try:
                self.gauge(
                    metric_name,
                    int(response_json[key]["healthy"]),
                    [f"sonatype_host:{self.extract_ip_from_url()}"] + (
                        self.custom_tags if self.custom_tags else []
                    ),
                    hostname=None,
                )
            except KeyError as key:
                raise KeyError(f"Expected key, '{key}' is not present in API response.") from None

    def generate_and_yield_analytics_metrics(self):
        url = f"{self._sonatype_nexus_server_url}{constants.ANALYTICS_ENDPOINT}"
        try:
            response_json = self.sonatype_nexus_client.call_sonatype_nexus_api(url).json()
        except requests.exceptions.JSONDecodeError as ex:
            self.log.error("Can't decode API response to json, Error: %s", str(ex))
            return {"message": "Can't decode API response to json", "error": str(ex)}
        try:
            for metric_name, metric_info in constants.METRIC_CONFIGS.items():
                metric_data = self.process_metrics(metric_info["metric_key"], response_json["gauges"])
                self.create_metric_for_configs(metric_data, metric_name)
            for metric_name, metric_info in constants.METRIC_CONFIGS_BY_FORMAT_TYPE.items():
                metric_data = self.process_metrics(metric_info["metric_key"], response_json["gauges"])
                self.create_metric_for_configs_by_format_type(metric_data["value"], metric_name, metric_info)
        except KeyError as key:
            raise KeyError(f"Expected key, '{key}' is not present in API response.") from None

    def process_metrics(self, metric_key, response_json) -> dict:
        if metric_key in response_json:
            return response_json[metric_key]

    def create_metric_for_configs(self, metric_data: dict, metric_name: str):
        base_tags = [f"sonatype_host:{self.extract_ip_from_url()}"] + (
            self.custom_tags if self.custom_tags else []
        )
        config = constants.METRIC_CONFIGS[metric_name]
        value = metric_data.get("value")

        if isinstance(value, list):
            for item in value:
                tag_list = []
                for tag_key in config["tag_key"]:
                    tag_list.append(f"{tag_key}:{item[tag_key]}")
                self.gauge(metric_name, int(item[config["value_key"]]), base_tags + tag_list, hostname=None)
        elif isinstance(value, int):
            self.gauge(metric_name, int(value), base_tags, hostname=None)
        elif isinstance(value, dict):
            self.gauge(metric_name, int(value[config["value_key"]]), base_tags, hostname=None)

    def create_metric_for_configs_by_format_type(self, metric_data, metric_name, metric_info):
        base_tags = [f"sonatype_host:{self.extract_ip_from_url()}"] + (
            self.custom_tags if self.custom_tags else []
        )

        if isinstance(metric_data, list):
            for item in metric_data:
                for format_type, data in item.items():
                    self.ingest_metric(base_tags, format_type, metric_info, metric_name, data[metric_info["value_key"]])
        elif isinstance(metric_data, dict):
            for format_type, metric_value in metric_data.items():
                self.ingest_metric(base_tags, format_type, metric_info, metric_name, metric_value)

    def ingest_metric(self, base_tags, format_type, metric_info, metric_name, value):
        tags = [f"{metric_info['tag_key']}:{format_type}"]
        self.gauge(metric_name, int(value), base_tags + tags, hostname=None)

    def ingest_service_check_and_event(self, **service_check_event_args):
        self.service_check(
            constants.SONATYPE_NEXUS_CHECK_NAME,
            service_check_event_args.get("status"),
            service_check_event_args.get("tags"),
            self.extract_ip_from_url(),
            service_check_event_args.get("message"),
        )
        self.event(
            {
                "sonatype_host": self.extract_ip_from_url(),
                "alert_type": constants.STATUS_NUMBER_TO_VALUE[service_check_event_args.get("status")],
                "tags": service_check_event_args.get("tags"),
                "msg_text": service_check_event_args.get("message"),
                "msg_title": service_check_event_args.get("title"),
                "source_type_name": service_check_event_args.get("source_type"),
            }
        )
