# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from time import time
import xml.etree.ElementTree as ET
import json as json_module 

from datadog_checks.base.utils.db.utils import DBMAsyncJob, default_json_event_encoding
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.utils import is_azure_sql_database

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


def agent_check_getter(self):
    return self._check


class XESessionBase(DBMAsyncJob):
    """Base class for all XE session handlers"""

    def __init__(self, check, config, session_name):
        self.session_name = session_name
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self._check = check
        self._log = check.log
        self._config = config
        self.collection_interval = 60  # Default for POC
        self.max_events = 100  # Default max events to collect

        super(XESessionBase, self).__init__(
            check,
            run_sync=True,
            enabled=True,  # TODO: ALLEN configuration options, enabled for POC
            min_collection_interval=self._config.min_collection_interval,
            dbms="sqlserver",
            rate_limit=1 / float(self.collection_interval),
            job_name=f"xe_{session_name}",
            shutdown_callback=self._close_db_conn,
        )
        self._conn_key_prefix = f"dbm-xe-{session_name}-"
        self._is_azure_sql_database = False
        self._check_azure_status()

    def _check_azure_status(self):
        """Check if this is Azure SQL Database"""
        engine_edition = self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, "")
        self._is_azure_sql_database = is_azure_sql_database(engine_edition)

    def _close_db_conn(self):
        """Close database connection on shutdown"""
        pass

    def session_exists(self):
        """Check if this XE session exists and is running"""
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # For Azure SQL Database support
                level = ""
                if self._is_azure_sql_database:
                    level = "database_"

                # Build the query with proper parameterization
                query = f"SELECT 1 FROM sys.dm_xe_{level}sessions WHERE name = ?"
                cursor.execute(query, (self.session_name,))

                return cursor.fetchone() is not None

    def _query_ring_buffer(self):
        """Query the ring buffer for this XE session"""
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # For Azure SQL Database support
                level = ""
                if self._is_azure_sql_database:
                    level = "database_"

                # Build the complete query string with the correct level
                query = f"""
                    SELECT CAST(t.target_data as xml) as event_data
                    FROM sys.dm_xe_{level}sessions s
                    JOIN sys.dm_xe_{level}session_targets t
                        ON s.address = t.event_session_address
                    WHERE s.name = ?
                    AND t.target_name = 'ring_buffer'
                """
                cursor.execute(query, (self.session_name,))
                result = cursor.fetchone()
                if not result:
                    return None

                return result[0]

    def _process_events(self, xml_data):
        """Process the events from the XML data - override in subclasses"""
        raise NotImplementedError

    def _create_event_payload(self, events):
        """Create a payload to send to Datadog"""
        if not events:
            return None

        return {
            "host": self._check.hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": f"xe_{self.session_name}",
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time() * 1000,
            "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "service": self._config.service,
            f"sqlserver_{self.session_name}_events": events,
        }

    def _format_event_for_log(self, event):
        """Format a single event for logging"""
        formatted_event = {}
        # Include the most important fields first for readability
        important_fields = ['timestamp', 'sql_text', 'duration_ms', 'statement', 'client_app_name', 'database_name']

        for field in important_fields:
            if field in event:
                formatted_event[field] = event[field]

        # Add remaining fields
        for key, value in event.items():
            if key not in formatted_event:
                formatted_event[key] = value

        return formatted_event

    def run_job(self):
        """Run the XE session collection job"""
        self._log.info(f"ALLEN: Running job for {self.session_name} session")
        if not self.session_exists():
            self._log.warning(f"XE session {self.session_name} not found or not running")
            return

        xml_data = self._query_ring_buffer()
        if not xml_data:
            self._log.debug(f"No data found in ring buffer for session {self.session_name}")
            return

        events = self._process_events(xml_data)
        if not events:
            self._log.debug(f"No events processed from {self.session_name} session")
            return

        self._log.info(f"Found {len(events)} events from {self.session_name} session")

        # Log a sample of events (up to 3) for debugging
        sample_size = min(3, len(events))
        sample_events = [self._format_event_for_log(event) for event in events[:sample_size]]

        try:
            formatted_json = json_module.dumps(sample_events, indent=2, default=str)
            self._log.info(f"Sample events from {self.session_name} session:\n{formatted_json}")
        except Exception as e:
            self._log.error(f"Error formatting events for logging: {e}")

        # Create the payload but don't send it
        payload = self._create_event_payload(events)
        if payload:
            self._log.debug(f"Created payload for {self.session_name} session with {len(events)} events (not sending)")
            # serialized_payload = json.dumps(payload, default=default_json_event_encoding)
            # self._check.database_monitoring_query_activity(serialized_payload) 