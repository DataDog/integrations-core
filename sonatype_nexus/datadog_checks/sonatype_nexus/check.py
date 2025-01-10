# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re

import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.errors import (
    ConfigurationError,
    ConfigValueError,
)

from . import constants
from .api_client import SonatypeNexusClient
from .errors import log_and_raise_exception


class SonatypeNexusCheck(AgentCheck):
    __NAMESPACE__ = "sonatype_nexus"

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self._username = self.instance.get("username")
        self._password = self.instance.get("password")
        self._sonatype_nexus_server_url = self.instance.get("sonatype_nexus_server_url")
        self.min_collection_interval = self.instance.get("min_collection_interval")
        self.sonatype_nexus_client = SonatypeNexusClient(self)

    def check(self, _):
        try:
            self.validate_integration_configurations()
            success_msg = "All the provided configurations in conf.yaml are valid."
            self.log.info("%s | HOST=%s | MESSAGE=%s", constants.INTEGRATION_PREFIX, self.hostname, success_msg)
            self.ingest_service_check_and_event(
                status=0,
                tags=constants.CONF_VAL_TAG,
                message=success_msg,
                title=constants.CONF_VAL_TITLE,
                source_type=constants.CONF_VAL_SOURCE_TYPE,
            )
        except Exception:
            err_message = (
                "Error occurred while validating the provided configurations in conf.yaml file."
                " Please check logs for more details."
            )
            self.ingest_service_check_and_event(
                status=2,
                tags=constants.CONF_VAL_TAG,
                message=err_message,
                title=constants.CONF_VAL_TITLE,
                source_type=constants.CONF_VAL_SOURCE_TYPE,
            )
            raise

        self.generate_and_yield_status_metrics()
        self.generate_and_yield_analytics_metrics()

    def extract_ip_from_url(self) -> str | None:
        pattern = r"http[s]?://([\d\.]+)"
        match = re.search(pattern, self._sonatype_nexus_server_url)
        return match.group(1) if match else None

    def validate_integration_configurations(self) -> None:
        for field_name in constants.REQUIRED_FIELDS:
            value = self.instance.get(field_name)
            if value is None:
                err_message = f"'{field_name}' field is required"
                log_and_raise_exception(self, err_message, ConfigurationError)
            if isinstance(value, str) and value.strip() == "":
                err_message = f"Empty value is not allowed in '{field_name}' field."
                log_and_raise_exception(self, err_message, ValueError)
            if not (isinstance(value, str)):
                err_message = f"Invalid value provided for {field_name} field. "
                f"The value type should be string but found {type(value)}."
                log_and_raise_exception(self, err_message, ValueError)

        self.validate_minimum_collection_interval()

    def validate_minimum_collection_interval(self):
        if self.min_collection_interval is None:
            err_message = "'min_collection_interval' field is required"
            log_and_raise_exception(self, err_message, ConfigValueError)
        if self.min_collection_interval <= 60 or self.min_collection_interval > 64800:
            err_message = (
                "'min_collection_interval' must be a positive integer value greater than 60 upto 64800,"
                f" but found {self.min_collection_interval}."
            )
            log_and_raise_exception(self, err_message, ValueError)
        if not (isinstance(self.min_collection_interval, int)):
            err_message = (
                "Invalid value provided for 'min_collection_interval' field. "
                f"The value type should be integer but found {type(self.min_collection_interval)}."
            )
            log_and_raise_exception(self, err_message, ValueError)

    def generate_and_yield_status_metrics(self):
        url = f"{self._sonatype_nexus_server_url}{constants.STATUS_ENDPOINT}"
        try:
            response_json = self.sonatype_nexus_client.call_sonatype_nexus_api(url).json()
        except requests.exceptions.JSONDecodeError as ex:
            return {"message": "can't decode response to json", "error": str(ex)}
        for key, metric_name in constants.STATUS_METRICS_MAP.items():
            self.gauge(
                metric_name,
                int(response_json[key]["healthy"]),
                [f"sonatype_host:{self.extract_ip_from_url()}"],
                hostname=None,
            )

    def generate_and_yield_analytics_metrics(self):
        url = f"{self._sonatype_nexus_server_url}{constants.ANALYTICS_ENDPOINT}"
        try:
            response_json = self.sonatype_nexus_client.call_sonatype_nexus_api(url).json()
        except requests.exceptions.JSONDecodeError as ex:
            return {"message": "can't decode response to json", "error": str(ex)}
        for metric_name, metric_info in constants.METRIC_CONFIGS.items():
            metric_data = self.process_metrics(metric_info["metric_key"], response_json["gauges"])
            self.create_metric_for_configs(metric_data, metric_name)
        for metric_name, metric_info in constants.METRIC_CONFIGS_BY_FORMAT_TYPE.items():
            metric_data = self.process_metrics(metric_info["metric_key"], response_json["gauges"])
            self.create_metric_for_configs_by_format_type(metric_data["value"], metric_name, metric_info)

    def process_metrics(self, metric_key, response_json) -> dict:
        if metric_key in response_json:
            return response_json[metric_key]

    def create_metric_for_configs(self, metric_data: dict, metric_name: str):
        base_tag = [f"sonatype_host:{self.extract_ip_from_url()}"]
        config = constants.METRIC_CONFIGS[metric_name]
        value = metric_data.get("value")

        if isinstance(value, list):
            for item in value:
                tag_list = []
                for tag_key in config["tag_key"]:
                    tag_list.append(f"{tag_key}:{item[tag_key]}")
                self.gauge(metric_name, int(item[config["value_key"]]), base_tag + tag_list, hostname=None)
        elif isinstance(value, int):
            self.gauge(metric_name, int(value), base_tag, hostname=None)
        elif isinstance(value, dict):
            self.gauge(metric_name, int(value[config["value_key"]]), base_tag, hostname=None)

    def create_metric_for_configs_by_format_type(self, metric_data, metric_name, metric_info):
        base_tag = [f"sonatype_host:{self.extract_ip_from_url()}"]

        if isinstance(metric_data, list):
            for item in metric_data:
                for format_type, data in item.items():
                    self.ingest_metric(base_tag, format_type, metric_info, metric_name, data[metric_info["value_key"]])
        elif isinstance(metric_data, dict):
            for format_type, metric_value in metric_data.items():
                self.ingest_metric(base_tag, format_type, metric_info, metric_name, metric_value)

    def ingest_metric(self, base_tag, format_type, metric_info, metric_name, value):
        tags = [f"{metric_info['tag_key']}:{format_type}"]
        self.gauge(metric_name, int(value), base_tag + tags, hostname=None)

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
