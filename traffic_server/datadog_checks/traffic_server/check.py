# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck, ConfigurationError

from .metrics import HOSTNAME_METRIC_NAMES, SHORT_VERSION_METRIC_NAMES, VERSION_BUILD_NUMBER_METRIC_NAME, build_metric

NULL_VALUE = "(null)"


class TrafficServerCheck(AgentCheck):

    __NAMESPACE__ = 'traffic_server'

    def __init__(self, name, init_config, instances):
        super(TrafficServerCheck, self).__init__(name, init_config, instances)

        self.traffic_server_url = self.instance.get("traffic_server_url")
        self.tags = self.instance.get("tags", [])

        if self.traffic_server_url is None:
            raise ConfigurationError('Must specify a traffic_server_url')

    def check(self, _):
        # type: (Any) -> None
        hostname_tag = []

        try:
            response = self.http.get(self.traffic_server_url)
            response.raise_for_status()
            response_json = response.json()
            hostname_tag = self.get_hostname_tag(response_json)
            self.collect_metrics(response_json, hostname_tag)

        except (HTTPError, Timeout, InvalidURL, ConnectionError) as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                tags=self.tags + hostname_tag,
                message="Request failed: {}, {}".format(self.traffic_server_url, e),
            )
            raise

        self.service_check("can_connect", AgentCheck.OK, tags=self.tags)

    def get_hostname_tag(self, response_json):
        global_metrics = response_json.get("global")
        if global_metrics is not None:
            for hostname_metric in HOSTNAME_METRIC_NAMES:
                hostname_value = global_metrics.get(hostname_metric)
                if hostname_value is not None and hostname_value != NULL_VALUE:
                    return ['traffic_server_host:{}'.format(hostname_value)]
        return []

    def collect_metrics(self, response_json, hostname_tag):
        global_metrics = response_json.get("global")
        if global_metrics is None:
            self.log.warning("Could not parse traffic server metrics payload, skipping metric and version collection")
            return

        for metric_name, metric_value in global_metrics.items():
            name, tags, metric_type = build_metric(metric_name, self.log)
            tags = tags + hostname_tag
            method = getattr(self, metric_type)

            if name is not None:
                method(name, metric_value, tags=self.tags + tags)

        server_version = None
        for short_version in SHORT_VERSION_METRIC_NAMES:
            short_version_val = global_metrics.get(short_version)
            if short_version_val is not None and short_version_val != NULL_VALUE:
                server_version = short_version_val

        build_number = global_metrics.get(VERSION_BUILD_NUMBER_METRIC_NAME)
        self._submit_version_metadata(server_version, build_number)

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self, short_version, build_number):
        version = short_version
        if short_version is not None:
            try:
                if build_number is not None and build_number != NULL_VALUE:
                    version = "{}-{}".format(short_version, build_number)
                self.set_metadata('version', version)
            except Exception as e:
                self.log.debug("Could not parse version: %s", str(e))
        else:
            self.log.debug("Could not submit version metadata, got: %s, build number: %s", short_version, build_number)
