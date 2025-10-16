# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck


class NutanixCheck(AgentCheck):
    """
    Nutanix integration for Datadog.

    Collects metrics from Nutanix Prism Central using v4 APIs:
    - Cluster-level metrics (CPU, memory, storage, IOPS, latency)
    - Host-level metrics (CPU, memory, disk I/O, network)
    - VM-level metrics (CPU, memory, disk I/O, network, latency)
    - Events and alerts
    """

    __NAMESPACE__ = 'nutanix'

    def __init__(self, name, init_config, instances):
        super(NutanixCheck, self).__init__(name, init_config, instances)

        self.pc_ip = self.instance.get("pc_ip")
        self.pc_port = self.instance.get("pc_port", 9440)
        self.pc_username = self.instance.get("pc_username") or self.instance.get("username")
        self.pc_password = self.instance.get("pc_password") or self.instance.get("password")

        # Collection toggles (all enabled by default)
        self.collect_cluster_metrics = self.instance.get("collect_cluster_metrics", True)
        self.collect_host_metrics = self.instance.get("collect_host_metrics", True)
        self.collect_vm_metrics = self.instance.get("collect_vm_metrics", True)
        self.collect_events = self.instance.get("collect_events", True)
        self.collect_alerts = self.instance.get("collect_alerts", True)

        # Pagination limits
        self.max_clusters = self.instance.get("max_clusters", 50)
        self.max_hosts = self.instance.get("max_hosts", 50)
        self.max_vms = self.instance.get("max_vms", 50)
        self.max_events = self.instance.get("max_events", 50)
        self.max_alerts = self.instance.get("max_alerts", 50)

        # Build the base URL for Prism Central
        self.base_url = f"https://{self.pc_ip}:{self.pc_port}"
        self.health_check_url = f"{self.base_url}/console"

        # Common tags for all metrics
        self.tags = list(self.instance.get("tags", []))
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

        # Collect host metrics
        if self.collect_host_metrics:
            self._collect_host_metrics()

        # Collect VM metrics
        if self.collect_vm_metrics:
            self._collect_vm_metrics()

        # Collect events
        if self.collect_events:
            self._collect_events()

        # Collect alerts
        if self.collect_alerts:
            self._collect_alerts()

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
            # Get cluster list
            clusters = self._get_clusters()
            if not clusters:
                self.log.debug("No clusters found")
                return

            for cluster in clusters:
                self._process_cluster(cluster)

        except Exception as e:
            self.log.exception("Error collecting cluster metrics: %s", e)

    def _get_clusters(self):
        # type: () -> List[Dict[str, Any]]
        """
        Fetch all clusters from Prism Central.

        Returns:
            List of cluster dictionaries
        """
        endpoint = f"{self.base_url}/api/clustermgmt/v4.0/config/clusters"
        params = {"$limit": self.max_clusters}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            self.log.error("Failed to fetch clusters: %s", e)
            return []

    def _process_cluster(self, cluster):
        # type: (Dict[str, Any]) -> None
        """Process a single cluster and collect its metrics."""
        cluster_id = cluster.get("extId")
        cluster_name = cluster.get("name", "unknown")

        if not cluster_id:
            self.log.warning("Cluster missing extId, skipping")
            return

        cluster_tags = self.tags + [
            f"nutanix_cluster_id:{cluster_id}",
            f"nutanix_cluster_name:{cluster_name}",
        ]

        # Basic cluster metrics
        self.gauge("cluster.count", 1, tags=cluster_tags)

        # VM count
        vm_count = cluster.get("vmCount", 0)
        if vm_count:
            self.gauge("cluster.vm_count", vm_count, tags=cluster_tags)

        # Node count
        nodes = cluster.get("nodes", {})
        node_count = nodes.get("numberOfNodes", 0)
        if node_count:
            self.gauge("cluster.node_count", node_count, tags=cluster_tags)

        # Configuration metrics
        config = cluster.get("config", {})
        redundancy_factor = config.get("redundancyFactor", 0)
        if redundancy_factor:
            self.gauge("cluster.redundancy_factor", redundancy_factor, tags=cluster_tags)

        # Cluster availability
        is_available = 1 if config.get("isAvailable", False) else 0
        self.gauge("cluster.available", is_available, tags=cluster_tags)

        # Get cluster statistics
        self._collect_cluster_stats(cluster_id, cluster_tags)

        # Get storage containers for this cluster
        self._collect_storage_containers(cluster_id, cluster_tags)

    def _collect_cluster_stats(self, cluster_id, cluster_tags):
        # type: (str, List[str]) -> None
        """Collect performance statistics for a cluster."""
        endpoint = f"{self.base_url}/api/clustermgmt/v4.0/stats/clusters/{cluster_id}"

        try:
            response = self.http.get(endpoint)
            response.raise_for_status()
            stats = response.json()

            # Extract stats data
            data = stats.get("data", [])
            if not data:
                self.log.debug("No stats data for cluster %s", cluster_id)
                return

            # Process the most recent stats
            latest_stats = data[0] if isinstance(data, list) else data
            self._process_cluster_stats(latest_stats, cluster_tags)

        except HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("Cluster stats endpoint not available for cluster %s", cluster_id)
            else:
                self.log.error("Failed to fetch cluster stats for %s: %s", cluster_id, e)
        except Exception as e:
            self.log.error("Error processing cluster stats for %s: %s", cluster_id, e)

    def _process_cluster_stats(self, stats, tags):
        # type: (Dict[str, Any], List[str]) -> None
        """Process cluster statistics and submit metrics."""
        # CPU metrics
        cpu_usage = stats.get("cpuUsagePpm")
        if cpu_usage is not None:
            self.gauge("cluster.cpu.usage_percent", cpu_usage / 10000.0, tags=tags)

        # Memory metrics
        memory_usage_ppm = stats.get("memoryUsagePpm")
        if memory_usage_ppm is not None:
            self.gauge("cluster.memory.usage_percent", memory_usage_ppm / 10000.0, tags=tags)

        memory_usage_bytes = stats.get("memoryUsageBytes")
        if memory_usage_bytes is not None:
            self.gauge("cluster.memory.usage_bytes", memory_usage_bytes, tags=tags)

        # Storage metrics
        storage_capacity = stats.get("storageCapacityBytes")
        if storage_capacity is not None:
            self.gauge("cluster.storage.capacity_bytes", storage_capacity, tags=tags)

        storage_usage = stats.get("storageUsageBytes")
        if storage_usage is not None:
            self.gauge("cluster.storage.usage_bytes", storage_usage, tags=tags)
            if storage_capacity:
                free_bytes = storage_capacity - storage_usage
                self.gauge("cluster.storage.free_bytes", free_bytes, tags=tags)

        # IOPS metrics
        read_iops = stats.get("readIops")
        if read_iops is not None:
            self.gauge("cluster.iops.read", read_iops, tags=tags)

        write_iops = stats.get("writeIops")
        if write_iops is not None:
            self.gauge("cluster.iops.write", write_iops, tags=tags)

        # Throughput metrics
        read_throughput = stats.get("readThroughputBps")
        if read_throughput is not None:
            self.gauge("cluster.throughput.read_bytes_per_sec", read_throughput, tags=tags)

        write_throughput = stats.get("writeThroughputBps")
        if write_throughput is not None:
            self.gauge("cluster.throughput.write_bytes_per_sec", write_throughput, tags=tags)

        # Latency metrics
        read_latency = stats.get("readLatencyUs")
        if read_latency is not None:
            self.gauge("cluster.latency.read_ms", read_latency / 1000.0, tags=tags)

        write_latency = stats.get("writeLatencyUs")
        if write_latency is not None:
            self.gauge("cluster.latency.write_ms", write_latency / 1000.0, tags=tags)

    def _collect_storage_containers(self, cluster_id, cluster_tags):
        # type: (str, List[str]) -> None
        """Collect storage container metrics for a cluster."""
        endpoint = f"{self.base_url}/api/clustermgmt/v4.0/config/storage-containers"
        params = {"$limit": 50}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            containers = data.get("data", [])
            for container in containers:
                # Check if container belongs to this cluster
                container_cluster_id = container.get("clusterExtId")
                if container_cluster_id == cluster_id:
                    self._process_storage_container(container, cluster_tags)

        except Exception as e:
            self.log.debug("Error collecting storage containers: %s", e)

    def _process_storage_container(self, container, cluster_tags):
        # type: (Dict[str, Any], List[str]) -> None
        """Process a single storage container."""
        container_name = container.get("name", "unknown")
        container_id = container.get("extId")

        if not container_id:
            return

        container_tags = cluster_tags + [
            f"storage_container_name:{container_name}",
            f"storage_container_id:{container_id}",
        ]

        # Basic container count
        self.gauge("storage_container.count", 1, tags=container_tags)

    def _collect_host_metrics(self):
        """Collect host-level metrics."""
        try:
            hosts = self._get_hosts()
            if not hosts:
                self.log.debug("No hosts found")
                return

            for host in hosts:
                self._process_host(host)

        except Exception as e:
            self.log.exception("Error collecting host metrics: %s", e)

    def _get_hosts(self):
        # type: () -> List[Dict[str, Any]]
        """Fetch all hosts from Prism Central."""
        endpoint = f"{self.base_url}/api/clustermgmt/v4.0/config/hosts"
        params = {"$limit": self.max_hosts}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            self.log.error("Failed to fetch hosts: %s", e)
            return []

    def _process_host(self, host):
        # type: (Dict[str, Any]) -> None
        """Process a single host and collect its metrics."""
        host_id = host.get("extId")
        host_name = host.get("name", "unknown")

        if not host_id:
            self.log.warning("Host missing extId, skipping")
            return

        host_tags = self.tags + [
            f"nutanix_host_id:{host_id}",
            f"nutanix_host_name:{host_name}",
        ]

        # Get cluster ID if available
        cluster_id = host.get("clusterExtId")
        if cluster_id:
            host_tags.append(f"nutanix_cluster_id:{cluster_id}")

        # Basic host metrics
        self.gauge("host.count", 1, tags=host_tags)

        # Get host statistics
        self._collect_host_stats(host_id, host_tags)

    def _collect_host_stats(self, host_id, host_tags):
        # type: (str, List[str]) -> None
        """Collect performance statistics for a host."""
        endpoint = f"{self.base_url}/api/clustermgmt/v4.0/stats/hosts/{host_id}"

        try:
            response = self.http.get(endpoint)
            response.raise_for_status()
            stats = response.json()

            data = stats.get("data", [])
            if not data:
                self.log.debug("No stats data for host %s", host_id)
                return

            latest_stats = data[0] if isinstance(data, list) else data
            self._process_host_stats(latest_stats, host_tags)

        except HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("Host stats endpoint not available for host %s", host_id)
            else:
                self.log.error("Failed to fetch host stats for %s: %s", host_id, e)
        except Exception as e:
            self.log.error("Error processing host stats for %s: %s", host_id, e)

    def _process_host_stats(self, stats, tags):
        # type: (Dict[str, Any], List[str]) -> None
        """Process host statistics and submit metrics."""
        # CPU metrics
        cpu_usage = stats.get("cpuUsagePpm")
        if cpu_usage is not None:
            self.gauge("host.cpu.usage_percent", cpu_usage / 10000.0, tags=tags)

        # Memory metrics
        memory_usage_ppm = stats.get("memoryUsagePpm")
        if memory_usage_ppm is not None:
            self.gauge("host.memory.usage_percent", memory_usage_ppm / 10000.0, tags=tags)

        memory_usage_bytes = stats.get("memoryUsageBytes")
        if memory_usage_bytes is not None:
            self.gauge("host.memory.usage_bytes", memory_usage_bytes, tags=tags)

        # Disk IOPS
        disk_read_iops = stats.get("diskReadIops")
        if disk_read_iops is not None:
            self.gauge("host.disk.iops.read", disk_read_iops, tags=tags)

        disk_write_iops = stats.get("diskWriteIops")
        if disk_write_iops is not None:
            self.gauge("host.disk.iops.write", disk_write_iops, tags=tags)

        # Disk throughput
        disk_read_throughput = stats.get("diskReadThroughputBps")
        if disk_read_throughput is not None:
            self.gauge("host.disk.throughput.read_bytes_per_sec", disk_read_throughput, tags=tags)

        disk_write_throughput = stats.get("diskWriteThroughputBps")
        if disk_write_throughput is not None:
            self.gauge("host.disk.throughput.write_bytes_per_sec", disk_write_throughput, tags=tags)

        # Network metrics
        network_rx = stats.get("networkReceivedThroughputBps")
        if network_rx is not None:
            self.gauge("host.network.throughput.rx_bytes_per_sec", network_rx, tags=tags)

        network_tx = stats.get("networkTransmittedThroughputBps")
        if network_tx is not None:
            self.gauge("host.network.throughput.tx_bytes_per_sec", network_tx, tags=tags)

    def _collect_vm_metrics(self):
        """Collect VM-level metrics."""
        try:
            vms = self._get_vms()
            if not vms:
                self.log.debug("No VMs found")
                return

            for vm in vms:
                self._process_vm(vm)

        except Exception as e:
            self.log.exception("Error collecting VM metrics: %s", e)

    def _get_vms(self):
        # type: () -> List[Dict[str, Any]]
        """Fetch all VMs from Prism Central."""
        endpoint = f"{self.base_url}/api/vmm/v4.0/content/vms"
        params = {"$limit": self.max_vms}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            self.log.error("Failed to fetch VMs: %s", e)
            return []

    def _process_vm(self, vm):
        # type: (Dict[str, Any]) -> None
        """Process a single VM and collect its metrics."""
        vm_id = vm.get("extId")
        vm_name = vm.get("name", "unknown")

        if not vm_id:
            self.log.warning("VM missing extId, skipping")
            return

        vm_tags = self.tags + [
            f"nutanix_vm_id:{vm_id}",
            f"nutanix_vm_name:{vm_name}",
        ]

        # Get cluster ID if available
        cluster_id = vm.get("clusterExtId")
        if cluster_id:
            vm_tags.append(f"nutanix_cluster_id:{cluster_id}")

        # Power state
        power_state = vm.get("powerState", "UNKNOWN")
        vm_tags.append(f"power_state:{power_state}")

        # Basic VM metrics
        self.gauge("vm.count", 1, tags=vm_tags)

        # vCPU count
        num_sockets = vm.get("numSockets", 0)
        num_cores_per_socket = vm.get("numCoresPerSocket", 1)
        total_vcpus = num_sockets * num_cores_per_socket
        if total_vcpus:
            self.gauge("vm.cpu_count", total_vcpus, tags=vm_tags)

        # Memory size
        memory_size_bytes = vm.get("memorySizeBytes", 0)
        if memory_size_bytes:
            self.gauge("vm.memory_size_bytes", memory_size_bytes, tags=vm_tags)

        # Get VM statistics (only for powered on VMs)
        if power_state == "ON":
            self._collect_vm_stats(vm_id, vm_tags)

    def _collect_vm_stats(self, vm_id, vm_tags):
        # type: (str, List[str]) -> None
        """Collect performance statistics for a VM."""
        endpoint = f"{self.base_url}/api/vmm/v4.0/ahv/stats/vms/{vm_id}"
        params = {"$statType": "SUMMARY"}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            stats = response.json()

            data = stats.get("data", [])
            if not data:
                self.log.debug("No stats data for VM %s", vm_id)
                return

            latest_stats = data[0] if isinstance(data, list) else data
            self._process_vm_stats(latest_stats, vm_tags)

        except HTTPError as e:
            if e.response.status_code == 404:
                self.log.debug("VM stats endpoint not available for VM %s", vm_id)
            else:
                self.log.error("Failed to fetch VM stats for %s: %s", vm_id, e)
        except Exception as e:
            self.log.error("Error processing VM stats for %s: %s", vm_id, e)

    def _process_vm_stats(self, stats, tags):
        # type: (Dict[str, Any], List[str]) -> None
        """Process VM statistics and submit metrics."""
        # CPU metrics
        cpu_usage = stats.get("cpuUsagePpm")
        if cpu_usage is not None:
            self.gauge("vm.cpu.usage_percent", cpu_usage / 10000.0, tags=tags)

        # CPU ready time (for inefficient VM detection)
        cpu_ready_time = stats.get("cpuReadyTimePpm")
        if cpu_ready_time is not None:
            self.gauge("vm.cpu.ready_time_ppm", cpu_ready_time, tags=tags)

        # Memory metrics
        memory_usage_ppm = stats.get("memoryUsagePpm")
        if memory_usage_ppm is not None:
            self.gauge("vm.memory.usage_percent", memory_usage_ppm / 10000.0, tags=tags)

        memory_usage_bytes = stats.get("memoryUsageBytes")
        if memory_usage_bytes is not None:
            self.gauge("vm.memory.usage_bytes", memory_usage_bytes, tags=tags)

        # Disk IOPS
        disk_read_iops = stats.get("diskReadIops")
        if disk_read_iops is not None:
            self.gauge("vm.disk.iops.read", disk_read_iops, tags=tags)

        disk_write_iops = stats.get("diskWriteIops")
        if disk_write_iops is not None:
            self.gauge("vm.disk.iops.write", disk_write_iops, tags=tags)

        # Disk throughput
        disk_read_throughput = stats.get("diskReadThroughputBps")
        if disk_read_throughput is not None:
            self.gauge("vm.disk.throughput.read_bytes_per_sec", disk_read_throughput, tags=tags)

        disk_write_throughput = stats.get("diskWriteThroughputBps")
        if disk_write_throughput is not None:
            self.gauge("vm.disk.throughput.write_bytes_per_sec", disk_write_throughput, tags=tags)

        # Disk latency
        disk_read_latency = stats.get("diskReadLatencyUs")
        if disk_read_latency is not None:
            self.gauge("vm.disk.latency.read_ms", disk_read_latency / 1000.0, tags=tags)

        disk_write_latency = stats.get("diskWriteLatencyUs")
        if disk_write_latency is not None:
            self.gauge("vm.disk.latency.write_ms", disk_write_latency / 1000.0, tags=tags)

        # Network metrics
        network_rx = stats.get("networkReceivedThroughputBps")
        if network_rx is not None:
            self.gauge("vm.network.throughput.rx_bytes_per_sec", network_rx, tags=tags)

        network_tx = stats.get("networkTransmittedThroughputBps")
        if network_tx is not None:
            self.gauge("vm.network.throughput.tx_bytes_per_sec", network_tx, tags=tags)

    def _collect_events(self):
        """Collect events from Prism Central."""
        endpoint = f"{self.base_url}/api/prism/v4.0/config/events"
        params = {"$limit": self.max_events}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            events = data.get("data", [])
            for event in events:
                self._process_event(event)

        except Exception as e:
            self.log.debug("Error collecting events: %s", e)

    def _process_event(self, event):
        # type: (Dict[str, Any]) -> None
        """Process a single event."""
        event_type = event.get("eventType", "UNKNOWN")
        severity = event.get("severity", "UNKNOWN")

        event_tags = self.tags + [
            f"event_type:{event_type}",
            f"severity:{severity}",
        ]

        # Count events by type and severity
        self.count("event.occurred", 1, tags=event_tags)

    def _collect_alerts(self):
        """Collect alerts from Prism Central."""
        endpoint = f"{self.base_url}/api/prism/v4.0/config/alerts"
        params = {"$limit": self.max_alerts}

        try:
            response = self.http.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            alerts = data.get("data", [])

            # Count alerts by severity
            critical_count = 0
            warning_count = 0
            info_count = 0

            for alert in alerts:
                severity = alert.get("severity", "").upper()
                if severity == "CRITICAL":
                    critical_count += 1
                elif severity == "WARNING":
                    warning_count += 1
                elif severity == "INFO":
                    info_count += 1

                self._process_alert(alert)

            # Submit aggregate alert counts
            self.gauge("alert.critical", critical_count, tags=self.tags)
            self.gauge("alert.warning", warning_count, tags=self.tags)
            self.gauge("alert.info", info_count, tags=self.tags)

        except Exception as e:
            self.log.debug("Error collecting alerts: %s", e)

    def _process_alert(self, alert):
        # type: (Dict[str, Any]) -> None
        """Process a single alert."""
        alert_type = alert.get("alertType", "UNKNOWN")
        severity = alert.get("severity", "UNKNOWN")
        status = alert.get("status", "UNKNOWN")

        alert_tags = self.tags + [
            f"alert_type:{alert_type}",
            f"severity:{severity}",
            f"status:{status}",
        ]

        # Count alerts by type, severity, and status
        self.gauge("alert.active", 1, tags=alert_tags)
