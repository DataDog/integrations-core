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
        self.pc_username = self.instance.get("pc_username")
        self.pc_password = self.instance.get("pc_password")

        # Build the base URL for Prism Central
        self.base_url = f"{self.pc_ip}:{self.pc_port}"

        if not self.base_url.startswith("http"):
            self.base_url = "https://" + self.base_url

        self.health_check_url = f"{self.base_url}/console"

        # Common tags for all metrics
        self.base_tags = self.instance.get("tags", [])
        self.base_tags.append(f"prism_central:{self.pc_ip}")

    def check(self, _):
        if not self._check_health():
            return

        self._collect_cluster_metrics()

    def _check_health(self):
        try:
            response = self.http.get(self.health_check_url)
            response.raise_for_status()
            self.gauge("health.up", 1, tags=self.base_tags)
            self.log.debug("Health check passed for Prism Central at %s:%s", self.pc_ip, self.pc_port)
            return True

        except (HTTPError, InvalidURL, ConnectionError, Timeout) as e:
            self.log.error("Cannot connect to Prism Central at %s:%s : %s", self.pc_ip, self.pc_port, str(e))
            self.gauge("health.up", 0, tags=self.base_tags)
            return False

        except Exception as e:
            self.log.exception("Unexpected error when connecting to Prism Central: %s", e)
            self.gauge("health.up", 0, tags=self.base_tags)
            return False

    def _collect_cluster_metrics(self):
        try:
            clusters = self._get_clusters()
            if not clusters:
                self.log.warning("No clusters found")
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
        tenant_id = cluster.get("tenantId")
        cluster_id = cluster.get("extId")
        cluster_name = cluster.get("name", "unknown")

        config = cluster.get("config")
        cluster_function = config.get("clusterFunction", [])

        if len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL":
            self.log.debug("detected prism central cluster, skipping cluster.")
            return

        nodes = cluster.get("nodes", {})
        nbr_nodes = int(nodes.get("numberOfNodes", 0))
        node_list = nodes.get("nodeList", [])

        upgrade_status = cluster.get("upgradeStatus").lower()
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))
        cluster_profile_ext_id = cluster.get("clusterProfileExtId")

        # Build cluster tags
        cluster_tags = self.base_tags + [
            f"ntnx_cluster_id:{cluster_id}",
            f"ntnx_cluster_name:{cluster_name}",
        ]

        if tenant_id:
            cluster_tags.append(f"ntnx_tenant_id:{tenant_id}")

        if upgrade_status:
            cluster_tags.append(f"ntnx_upgrade_status:{upgrade_status}")

        if cluster_profile_ext_id:
            cluster_tags.append(f"ntnx_cluster_profile_id:{cluster_profile_ext_id}")

        self.gauge("cluster.count", 1, tags=cluster_tags)
        self.gauge("cluster.node.count", nbr_nodes, tags=cluster_tags)
        self.gauge("cluster.vm.count", vm_count, tags=cluster_tags)
        self.gauge("cluster.vm.inefficient_count", inefficient_vm_count, tags=cluster_tags)
