# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck, ConfigurationError

from .metrics import VERSION_METRIC_NAME, build_metric


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

        try:
            response = self.http.get(self.traffic_server_url)
            response.raise_for_status()
            response_json = response.json()
            self.collect_metrics(response_json)

        except (HTTPError, Timeout, InvalidURL, ConnectionError) as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                tags=self.tags,
                message="Request failed: {}, {}".format(self.traffic_server_url, e),
            )
            raise

        self.service_check("can_connect", AgentCheck.OK, tags=self.tags)

    def collect_metrics(self, response_json):
        global_metrics = response_json.get("global")

        for metric_name, metric_value in global_metrics.items():
            name, tags, metric_type = build_metric(metric_name, self.log)
            method = getattr(self, metric_type)

            if name is not None:
                method(name, metric_value, tags=self.tags + tags)

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
