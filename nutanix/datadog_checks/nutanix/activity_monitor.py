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
        # Read boolean flag from cache (stored as string)
        cached_value = self.check.read_persistent_cache("alerts_v42_supported")
        if cached_value == "True":
            self.alerts_v42_supported = True
        elif cached_value == "False":
            self.alerts_v42_supported = False
        else:
            self.alerts_v42_supported = None

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

    def collect_events(self) -> int:
        """Collect events from Nutanix Prism Central."""
        try:
            return self._collect(
                activity_kind="event",
                list_fn=lambda t: self._list_activity("api/monitoring/v4.0/serviceability/events", "creationTime", t),
                process_fn=self._process_event,
                time_field="creationTime",
                cache_key="last_event_collection_time",
            )
        except HTTPError as e:
            self.check.log.error(
                "[PC:%s:%s] Failed to collect events from endpoint 'api/monitoring/v4.0/serviceability/events': %s",
                self.check.pc_ip,
                self.check.pc_port,
                e.response.status_code if e.response else "HTTP error",
            )
            return 0
        except Exception as e:
            self.check.log.exception(
                "[PC:%s:%s] Unexpected error collecting events: %s", self.check.pc_ip, self.check.pc_port, e
            )
            return 0

    def collect_tasks(self) -> int:
        """Collect tasks from Nutanix Prism Central."""
        try:

            def _filter_subtasks(tasks: list[dict]) -> list[dict]:
                if not self.check.collect_subtasks_enabled:
                    return [t for t in tasks if not t.get("parentTask")]
                return tasks

            return self._collect(
                activity_kind="task",
                list_fn=lambda t: self._list_activity("api/prism/v4.0/config/tasks", "createdTime", t),
                process_fn=self._process_task,
                time_field="createdTime",
                cache_key="last_task_collection_time",
                pre_filter_fn=_filter_subtasks,
            )
        except HTTPError as e:
            self.check.log.error(
                "[PC:%s:%s] Failed to collect tasks from API endpoint 'api/prism/v4.0/config/tasks': HTTP %s",
                self.check.pc_ip,
                self.check.pc_port,
                e.response.status_code if e.response else "error",
            )
            return 0
        except Exception as e:
            self.check.log.exception(
                "[PC:%s:%s] Unexpected error collecting tasks: %s", self.check.pc_ip, self.check.pc_port, e
            )
            return 0

    def collect_audits(self) -> int:
        """Collect audits from Nutanix Prism Central."""
        try:
            return self._collect(
                activity_kind="audit",
                list_fn=lambda t: self._list_activity("api/monitoring/v4.0/serviceability/audits", "creationTime", t),
                process_fn=self._process_audit,
                time_field="creationTime",
                cache_key="last_audit_collection_time",
            )
        except HTTPError as e:
            self.check.log.error(
                "[PC:%s:%s] Failed to collect audits from endpoint 'api/monitoring/v4.0/serviceability/audits': %s",
                self.check.pc_ip,
                self.check.pc_port,
                e.response.status_code if e.response else "HTTP error",
            )
            return 0
        except Exception as e:
            self.check.log.exception(
                "[PC:%s:%s] Unexpected error collecting audits: %s", self.check.pc_ip, self.check.pc_port, e
            )
            return 0

    def collect_alerts(self) -> int:
        """Collect alerts from Nutanix Prism Central."""
        try:
            return self._collect(
                activity_kind="alert",
                list_fn=self._list_alerts,
                process_fn=self._process_alert,
                time_field="creationTime",
                cache_key="last_alert_collection_time",
            )
        except HTTPError as e:
            self.check.log.error(
                "[PC:%s:%s] Failed to collect alerts from API: HTTP %s",
                self.check.pc_ip,
                self.check.pc_port,
                e.response.status_code if e.response else "error",
            )
            return 0
        except Exception as e:
            self.check.log.exception(
                "[PC:%s:%s] Unexpected error collecting alerts: %s", self.check.pc_ip, self.check.pc_port, e
            )
            return 0

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

        cluster_id = event.get("sourceClusterUUID", event.get("clusterUUID"))

        if cluster_id and cluster_id in self.check.cluster_names:
            event_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")

        for classification in classifications:
            event_tags.append(f"ntnx_event_classification:{classification}")

        if source_entity := event.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                entity_name = source_entity.get("name")
                if entity_name:
                    event_tags.append(f"ntnx_{entity_type}_name:{entity_name}")

            # Add category tags from source entity
            event_tags.extend(self.check.extract_category_tags(source_entity))

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

        # Get cluster context for logging
        cluster_label = ""
        if cluster_ref := audit.get("clusterReference"):
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

        if cluster_ref := audit.get("clusterReference"):
            cluster_id = cluster_ref.get("extId")
            cluster_name = cluster_ref.get("name")
            if cluster_id and cluster_id in self.check.cluster_names:
                audit_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")
            elif cluster_name:
                audit_tags.append(f"ntnx_cluster_name:{cluster_name}")

        if source_entity := audit.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                entity_name = source_entity.get("name")
                if entity_name:
                    audit_tags.append(f"ntnx_{entity_type}_name:{entity_name}")

            # Add category tags from source entity
            audit_tags.extend(self.check.extract_category_tags(source_entity))

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

        if cluster_id := alert.get("clusterUUID"):
            if cluster_id in self.check.cluster_names:
                alert_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")

        for classification in alert.get("classifications", []) or []:
            alert_tags.append(f"ntnx_alert_classification:{classification}")

        for impact in alert.get("impactTypes", []) or []:
            alert_tags.append(f"ntnx_alert_impact:{impact}")

        if source_entity := alert.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                if entity_name := source_entity.get("name"):
                    alert_tags.append(f"ntnx_{entity_type}_name:{entity_name}")

            # Add category tags from source entity
            alert_tags.extend(self.check.extract_category_tags(source_entity))

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

        # alert type
        alert_type_map = {
            "SUCCEEDED": "success",
            "FAILED": "error",
            "RUNNING": "info",
            "QUEUED": "info",
            "CANCELED": "warning",
        }
        alert_type = alert_type_map.get(status, "info")

        # tags
        task_tags = self.check.base_tags.copy()
        task_tags.append(f"ntnx_task_status:{status}")

        # cluster info
        cluster_ext_ids = task.get("clusterExtIds", [])
        if cluster_ext_ids:
            for cluster_id in cluster_ext_ids:
                if cluster_id in self.check.cluster_names:
                    task_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")

        # owner info
        if owner := task.get("ownedBy"):
            if owner_name := owner.get("name"):
                task_tags.append(f"ntnx_owner_name:{owner_name}")

        # affected entities
        entities_affected = task.get("entitiesAffected", [])
        for entity in entities_affected:
            if entity_type := entity.get("rel"):
                task_tags.append(f"ntnx_entity_type:{entity_type}")
            if entity_name := entity.get("name"):
                task_tags.append(f"ntnx_entity_name:{entity_name}")

            # Add category tags from affected entity
            task_tags.extend(self.check.extract_category_tags(entity))

        # distinguish from other events we emit
        task_tags.append("ntnx_type:task")

        # message text
        msg_text = task_description
        if progress := task.get("progressPercentage"):
            msg_text += f" (Progress: {progress}%)"

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

    def _parse_timestamp(self, timestamp_str: str) -> int | None:
        """Parse ISO 8601 timestamp string to Unix timestamp."""
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except (ValueError, AttributeError):
            self.check.log.warning(
                "[PC:%s:%s] Failed to parse timestamp: %s", self.check.pc_ip, self.check.pc_port, timestamp_str
            )
            return None

    def _should_collect_activity_item(self, item: dict, item_kind: str) -> bool:
        """Return True if the activity item should be collected per resource_filters."""
        filters = self.check.resource_filters
        resources = []
        if item_kind == "event":
            cid = item.get("sourceClusterUUID") or item.get("clusterUUID")
            if cid:
                cluster_entity = {"extId": cid, "name": self.check.cluster_names.get(cid, "")}
                resources.append(("cluster", cluster_entity))
            if se := item.get("sourceEntity"):
                rtype = se.get("type")
                if rtype in ("cluster", "host", "vm"):
                    entity = {"extId": se.get("extId"), "name": se.get("name") or ""}
                    resources.append((rtype, entity))
        elif item_kind == "task":
            for cid in item.get("clusterExtIds") or []:
                cluster_entity = {"extId": cid, "name": self.check.cluster_names.get(cid, "")}
                resources.append(("cluster", cluster_entity))
            for ent in item.get("entitiesAffected") or []:
                rel = ent.get("rel", "")
                rtype = "cluster" if "cluster" in rel else "host" if "host" in rel else "vm" if "vm" in rel else None
                if rtype:
                    entity = {"extId": ent.get("extId"), "name": ent.get("name") or ""}
                    resources.append((rtype, entity))
        elif item_kind == "alert":
            if cid := item.get("clusterUUID"):
                cluster_entity = {"extId": cid, "name": self.check.cluster_names.get(cid, "")}
                resources.append(("cluster", cluster_entity))
            if se := item.get("sourceEntity"):
                rtype = se.get("type")
                if rtype in ("cluster", "host", "vm"):
                    entity = {"extId": se.get("extId"), "name": se.get("name") or ""}
                    resources.append((rtype, entity))
        elif item_kind == "audit":
            if cr := item.get("clusterReference"):
                cid, cname = cr.get("extId"), cr.get("name") or ""
                if cid:
                    cluster_entity = {"extId": cid, "name": cname or self.check.cluster_names.get(cid, "")}
                    resources.append(("cluster", cluster_entity))
            if se := item.get("sourceEntity"):
                rtype = se.get("type")
                if rtype in ("cluster", "host", "vm"):
                    entity = {"extId": se.get("extId"), "name": se.get("name") or ""}
                    resources.append((rtype, entity))

        # Infrastructure filters: cluster/host/vm
        if filters:
            if resources:
                if not all(should_collect_resource(rt, entity, filters, self.check.log) for rt, entity in resources):
                    return False
            # Activity filters: event/task/alert/audit
            if item_kind in ("event", "task", "alert", "audit") and not should_collect_activity(
                item_kind, item, filters, self.check.log
            ):
                return False
        return True

    def _filter_after_time(self, items: list[dict], last_time_str: str | None, field_name: str) -> list[dict]:
        """Filter items to those strictly after the last submitted time."""
        if not last_time_str:
            return items

        try:
            last_time = datetime.fromisoformat(last_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            self.check.log.warning(
                "[PC:%s:%s] Failed to parse last collection time: %s",
                self.check.pc_ip,
                self.check.pc_port,
                last_time_str,
            )
            return items

        filtered = []
        for item in items:
            item_time_str = item.get(field_name)
            if not item_time_str:
                continue
            try:
                item_time = datetime.fromisoformat(item_time_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                self.check.log.warning(
                    "[PC:%s:%s] Failed to parse item timestamp: %s", self.check.pc_ip, self.check.pc_port, item_time_str
                )
                continue
            if item_time > last_time:
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
            try:
                item_time = datetime.fromisoformat(item_time_str.replace("Z", "+00:00"))
                if max_time is None or item_time > max_time:
                    max_time = item_time
                    max_time_str = item_time_str
            except (ValueError, AttributeError):
                self.check.log.warning(
                    "[PC:%s:%s] Failed to parse item timestamp: %s", self.check.pc_ip, self.check.pc_port, item_time_str
                )
                continue

        return max_time_str
