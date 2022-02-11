# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck

from .metrics import COUNT_METRICS, GAUGE_METRICS, VERSION_METRIC_NAME


class TrafficServerCheck(AgentCheck):

    __NAMESPACE__ = 'traffic_server'

    def __init__(self, name, init_config, instances):
        super(TrafficServerCheck, self).__init__(name, init_config, instances)

        self.traffic_server_url = self.instance.get("traffic_server_url")
        self.tags = self.instance.get("tags", [])

    def check(self, _):
        # type: (Any) -> None

        try:
            response = self.http.get(self.traffic_server_url)
            response.raise_for_status()
            response_json = response.json()
            self.send_metrics(response_json)

        except (HTTPError, Timeout, InvalidURL, ConnectionError) as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                tags=self.tags,
                message="Request failed: {}, {}".format(self.traffic_server_url, e),
            )
            raise

        self.service_check("can_connect", AgentCheck.OK)

    def send_metrics(self, response_json):
        global_metrics = response_json.get("global")

        for metric_name, metric_value in global_metrics.items():
            if metric_name in COUNT_METRICS:
                normalized_name = COUNT_METRICS[metric_name]
                self.monotonic_count(normalized_name, metric_value, tags=self.tags)

            elif metric_name in GAUGE_METRICS:
                normalized_name = GAUGE_METRICS[metric_name]
                self.gauge(normalized_name, metric_value, tags=self.tags)

        server_version = global_metrics.get(VERSION_METRIC_NAME, None)
        self._submit_version_metadata(server_version)

    @AgentCheck.metadata_entrypoint
    def _submit_version_metadata(self, version):
        if version:
            try:
                self.set_metadata('version', version)
            except Exception as e:
                self.log.debug("Could not parse version: %s", str(e))
        else:
            self.log.debug("Could not submit version metadata, got: %s", version)
