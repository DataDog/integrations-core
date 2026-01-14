from datetime import datetime, timedelta, timezone

from datadog_checks.base import is_affirmative
from datadog_checks.nutanix.metrics import CLUSTER_STATS_METRICS, HOST_STATS_METRICS, VM_STATS_METRICS


class InfrastructureMonitor:
    def __init__(self, check):
        self.check = check
        self.external_tags = []
        self.cluster_names = {}  # cluster_id -> cluster_name
        self.host_names = {}  # host_id -> host_name

    def collect_cluster_metrics(self):
        """Collect metrics from all Nutanix clusters."""
        try:
            clusters = self._list_clusters()
            if not clusters:
                self.check.log.warning("No clusters found")
                return

            for cluster in clusters:
                # map cluster name
                cluster_id = cluster.get("extId")
                cluster_name = cluster.get("name")
                if cluster_id and cluster_name:
                    self.cluster_names[cluster_id] = cluster_name

                if self._is_prism_central_cluster(cluster):
                    self.check.log.debug("Skipping Prism Central cluster from cluster metrics collection")
                    continue

                self._process_cluster(cluster)
                self._process_hosts(cluster)

        except Exception as e:
            self.check.log.exception("Error collecting cluster metrics: %s", e)

    def collect_vm_metrics(self):
        """Collect metrics from all Nutanix vms."""
        try:
            vms = self._list_vms()
            if not vms:
                self.check.log.warning("No vms found")
                return

            all_vm_stats_dict = self._list_all_vm_stats()

            for vm in vms:
                self._process_vm(vm, all_vm_stats_dict)

        except Exception as e:
            self.check.log.exception("Error collecting vm metrics: %s", e)

    def _is_prism_central_cluster(self, cluster):
        """Check if cluster is a Prism Central cluster (should be skipped)."""
        cluster_function = cluster.get("config", {}).get("clusterFunction", [])
        return len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL"

    def _process_cluster(self, cluster):
        """Process and report metrics for a single cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.check.base_tags + self._extract_cluster_tags(cluster)

        self._report_cluster_basic_metrics(cluster, cluster_tags)
        self._report_cluster_stats(cluster_id, cluster_tags)

    def _process_vm(self, vm, all_vm_stats_dict):
        """Process and report metrics for a single vm."""
        vm_id = vm.get("extId", "unknown")
        hostname = vm.get("name")
        vm_tags = self.check.base_tags + self._extract_vm_tags(vm)

        self._set_external_tags_for_host(hostname, vm_tags)
        self._report_vm_basic_metrics(vm, hostname, vm_tags)
        self._report_vm_stats(vm_id, hostname, vm_tags, all_vm_stats_dict)

    def _report_vm_basic_metrics(self, vm, hostname, vm_tags):
        """Report basic vm metrics (counts)."""
        self.check.gauge("vm.count", 1, hostname=hostname, tags=vm_tags)

    def _report_cluster_basic_metrics(self, cluster, cluster_tags):
        """Report basic cluster metrics (counts)."""
        nbr_nodes = int(cluster.get("nodes", {}).get("numberOfNodes", 0))
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))

        self.check.gauge("cluster.count", 1, tags=cluster_tags)
        self.check.gauge("cluster.nbr_nodes", nbr_nodes, tags=cluster_tags)
        self.check.gauge("cluster.vm.count", vm_count, tags=cluster_tags)
        self.check.gauge("cluster.vm.inefficient_count", inefficient_vm_count, tags=cluster_tags)

    def _report_cluster_stats(self, cluster_id, cluster_tags):
        """Report time-series stats for a cluster."""
        stats = self._get_cluster_stats(cluster_id)
        if not stats:
            self.check.log.debug("No cluster stats returned for cluster %s", cluster_id)
            return

        for key, metric_name in CLUSTER_STATS_METRICS.items():
            entries = stats.get(key, [])
            for entry in entries:
                value = entry.get("value")
                if value is not None:
                    self.check.gauge(metric_name, value, tags=cluster_tags)

    def _report_vm_stats(self, vm_id, hostname, vm_tags, all_vm_stats_dict):
        """Report time-series stats for a vm."""
        stats = all_vm_stats_dict.get(vm_id)
        if not stats:
            self.check.log.debug("No vm stats returned for vm %s", vm_id)
            return

        for key, metric_name in VM_STATS_METRICS.items():
            for s in stats:
                value = s.get(key)
                if value is not None:
                    self.check.gauge(metric_name, value, hostname=hostname, tags=vm_tags)

    def _process_hosts(self, cluster):
        """Process and report metrics for all hosts in a cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.check.base_tags + self._extract_cluster_tags(cluster)

        hosts = self._list_hosts_by_cluster(cluster_id)
        for host in hosts:
            host_id = host.get("extId")
            hostname = host.get("hostName")

            # map host name
            if host_id and hostname:
                self.host_names[host_id] = hostname

            host_tags = cluster_tags + self._extract_host_tags(host)
            self.check.gauge("host.count", 1, hostname=hostname, tags=host_tags)

            self._set_external_tags_for_host(hostname, host_tags)

            stats = self._get_host_stats(cluster_id, host_id)
            if not stats:
                self.check.log.debug("No host stats returned for host %s", host_id)
                continue

            for key, metric_name in HOST_STATS_METRICS.items():
                entries = stats.get(key, [])
                for entry in entries:
                    value = entry.get("value")
                    if value is not None:
                        self.check.gauge(metric_name, value, hostname=hostname, tags=host_tags)

    def _extract_host_tags(self, host):
        """Extract tags from a host object."""
        tags = []

        tags.append("ntnx_type:host")

        if tenant_id := host.get("tenantId"):
            tags.append(f"ntnx_tenant_id:{tenant_id}")

        if host_id := host.get("extId"):
            tags.append(f"ntnx_host_id:{host_id}")

        if host_name := host.get("hostName"):
            tags.append(f"ntnx_host_name:{host_name}")

        if host_type := host.get("hostType"):
            tags.append(f"ntnx_host_type:{host_type}")

        # hypervisor tags
        hypervisor = host.get("hypervisor", {})
        if hypervisor_name := hypervisor.get("fullName"):
            tags.append(f"ntnx_hypervisor_name:{hypervisor_name}")
        if hypervisor_type := hypervisor.get("type"):
            tags.append(f"ntnx_hypervisor_type:{hypervisor_type}")

        return tags

    def _extract_cluster_tags(self, cluster):
        """Extract tags from a cluster object."""

        tags = []

        cluster_id = cluster.get("extId")
        if cluster_id:
            tags.append(f"ntnx_cluster_id:{cluster_id}")

        cluster_name = cluster.get("name")
        if cluster_name:
            tags.append(f"ntnx_cluster_name:{cluster_name}")

        if tenant_id := cluster.get("tenantId"):
            tags.append(f"ntnx_tenant_id:{tenant_id}")

        if cluster_profile_id := cluster.get("clusterProfileExtId"):
            tags.append(f"ntnx_cluster_profile_id:{cluster_profile_id}")

        return tags

    def _extract_vm_tags(self, vm):
        """Extract tags from a VM object."""
        tags = []

        tags.append("ntnx_type:vm")

        vm_id = vm.get("extId")
        if vm_id:
            tags.append(f"ntnx_vm_id:{vm_id}")

        vm_name = vm.get("name")
        if vm_name:
            tags.append(f"ntnx_vm_name:{vm_name}")

        vm_generation_uuid = vm.get("generationUuid")
        if vm_generation_uuid:
            tags.append(f"ntnx_generation_uuid:{vm_generation_uuid}")

        categories = vm.get("categories")
        if categories:
            for c in categories:
                category_id = c.get("extId")
                tags.append(f"ntnx_category_id:{category_id}")

        owner_id = vm.get("ownershipInfo", {}).get("owner", {}).get("extId")
        if owner_id:
            tags.append(f"ntnx_owner_id:{owner_id}")

        host_id = vm.get("host", {}).get("extId")
        if host_id:
            tags.append(f"ntnx_host_id:{host_id}")
            # add host name
            if host_id in self.host_names:
                tags.append(f"ntnx_host_name:{self.host_names[host_id]}")

        cluster_id = vm.get("cluster", {}).get("extId")
        if cluster_id:
            tags.append(f"ntnx_cluster_id:{cluster_id}")
            # add cluster name
            if cluster_id in self.cluster_names:
                tags.append(f"ntnx_cluster_name:{self.cluster_names[cluster_id]}")

        availability_zone_id = vm.get("availabilityZone", {}).get("extId")
        if availability_zone_id:
            tags.append(f"ntnx_availability_zone_id:{availability_zone_id}")

        is_agent_vm = is_affirmative(vm.get("isAgentVm"))
        if is_agent_vm:
            tags.append(f"ntnx_is_agent_vm:{is_agent_vm}")

        return tags

    def _set_external_tags_for_host(self, hostname: str, tags: list[str]):
        for i, entry in enumerate(self.external_tags):
            if entry[0] == hostname:
                self.external_tags[i] = (hostname, {self.check.__NAMESPACE__: tags})
                return

        self.external_tags.append((hostname, {self.check.__NAMESPACE__: tags}))

    def _list_clusters(self):
        """Fetch all clusters from Prism Central."""
        return self.check._get_paginated_request_data("api/clustermgmt/v4.0/config/clusters")

    def _list_vms(self):
        """Fetch all clusters from Prism Central."""
        return self.check._get_paginated_request_data("api/vmm/v4.0/ahv/config/vms")

    def _list_hosts_by_cluster(self, cluster_id: str):
        """Fetch all hosts/hosts for a specific cluster."""
        return self.check._get_paginated_request_data(f"api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts")

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
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
        }

        return self.check._get_request_data(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}", params=params)

    def _get_host_stats(self, cluster_id: str, host_id: str):
        """
        Fetch time-series stats for a specific host.
        """
        start_time, end_time = self._calculate_stats_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
        }

        return self.check._get_request_data(
            f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}/hosts/{host_id}", params=params
        )

    def _list_all_vm_stats(self):
        """
        Fetch time-series stats for all VMs and return as a dictionary.

        Returns:
            dict: Dictionary mapping vmExtId -> stats array
        """
        start_time, end_time = self._calculate_stats_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
            "$select": "*",
        }

        vm_stats_data = self.check._get_paginated_request_data("api/vmm/v4.0/ahv/stats/vms/", params=params)

        # Create dictionary mapping vmExtId -> stats
        all_vm_stats_dict = {}
        for vm_stat in vm_stats_data:
            vm_id = vm_stat.get("extId")
            stats = vm_stat.get("stats", [])
            if vm_id:
                all_vm_stats_dict[vm_id] = stats

        return all_vm_stats_dict

    def _calculate_stats_time_window(self):
        """
        Calculate the time window for stats queries.

        Returns:
            tuple: (start_time_str, end_time_str) in ISO 8601 format
        """
        now = datetime.now(timezone.utc)

        end_time = now - timedelta(seconds=self.check.sampling_interval)

        # Round end_time down to the nearest minute for consistency
        end_time = end_time.replace(second=0, microsecond=0)

        start_time = end_time - timedelta(seconds=self.check.sampling_interval)

        return start_time.isoformat(), end_time.isoformat()
