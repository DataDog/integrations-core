# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta

from datadog_checks.base.utils.time import get_current_datetime, get_timestamp


class ActivityMonitor:
    def __init__(self, check):
        self.check = check
        self.last_event_collection_time = None
        self.last_task_collection_time = None

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

            for event in events:
                self._process_event(event)

            # update last time
            most_recent_time_str = events[-1].get("creationTime")
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

            for task in tasks:
                self._process_task(task)

            # update last time
            most_recent_time_str = tasks[-1].get("createdTime")
            if most_recent_time_str:
                self.last_task_collection_time = most_recent_time_str

        except Exception as e:
            self.check.log.exception("Error collecting tasks: %s", e)

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
