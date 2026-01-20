# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta

from requests.exceptions import HTTPError

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp


class ActivityMonitor:
    def __init__(self, check):
        self.check = check
        self.last_event_collection_time = None
        self.last_task_collection_time = None
        self.last_audit_collection_time = None
        self.last_alert_collection_time = None
        self.last_audit_collection_time = None
        self.alerts_v42_supported = is_affirmative(self.check.read_persistent_cache("alerts_v42_supported"))

    def collect_events(self):
        """Collect events from Nutanix Prism Central."""
        try:
            start_time = self.last_event_collection_time
            if not start_time:
                now = get_current_datetime()
                start_time = (now - timedelta(seconds=self.check.sampling_interval)).isoformat().replace("+00:00", "Z")

            events = self._list_events(start_time)
            if not events:
                self.check.log.debug("No events found")
                return

            # Filter out events with timestamps older than or equal to last collection time
            events = self._filter_after_time(events, self.last_event_collection_time, "creationTime")
            if not events:
                self.check.log.debug("No new events after filtering")
                return

            for event in events:
                self._process_event(event)

            # update last time to the maximum creationTime seen
            most_recent_time_str = self._find_max_timestamp(events, "creationTime")
            if most_recent_time_str:
                self.last_event_collection_time = most_recent_time_str

        except Exception as e:
            self.check.log.exception("Error collecting events: %s", e)

    def _list_events(self, start_time_str):
        """Fetch events from Prism Central.

        Returns a list of events since the last collection.
        On the first run, collects events from the last collection interval.
        """
        params = {}
        params["$filter"] = f"creationTime gt {start_time_str}"
        params["$orderBy"] = "creationTime asc"

        return self.check._get_paginated_request_data("api/monitoring/v4.0/serviceability/events", params=params)

    def _process_event(self, event):
        """Process and send a single event to Datadog."""
        event_id = event.get("extId", "unknown")
        event_title = event.get("eventType", "Nutanix Event")
        event_message = event.get("message", "")
        created_time = event.get("creationTime")
        classifications = event.get("classifications", [])
        alert_type = "info"

        # Extract entity information for tagging
        event_tags = self.check.base_tags.copy()

        event_tags.append(f"ntnx_event_id:{event_id}")

        cluster_id = event.get("sourceClusterUUID", event.get("clusterUUID"))

        if cluster_id:
            event_tags.append(f"ntnx_cluster_id:{cluster_id}")
            # Access cluster_names via parent check's infrastructure_monitor (which should expose it)
            # or directly if we choose to expose it on check.
            # Assuming check exposes access to cluster_names property/attribute
            if cluster_id in self.check.cluster_names:
                event_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")

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

    def collect_tasks(self):
        """Collect tasks from Nutanix Prism Central."""
        try:
            start_time = self.last_task_collection_time
            if not start_time:
                now = get_current_datetime()
                start_time = (now - timedelta(seconds=self.check.sampling_interval)).isoformat().replace("+00:00", "Z")

            tasks = self._list_tasks(start_time)
            if not tasks:
                self.check.log.debug("No tasks found")
                return

            # Filter out tasks with timestamps older than or equal to last collection time
            tasks = self._filter_after_time(tasks, self.last_task_collection_time, "createdTime")
            if not tasks:
                self.check.log.debug("No new tasks after filtering")
                return

            for task in tasks:
                self._process_task(task)

            # update last time to the maximum createdTime seen
            most_recent_time_str = self._find_max_timestamp(tasks, "createdTime")
            if most_recent_time_str:
                self.last_task_collection_time = most_recent_time_str

        except Exception as e:
            self.check.log.exception("Error collecting tasks: %s", e)

    def collect_audits(self):
        """Collect audits from Nutanix Prism Central."""
        try:
            start_time = self.last_audit_collection_time
            if not start_time:
                now = get_current_datetime()
                start_time = (now - timedelta(seconds=self.check.sampling_interval)).isoformat().replace("+00:00", "Z")

            audits = self._list_audits(start_time)
            if not audits:
                self.check.log.debug("No audits found")
                return

            # Filter out audits with timestamps older than or equal to last collection time
            audits = self._filter_after_time(audits, self.last_audit_collection_time, "creationTime")
            if not audits:
                self.check.log.debug("No new audits after filtering")
                return

            for audit in audits:
                self._process_audit(audit)

            # update last time to the maximum creationTime seen
            most_recent_time_str = self._find_max_timestamp(audits, "creationTime")
            if most_recent_time_str:
                self.last_audit_collection_time = most_recent_time_str

        except Exception as e:
            self.check.log.exception("Error collecting audits: %s", e)

    def collect_alerts(self):
        """Collect alerts from Nutanix Prism Central."""
        try:
            start_time = self.last_alert_collection_time
            if not start_time:
                now = get_current_datetime()
                start_time = (now - timedelta(seconds=self.check.sampling_interval)).isoformat().replace("+00:00", "Z")

            alerts = self._list_alerts(start_time)
            if not alerts:
                self.check.log.debug("No alerts found")
                return

            # Filter out alerts with timestamps older than or equal to last collection time
            alerts = self._filter_after_time(alerts, self.last_alert_collection_time, "creationTime")
            if not alerts:
                self.check.log.debug("No new alerts after filtering")
                return

            for alert in alerts:
                self._process_alert(alert)

            # update last time to the maximum creationTime seen
            most_recent_time_str = self._find_max_timestamp(alerts, "creationTime")
            if most_recent_time_str:
                self.last_alert_collection_time = most_recent_time_str

        except Exception as e:
            self.check.log.exception("Error collecting alerts: %s", e)

    def _list_audits(self, start_time_str):
        """Fetch audits from Prism Central."""
        params = {}
        params["$filter"] = f"creationTime gt {start_time_str}"
        params["$orderBy"] = "creationTime asc"

        return self.check._get_paginated_request_data("api/monitoring/v4.0/serviceability/audits", params=params)

    def _list_alerts(self, start_time_str):
        """Fetch alerts from Prism Central."""
        params = {}
        params["$filter"] = f"creationTime gt {start_time_str}"
        params["$orderBy"] = "creationTime asc"

        if self.alerts_v42_supported is False:
            del params["$filter"]
            return self.check._get_paginated_request_data("api/monitoring/v4.0/serviceability/alerts", params=params)

        try:
            result = self.check._get_paginated_request_data("api/monitoring/v4.2/serviceability/alerts", params=params)
            if self.alerts_v42_supported is None:
                self.alerts_v42_supported = True
                self.check.write_persistent_cache("alerts_v42_supported", True)
            return result
        except HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                self.alerts_v42_supported = False
                self.check.write_persistent_cache("alerts_v42_supported", False)
                del params["$filter"]
                return self.check._get_paginated_request_data(
                    "api/monitoring/v4.0/serviceability/alerts", params=params
                )
            raise

    def _process_audit(self, audit):
        """Process and send a single audit to Datadog."""
        audit_id = audit.get("extId", "unknown")

        # Log audit submission for duplicate debugging
        self.check.log.info(
            "Submitting audit - ID: %s, CreationTime: %s",
            audit_id,
            audit.get("creationTime", "unknown"),
        )

        audit_type = audit.get("auditType", "Nutanix Audit")
        operation_type = audit.get("operationType")
        message = audit.get("message", "")
        created_time = audit.get("creationTime")

        audit_tags = self.check.base_tags.copy()
        audit_tags.append(f"ntnx_audit_id:{audit_id}")
        audit_tags.append(f"ntnx_audit_type:{audit_type}")
        if operation_type:
            audit_tags.append(f"ntnx_operation_type:{operation_type}")

        if cluster_ref := audit.get("clusterReference"):
            cluster_id = cluster_ref.get("extId")
            cluster_name = cluster_ref.get("name")
            if cluster_id:
                audit_tags.append(f"ntnx_cluster_id:{cluster_id}")
                if cluster_id in self.check.cluster_names:
                    audit_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")
                elif cluster_name:
                    audit_tags.append(f"ntnx_cluster_name:{cluster_name}")
            elif cluster_name:
                audit_tags.append(f"ntnx_cluster_name:{cluster_name}")

        if source_entity := audit.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                entity_id = source_entity.get("extId")
                if entity_id:
                    audit_tags.append(f"ntnx_{entity_type}_id:{entity_id}")
                entity_name = source_entity.get("name")
                if entity_name:
                    audit_tags.append(f"ntnx_{entity_type}_name:{entity_name}")

        if user_ref := audit.get("userReference"):
            if user_name := user_ref.get("name"):
                audit_tags.append(f"ntnx_user_name:{user_name}")

        affected_entities = audit.get("affectedEntities", [])
        for entity in affected_entities:
            if entity_type := entity.get("type"):
                audit_tags.append(f"ntnx_affected_entity_type:{entity_type}")
            if entity_id := entity.get("extId"):
                audit_tags.append(f"ntnx_affected_entity_id:{entity_id}")
            if entity_name := entity.get("name"):
                audit_tags.append(f"ntnx_affected_entity_name:{entity_name}")

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

    def _process_alert(self, alert):
        """Process and send a single alert to Datadog."""
        alert_id = alert.get("extId", "unknown")
        title = alert.get("title", "Nutanix Alert")
        message = alert.get("message", "")
        created_time = alert.get("creationTime")
        severity = alert.get("severity")
        alert_type = alert.get("alertType")

        # map severity to alert_type
        severity_map = {
            "CRITICAL": "error",
            "WARNING": "warning",
            "INFO": "info",
        }
        event_alert_type = severity_map.get(severity, "info")

        alert_tags = self.check.base_tags.copy()
        alert_tags.append(f"ntnx_alert_id:{alert_id}")
        if alert_type:
            alert_tags.append(f"ntnx_alert_type:{alert_type}")
        if severity:
            alert_tags.append(f"ntnx_alert_severity:{severity}")

        if cluster_id := alert.get("clusterUUID"):
            alert_tags.append(f"ntnx_cluster_id:{cluster_id}")
            if cluster_id in self.check.cluster_names:
                alert_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")

        for classification in alert.get("classifications", []) or []:
            alert_tags.append(f"ntnx_alert_classification:{classification}")

        for impact in alert.get("impactTypes", []) or []:
            alert_tags.append(f"ntnx_alert_impact:{impact}")

        if source_entity := alert.get("sourceEntity"):
            if entity_type := source_entity.get("type"):
                if entity_id := source_entity.get("extId"):
                    alert_tags.append(f"ntnx_{entity_type}_id:{entity_id}")
                if entity_name := source_entity.get("name"):
                    alert_tags.append(f"ntnx_{entity_type}_name:{entity_name}")

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

    def _list_tasks(self, start_time_str):
        """Fetch tasks from Prism Central.

        Returns a list of tasks since the last collection.
        Uses last_task_collection_time if available, otherwise uses now - sampling_interval.
        """
        params = {}
        params["$filter"] = f"createdTime gt {start_time_str}"
        params["$orderBy"] = "createdTime asc"

        return self.check._get_paginated_request_data("api/prism/v4.0/config/tasks", params=params)

    def _process_task(self, task):
        """Process and send a single task to Datadog as an event."""
        task_id = task.get("extId", "unknown")
        task_operation = task.get("operation", "Nutanix Task")
        task_description = task.get("operationDescription", "")
        created_time = task.get("createdTime")
        status = task.get("status", "UNKNOWN")

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
        task_tags.append(f"ntnx_task_id:{task_id}")
        task_tags.append(f"ntnx_task_status:{status}")

        # cluster info
        cluster_ext_ids = task.get("clusterExtIds", [])
        if cluster_ext_ids:
            for cluster_id in cluster_ext_ids:
                task_tags.append(f"ntnx_cluster_id:{cluster_id}")
                if cluster_id in self.check.cluster_names:
                    task_tags.append(f"ntnx_cluster_name:{self.check.cluster_names[cluster_id]}")

        # owner info
        if owner := task.get("ownedBy"):
            if owner_name := owner.get("name"):
                task_tags.append(f"ntnx_owner_name:{owner_name}")
            if owner_id := owner.get("extId"):
                task_tags.append(f"ntnx_owner_id:{owner_id}")

        # affected entities
        entities_affected = task.get("entitiesAffected", [])
        for entity in entities_affected:
            if entity_type := entity.get("rel"):
                task_tags.append(f"ntnx_entity_type:{entity_type}")
            if entity_id := entity.get("extId"):
                task_tags.append(f"ntnx_entity_id:{entity_id}")
            if entity_name := entity.get("name"):
                task_tags.append(f"ntnx_entity_name:{entity_name}")

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
                "msg_title": f"Task: {task_operation}",
                "msg_text": msg_text,
                "alert_type": alert_type,
                "source_type_name": self.check.__NAMESPACE__,
                "tags": task_tags,
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
            self.check.log.warning("Failed to parse timestamp: %s", timestamp_str)
            return None

    def _filter_after_time(self, items, last_time_str, field_name):
        """Filter items to those strictly after the last submitted time.

        This provides client-side filtering as a safeguard against API edge cases
        where items might be returned with timestamps equal to or before the last collection time.

        Args:
            items: List of items to filter
            last_time_str: ISO 8601 formatted timestamp string of the last collection
            field_name: Name of the timestamp field in the items

        Returns:
            List of items with timestamps strictly after last_time_str
        """
        if not last_time_str:
            return items

        try:
            last_time = datetime.fromisoformat(last_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            self.check.log.warning("Failed to parse last collection time: %s", last_time_str)
            return items

        filtered = []
        for item in items:
            item_time_str = item.get(field_name)
            if not item_time_str:
                continue
            try:
                item_time = datetime.fromisoformat(item_time_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                self.check.log.warning("Failed to parse item timestamp: %s", item_time_str)
                continue
            if item_time > last_time:
                filtered.append(item)

        return filtered

    def _find_max_timestamp(self, items, field_name):
        """Find the maximum timestamp among all items.

        The Nutanix API may not return items sorted by timestamp despite the $orderBy parameter,
        so we need to explicitly find the maximum timestamp to track the last collection time.

        Args:
            items: List of items to search
            field_name: Name of the timestamp field in the items

        Returns:
            The maximum timestamp string, or None if no valid timestamps found
        """
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
                self.check.log.warning("Failed to parse item timestamp: %s", item_time_str)
                continue

        return max_time_str
