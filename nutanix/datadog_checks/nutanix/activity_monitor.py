# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from collections.abc import Callable
from datetime import datetime, timedelta

from requests.exceptions import HTTPError

from datadog_checks.base.utils.time import get_current_datetime, get_timestamp
from datadog_checks.nutanix.resource_filters import should_collect_activity, should_collect_resource


class _SafeDict(dict):
    """Dict that returns missing keys as template placeholders for safe string formatting."""

    def __missing__(self, key):
        return "{" + key + "}"


class ActivityMonitor:
    def __init__(self, check):
        self.check = check
        self.last_event_collection_time = self.check.read_persistent_cache("last_event_collection_time")
        self.last_task_collection_time = self.check.read_persistent_cache("last_task_collection_time")
        self.last_audit_collection_time = self.check.read_persistent_cache("last_audit_collection_time")
        self.last_alert_collection_time = self.check.read_persistent_cache("last_alert_collection_time")
        # In-memory caches: id -> raw item (reset each check run)
        self._events: dict[str, dict] = {}
        self._audits: dict[str, dict] = {}
        self._alerts: dict[str, dict] = {}
        self._tasks: dict[str, dict] = {}
        # Read boolean flag from cache (stored as string)
        cached_value = self.check.read_persistent_cache("alerts_v42_supported")
        if cached_value == "True":
            self.alerts_v42_supported = True
        elif cached_value == "False":
            self.alerts_v42_supported = False
        else:
            self.alerts_v42_supported = None

    def reset_state(self) -> None:
        """Reset in-memory caches for a new collection run."""
        self._events = {}
        self._audits = {}
        self._alerts = {}
        self._tasks = {}

    def _collect(
        self,
        activity_kind: str,
        list_fn: Callable[[str], list[dict]],
        process_fn: Callable[[dict], None],
        time_field: str,
        cache_key: str,
        pre_filter_fn: Callable[[list[dict]], list[dict]] | None = None,
    ) -> int:
        """Collect activity items of a given kind from Nutanix Prism Central."""
        last_time = getattr(self, cache_key)
        start_time = last_time
        if not start_time:
            now = get_current_datetime()
            start_time = (now - timedelta(seconds=self.check.sampling_interval)).isoformat().replace("+00:00", "Z")

        self.check.log.debug(
            "[PC:%s:%s] Collecting %ss since: %s", self.check.pc_ip, self.check.pc_port, activity_kind, start_time
        )

        items = list_fn(start_time)
        if not items:
            self.check.log.debug("[PC:%s:%s] No %ss found", self.check.pc_ip, self.check.pc_port, activity_kind)
            return 0

        self.check.log.debug(
            "[PC:%s:%s] Fetched %d %ss from API", self.check.pc_ip, self.check.pc_port, len(items), activity_kind
        )

        items = self._filter_after_time(items, last_time, time_field)
        if not items:
            self.check.log.debug(
                "[PC:%s:%s] No new %ss after filtering", self.check.pc_ip, self.check.pc_port, activity_kind
            )
            return 0

        # Advance past all fetched items before applying resource filters
        most_recent_time_str = self._find_max_timestamp(items, time_field)

        if pre_filter_fn:
            items = pre_filter_fn(items)

        items = [i for i in items if self._should_collect_activity_item(i, activity_kind)]

        # Cache collected items by ID
        cache = getattr(self, f"_{activity_kind}s")
        for item in items:
            if ext_id := item.get("extId"):
                cache[ext_id] = item

        self.check.log.debug(
            "[PC:%s:%s] Processing %d %ss after filtering",
            self.check.pc_ip,
            self.check.pc_port,
            len(items),
            activity_kind,
        )

        for item in items:
            process_fn(item)

        if most_recent_time_str:
            setattr(self, cache_key, most_recent_time_str)
            self.check.write_persistent_cache(cache_key, most_recent_time_str)
            self.check.log.debug(
                "[PC:%s:%s] Updated %s to: %s",
                self.check.pc_ip,
                self.check.pc_port,
                cache_key,
                most_recent_time_str,
            )

        return len(items)

    def _safe_collect(self, activity_kind: str, collect_fn: Callable[[], int]) -> int:
        """Run a collection function with standard error handling."""
        try:
            return collect_fn()
        except HTTPError as e:
            self.check.log.error(
                "[PC:%s:%s] Failed to collect %ss: HTTP %s",
                self.check.pc_ip,
                self.check.pc_port,
                activity_kind,
                e.response.status_code if e.response else "error",
            )
            return 0
        except Exception as e:
            self.check.log.exception(
                "[PC:%s:%s] Unexpected error collecting %ss: %s",
                self.check.pc_ip,
                self.check.pc_port,
                activity_kind,
                e,
            )
            return 0

    def collect_events(self) -> int:
        return self._safe_collect(
            "event",
            lambda: self._collect(
                activity_kind="event",
                list_fn=lambda t: self._list_activity("api/monitoring/v4.0/serviceability/events", "creationTime", t),
                process_fn=self._process_event,
                time_field="creationTime",
                cache_key="last_event_collection_time",
            ),
        )

    def collect_tasks(self) -> int:
        def _filter_subtasks(tasks: list[dict]) -> list[dict]:
            if not self.check.collect_subtasks_enabled:
                return [t for t in tasks if not t.get("parentTask")]
            return tasks

        return self._safe_collect(
            "task",
            lambda: self._collect(
                activity_kind="task",
                list_fn=lambda t: self._list_activity("api/prism/v4.0/config/tasks", "createdTime", t),
                process_fn=self._process_task,
                time_field="createdTime",
                cache_key="last_task_collection_time",
                pre_filter_fn=_filter_subtasks,
            ),
        )

    def collect_audits(self) -> int:
        return self._safe_collect(
            "audit",
            lambda: self._collect(
                activity_kind="audit",
                list_fn=lambda t: self._list_activity("api/monitoring/v4.0/serviceability/audits", "creationTime", t),
                process_fn=self._process_audit,
                time_field="creationTime",
                cache_key="last_audit_collection_time",
            ),
        )

    def collect_alerts(self) -> int:
        return self._safe_collect(
            "alert",
            lambda: self._collect(
                activity_kind="alert",
                list_fn=self._list_alerts,
                process_fn=self._process_alert,
                time_field="creationTime",
                cache_key="last_alert_collection_time",
            ),
        )

    def _list_activity(self, endpoint: str, time_field: str, start_time_str: str) -> list[dict]:
        """Fetch activity items from Prism Central."""
        params = {
            "$filter": f"{time_field} gt {start_time_str}",
            "$orderBy": f"{time_field} asc",
        }
        return self.check._get_paginated_request_data(endpoint, params=params)

    def _list_alerts(self, start_time_str: str) -> list[dict]:
        """Fetch alerts from Prism Central with v4.2/v4.0 fallback."""
        params = {
            "$filter": f"creationTime gt {start_time_str}",
            "$orderBy": "creationTime asc",
        }

        if self.alerts_v42_supported is False:
            self.check.log.debug(
                "[PC:%s:%s] Using alerts API v4.0 (v4.2 not supported)", self.check.pc_ip, self.check.pc_port
            )
            del params["$filter"]
            return self.check._get_paginated_request_data("api/monitoring/v4.0/serviceability/alerts", params=params)

        try:
            self.check.log.debug("[PC:%s:%s] Attempting to use alerts API v4.2", self.check.pc_ip, self.check.pc_port)
            result = self.check._get_paginated_request_data("api/monitoring/v4.2/serviceability/alerts", params=params)
            if self.alerts_v42_supported is None:
                self.check.log.debug(
                    "[PC:%s:%s] Alerts API v4.2 is supported, caching for future use",
                    self.check.pc_ip,
                    self.check.pc_port,
                )
                self.alerts_v42_supported = True
                self.check.write_persistent_cache("alerts_v42_supported", "True")
            return result
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self.check.log.debug(
                    "[PC:%s:%s] Alerts API v4.2 not supported, falling back to v4.0 permanently",
                    self.check.pc_ip,
                    self.check.pc_port,
                )
                self.alerts_v42_supported = False
                self.check.write_persistent_cache("alerts_v42_supported", "False")
                del params["$filter"]
                return self.check._get_paginated_request_data(
                    "api/monitoring/v4.0/serviceability/alerts", params=params
                )
            raise

    def _get_alert(self, alert_ext_id: str) -> dict | None:
        """Get an alert by ID, from cache or fetched from the API."""
        if alert := self._alerts.get(alert_ext_id):
            return alert

        endpoint = "api/monitoring/v4.0/serviceability/alerts"
        if self.alerts_v42_supported is True:
            endpoint = "api/monitoring/v4.2/serviceability/alerts"

        self.check.log.debug(
            "[PC:%s:%s] Alert %s not in cache, fetching from API",
            self.check.pc_ip,
            self.check.pc_port,
            alert_ext_id,
        )
        try:
            alert = self.check._get_request_data(f"{endpoint}/{alert_ext_id}")
            if alert:
                self._alerts[alert_ext_id] = alert
                self.check.log.debug(
                    "[PC:%s:%s] Fetched alert %s: %s",
                    self.check.pc_ip,
                    self.check.pc_port,
                    alert_ext_id,
                    alert.get("title", ""),
                )
            return alert
        except Exception as e:
            self.check.log.debug(
                "[PC:%s:%s] Failed to fetch alert %s: %s",
                self.check.pc_ip,
                self.check.pc_port,
                alert_ext_id,
                e,
            )
            return None

    def _process_event(self, event: dict) -> None:
        """Process and send a single event to Datadog."""
        event_title = event.get("eventType", "Nutanix Event")
        event_message = event.get("message", "")
        created_time = event.get("creationTime")
        classifications = event.get("classifications", [])
        alert_type = "info"

        # Render template variables in message from parameters
        if parameters := event.get("parameters"):
            event_message = self._render_message(event_message, parameters)

        # Extract entity information for tagging
        event_tags = self.check.base_tags.copy()

        self._add_cluster_name_tag(event_tags, event.get("sourceClusterUUID", event.get("clusterUUID")))

        for classification in classifications:
            event_tags.append(f"ntnx_event_classification:{classification}")

        self._add_source_entity_tags(event_tags, event)

        # Distinguish Prism Central events from tasks
        event_tags.append("ntnx_type:event")

        self.check.event(
            {
                "timestamp": self._parse_timestamp(created_time)
                if created_time
                else get_timestamp(get_current_datetime()),
                "event_type": self.check.__NAMESPACE__,
                "msg_title": event_title,
                "msg_text": event_message,
                "alert_type": alert_type,
                "source_type_name": self.check.__NAMESPACE__,
                "tags": event_tags,
            }
        )

    def _process_audit(self, audit: dict) -> None:
        """Process and send a single audit to Datadog."""
        audit_id = audit.get("extId", "unknown")

        # Get cluster context for logging and tagging
        cluster_ref = audit.get("clusterReference")
        cluster_label = ""
        if cluster_ref:
            cluster_id = cluster_ref.get("extId")
            if cluster_id and cluster_id in self.check.cluster_names:
                cluster_label = f"[{self.check.cluster_names[cluster_id]}]"

        # Log audit submission for duplicate debugging
        self.check.log.debug(
            "[PC:%s:%s]%s Submitting audit - ID: %s, CreationTime: %s",
            self.check.pc_ip,
            self.check.pc_port,
            cluster_label,
            audit_id,
            audit.get("creationTime", "unknown"),
        )

        audit_type = audit.get("auditType", "Nutanix Audit")
        operation_type = audit.get("operationType")
        message = audit.get("message", "")
        created_time = audit.get("creationTime")

        # Render template variables in message from parameters
        if parameters := audit.get("parameters"):
            message = self._render_message(message, parameters)

        audit_tags = self.check.base_tags.copy()
        audit_tags.append(f"ntnx_audit_type:{audit_type}")
        if operation_type:
            audit_tags.append(f"ntnx_operation_type:{operation_type}")

        if cluster_ref:
            self._add_cluster_name_tag(audit_tags, cluster_ref.get("extId"), cluster_ref.get("name"))

        self._add_source_entity_tags(audit_tags, audit)

        if user_ref := audit.get("userReference"):
            if user_name := user_ref.get("name"):
                audit_tags.append(f"ntnx_user_name:{user_name}")

        affected_entities = audit.get("affectedEntities", [])
        for entity in affected_entities:
            if entity_type := entity.get("type"):
                audit_tags.append(f"ntnx_affected_entity_type:{entity_type}")
            if entity_name := entity.get("name"):
                audit_tags.append(f"ntnx_affected_entity_name:{entity_name}")

            # Add category tags from affected entity
            audit_tags.extend(self.check.extract_category_tags(entity))

        audit_tags.append("ntnx_type:audit")

        self.check.event(
            {
                "timestamp": self._parse_timestamp(created_time)
                if created_time
                else get_timestamp(get_current_datetime()),
                "event_type": self.check.__NAMESPACE__,
                "msg_title": f"Audit: {audit_type}",
                "msg_text": message,
                "alert_type": "info",
                "source_type_name": self.check.__NAMESPACE__,
                "tags": audit_tags,
            }
        )

    def _render_message(self, message: str, parameters: list[dict]) -> str:
        """Render template variables in a message using parameter values."""
        if not message or not parameters:
            return message

        # Build parameter map from parameters array
        param_map = {}
        for param in parameters:
            param_name = param.get("paramName")
            if not param_name:
                continue

            param_value = param.get("paramValue", {})
            # Extract value based on type
            if "stringValue" in param_value:
                param_map[param_name] = param_value["stringValue"]
            elif "intValue" in param_value:
                param_map[param_name] = str(param_value["intValue"])
            elif "boolValue" in param_value:
                param_map[param_name] = str(param_value["boolValue"])

        # Render template using format_map (handles {variable} syntax)
        try:
            return message.format_map(_SafeDict(**param_map))
        except Exception as e:
            self.check.log.debug("Failed to render alert message template: %s", e)
            return message

    def _process_alert(self, alert: dict) -> None:
        """Process and send a single alert to Datadog."""
        title = alert.get("title", "Nutanix Alert")
        message = alert.get("message", "")
        created_time = alert.get("creationTime")
        severity = alert.get("severity")
        alert_type = alert.get("alertType")

        # Render template variables in title and message from parameters
        if parameters := alert.get("parameters"):
            title = self._render_message(title, parameters)
            message = self._render_message(message, parameters)

        # map severity to alert_type
        severity_map = {
            "CRITICAL": "error",
            "WARNING": "warning",
            "INFO": "info",
        }
        event_alert_type = severity_map.get(severity, "info")

        alert_tags = self.check.base_tags.copy()
        if alert_type:
            alert_tags.append(f"ntnx_alert_type:{alert_type}")
        if severity:
            alert_tags.append(f"ntnx_alert_severity:{severity}")

        self._add_cluster_name_tag(alert_tags, alert.get("clusterUUID"))

        for classification in alert.get("classifications", []) or []:
            alert_tags.append(f"ntnx_alert_classification:{classification}")

        for impact in alert.get("impactTypes", []) or []:
            alert_tags.append(f"ntnx_alert_impact:{impact}")

        self._add_source_entity_tags(alert_tags, alert)

        alert_tags.append("ntnx_type:alert")

        self.check.event(
            {
                "timestamp": self._parse_timestamp(created_time)
                if created_time
                else get_timestamp(get_current_datetime()),
                "event_type": self.check.__NAMESPACE__,
                "msg_title": f"Alert: {title}",
                "msg_text": message,
                "alert_type": event_alert_type,
                "source_type_name": self.check.__NAMESPACE__,
                "tags": alert_tags,
            }
        )

    def _process_task(self, task: dict) -> None:
        """Process and send a single task to Datadog as an event."""
        task_operation = task.get("operation", "Nutanix Task")
        task_description = task.get("operationDescription", "")
        created_time = task.get("createdTime")
        status = task.get("status", "UNKNOWN")
        is_subtask = task.get("parentTask") is not None

        alert_type = {
            "SUCCEEDED": "success",
            "FAILED": "error",
            "RUNNING": "info",
            "QUEUED": "info",
            "CANCELED": "warning",
        }.get(status, "info")

        task_tags = self.check.base_tags.copy()
        task_tags.append(f"ntnx_task_status:{status}")

        for cluster_id in task.get("clusterExtIds", []):
            self._add_cluster_name_tag(task_tags, cluster_id)

        if owner := task.get("ownedBy"):
            if owner_name := owner.get("name"):
                task_tags.append(f"ntnx_owner_name:{owner_name}")

        # Extract tags and resolve alert references from affected entities
        entities_affected = task.get("entitiesAffected", [])
        alert_titles = []
        for entity in entities_affected:
            if entity_type := entity.get("rel"):
                task_tags.append(f"ntnx_entity_type:{entity_type}")
            if entity_name := entity.get("name"):
                task_tags.append(f"ntnx_entity_name:{entity_name}")
            task_tags.extend(self.check.extract_category_tags(entity))

            # Enrich with rendered alert title when the entity is an alert
            if entity_type == "monitoring:serviceability:alert":
                if alert := self._get_alert(entity.get("extId", "")):
                    title = alert.get("title", "")
                    if parameters := alert.get("parameters"):
                        title = self._render_message(title, parameters)
                    if title:
                        alert_titles.append(title)

        task_tags.append("ntnx_type:task")

        msg_text = task_description
        if progress := task.get("progressPercentage"):
            msg_text += f" (Progress: {progress}%)"
        if alert_titles:
            msg_text += "\n\nAffected alerts:\n" + "\n".join(f"- {t}" for t in alert_titles)

        self.check.event(
            {
                "timestamp": self._parse_timestamp(created_time)
                if created_time
                else get_timestamp(get_current_datetime()),
                "event_type": self.check.__NAMESPACE__,
                "msg_title": f"Subtask: {task_operation}" if is_subtask else f"Task: {task_operation}",
                "msg_text": msg_text,
                "alert_type": alert_type,
                "source_type_name": self.check.__NAMESPACE__,
                "tags": task_tags,
            }
        )

    def _parse_iso(self, timestamp_str: str) -> datetime | None:
        """Parse an ISO 8601 timestamp string to a datetime object."""
        try:
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            self.check.log.warning(
                "[PC:%s:%s] Failed to parse timestamp: %s", self.check.pc_ip, self.check.pc_port, timestamp_str
            )
            return None

    def _parse_timestamp(self, timestamp_str: str) -> int | None:
        """Parse ISO 8601 timestamp string to Unix timestamp."""
        dt = self._parse_iso(timestamp_str)
        return int(dt.timestamp()) if dt else None

    def _add_source_entity_tags(self, tags: list[str], item: dict) -> None:
        """Add source entity type/name and category tags."""
        if source_entity := item.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                if entity_name := source_entity.get("name"):
                    tags.append(f"ntnx_{entity_type}_name:{entity_name}")
            tags.extend(self.check.extract_category_tags(source_entity))

    def _add_cluster_name_tag(self, tags: list[str], cluster_id: str | None, fallback_name: str | None = None) -> None:
        """Add cluster name tag from ID lookup, with optional fallback."""
        if not cluster_id:
            return
        if cluster_id in self.check.cluster_names:
            tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")
        elif fallback_name:
            tags.append(f"ntnx_cluster_name:{fallback_name}")

    def _cluster_resource(self, cluster_id: str) -> tuple[str, dict]:
        """Build a cluster resource tuple from a cluster ID."""
        cluster_name = self.check.cluster_names.get(cluster_id, "")
        return ("cluster", {"extId": cluster_id, "name": cluster_name})

    def _source_entity_resource(self, item: dict) -> tuple[str, dict] | None:
        """Extract a resource tuple from the sourceEntity field if valid."""
        source_entity = item.get("sourceEntity")
        if not source_entity:
            return None
        resource_type = source_entity.get("type")
        if resource_type not in ("cluster", "host", "vm"):
            return None
        entity = {"extId": source_entity.get("extId"), "name": source_entity.get("name") or ""}
        return (resource_type, entity)

    def _extract_item_resources(self, item: dict, item_kind: str) -> list[tuple[str, dict]]:
        """Extract filterable resources from an activity item."""
        resources: list[tuple[str, dict]] = []
        if item_kind == "event":
            cluster_id = item.get("sourceClusterUUID") or item.get("clusterUUID")
            if cluster_id:
                resources.append(self._cluster_resource(cluster_id))
            if source_resource := self._source_entity_resource(item):
                resources.append(source_resource)
        elif item_kind == "task":
            for cluster_id in item.get("clusterExtIds") or []:
                resources.append(self._cluster_resource(cluster_id))
            for affected_entity in item.get("entitiesAffected") or []:
                relation = affected_entity.get("rel", "")
                resource_type = (
                    "cluster"
                    if "cluster" in relation
                    else "host"
                    if "host" in relation
                    else "vm"
                    if "vm" in relation
                    else None
                )
                if resource_type:
                    entity = {"extId": affected_entity.get("extId"), "name": affected_entity.get("name") or ""}
                    resources.append((resource_type, entity))
        elif item_kind == "alert":
            if cluster_id := item.get("clusterUUID"):
                resources.append(self._cluster_resource(cluster_id))
            if source_resource := self._source_entity_resource(item):
                resources.append(source_resource)
        elif item_kind == "audit":
            cluster_ref = item.get("clusterReference")
            if cluster_ref:
                cluster_id = cluster_ref.get("extId")
                if cluster_id:
                    cluster_name = cluster_ref.get("name") or self.check.cluster_names.get(cluster_id, "")
                    resources.append(("cluster", {"extId": cluster_id, "name": cluster_name}))
            if source_resource := self._source_entity_resource(item):
                resources.append(source_resource)
        return resources

    def _should_collect_activity_item(self, item: dict, item_kind: str) -> bool:
        """Return True if the activity item should be collected per resource_filters."""
        resource_filters = self.check.resource_filters
        if not resource_filters:
            return True
        resources = self._extract_item_resources(item, item_kind)
        if resources and not all(
            should_collect_resource(resource_type, entity, resource_filters, self.check.log)
            for resource_type, entity in resources
        ):
            return False
        if not should_collect_activity(item_kind, item, resource_filters, self.check.log):
            return False
        return True

    def _filter_after_time(self, items: list[dict], last_time_str: str | None, field_name: str) -> list[dict]:
        """Filter items to those strictly after the last submitted time."""
        if not last_time_str:
            return items

        last_time = self._parse_iso(last_time_str)
        if not last_time:
            return items

        filtered = []
        for item in items:
            item_time_str = item.get(field_name)
            if not item_time_str:
                continue
            item_time = self._parse_iso(item_time_str)
            if item_time and item_time > last_time:
                filtered.append(item)

        return filtered

    def _find_max_timestamp(self, items: list[dict], field_name: str) -> str | None:
        """Find the maximum timestamp among all items."""
        max_time = None
        max_time_str = None

        for item in items:
            item_time_str = item.get(field_name)
            if not item_time_str:
                continue
            item_time = self._parse_iso(item_time_str)
            if item_time and (max_time is None or item_time > max_time):
                max_time = item_time
                max_time_str = item_time_str

        return max_time_str
