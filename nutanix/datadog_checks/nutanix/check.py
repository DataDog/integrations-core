# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck


class NutanixCheck(AgentCheck):
    __NAMESPACE__ = 'nutanix'

    def __init__(self, name, init_config, instances):
        super(NutanixCheck, self).__init__(name, init_config, instances)

        self.pc_ip = self.instance.get("pc_ip")
        self.pc_port = self.instance.get("pc_port", 9440)
        self.pc_username = self.instance.get("pc_username") or self.instance.get("username")
        self.pc_password = self.instance.get("pc_password") or self.instance.get("password")

        # Build the base URL for Prism Central
        self.base_url = f"https://{self.pc_ip}:{self.pc_port}"
        self.health_check_url = f"{self.base_url}/console"

        # Common tags for all metrics
        self.tags.append(f"prism_central:{self.pc_ip}")

    def check(self, _):
        # type: (Any) -> None
        """Main check method called by the agent."""

        # Health check
        if not self._check_health():
            return

        # Collect cluster metrics
        if self.collect_cluster_metrics:
            self._collect_cluster_metrics()

    def _check_health(self):
        # type: () -> bool
        """
        Check if Prism Central is reachable.

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = self.http.get(self.health_check_url)
            response.raise_for_status()
            self.gauge("health.up", 1, tags=self.tags)
            self.log.debug("Health check passed for Prism Central at %s:%s", self.pc_ip, self.pc_port)
            return True

        except (HTTPError, InvalidURL, ConnectionError, Timeout) as e:
            self.log.error("Cannot connect to Prism Central at %s:%s : %s", self.pc_ip, self.pc_port, str(e))
            self.gauge("health.up", 0, tags=self.tags)
            return False

        except Exception as e:
            self.log.exception("Unexpected error when connecting to Prism Central: %s", e)
            self.gauge("health.up", 0, tags=self.tags)
            return False

    def _collect_cluster_metrics(self):
        """Collect cluster-level metrics."""
        try:
            clusters = self._get_clusters()
            if not clusters:
                raise Exception("No clusters found")
                self.log.debug("No clusters found")
                return

            for cluster in clusters:
                self._process_cluster(cluster)

        except Exception as e:
            self.log.exception("Error collecting cluster metrics: %s", e)

    def _get_clusters(self):
        endpoint = f"{self.base_url}/api/clustermgmt/v4.0/config/clusters"

        try:
            response = self.http.get(endpoint)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            raise Exception("Failed to fetch clusters: %s", e)
            return []

    def _process_cluster(self, cluster):
        cluster_id = cluster.get("extId")
        cluster_name = cluster.get("name", "unknown")

        if not cluster_id:
            self.log.warning("Cluster missing extId, skipping")
            return

        cluster_tags = self.tags + [
            f"nutanix_cluster_id:{cluster_id}",
            f"nutanix_cluster_name:{cluster_name}",
        ]
