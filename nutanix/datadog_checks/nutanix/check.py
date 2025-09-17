# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from json import JSONDecodeError
from typing import Any  # noqa: F401

import ntnx_prism_py_client as nutanix
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck  # noqa: F401

# from datadog_checks.base.utils.db import QueryManager


class NutanixCheck(AgentCheck):
    # This will be the prefix of every metric the integration sends
    __NAMESPACE__ = 'nutanix'

    def __init__(self, name, init_config, instances):
        super(NutanixCheck, self).__init__(name, init_config, instances)

        self.pc_ip = self.instance.get("pc_ip")
        self.pc_port = self.instance.get("pc_port", 9440)
        self.pc_username = self.instance.get("pc_username")
        self.pc_password = self.instance.get("pc_password")
        self.pc_api_key = self.instance.get("pc_api_key")

        # Build the base URL for Prism Centra
        self.base_url = f"https://{self.pc_ip}:{self.pc_port}"
        self.health_check_url = f"{self.base_url}/console"

        self._setup_pc_client()

    def _setup_pc_client(self):
        config = nutanix.Configuration()
        config.host = self.pc_ip
        config.port = self.pc_port
        config.username = self.pc_username
        config.password = self.pc_password
        self.pc_client = nutanix.ApiClient(configuration=config)

    def check(self, _):
        # type: (Any) -> None

        # First, perform a health check on the Prism Central
        try:
            # Try to connect to the Prism Central API
            response = self.http.get(self.health_check_url)
            response.raise_for_status()

            self.count("health.up", 1)

        except (HTTPError, InvalidURL, ConnectionError, Timeout) as e:
            # Connection failed
            error_msg = f"Cannot connect to Prism Central at {self.pc_ip}:{self.pc_port}: {e}"
            self.log.error(error_msg)

            self.count("health.up", 0)
            raise

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error when connecting to Prism Central: {e}"
            self.log.error(error_msg, exc_info=True)

            self.count("health.up", 0)
            raise

        try:
            # Try to connect to the Prism Central API
            response = self.http.get(self.base_url + "/api/clustermgmt/v4.0/config/clusters")
            response.raise_for_status()

            if response["data"]:
                for cluster in response["data"]:
                    self.gauge("clusters.count", 1, tags=[f"cluster_id:{cluster['extId']}"])

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error when collecting clusters: {e}"
            self.log.error(error_msg, exc_info=True)
            raise
