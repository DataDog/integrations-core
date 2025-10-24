# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timedelta, timezone

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck
from datadog_checks.nutanix.metrics import CLUSTER_STATS_METRICS, HOST_STATS_METRICS


class NutanixCheck(AgentCheck):
    __NAMESPACE__ = 'nutanix'

    # Prism v4 API requires 120s sampling interval and time lag for rollup completion
    STATS_SAMPLING_INTERVAL = 120

    def __init__(self, name, init_config, instances):
        super(NutanixCheck, self).__init__(name, init_config, instances)

        self.pc_ip = self.instance.get("pc_ip")
        self.pc_port = self.instance.get("pc_port", 9440)

        pc_username = self.instance.get("pc_username")
        pc_password = self.instance.get("pc_password")

        if pc_username and "username" not in self.instance:
            self.instance["username"] = pc_username
        if pc_password and "password" not in self.instance:
            self.instance["password"] = pc_password

        self.base_url = f"{self.pc_ip}:{self.pc_port}"
        if not self.base_url.startswith("http"):
            self.base_url = "https://" + self.base_url

        self.health_check_url = f"{self.base_url}/console"

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
        """Collect metrics from all Nutanix clusters."""
        try:
            clusters = self._get_clusters()
            if not clusters:
                self.log.warning("No clusters found")
                return

            for cluster in clusters:
                if self._is_prism_central_cluster(cluster):
                    self.log.debug("Skipping Prism Central cluster")
                    continue

                self._process_cluster(cluster)
                self._process_nodes(cluster)

        except Exception as e:
            self.log.exception("Error collecting cluster metrics: %s", e)

    def _is_prism_central_cluster(self, cluster):
        """Check if cluster is a Prism Central cluster (should be skipped)."""
        cluster_function = cluster.get("config", {}).get("clusterFunction", [])
        return len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL"

    def _process_cluster(self, cluster):
        """Process and report metrics for a single cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.base_tags + self._extract_cluster_tags(cluster)

        # Report basic cluster metrics
        self._report_cluster_basic_metrics(cluster, cluster_tags)

        # Report time-series stats
        self._report_cluster_stats(cluster_id, cluster_tags)

    def _report_cluster_basic_metrics(self, cluster, cluster_tags):
        """Report basic cluster metrics (counts)."""
        nbr_nodes = int(cluster.get("nodes", {}).get("numberOfNodes", 0))
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))

        self.gauge("cluster.count", 1, tags=cluster_tags)
        self.gauge("cluster.node.count", nbr_nodes, tags=cluster_tags)
        self.gauge("cluster.vm.count", vm_count, tags=cluster_tags)
        self.gauge("cluster.vm.inefficient_count", inefficient_vm_count, tags=cluster_tags)

    def _report_cluster_stats(self, cluster_id, cluster_tags):
        """Report time-series stats for a cluster."""
        stats = self._get_cluster_stats(cluster_id)
        if not stats:
            self.log.debug("No cluster stats returned for cluster %s", cluster_id)
            return

        for key, metric_name in CLUSTER_STATS_METRICS.items():
            entries = stats.get(key, [])
            for entry in entries:
                value = entry.get("value")
                if value is not None:
                    self.gauge(metric_name, value, tags=cluster_tags)

    def _process_nodes(self, cluster):
        """Process and report metrics for all nodes in a cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.base_tags + self._extract_cluster_tags(cluster)

        nodes = self._get_nodes_by_cluster(cluster_id)
        for node in nodes:
            node_id = node.get("extId")
            node_tags = cluster_tags + self._extract_node_tags(node)
            self.gauge("node.count", 1, tags=node_tags)

            stats = self._get_node_stats(cluster_id, node_id)
            if not stats:
                self.log.debug("No host stats returned for node %s", node_id)
                continue

            for key, metric_name in HOST_STATS_METRICS.items():
                entries = stats.get(key, [])
                for entry in entries:
                    value = entry.get("value")
                    if value is not None:
                        self.gauge(metric_name, value, tags=node_tags)



    def _extract_node_tags(self, node):
        """Extract tags from a node object."""
        tags = []

        if tenant_id := node.get("tenantId"):
            tags.append(f"ntnx_tenant_id:{tenant_id}")

        if node_id := node.get("extId"):
            tags.append(f"ntnx_node_id:{node_id}")

        if host_name := node.get("hostName"):
            tags.append(f"ntnx_host_name:{host_name}")

        if host_type := node.get("hostType"):
            tags.append(f"ntnx_host_type:{host_type}")

        # Handle nested hypervisor tags
        hypervisor = node.get("hypervisor", {})
        if hypervisor_name := hypervisor.get("fullName"):
            tags.append(f"ntnx_hypervisor_name:{hypervisor_name}")
        if hypervisor_type := hypervisor.get("type"):
            tags.append(f"ntnx_hypervisor_type:{hypervisor_type}")

        return tags

    def _extract_cluster_tags(self, cluster):
        """Extract tags from a cluster object."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_name = cluster.get("name", "unknown")

        tags = [
            f"ntnx_cluster_id:{cluster_id}",
            f"ntnx_cluster_name:{cluster_name}",
        ]

        if tenant_id := cluster.get("tenantId"):
            tags.append(f"ntnx_tenant_id:{tenant_id}")

        if cluster_profile_id := cluster.get("clusterProfileExtId"):
            tags.append(f"ntnx_cluster_profile_id:{cluster_profile_id}")

        return tags

    def _get_request_data(self, endpoint, params=None):
        """Make an API request to Prism Central and return the data field."""
        url = f"{self.base_url}/{endpoint}"
        response = self.http.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    def _get_clusters(self):
        """Fetch all clusters from Prism Central."""
        return self._get_request_data("api/clustermgmt/v4.0/config/clusters")

    def _get_nodes_by_cluster(self, cluster_id: str):
        """Fetch all nodes/hosts for a specific cluster."""
        return self._get_request_data(f"api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts")

    def _get_cluster_stats(self, cluster_id: str):
        """
        Fetch time-series stats for a specific cluster.

        Prism v4 only emits cluster-level time series at discrete rollups
        and the freshest rollup isn't available immediately.
        For clusters, the practical floor is 120s, and newest points lag ingestion by ~1-2 minutes.
        We use a 120s window and set endTime to now - 120s to ensure data is available.
        """
        start_time, end_time = self._calculate_stats_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statsType": "AVG",
            "$samplingInterval": self.STATS_SAMPLING_INTERVAL,
        }

        return self._get_request_data(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}", params=params)

    def _get_node_stats(self, cluster_id: str, host_id: str):
        """
        Fetch time-series stats for a specific host/node.
        """
        start_time, end_time = self._calculate_stats_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statsType": "AVG",
            "$samplingInterval": self.STATS_SAMPLING_INTERVAL,
        }

        return self._get_request_data(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}/hosts/{host_id}", params=params)

    def _calculate_stats_time_window(self):
        """
        Calculate the time window for stats queries.

        Returns:
            tuple: (start_time_str, end_time_str) in ISO 8601 format
        """
        now = datetime.now(timezone.utc)

        # Set end time to 120 seconds in the past (to allow rollup completion)
        end_time = now - timedelta(seconds=self.STATS_SAMPLING_INTERVAL)

        # Round end_time down to the nearest minute for consistency
        end_time = end_time.replace(second=0, microsecond=0)

        # Start time is 120 seconds (2 minutes) before end_time
        start_time = end_time - timedelta(seconds=self.STATS_SAMPLING_INTERVAL)

        return start_time.isoformat(), end_time.isoformat()
