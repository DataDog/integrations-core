# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta, timezone
from typing import Literal

from datadog_checks.base import is_affirmative
from datadog_checks.nutanix.metrics import CLUSTER_STATS_METRICS, HOST_STATS_METRICS, VM_STATS_METRICS

# Entity types for metrics counting
EntityType = Literal['cluster', 'host', 'vm']


class InfrastructureMonitor:
    def __init__(self, check):
        self.check = check
        self.external_tags = []
        self.cluster_names = {}  # cluster_id -> cluster_name
        self.host_names = {}  # host_id -> host_name
        self.collection_time_window = None
        # Metrics counters
        self.cluster_metrics_count = 0
        self.host_metrics_count = 0
        self.vm_metrics_count = 0

    def reset_state(self) -> None:
        """Reset all caches and counters for a new collection run."""
        self.cluster_names = {}
        self.host_names = {}
        self.external_tags = []
        self.collection_time_window = None
        self.cluster_metrics_count = 0
        self.host_metrics_count = 0
        self.vm_metrics_count = 0

    def collect_cluster_metrics(self) -> None:
        """Collect metrics from all Nutanix clusters."""
        pc_label = f"PC:{self.check.pc_ip}"

        try:
            clusters = self._list_clusters()
            if not clusters:
                self.check.log.warning("[%s] No clusters found", pc_label)
                return

            self.check.log.info("[%s] Found %d clusters", pc_label, len(clusters))

            # Cache cluster names for VM/audit tagging
            for cluster in clusters:
                cluster_id, cluster_name = cluster.get("extId"), cluster.get("name")
                if cluster_id and cluster_name:
                    self.cluster_names[cluster_id] = cluster_name

            # Process each cluster
            processed, skipped = 0, 0
            for cluster in clusters:
                cluster_name = cluster.get("name", "unknown")

                if self._is_prism_central_cluster(cluster):
                    self.check.log.info("[%s] Skipping Prism Central cluster: %s", pc_label, cluster_name)
                    skipped += 1
                    continue

                self.check.log.info("[%s][%s] Processing cluster", pc_label, cluster_name)
                self._process_cluster(cluster, pc_label)

                # Fetch VM stats for entire cluster in one call
                cluster_id = cluster.get("extId")
                vm_stats = self._get_vm_stats_by_cluster_id(cluster_id, pc_label, cluster_name)
                self.check.log.debug("[%s][%s] Fetched stats for %d VMs", pc_label, cluster_name, len(vm_stats))

                self._process_hosts(cluster, vm_stats, cluster_name, pc_label)
                processed += 1

            if skipped > 0:
                self.check.log.info("[%s] Processed %d clusters (%d skipped)", pc_label, processed, skipped)
            else:
                self.check.log.info("[%s] Processed %d clusters", pc_label, processed)

        except Exception as e:
            self.check.log.exception("[%s] Failed to collect cluster metrics: %s", pc_label, e)

    def _is_prism_central_cluster(self, cluster: dict) -> bool:
        """Check if cluster is a Prism Central cluster (should be skipped).

        Args:
            cluster: Cluster object from API

        Returns:
            True if this is a Prism Central cluster
        """
        cluster_function = cluster.get("config", {}).get("clusterFunction", [])
        return len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL"

    def _process_cluster(self, cluster: dict, pc_label: str) -> None:
        """Process and report metrics for a single cluster.

        Args:
            cluster: Cluster object from API
            pc_label: Prism Central label for logging
        """
        cluster_id = cluster.get("extId", "unknown")
        cluster_name = cluster.get("name", "unknown")
        cluster_tags = self.check.base_tags + self._extract_cluster_tags(cluster)

        self._report_cluster_basic_metrics(cluster, cluster_tags)
        self._report_cluster_stats(cluster_name, cluster_id, cluster_tags, pc_label)

    def _process_vm(self, vm: dict, vm_stats_dict: dict, cluster_name: str, pc_label: str) -> None:
        """Process and report metrics for a single VM.

        Args:
            vm: VM object from API
            vm_stats_dict: Dictionary mapping VM IDs to their stats
            cluster_name: Name of the cluster
            pc_label: Prism Central label for logging
        """
        vm_id = vm.get("extId", "unknown")
        hostname = vm.get("name")
        vm_tags = self.check.base_tags + self._extract_vm_tags(vm)

        self._set_external_tags_for_host(hostname, vm_tags)
        self._report_vm_basic_metrics(vm, hostname, vm_tags)
        self._report_vm_stats(vm_id, hostname, vm_tags, vm_stats_dict, cluster_name, pc_label)

    def _report_vm_basic_metrics(self, vm: dict, hostname: str, vm_tags: list[str]) -> None:
        """Report basic VM metrics (counts).

        Args:
            vm: VM object from API
            hostname: VM hostname
            vm_tags: Tags to apply to metrics
        """
        self.check.gauge("vm.count", 1, hostname=hostname, tags=vm_tags)

    def _report_cluster_basic_metrics(self, cluster: dict, cluster_tags: list[str]) -> None:
        """Report basic cluster metrics (counts).

        Args:
            cluster: Cluster object from API
            cluster_tags: Tags to apply to metrics
        """
        nbr_nodes = int(cluster.get("nodes", {}).get("numberOfNodes", 0))
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))

        self.check.gauge("cluster.count", 1, tags=cluster_tags)
        self.check.gauge("cluster.nbr_nodes", nbr_nodes, tags=cluster_tags)
        self.check.gauge("cluster.vm.count", vm_count, tags=cluster_tags)
        self.check.gauge("cluster.vm.inefficient_count", inefficient_vm_count, tags=cluster_tags)

    def _report_stats(
        self,
        entity_name: str,
        stats: dict | list,
        metrics_map: dict[str, str],
        tags: list[str],
        log_level: str = "info",
        hostname: str | None = None,
        entity_type: EntityType | None = None,
    ) -> None:
        """Generic stats reporter for any entity type (cluster/host/VM).

        Args:
            entity_name: Name of the entity for logging
            stats: Stats dict or list from API
            metrics_map: Dict mapping stat keys to metric names
            tags: Tags for the metrics
            log_level: Logging level for summary (info/debug)
            hostname: Optional hostname for VM metrics
            entity_type: Type of entity ('cluster', 'host', 'vm') for counting
        """
        if not stats:
            self.check.log.warning("No stats returned for %s", entity_name)
            return

        # Handle list vs dict stats (VMs return list, others return dict)
        is_list_stats = isinstance(stats, list)
        sample_stats = stats[0] if is_list_stats else stats

        actual_keys = set(sample_stats.keys())
        expected_keys = set(metrics_map.keys())
        matching_keys = actual_keys & expected_keys
        missing_keys = expected_keys - actual_keys

        # Submit metrics
        metrics_submitted = self._submit_stats_metrics(stats, metrics_map, tags, hostname, is_list_stats)

        # Track metrics by type
        if entity_type == 'cluster':
            self.cluster_metrics_count += metrics_submitted
        elif entity_type == 'host':
            self.host_metrics_count += metrics_submitted
        elif entity_type == 'vm':
            self.vm_metrics_count += metrics_submitted

        # Log summary
        log_fn = getattr(self.check.log, log_level)
        log_fn(
            "%s - returned_keys=%d, expected_keys=%d, matching=%d, missing=%d, metrics_submitted=%d",
            entity_name,
            len(actual_keys),
            len(expected_keys),
            len(matching_keys),
            len(missing_keys),
            metrics_submitted,
        )

        if metrics_submitted == 0:
            self.check.log.warning("%s - No metrics submitted. API keys: %s", entity_name, list(actual_keys)[:5])
            self.check.log.trace("%s - Full stats payload: %s", entity_name, stats)

    def _submit_stats_metrics(
        self, stats: dict | list, metrics_map: dict[str, str], tags: list[str], hostname: str | None, is_list: bool
    ) -> int:
        """Submit metrics from stats payload.

        Args:
            stats: Stats dict or list from API
            metrics_map: Dict mapping stat keys to metric names
            tags: Tags to apply to metrics
            hostname: Optional hostname for VM metrics
            is_list: Whether stats is a list (True) or dict (False)

        Returns:
            Number of metrics submitted
        """
        metrics_submitted = 0

        for key, metric_name in metrics_map.items():
            if is_list:
                # VM stats: list of stat entries
                for entry in stats:
                    value = entry.get(key)
                    if value is not None:
                        self.check.gauge(metric_name, value, hostname=hostname, tags=tags)
                        metrics_submitted += 1
            else:
                # Cluster/Host stats: dict with arrays of values
                entries = stats.get(key, [])
                for entry in entries:
                    value = entry.get("value")
                    if value is not None:
                        self.check.gauge(metric_name, value, hostname=hostname, tags=tags)
                        metrics_submitted += 1

        return metrics_submitted

    def _report_cluster_stats(self, cluster_name: str, cluster_id: str, cluster_tags: list[str], pc_label: str) -> None:
        """Report time-series stats for a cluster.

        Args:
            cluster_name: Name of the cluster
            cluster_id: Cluster ID
            cluster_tags: Tags to apply to metrics
            pc_label: Prism Central label for logging
        """
        stats = self._get_cluster_stats(cluster_id)
        self._report_stats(
            f"[{pc_label}][{cluster_name}] Cluster",
            stats,
            CLUSTER_STATS_METRICS,
            cluster_tags,
            log_level="info",
            entity_type="cluster",
        )

    def _report_vm_stats(
        self, vm_id: str, hostname: str, vm_tags: list[str], vm_stats_dict: dict, cluster_name: str, pc_label: str
    ) -> None:
        """Report time-series stats for a VM.

        Args:
            vm_id: VM ID
            hostname: VM hostname
            vm_tags: Tags to apply to metrics
            vm_stats_dict: Dictionary mapping VM IDs to their stats
            cluster_name: Name of the cluster
            pc_label: Prism Central label for logging
        """
        stats = vm_stats_dict.get(vm_id)
        if stats:
            self._report_stats(
                f"[{pc_label}][{cluster_name}] VM {hostname}",
                stats,
                VM_STATS_METRICS,
                vm_tags,
                log_level="debug",
                hostname=hostname,
                entity_type="vm",
            )

    def _process_hosts(self, cluster: dict, cluster_vm_stats_dict: dict, cluster_name: str, pc_label: str) -> None:
        """Process and report metrics for all hosts in a cluster.

        Args:
            cluster: Cluster object from API
            cluster_vm_stats_dict: Dictionary mapping VM IDs to their stats
            cluster_name: Name of the cluster
            pc_label: Prism Central label for logging
        """
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.check.base_tags + self._extract_cluster_tags(cluster)

        hosts = self._list_hosts_by_cluster(cluster_id)
        self.check.log.info("[%s][%s] Processing %d hosts", pc_label, cluster_name, len(hosts))

        total_vms = sum(
            self._process_single_host(host, cluster_id, cluster_tags, cluster_vm_stats_dict, cluster_name, pc_label)
            for host in hosts
        )

        self.check.log.info("[%s][%s] Processed %d hosts and %d VMs", pc_label, cluster_name, len(hosts), total_vms)

    def _process_single_host(
        self,
        host: dict,
        cluster_id: str,
        cluster_tags: list[str],
        cluster_vm_stats_dict: dict,
        cluster_name: str,
        pc_label: str,
    ) -> int:
        """Process a single host and its VMs.

        Returns:
            Number of VMs processed on this host
        """
        host_id = host.get("extId")
        host_name = host.get("hostName")

        if not host_id:
            self.check.log.warning("[%s][%s] Host %s has no extId, skipping", pc_label, cluster_name, host_name)
            return 0

        # Cache host name for VM tagging
        if host_name:
            self.host_names[host_id] = host_name

        # Report host metrics
        host_tags = cluster_tags + self._extract_host_tags(host)
        self.check.gauge("host.count", 1, hostname=host_name, tags=host_tags)
        self._set_external_tags_for_host(host_name, host_tags)

        # Report host stats
        stats = self._get_host_stats(cluster_id, host_id)
        if stats:
            self._report_stats(
                f"[{pc_label}][{cluster_name}] Host {host_name}",
                stats,
                HOST_STATS_METRICS,
                host_tags,
                log_level="info",
                hostname=host_name,
                entity_type="host",
            )

        # Process VMs on this host
        vms = self._list_vms_by_host(host_id)
        self.check.log.debug("[%s][%s] Host %s has %d VMs", pc_label, cluster_name, host_name, len(vms))

        for vm in vms:
            self._process_vm(vm, cluster_vm_stats_dict, cluster_name, pc_label)

        return len(vms)

    def _extract_host_tags(self, host: dict) -> list[str]:
        """Extract tags from a host object.

        Args:
            host: Host object from API

        Returns:
            List of tags
        """
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

    def _extract_cluster_tags(self, cluster: dict) -> list[str]:
        """Extract tags from a cluster object.

        Args:
            cluster: Cluster object from API

        Returns:
            List of tags
        """
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

    def _extract_vm_tags(self, vm: dict) -> list[str]:
        """Extract tags from a VM object.

        Args:
            vm: VM object from API

        Returns:
            List of tags
        """
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

    def _set_external_tags_for_host(self, hostname: str, tags: list[str]) -> None:
        """Set or update external tags for a host.

        Args:
            hostname: Host hostname
            tags: List of tags to apply
        """
        for i, entry in enumerate(self.external_tags):
            if entry[0] == hostname:
                self.external_tags[i] = (hostname, {self.check.__NAMESPACE__: tags})
                return

        self.external_tags.append((hostname, {self.check.__NAMESPACE__: tags}))

    def _list_clusters(self) -> list[dict]:
        """Fetch all clusters from Prism Central.

        Returns:
            List of cluster objects
        """
        clusters = self.check._get_paginated_request_data("api/clustermgmt/v4.0/config/clusters")
        return clusters

    def _list_vms_by_host(self, host_id: str) -> list[dict]:
        """Fetch all VMs for a specific host.

        Args:
            host_id: Host ID

        Returns:
            List of VM objects
        """
        params = {"$filter": f"host/extId eq '{host_id}'"}
        vms = self.check._get_paginated_request_data("api/vmm/v4.0/ahv/config/vms", params=params)
        return vms

    def _list_hosts_by_cluster(self, cluster_id: str) -> list[dict]:
        """Fetch all hosts for a specific cluster.

        Args:
            cluster_id: Cluster ID

        Returns:
            List of host objects
        """
        hosts = self.check._get_paginated_request_data(f"api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts")
        return hosts

    def _get_cluster_stats(self, cluster_id: str) -> dict:
        """Fetch time-series stats for a specific cluster.

        Prism v4 only emits cluster-level time series at discrete rollups
        and the freshest rollup isn't available immediately.
        For clusters, the practical floor is 120s, and newest points lag ingestion by ~1-2 minutes.
        We use a 120s window and set endTime to now - 120s to ensure data is available.

        Args:
            cluster_id: Cluster ID

        Returns:
            Dict of stats from a single time period
        """
        start_time, end_time = self._get_collection_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
        }

        result = self.check._get_request_data(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}", params=params)
        return result

    def _get_host_stats(self, cluster_id: str, host_id: str) -> dict:
        """Fetch time-series stats for a specific host.

        Args:
            cluster_id: Cluster ID
            host_id: Host ID

        Returns:
            Dict of stats from a single time period
        """
        start_time, end_time = self._get_collection_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
        }

        result = self.check._get_request_data(
            f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}/hosts/{host_id}", params=params
        )
        return result

    def _get_vm_stats_by_cluster_id(self, cluster_id: str, pc_label: str, cluster_name: str) -> dict[str, list]:
        """Fetch time-series stats for all VMs in a cluster.

        Args:
            cluster_id: Cluster ID
            pc_label: Prism Central label for logging
            cluster_name: Name of the cluster

        Returns:
            Dictionary mapping VM IDs to their stats lists
        """
        start_time, end_time = self._get_collection_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
            "$filter": f"stats/cluster eq '{cluster_id}'",
            "$select": "*",
        }

        vm_stats_data = self.check._get_paginated_request_data("api/vmm/v4.0/ahv/stats/vms", params=params)

        vm_stats_dict = {}
        for vm_stat in vm_stats_data:
            vm_id = vm_stat.get("extId")
            stats = vm_stat.get("stats", [])
            if vm_id:
                vm_stats_dict[vm_id] = stats

        self.check.log.debug(
            "[%s][%s] Retrieved %d VM stats from API for cluster_id=%s",
            pc_label,
            cluster_name,
            len(vm_stats_dict),
            cluster_id,
        )
        return vm_stats_dict

    def _calculate_collection_time_window(self) -> tuple[str, str]:
        """Calculate the time window [start_time, end_time] for Nutanix v4 API queries.

        Returns:
            Tuple of (start_time_str, end_time_str) in ISO 8601 format
        """
        now = datetime.now(timezone.utc)
        end_time = now - timedelta(seconds=self.check.sampling_interval)
        start_time = end_time - timedelta(seconds=self.check.sampling_interval)

        return start_time.isoformat(), end_time.isoformat()

    def init_collection_time_window(self) -> None:
        """Set the collection time window once per check run."""
        self.collection_time_window = self._calculate_collection_time_window()

    def _get_collection_time_window(self) -> tuple[str, str]:
        """Return cached collection time window for this check run.

        Returns:
            Tuple of (start_time_str, end_time_str) in ISO 8601 format
        """
        if self.collection_time_window is None:
            self.collection_time_window = self._calculate_collection_time_window()
        return self.collection_time_window
