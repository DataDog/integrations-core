# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datetime import datetime, timedelta, timezone

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout

from datadog_checks.base import AgentCheck, ConfigurationError, is_affirmative
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp
from datadog_checks.nutanix.metrics import CLUSTER_STATS_METRICS, HOST_STATS_METRICS, VM_STATS_METRICS
from datadog_checks.nutanix.utils import retry_on_rate_limit


class NutanixCheck(AgentCheck):
    __NAMESPACE__ = 'nutanix'

    def __init__(self, name, init_config, instances):
        super(NutanixCheck, self).__init__(name, init_config, instances)

        self.sampling_interval = self.instance.get("min_collection_interval", 120)
        self.page_limit = self.instance.get("page_limit", 50)

        self.pc_ip = self.instance.get("pc_ip")
        self.pc_port = self.instance.get("pc_port")
        if self.pc_ip and ":" in self.pc_ip:
            host, _, port = self.pc_ip.rpartition(":")
            if port.isdigit():
                if "pc_port" in self.instance:
                    raise ConfigurationError(f"Conflicting configuration: pc_ip ({port}) and pc_port ({self.pc_port})")
                self.pc_ip, self.pc_port = host, int(port)
        self.pc_port = self.pc_port or 9440

        pc_username = self.instance.get("pc_username")
        pc_password = self.instance.get("pc_password")

        if pc_username and "username" not in self.instance:
            self.instance["username"] = pc_username
        if pc_password and "password" not in self.instance:
            self.instance["password"] = pc_password

        self.collect_events_enabled = is_affirmative(self.instance.get("collect_events"))
        self.collect_tasks_enabled = is_affirmative(self.instance.get("collect_tasks"))

        self.base_url = f"{self.pc_ip}:{self.pc_port}"
        if not self.base_url.startswith("http"):
            self.base_url = "https://" + self.base_url

        self.health_check_url = f"{self.base_url}/console"

        self.base_tags = self.instance.get("tags", [])
        self.base_tags.append(f"prism_central:{self.pc_ip}")

        self.external_tags = []
        self.cluster_names = {}  # Mapping of cluster_id -> cluster_name
        self.host_names = {}  # Mapping of host_id -> host_name
        self.last_event_collection_time = None  # Track last event collection timestamp
        # Track the timestamp of the most recently collected task (timezone-aware datetime)
        self.last_task_collection_time = None

    def _set_external_tags_for_host(self, hostname: str, tags: list[str]):
        for i, entry in enumerate(self.external_tags):
            if entry[0] == hostname:
                self.external_tags[i] = (hostname, {self.__NAMESPACE__: tags})
                return

        self.external_tags.append((hostname, {self.__NAMESPACE__: tags}))

    def check(self, _):
        # Clear caches at the beginning of each check run to prevent unbounded growth
        self.cluster_names = {}
        self.host_names = {}
        self.external_tags = []

        if not self._check_health():
            return

        self._collect_cluster_metrics()
        self._collect_vm_metrics()

        if self.collect_events_enabled:
            self._collect_events()

        if self.collect_tasks_enabled:
            self._collect_tasks()

        if self.external_tags:
            self.set_external_tags(self.external_tags)

    def _check_health(self):
        try:
            response = self._make_request_with_retry(self.health_check_url, method='get')
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
            clusters = self._list_clusters()
            if not clusters:
                self.log.warning("No clusters found")
                return

            for cluster in clusters:
                # Store cluster name mapping for VM tagging
                cluster_id = cluster.get("extId")
                cluster_name = cluster.get("name")
                if cluster_id and cluster_name:
                    self.cluster_names[cluster_id] = cluster_name

                if self._is_prism_central_cluster(cluster):
                    self.log.debug("Skipping Prism Central cluster from cluster metrics collection")
                    continue

                self._process_cluster(cluster)
                self._process_hosts(cluster)

        except Exception as e:
            self.log.exception("Error collecting cluster metrics: %s", e)

    def _collect_vm_metrics(self):
        """Collect metrics from all Nutanix vms."""
        try:
            vms = self._list_vms()
            if not vms:
                self.log.warning("No vms found")
                return

            all_vm_stats_dict = self._list_all_vm_stats()

            for vm in vms:
                self._process_vm(vm, all_vm_stats_dict)

        except Exception as e:
            self.log.exception("Error collecting vm metrics: %s", e)

    def _is_prism_central_cluster(self, cluster):
        """Check if cluster is a Prism Central cluster (should be skipped)."""
        cluster_function = cluster.get("config", {}).get("clusterFunction", [])
        return len(cluster_function) == 1 and cluster_function[0] == "PRISM_CENTRAL"

    def _process_cluster(self, cluster):
        """Process and report metrics for a single cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.base_tags + self._extract_cluster_tags(cluster)

        self._report_cluster_basic_metrics(cluster, cluster_tags)
        self._report_cluster_stats(cluster_id, cluster_tags)

    def _process_vm(self, vm, all_vm_stats_dict):
        """Process and report metrics for a single vm."""
        vm_id = vm.get("extId", "unknown")
        hostname = vm.get("name")
        vm_tags = self.base_tags + self._extract_vm_tags(vm)

        self._set_external_tags_for_host(hostname, vm_tags)
        self._report_vm_basic_metrics(vm, hostname, vm_tags)
        self._report_vm_stats(vm_id, hostname, vm_tags, all_vm_stats_dict)

    def _report_vm_basic_metrics(self, vm, hostname, vm_tags):
        """Report basic vm metrics (counts)."""
        self.gauge("vm.count", 1, hostname=hostname, tags=vm_tags)

    def _report_cluster_basic_metrics(self, cluster, cluster_tags):
        """Report basic cluster metrics (counts)."""
        nbr_nodes = int(cluster.get("nodes", {}).get("numberOfNodes", 0))
        vm_count = int(cluster.get("vmCount", 0))
        inefficient_vm_count = int(cluster.get("inefficientVmCount", 0))

        self.gauge("cluster.count", 1, tags=cluster_tags)
        self.gauge("cluster.nbr_nodes", nbr_nodes, tags=cluster_tags)
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

    def _report_vm_stats(self, vm_id, hostname, vm_tags, all_vm_stats_dict):
        """Report time-series stats for a vm."""
        stats = all_vm_stats_dict.get(vm_id)
        if not stats:
            self.log.debug("No vm stats returned for vm %s", vm_id)
            return

        for key, metric_name in VM_STATS_METRICS.items():
            for s in stats:
                value = s.get(key)
                if value is not None:
                    self.gauge(metric_name, value, hostname=hostname, tags=vm_tags)

    def _process_hosts(self, cluster):
        """Process and report metrics for all hosts in a cluster."""
        cluster_id = cluster.get("extId", "unknown")
        cluster_tags = self.base_tags + self._extract_cluster_tags(cluster)

        hosts = self._list_hosts_by_cluster(cluster_id)
        for host in hosts:
            host_id = host.get("extId")
            hostname = host.get("hostName")

            # Store host name mapping for VM tagging
            if host_id and hostname:
                self.host_names[host_id] = hostname

            host_tags = cluster_tags + self._extract_host_tags(host)
            self.gauge("host.count", 1, hostname=hostname, tags=host_tags)

            self._set_external_tags_for_host(hostname, host_tags)

            stats = self._get_host_stats(cluster_id, host_id)
            if not stats:
                self.log.debug("No host stats returned for host %s", host_id)
                continue

            for key, metric_name in HOST_STATS_METRICS.items():
                entries = stats.get(key, [])
                for entry in entries:
                    value = entry.get("value")
                    if value is not None:
                        self.gauge(metric_name, value, hostname=hostname, tags=host_tags)

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

        # Handle nested hypervisor tags
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
            # Add host name if available in mapping
            if host_id in self.host_names:
                tags.append(f"ntnx_host_name:{self.host_names[host_id]}")

        cluster_id = vm.get("cluster", {}).get("extId")
        if cluster_id:
            tags.append(f"ntnx_cluster_id:{cluster_id}")
            # Add cluster name if available in mapping
            if cluster_id in self.cluster_names:
                tags.append(f"ntnx_cluster_name:{self.cluster_names[cluster_id]}")

        availability_zone_id = vm.get("availabilityZone", {}).get("extId")
        if availability_zone_id:
            tags.append(f"ntnx_availability_zone_id:{availability_zone_id}")

        is_agent_vm = is_affirmative(vm.get("isAgentVm"))
        if is_agent_vm:
            tags.append(f"ntnx_is_agent_vm:{is_agent_vm}")

        return tags

    @retry_on_rate_limit
    def _make_request_with_retry(self, url, method='get', **kwargs):
        """Make an HTTP request with retry logic for rate limiting.

        Args:
            url: The URL to make the request to
            method: The HTTP method to use (get, post, put, delete, etc.)
            **kwargs: Additional arguments to pass to the request method (params, json, data, etc.)

        Returns:
            The response object from the request
        """
        self.log.debug("HTTP request: %s %s, kwargs=%s", method.upper(), url, kwargs)
        http_method = getattr(self.http, method.lower())
        response = http_method(url, **kwargs)
        status = response.status_code

        # rate limits
        if status == 429:
            self.log.debug(
                "HTTP 429 rate limited: %s %s, payload_length=%s",
                method.upper(),
                url,
                len(response.content) if response.content else 0,
            )

        # any other non-2xx response
        elif not response.ok:
            self.log.debug(
                "HTTP non-2xx response: %s %s, status_code=%s, payload_length=%s",
                method.upper(),
                url,
                status,
                len(response.content) if response.content else 0,
            )

        return response

    def _get_paginated_request_data(self, endpoint, params=None):
        """Make a paginated API request to Prism Central and return the aggregated data field from all the pages."""

        all_items = []

        url = f"{self.base_url}/{endpoint}"

        # Initialize pagination parameters
        page = 0
        limit = self.page_limit

        # Create a copy of params to avoid mutating the caller's dictionary
        req_params = {} if params is None else params.copy()

        req_params["$page"] = page
        req_params["$limit"] = limit

        while True:
            response = self._make_request_with_retry(url, method='get', params=req_params)
            response.raise_for_status()
            payload = response.json()

            data = payload.get("data", [])
            if not data:
                self.log.debug("Stopping pagination for %s: no data returned on page %d", endpoint, page)
                break

            all_items.extend(data)

            # Check metadata for next link to determine if more pages exist
            links = payload.get("metadata", {}).get("links", [])
            next_link = next((l.get("href") for l in links if l.get("rel") == "next"), None)

            if not next_link:
                break

            page += 1
            req_params["$page"] = page

        self.log.debug("Fetched %d items from %s (%d pages)", len(all_items), endpoint, page + 1)
        return all_items

    def _get_request_data(self, endpoint, params=None):
        """Make an API request to Prism Central and return the data field."""
        url = f"{self.base_url}/{endpoint}"
        response = self._make_request_with_retry(url, method='get', params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("data", {})

    def _list_clusters(self):
        """Fetch all clusters from Prism Central."""
        return self._get_paginated_request_data("api/clustermgmt/v4.0/config/clusters")

    def _list_vms(self):
        """Fetch all clusters from Prism Central."""
        return self._get_paginated_request_data("api/vmm/v4.0/ahv/config/vms")

    def _list_hosts_by_cluster(self, cluster_id: str):
        """Fetch all hosts/hosts for a specific cluster."""
        return self._get_paginated_request_data(f"api/clustermgmt/v4.0/config/clusters/{cluster_id}/hosts")

    def _list_tasks(self):
        """Fetch tasks from Prism Central.

        Returns a list of tasks since the last collection.
        Uses last_task_collection_time if available, otherwise uses now - sampling_interval.
        """
        now = get_current_datetime()

        start_time = self.last_task_collection_time or (now - timedelta(seconds=self.sampling_interval))
        start_time_str = start_time.isoformat().replace("+00:00", "Z")

        params = {}
        params["$filter"] = f"createdTime gt {start_time_str}"
        params["$orderBy"] = "createdTime asc"

        return self._get_paginated_request_data("api/prism/v4.0/config/tasks", params=params)

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
            "$samplingInterval": self.sampling_interval,
        }

        return self._get_request_data(f"api/clustermgmt/v4.0/stats/clusters/{cluster_id}", params=params)

    def _get_host_stats(self, cluster_id: str, host_id: str):
        """
        Fetch time-series stats for a specific host.
        """
        start_time, end_time = self._calculate_stats_time_window()

        params = {
            "$startTime": start_time,
            "$endTime": end_time,
            "$statType": "AVG",
            "$samplingInterval": self.sampling_interval,
        }

        return self._get_request_data(
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
            "$samplingInterval": self.sampling_interval,
            "$select": "*",
        }

        vm_stats_data = self._get_paginated_request_data("api/vmm/v4.0/ahv/stats/vms/", params=params)

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

        end_time = now - timedelta(seconds=self.sampling_interval)

        # Round end_time down to the nearest minute for consistency
        end_time = end_time.replace(second=0, microsecond=0)

        start_time = end_time - timedelta(seconds=self.sampling_interval)

        return start_time.isoformat(), end_time.isoformat()

    def _collect_events(self):
        """Collect events from Nutanix Prism Central."""
        try:
            events = self._list_events()
            if not events:
                self.log.debug("No events found")
                return

            for event in events:
                if self._should_skip_event(event):
                    continue
                self._process_event(event)

        except Exception as e:
            self.log.exception("Error collecting events: %s", e)

    def _should_skip_event(self, event):
        """Check if an event should be skipped based on its timestamp.

        Returns True if the event's creationTime is before or equal to last_event_collection_time.
        """
        if not self.last_event_collection_time:
            return False

        event_time_str = event.get("creationTime")
        if not event_time_str:
            return False

        event_time = int(get_timestamp(datetime.fromisoformat(event_time_str.replace("Z", "+00:00"))))
        if event_time < self.last_event_collection_time:
            self.log.debug(
                "Skipping event %s with timestamp %s (before last collection time %s)",
                event.get("extId"),
                event_time,
                self.last_event_collection_time,
            )
            return True

        return False

    def _process_event(self, event):
        """Process and send a single event to Datadog."""
        event_id = event.get("extId", "unknown")
        event_title = event.get("eventType", "Nutanix Event")
        event_message = event.get("message", "")
        created_time = event.get("creationTime")
        classifications = event.get("classifications", [])
        alert_type = "info"

        # Extract entity information for tagging
        event_tags = self.base_tags.copy()

        event_tags.append(f"ntnx_event_id:{event_id}")

        cluster_id = event.get("sourceClusterUUID", event.get("clusterUUID"))

        if cluster_id:
            event_tags.append(f"ntnx_cluster_id:{cluster_id}")
            if cluster_id in self.cluster_names:
                event_tags.append(f"ntnx_cluster_name:{self.cluster_names[cluster_id]}")

        for classification in classifications:
            event_tags.append(f"ntnx_event_classification:{classification}")

        if source_entity := event.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                entity_id = source_entity.get("extId")
                if entity_id:
                    event_tags.append(f"ntnx_{entity_type}_id:{entity_id}")

                entity_name = source_entity.get("name")
                if entity_name:
                    event_tags.append(f"ntnx_{entity_type}_name:{entity_name}")

        self.event(
            {
                "timestamp": self._parse_timestamp(created_time)
                if created_time
                else get_timestamp(get_current_datetime()),
                "event_type": self.__NAMESPACE__,
                "msg_title": event_title,
                "msg_text": event_message,
                "alert_type": alert_type,
                "source_type_name": self.__NAMESPACE__,
                "tags": event_tags,
            }
        )

    def _parse_timestamp(self, timestamp_str: str) -> int | None:
        """Parse ISO 8601 timestamp string to Unix timestamp.

        Args:
            timestamp_str: ISO 8601 formatted timestamp string

        Returns:
            Unix timestamp in seconds, or None if parsing fails
        """
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            self.log.warning("Failed to parse timestamp: %s", timestamp_str)
            return None

    def _list_events(self):
        """Fetch events from Prism Central.

        Returns a list of events since the last collection.
        On the first run, collects events from the last collection interval.
        """
        now = get_current_datetime()

        start_time = now - timedelta(seconds=self.sampling_interval)

        # Format time for API (ISO 8601 with Z suffix)
        start_time_str = start_time.replace(microsecond=0).isoformat().replace("+00:00", "Z")

        params = {}
        params["$filter"] = f"creationTime gt {start_time_str}"
        params["$orderBy"] = "creationTime asc"

        events = self._get_paginated_request_data("api/monitoring/v4.0/serviceability/events", params=params)

        self.last_event_collection_time = int(
            get_timestamp(datetime.fromisoformat(now.isoformat().replace("Z", "+00:00")))
        )

        return events

    def _collect_tasks(self):
        """Collect tasks from Nutanix Prism Central."""
        try:
            tasks = self._list_tasks()
            if not tasks:
                self.log.debug("No tasks found")
                return

            for task in tasks:
                # Belt-and-suspenders: the API filter should prevent duplicates, but
                # we defensively skip anything <= the last seen timestamp.
                if self.last_task_collection_time:
                    task_time_str = task.get("createdTime")
                    if task_time_str:
                        task_time = datetime.fromisoformat(task_time_str.replace("Z", "+00:00"))
                        if task_time <= self.last_task_collection_time:
                            continue

                self._process_task(task)
                # We request tasks ordered by createdTime asc, so the last one is the most recent.
            most_recent_time_str = tasks[-1].get("createdTime")
            most_recent_time = (
                datetime.fromisoformat(most_recent_time_str.replace("Z", "+00:00")) if most_recent_time_str else None
            )

            if most_recent_time:
                self.last_task_collection_time = most_recent_time

        except Exception as e:
            self.log.exception("Error collecting tasks: %s", e)

    def _process_task(self, task):
        """Process and send a single task to Datadog as an event."""
        task_id = task.get("extId", "unknown")
        task_operation = task.get("operation", "Nutanix Task")
        task_description = task.get("operationDescription", "")
        created_time = task.get("createdTime")
        status = task.get("status", "UNKNOWN")

        # Determine alert type based on task status
        alert_type_map = {
            "SUCCEEDED": "success",
            "FAILED": "error",
            "RUNNING": "info",
            "QUEUED": "info",
            "CANCELED": "warning",
        }
        alert_type = alert_type_map.get(status, "info")

        # Extract entity information for tagging
        task_tags = self.base_tags.copy()
        task_tags.append(f"ntnx_task_id:{task_id}")
        task_tags.append(f"ntnx_task_status:{status}")

        # Add cluster information
        cluster_ext_ids = task.get("clusterExtIds", [])
        if cluster_ext_ids:
            for cluster_id in cluster_ext_ids:
                task_tags.append(f"ntnx_cluster_id:{cluster_id}")
                if cluster_id in self.cluster_names:
                    task_tags.append(f"ntnx_cluster_name:{self.cluster_names[cluster_id]}")

        # Add owner information
        if owner := task.get("ownedBy"):
            if owner_name := owner.get("name"):
                task_tags.append(f"ntnx_owner_name:{owner_name}")
            if owner_id := owner.get("extId"):
                task_tags.append(f"ntnx_owner_id:{owner_id}")

        # Add affected entities information
        entities_affected = task.get("entitiesAffected", [])
        for entity in entities_affected:
            if entity_type := entity.get("rel"):
                task_tags.append(f"ntnx_entity_type:{entity_type}")
            if entity_id := entity.get("extId"):
                task_tags.append(f"ntnx_entity_id:{entity_id}")
            if entity_name := entity.get("name"):
                task_tags.append(f"ntnx_entity_name:{entity_name}")

        # Build message text
        msg_text = task_description
        if progress := task.get("progressPercentage"):
            msg_text += f" (Progress: {progress}%)"

        self.event(
            {
                "timestamp": self._parse_timestamp(created_time)
                if created_time
                else get_timestamp(get_current_datetime()),
                "event_type": self.__NAMESPACE__,
                "msg_title": f"Task: {task_operation}",
                "msg_text": msg_text,
                "alert_type": alert_type,
                "source_type_name": self.__NAMESPACE__,
                "tags": task_tags,
            }
        )
