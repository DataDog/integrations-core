# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from json import JSONDecodeError
from typing import Any  # noqa: F401

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck  # noqa: F401


class ProxmoxCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'proxmox'

    def __init__(self, name, init_config, instances):
        super(ProxmoxCheck, self).__init__(name, init_config, instances)

        self.url = self.instance.get("url", "https://localhost:8006")
        self.token_id = self.instance.get("token_id")
        self.token_secret = self.instance.get("token_secret")

        if not self.token_id or not self.token_secret:
            raise ValueError("token_id and token_secret are required")

    def check(self, _):
        try:
            headers = {"Authorization": f"PVEAPIToken={self.token_id}={self.token_secret}"}
            response = self.http.get(f"{self.url}/api2/json/cluster/resources", verify=False, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            resourcemap = {}
            for data in response_json['data']:
                resourcemap[data['id']] = data

            response = self.http.get(f"{self.url}/api2/json/cluster/metrics/export", verify=False, headers=headers)
            response.raise_for_status()
            response_json = response.json()

            for data in response_json['data']['data']:
                if data["id"] not in resourcemap:
                    self.log.debug("Skipping metric for resource", extra={"resource_id": data["id"]})
                    continue

                resource_type = resourcemap[data["id"]]["type"]
                resource_name = resourcemap[data["id"]].get("name", "unknown")
                resource_node = resourcemap[data["id"]].get("node", "unknown")
                match data["type"]:
                    case "gauge":
                        self.gauge(
                            data["metric"],
                            data["value"],
                            tags=[
                                f"id:{data['id']}",
                                f"type:{resource_type}",
                                f"name:{resource_name}",
                                f"node:{resource_node}",
                            ],
                        )
                    case "derive":
                        self.rate(
                            data["metric"],
                            data["value"],
                            tags=[
                                f"id:{data['id']}",
                                f"type:{resource_type}",
                                f"name:{resource_name}",
                                f"node:{resource_node}",
                            ],
                        )
                    case _:
                        self.log.warning("Unsupported metric type", extra={"type": data["type"]})

            self.service_check("can_connect", AgentCheck.OK)

        except Timeout as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                message="Request timeout: {}, {}".format(self.url, e),
            )
            raise

        except (HTTPError, InvalidURL, ConnectionError) as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                message="Request failed: {}, {}".format(self.url, e),
            )
            raise

        except JSONDecodeError as e:
            self.service_check(
                "can_connect",
                AgentCheck.CRITICAL,
                message="JSON Parse failed: {}, {}".format(self.url, e),
            )
            raise

        except ValueError as e:
            self.service_check("can_connect", AgentCheck.CRITICAL, message=str(e))
            raise
