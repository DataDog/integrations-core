# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Literal

from datadog_checks.base import is_affirmative
from datadog_checks.nutanix.metrics import CLUSTER_STATS_METRICS, HOST_STATS_METRICS, VM_STATS_METRICS
from datadog_checks.nutanix.resource_filters import should_collect_resource

if TYPE_CHECKING:
    from datadog_checks.nutanix.check import NutanixCheck

# Entity types for metrics counting
EntityType = Literal['cluster', 'host', 'vm']


@dataclass
class ClusterCapacity:
    """Accumulator for cluster-level capacity metrics aggregated from hosts and VMs."""

    # Host capacity totals
    total_cores: int = 0
    total_threads: int = 0
    total_memory_bytes: int = 0

    # VM allocation totals
    vcpus_allocated: int = 0
    memory_allocated_bytes: int = 0

    def reset(self) -> None:
        """Reset all accumulators to zero."""
        self.total_cores = 0
        self.total_threads = 0
        self.total_memory_bytes = 0
        self.vcpus_allocated = 0
        self.memory_allocated_bytes = 0

    def add_host(self, cores: int, threads: int, memory_bytes: int) -> None:
        """Add host capacity to cluster totals."""
        self.total_cores += cores
        self.total_threads += threads
        self.total_memory_bytes += memory_bytes

    def add_vm(self, vcpus: int, memory_bytes: int) -> None:
        """Add VM allocation to cluster totals."""
        self.vcpus_allocated += vcpus
        self.memory_allocated_bytes += memory_bytes


class InfrastructureMonitor:
    def __init__(self, check: NutanixCheck):
        self.check = check
        self.external_tags = []
        self.cluster_names = {}  # cluster_id -> cluster_name
        self.host_names = {}  # host_id -> host_name
        self.categories = {}  # category_id -> category object
        self.collection_time_window = None
        # Metrics counters
        self.cluster_metrics_count = 0
        self.host_metrics_count = 0
        self.vm_metrics_count = 0
        # Cluster capacity accumulator
        self._cluster_capacity = ClusterCapacity()
        self._vms_by_host: dict[str, list[dict]] = {}

    def reset_state(self) -> None:
        """Reset all caches and counters for a new collection run."""
        self.cluster_names = {}
        self.host_names = {}
        self.categories = {}
        self.external_tags = []
        self.collection_time_window = None
        self.cluster_metrics_count = 0
        self.host_metrics_count = 0
        self.vm_metrics_count = 0
        self._cluster_capacity.reset()
        self._vms_by_host = {}

    def collect_cluster_metrics(self) -> None:
        """Collect metrics from all Nutanix clusters."""
        pc_label = f"PC:{self.check.pc_ip}"

        # Fetch and cache categories for VM tagging
        try:
            categories = self._list_categories()
        except Exception:
            self.check.log.exception("[%s] Failed to fetch categories", pc_label)
            categories = []

        self.check.log.info("[%s] Found %d categories", pc_label, len(categories))
        for category in categories:
            category_id = category.get("extId")
            if category_id and should_collect_resource(
                'category', category, self.check.resource_filters, self.check.log
            ):
                self.categories[category_id] = category

        try:
            clusters = self._list_clusters()
        except Exception:
            self.check.log.exception("[%s] Failed to fetch clusters, aborting", pc_label)
            return

        if not clusters:
            self.check.log.warning("[%s] No clusters found", pc_label)
            return

        self.check.log.info("[%s] Found %d clusters", pc_label, len(clusters))

        # Cache cluster names for VM/audit tagging
        for cluster in clusters:
            cluster_id, cluster_name = cluster.get("extId"), cluster.get("name")
            if cluster_id and cluster_name:
                self.cluster_names[cluster_id] = cluster_name

        if self.check.batch_vm_collection:
            try:
                self._build_vms_by_host_cache()
                self.check.log.info("[%s] Cached VMs for %d hosts", pc_label, len(self._vms_by_host))
            except Exception:
                self.check.log.exception("[%s] Failed to fetch all VMs", pc_label)

        # Process each cluster
        processed, skipped = 0, 0
        for cluster in clusters:
            cluster_name = cluster.get("name", "unknown")

            if self._is_prism_central_cluster(cluster):
                self.check.log.info("[%s] Skipping Prism Central cluster: %s", pc_label, cluster_name)
                skipped += 1
                continue

            if not should_collect_resource("cluster", cluster, self.check.resource_filters, self.check.log):
                skipped += 1
                continue

            self.check.log.info("[%s][%s] Processing cluster", pc_label, cluster_name)

            try:
                # Reset capacity accumulator for this cluster
                self._cluster_capacity.reset()

                self._process_cluster(cluster, pc_label)

                # Fetch VM stats for entire cluster in one call
                cluster_id = cluster.get("extId")
                vm_stats = self._get_vm_stats_by_cluster_id(cluster_id, pc_label, cluster_name)
                self.check.log.debug("[%s][%s] Fetched stats for %d VMs", pc_label, cluster_name, len(vm_stats))

                self._process_hosts(cluster, vm_stats, cluster_name, pc_label)

                # Report cluster capacity metrics (aggregated from hosts and VMs)
                cluster_tags = self.check.base_tags + self._extract_cluster_tags(cluster)
                self._report_cluster_capacity_metrics(cluster_tags)

                processed += 1
            except Exception:
                cluster_id = cluster.get("extId", "unknown")
                self.check.log.exception(
                    "[%s][%s] Failed to process cluster (id=%s)",
                    pc_label,
                    cluster_name,
                    cluster_id,
                )

        if skipped > 0:
            self.check.log.info("[%s] Processed %d clusters (%d skipped)", pc_label, processed, skipped)
        else:
            self.check.log.info("[%s] Processed %d clusters", pc_label, processed)

    def _is_prism_central_cluster(self, cluster: dict) -> bool:
        """Check if cluster is a Prism Central cluster (should be skipped)."""
        cluster_function = cluster.get("config", {}).get("clusterFunction", [])
        return len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL"

    def _process_cluster(self, cluster: dict, pc_label: str) -> None:
        """Process and report metrics for a single cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_name = cluster.get("name", "unknown")
        cluster_tags = self.check.base_tags + self._extract_cluster_tags(cluster)

        self._report_cluster_basic_metrics(cluster, cluster_tags)
        self._report_cluster_stats(cluster_name, cluster_id, cluster_tags, pc_label)

    def _process_vm(self, vm: dict, vm_stats_dict: dict, cluster_name: str, pc_label: str) -> None:
        """Process and report metrics for a single VM."""
        vm_id = vm.get("extId", "unknown")
        hostname = vm.get("name")
        if not self._should_collect_vm(vm):
            return
        vm_tags = self.check.base_tags + self._extract_vm_tags(vm)

        self._set_external_tags_for_host(hostname, vm_tags)
        self._report_vm_basic_metrics(vm, hostname, vm_tags)
        self._report_vm_stats(vm_id, hostname, vm_tags, vm_stats_dict, cluster_name, pc_label)

    def _report_vm_basic_metrics(self, vm: dict, hostname: str, vm_tags: list[str]) -> None:
        """Report basic VM metrics (counts and status)."""
        self.check.gauge("vm.count", 1, hostname=hostname, tags=vm_tags)

        power_state = vm.get("powerState", "$UNKNOWN")
        status_value = 0 if power_state == "ON" else 1 if power_state == "PAUSED" else 2
        self.check.gauge(
            "vm.status", status_value, hostname=hostname, tags=vm_tags + [f"ntnx_power_state:{power_state}"]
        )

        self._report_vm_capacity_metrics(vm, hostname, vm_tags)

    def _report_vm_capacity_metrics(self, vm: dict, hostname: str, vm_tags: list[str]) -> None:
        """Report VM capacity metrics (CPU and memory allocation)."""
        num_sockets = int(vm.get("numSockets") or 0)
        num_cores_per_socket = int(vm.get("numCoresPerSocket") or 0)
        num_threads_per_core = int(vm.get("numThreadsPerCore") or 0)
        memory_bytes = int(vm.get("memorySizeBytes") or 0)

        # Total vCPUs = sockets * cores_per_socket
        vcpus_allocated = num_sockets * num_cores_per_socket

        self.check.gauge("vm.cpu.sockets", num_sockets, hostname=hostname, tags=vm_tags)
        self.check.gauge("vm.cpu.cores_per_socket", num_cores_per_socket, hostname=hostname, tags=vm_tags)
        self.check.gauge("vm.cpu.threads_per_core", num_threads_per_core, hostname=hostname, tags=vm_tags)
        self.check.gauge("vm.cpu.vcpus_allocated", vcpus_allocated, hostname=hostname, tags=vm_tags)
        self.check.gauge("vm.memory.allocated_bytes", memory_bytes, hostname=hostname, tags=vm_tags)

        # Accumulate for cluster totals
        self._cluster_capacity.add_vm(vcpus_allocated, memory_bytes)

    def _report_cluster_basic_metrics(self, cluster: dict, cluster_tags: list[str]) -> None:
        """Report basic cluster metrics (counts)."""
        nbr_nodes = int(cluster.get("nodes", {}).get("numberOfNodes", 0))
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))

        self.check.gauge("cluster.count", 1, tags=cluster_tags)
        self.check.gauge("cluster.nbr_nodes", nbr_nodes, tags=cluster_tags)
        self.check.gauge("cluster.vm.count", vm_count, tags=cluster_tags)
        self.check.gauge("cluster.vm.inefficient_count", inefficient_vm_count, tags=cluster_tags)

    def _report_cluster_capacity_metrics(self, cluster_tags: list[str]) -> None:
        """Report cluster capacity metrics aggregated from hosts and VMs."""
        cap = self._cluster_capacity
        self.check.gauge("cluster.cpu.total_cores", cap.total_cores, tags=cluster_tags)
        self.check.gauge("cluster.cpu.total_threads", cap.total_threads, tags=cluster_tags)
        self.check.gauge("cluster.memory.total_bytes", cap.total_memory_bytes, tags=cluster_tags)
        self.check.gauge("cluster.cpu.vcpus_allocated", cap.vcpus_allocated, tags=cluster_tags)
        self.check.gauge("cluster.memory.allocated_bytes", cap.memory_allocated_bytes, tags=cluster_tags)

    def _report_stats(
        self,
        entity_name: str,
        stats: dict | list,
        metrics_map: dict[str, str],
        tags: list[str],
        hostname: str | None = None,
        entity_type: EntityType | None = None,
    ) -> None:
        """Submit stats metrics for any entity type."""
        if not stats:
            self.check.log.warning("No stats returned for %s", entity_name)
            return

        is_list = isinstance(stats, list)
        metrics_submitted = 0

        for key, metric_name in metrics_map.items():
            entries = stats if is_list else stats.get(key, [])
            value_field = key if is_list else "value"
            for entry in entries:
                value = entry.get(value_field)
                if value is not None:
                    self.check.gauge(metric_name, value, hostname=hostname, tags=tags)
                    metrics_submitted += 1

        # Track metrics by type
        if entity_type == 'cluster':
            self.cluster_metrics_count += metrics_submitted
        elif entity_type == 'host':
            self.host_metrics_count += metrics_submitted
        elif entity_type == 'vm':
            self.vm_metrics_count += metrics_submitted

    def _report_cluster_stats(self, cluster_name: str, cluster_id: str, cluster_tags: list[str], pc_label: str) -> None:
        """Report time-series stats for a cluster."""
        stats = self._get_stats(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}")
        self._report_stats(
            f"[{pc_label}][{cluster_name}] Cluster",
            stats,
            CLUSTER_STATS_METRICS,
            cluster_tags,
            entity_type="cluster",
        )

    def _report_vm_stats(
        self, vm_id: str, hostname: str, vm_tags: list[str], vm_stats_dict: dict, cluster_name: str, pc_label: str
    ) -> None:
        """Report time-series stats for a VM."""
        stats = vm_stats_dict.get(vm_id)
        if stats:
            self._report_stats(
                f"[{pc_label}][{cluster_name}] VM {hostname}",
                stats,
                VM_STATS_METRICS,
                vm_tags,
                hostname=hostname,
                entity_type="vm",
            )

    def _process_hosts(self, cluster: dict, cluster_vm_stats_dict: dict, cluster_name: str, pc_label: str) -> None:
        """Process and report metrics for all hosts in a cluster."""
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
        """Process a single host and its VMs, returning number of VMs processed."""
        host_id = host.get("extId")
        host_name = host.get("hostName")

        if not host_id:
            self.check.log.warning("[%s][%s] Host %s has no extId, skipping", pc_label, cluster_name, host_name)
            return 0

        if not should_collect_resource("host", host, self.check.resource_filters, self.check.log):
            return 0

        # Cache host name for VM tagging
        if host_name:
            self.host_names[host_id] = host_name

        # Report host metrics
        host_tags = cluster_tags + self._extract_host_tags(host)
        self.check.gauge("host.count", 1, hostname=host_name, tags=host_tags)

        self._report_host_status_metrics(host, host_name, host_tags)
        self._set_external_tags_for_host(host_name, host_tags)
        self._report_host_capacity_metrics(host, host_name, host_tags)

        # Report host stats
        try:
            stats = self._get_stats(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}/hosts/{host_id}")
            if stats:
                self._report_stats(
                    f"[{pc_label}][{cluster_name}] Host {host_name}",
                    stats,
                    HOST_STATS_METRICS,
                    host_tags,
                    hostname=host_name,
                    entity_type="host",
                )
        except Exception:
            self.check.log.exception("[%s][%s] Failed to fetch stats for host %s", pc_label, cluster_name, host_name)

        # Process VMs on this host
        if self.check.batch_vm_collection:
            vms = self._vms_by_host.get(host_id, [])
        else:
            try:
                vms = self._list_vms(host_id)
            except Exception:
                self.check.log.exception("[%s][%s] Failed to list VMs for host %s", pc_label, cluster_name, host_name)
                return 0

        self.check.log.debug("[%s][%s] Host %s has %d VMs", pc_label, cluster_name, host_name, len(vms))

        for vm in vms:
            self._process_vm(vm, cluster_vm_stats_dict, cluster_name, pc_label)

        return len(vms)

    def _report_host_capacity_metrics(self, host: dict, hostname: str, host_tags: list[str]) -> None:
        """Report host capacity metrics (CPU sockets, cores, threads, memory)."""
        cpu_sockets = int(host.get("numberOfCpuSockets") or 0)
        cpu_cores = int(host.get("numberOfCpuCores") or 0)
        cpu_threads = int(host.get("numberOfCpuThreads") or 0)
        memory_bytes = int(host.get("memorySizeBytes") or 0)

        self.check.gauge("host.cpu.sockets", cpu_sockets, hostname=hostname, tags=host_tags)
        self.check.gauge("host.cpu.cores", cpu_cores, hostname=hostname, tags=host_tags)
        self.check.gauge("host.cpu.threads", cpu_threads, hostname=hostname, tags=host_tags)
        self.check.gauge("host.memory.bytes", memory_bytes, hostname=hostname, tags=host_tags)

        # Accumulate for cluster totals
        self._cluster_capacity.add_host(cpu_cores, cpu_threads, memory_bytes)

    def _report_host_status_metrics(self, host: dict, hostname: str, host_tags: list[str]) -> None:
        """Report host node status as a gauge (0=OK, 1=WARNING, 2=CRITICAL/UNKNOWN)."""
        node_status_ok = {"NORMAL", "NEW_NODE", "PREPROTECTED"}
        node_status_warning = {"TO_BE_PREPROTECTED", "TO_BE_REMOVED", "OK_TO_BE_REMOVED"}

        node_status = host.get("nodeStatus", "$UNKNOWN")

        if node_status in node_status_ok:
            status_value = 0
        elif node_status in node_status_warning:
            status_value = 1
        else:
            status_value = 2

        status_tags = host_tags + [f"ntnx_node_status:{node_status}"]
        self.check.gauge("host.status", status_value, hostname=hostname, tags=status_tags)

    def _extract_host_tags(self, host: dict) -> list[str]:
        """Extract tags from a host object."""
        tags = []

        tags.append("ntnx_type:host")

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

        # Add category tags
        tags.extend(self.check.extract_category_tags(host))

        return tags

    def _extract_cluster_tags(self, cluster: dict) -> list[str]:
        """Extract tags from a cluster object."""
        tags = []

        cluster_name = cluster.get("name")
        if cluster_name:
            tags.append(f"ntnx_cluster_name:{cluster_name}")

        # Add category tags
        tags.extend(self.check.extract_category_tags(cluster))

        return tags

    def _extract_vm_tags(self, vm: dict) -> list[str]:
        """Extract tags from a VM object."""
        tags = []

        tags.append("ntnx_type:vm")

        vm_name = vm.get("name")
        if vm_name:
            tags.append(f"ntnx_vm_name:{vm_name}")

        # Add category tags
        tags.extend(self.check.extract_category_tags(vm))

        host_id = vm.get("host", {}).get("extId")
        if host_id and host_id in self.host_names:
            tags.append(f"ntnx_host_name:{self.host_names[host_id]}")

        cluster_id = vm.get("cluster", {}).get("extId")
        if cluster_id and cluster_id in self.cluster_names:
            tags.append(f"ntnx_cluster_name:{self.cluster_names[cluster_id]}")

        is_agent_vm = is_affirmative(vm.get("isAgentVm"))
        tags.append(f"ntnx_is_agent_vm:{is_agent_vm}")

        return tags

    def _set_external_tags_for_host(self, hostname: str, tags: list[str]) -> None:
        """Set or update external tags for a host."""
        for i, entry in enumerate(self.external_tags):
            if entry[0] == hostname:
                self.external_tags[i] = (hostname, {self.check.__NAMESPACE__: tags})
                return

        self.external_tags.append((hostname, {self.check.__NAMESPACE__: tags}))

    def _should_collect_vm(self, vm: dict) -> bool:
        """Check if a VM should be collected based on power state and resource filters."""
        has_power_state_filter = any(
            f['resource'] == 'vm' and f['property'] == 'powerState' for f in self.check.resource_filters
        )
        if not has_power_state_filter and vm.get("powerState") != "ON":
            return False
        if not should_collect_resource("vm", vm, self.check.resource_filters, self.check.log):
            return False
        return True

    def _build_vms_by_host_cache(self) -> None:
        """Fetch all VMs and group them by host, applying filters."""
        for vm in self._list_vms():
            host_id = vm.get("host", {}).get("extId")
            if host_id and self._should_collect_vm(vm):
                self._vms_by_host.setdefault(host_id, []).append(vm)

    def _list_clusters(self) -> list[dict]:
        """Fetch all clusters from Prism Central."""
        return self.check._get_paginated_request_data("api/clustermgmt/v4.0/config/clusters")

    def _list_categories(self) -> list[dict]:
        """Fetch all categories from Prism Central."""
        return self.check._get_paginated_request_data("api/prism/v4.0/config/categories")

    def _list_vms(self, host_id: str | None = None) -> list[dict]:
        """Fetch VMs from Prism Central, optionally filtered by host."""
        params = {"$filter": f"host/extId eq '{host_id}'"} if host_id else None
        return self.check._get_paginated_request_data("api/vmm/v4.0/ahv/config/vms", params=params)

    def _list_hosts_by_cluster(self, cluster_id: str) -> list[dict]:
        """Fetch all hosts for a specific cluster."""
        return self.check._get_paginated_request_data(f"api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts")

    def _build_stats_params(self) -> dict[str, str | int]:
        """Build the common query parameters for stats API calls."""
        start_time, end_time = self.collection_time_window
        return {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.check.sampling_interval,
        }

    def _get_stats(self, endpoint: str) -> dict:
        """Fetch time-series stats for a cluster or host endpoint."""
        return self.check._get_request_data(endpoint, params=self._build_stats_params())

    def _get_vm_stats_by_cluster_id(self, cluster_id: str, pc_label: str, cluster_name: str) -> dict[str, list]:
        """Fetch time-series stats for all VMs in a cluster."""
        params = self._build_stats_params()
        params["$filter"] = f"stats/cluster eq '{cluster_id}'"
        params["$select"] = "*"

        vm_stats_data = self.check._get_paginated_request_data("api/vmm/v4.0/ahv/stats/vms", params=params)

        vm_stats_dict = {}
        for vm_stat in vm_stats_data:
            vm_id = vm_stat.get("extId")
            stats = vm_stat.get("stats", [])
            if vm_id:
                vm_stats_dict[vm_id] = stats

        self.check.log.info(
            "[%s][%s] Retrieved %d VM stats from API for cluster_id=%s",
            pc_label,
            cluster_name,
            len(vm_stats_dict),
            cluster_id,
        )
        return vm_stats_dict

    def init_collection_time_window(self) -> None:
        """Calculate and set the collection time window for this check run."""
        now = datetime.now(timezone.utc)
        end_time = now - timedelta(seconds=self.check.sampling_interval)
        start_time = end_time - timedelta(seconds=self.check.sampling_interval)
        self.collection_time_window = start_time.isoformat(), end_time.isoformat()
