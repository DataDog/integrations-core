# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.nutanix.metrics import METRICS_MAP


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
                self._process_nodes(cluster)

        except Exception as e:
            self.log.exception("Error collecting cluster metrics: %s", e)

    def _process_cluster(self, cluster):
        cluster_id = cluster.get("extId", "unknown")
        cluster_function = cluster.get("config", {}).get("clusterFunction", [])

        if len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL":
            self.log.debug("detected prism central cluster, skipping cluster.")
            return

        cluster_tags = self.base_tags + self._extract_cluster_tags(cluster)

        nbr_nodes = int(cluster.get("nodes", {}).get("numberOfNodes", 0))
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))

        self.gauge("cluster.count", 1, tags=cluster_tags)
        self.gauge("cluster.node.count", nbr_nodes, tags=cluster_tags)
        self.gauge("cluster.vm.count", vm_count, tags=cluster_tags)
        self.gauge("cluster.vm.inefficient_count", inefficient_vm_count, tags=cluster_tags)

        # Report Cluster Stats
        stats = self._get_cluster_stats(cluster_id)

        for key, metric_name in METRICS_MAP.items():
            if entry := stats.get(key, None):
                for e in entry:
                    # timestamp = e.get("timestamp")
                    value = e.get("value")
                    self.gauge(metric_name, value, tags=cluster_tags)

    def _process_nodes(self, cluster):
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.base_tags + self._extract_cluster_tags(cluster)

        nodes = self._get_nodes_by_cluster(cluster_id)

        for node in nodes:
            node_tags = cluster_tags

            tenant_id = node.get("tenantId")
            node_id = node.get("extId")
            host_name = node.get("hostName")
            host_type = node.get("hostType")
            hypervisor_name = node.get("hypervisor", {}).get("fullName")
            hypervisor_type = node.get("hypervisor", {}).get("type")

            if tenant_id:
                node_tags.append(f"ntnx_tenant_id:{tenant_id}")

            if node_id:
                node_tags.append(f"ntnx_node_id:{node_id}")

            if host_name:
                node_tags.append(f"ntnx_host_name:{host_name}")

            if host_type:
                node_tags.append(f"ntnx_host_type:{host_type}")

            if hypervisor_name:
                node_tags.append(f"ntnx_hypervisor_name:{hypervisor_name}")

            if hypervisor_type:
                node_tags.append(f"ntnx_hypervisor_type:{hypervisor_type}")

            self.gauge("node.count", 1, tags=node_tags)

    def _extract_cluster_tags(self, cluster):
        cluster_id = cluster.get("extId", "unknown")
        cluster_name = cluster.get("name", "unknown")

        cluster_tags = [
            f"ntnx_cluster_id:{cluster_id}",
            f"ntnx_cluster_name:{cluster_name}",
        ]

        tenant_id = cluster.get("tenantId")
        if tenant_id:
            cluster_tags.append(f"ntnx_tenant_id:{tenant_id}")

        upgrade_status = cluster.get("upgradeStatus")
        if upgrade_status:
            cluster_tags.append(f"ntnx_upgrade_status:{upgrade_status.lower()}")

        cluster_profile_ext_id = cluster.get("clusterProfileExtId")
        if cluster_profile_ext_id:
            cluster_tags.append(f"ntnx_cluster_profile_id:{cluster_profile_ext_id}")

        return cluster_tags

    def _get_clusters(self):
        url = f"{self.base_url}/api/clustermgmt/v4.0/config/clusters"
        response = self.http.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def _get_nodes_by_cluster(self, cluster_id: str):
        url = f"{self.base_url}/api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts"
        response = self.http.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def _get_cluster_stats(self, cluster_id: str):
        # Prism v4 only emits cluster-level time series at discrete rollups
        # and the freshest rollup isn't available immediately.
        # For clusters, the practical floor is 120s, and newest points lag ingestion by ~1-2 minutes.

        SAMPLING_INTERVAL = 120

        now = datetime.now(timezone.utc)

        # Set end time to 120 seconds in the past (to allow rollup completion)
        end_time = now - timedelta(seconds=SAMPLING_INTERVAL)

        # Round end_time down to the nearest minute
        end_time = end_time.replace(second=0, microsecond=0)

        start_time = end_time - timedelta(seconds=SAMPLING_INTERVAL)

        # Format times in ISO 8601 format with timezone
        start_time_str = start_time.isoformat()
        end_time_str = end_time.isoformat()

        url = f"{self.base_url}/api/clustermgmt/v4.0/stats/clusters/{cluster_id}"
        params = {
            "$startTime": start_time_str,
            "$endTime": end_time_str,
            "$samplingInterval": SAMPLING_INTERVAL,
        }

        response = self.http.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        return data.get("data", [])
