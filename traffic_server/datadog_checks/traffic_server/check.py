# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck


class TrafficServerCheck(AgentCheck):

    __NAMESPACE__ = 'traffic_server'

    def __init__(self, name, init_config, instances):
        super(TrafficServerCheck, self).__init__(name, init_config, instances)

        self.traffic_server_url = self.instance.get("traffic_server_url")

    def check(self, _):
        # type: (Any) -> None

        try:
            response = self.http.get(self.traffic_server_url)
            response.raise_for_status()
            # response_json = response.json()

        except (HTTPError, Timeout, InvalidURL, ConnectionError) as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                message="Request failed: {}, {}".format(self.traffic_server_url, e),
            )
            raise

        self.service_check("can_connect", AgentCheck.OK)
