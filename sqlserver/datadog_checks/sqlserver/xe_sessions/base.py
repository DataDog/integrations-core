# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json as json_module
from io import BytesIO, StringIO
from time import time

from lxml import etree

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
        self.collection_interval = 10  # Default for POC
        self.max_events = 100  # Default max events to collect
        self._last_event_timestamp = None  # Initialize timestamp tracking

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
        """
        Query the ring buffer data and parse the XML on the client side.
        This avoids expensive server-side XML parsing for better performance.
        """
        # Time just the database query
        query_start_time = time()
        raw_xml = None
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # For Azure SQL Database support
                level = ""
                if self._is_azure_sql_database:
                    level = "database_"

                # Get raw XML data without server-side parsing
                query = f"""
                    SELECT CAST(t.target_data AS XML) AS target_xml
                    FROM sys.dm_xe_{level}sessions s
                    JOIN sys.dm_xe_{level}session_targets t
                        ON s.address = t.event_session_address
                    WHERE s.name = ?
                    AND t.target_name = 'ring_buffer'
                """

                try:
                    cursor.execute(query, (self.session_name,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        raw_xml = str(row[0])
                except Exception as e:
                    self._log.error(f"Error querying ring buffer: {e}")

        query_time = time() - query_start_time

        if not raw_xml:
            return None, query_time, 0

        # Time the XML parsing separately
        parse_start_time = time()
        filtered_events = self._filter_ring_buffer_events(raw_xml)
        if not filtered_events:
            return None, query_time, time() - parse_start_time

        combined_xml = "<events>"
        for event_xml in filtered_events:
            combined_xml += event_xml
        combined_xml += "</events>"
        parse_time = time() - parse_start_time

        return combined_xml, query_time, parse_time

    def _query_event_file(self):
        """Query the event file for this XE session with timestamp filtering"""
        query_start_time = time()
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # Azure SQL Database doesn't support file targets
                if self._is_azure_sql_database:
                    self._log.warning("Event file target is not supported on Azure SQL Database")
                    query_time = time() - query_start_time
                    return None, query_time, 0

                # Define the file path pattern
                file_path = f"d:\\rdsdbdata\\log\\{self.session_name}*.xel"
                self._log.debug(f"Reading events from file path: {file_path}")

                # Build parameters based on checkpoints
                params = []
                where_clauses = []

                if self._last_event_timestamp:
                    where_clauses.append("CAST(xe.event_data AS XML).value('(event/@timestamp)[1]', 'datetime2') > ?")
                    params.append(self._last_event_timestamp)
                    self._log.debug(f"Filtering events newer than timestamp: {self._last_event_timestamp}")

                # Build the query
                where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                query = f"""
                    SELECT CAST(event_data AS XML) as event_xml
                    FROM (
                        SELECT *
                        FROM sys.fn_xe_file_target_read_file(
                            ?,
                            NULL,
                            NULL,
                            NULL
                        )
                    ) AS xe
                    {where_clause}
                    ORDER BY CAST(xe.event_data AS XML).value('(event/@timestamp)[1]', 'datetime2')
                """

                try:
                    params.insert(0, file_path)
                    cursor.execute(query, params)

                    # Combine all results into one XML document
                    rows = cursor.fetchall()
                    query_time = time() - query_start_time

                    if not rows:
                        return None, query_time, 0

                    combined_xml = "<events>"
                    for row in rows:
                        combined_xml += str(row[0])
                    combined_xml += "</events>"

                    # Log a sample of the generated XML for debugging
                    if rows:
                        self._log.debug(f"Sample XML from event file: {str(rows[0][0])[:200]}...")

                    return combined_xml, query_time, 0
                except Exception as e:
                    self._log.error(f"Error querying event file: {e}")
                    query_time = time() - query_start_time
                    return None, query_time, 0

    def _filter_ring_buffer_events(self, xml_data):
        """
        Parse and filter ring buffer XML data using lxml.etree.iterparse.
        Returns a list of event XML strings that match the timestamp filter.
        """
        if not xml_data:
            return []
        filtered_events = []
        try:
            # Convert string to bytes for lxml
            xml_stream = BytesIO(xml_data.encode('utf-8'))

            # Only parse 'end' events for <event> tags
            context = etree.iterparse(xml_stream, events=('end',), tag='event')

            for _, elem in context:
                timestamp = elem.get('timestamp')

                if (not self._last_event_timestamp) or (timestamp and timestamp > self._last_event_timestamp):
                    event_xml = etree.tostring(elem, encoding='unicode')
                    filtered_events.append(event_xml)

                # Free memory for processed elements
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                if len(filtered_events) >= self.max_events:
                    break

            return filtered_events

        except Exception as e:
            self._log.error(f"Error filtering ring buffer events: {e}")
            return []

    def _extract_value(self, element, default=None):
        """Helper method to extract values from XML elements with consistent handling"""
        if element is None:
            return default

        # First try to get from value element
        value_elem = element.find('./value')
        if value_elem is not None and value_elem.text:
            return value_elem.text.strip()

        # If no value element or empty, try the element's text directly
        if element.text:
            return element.text.strip()

        return default

    def _extract_int_value(self, element, default=None):
        """Helper method to extract integer values with error handling"""
        value = self._extract_value(element, default)
        if value is None:
            return default

        try:
            return int(value)
        except (ValueError, TypeError) as e:
            self._log.debug(f"Error converting to int: {e}")
            return default

    def _extract_text_representation(self, element, default=None):
        """Get the text representation when both value and text are available"""
        text_elem = element.find('./text')
        if text_elem is not None and text_elem.text:
            return text_elem.text.strip()
        return default

    def _process_events(self, xml_data):
        """Process the events from the XML data - override in subclasses"""
        raise NotImplementedError

    def _normalize_event(self, event, numeric_fields, string_fields):
        """
        Generic method to normalize and validate an event data structure.

        Args:
            event: The raw event data dictionary
            numeric_fields: Dictionary mapping field names to default values for numeric fields
            string_fields: List of string field names

        Returns:
            A normalized event dictionary with consistent types
        """
        normalized = {}

        # Required fields with defaults
        normalized["timestamp"] = event.get("timestamp", "")

        # Numeric fields with defaults
        for field, default in numeric_fields.items():
            value = event.get(field)
            if value is None:
                normalized[field] = default
            else:
                try:
                    normalized[field] = float(value) if field == "duration_ms" else int(value)
                except (ValueError, TypeError):
                    normalized[field] = default

        # String fields with defaults
        for field in string_fields:
            normalized[field] = str(event.get(field, "") or "")

        return normalized

    def _create_event_payload(self, raw_event, event_type, normalized_event_field):
        """
        Create a structured event payload for a single event with consistent format.

        Args:
            raw_event: The raw event data to normalize
            event_type: The type of event (e.g., "xe_rpc" or "xe_batch")
            normalized_event_field: The field name for the normalized event in the payload

        Returns:
            A dictionary with the standard payload structure
        """
        # Normalize the event - must be implemented by subclass
        normalized_event = self._normalize_event_impl(raw_event)

        return {
            "host": self._check.hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": event_type,
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time() * 1000,
            "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "service": self._config.service,
            normalized_event_field: normalized_event,
        }

    def _format_event_for_log(self, event, important_fields):
        """
        Format a single event for logging with important fields first

        Args:
            event: The event data dictionary
            important_fields: List of field names to prioritize in the output

        Returns:
            A formatted event dictionary with the most important fields first
        """
        formatted_event = {}

        # Include the most important fields first for readability
        for field in important_fields:
            if field in event:
                formatted_event[field] = event[field]

        # Add remaining fields
        for key, value in event.items():
            if key not in formatted_event:
                formatted_event[key] = value

        return formatted_event

    def _normalize_event_impl(self, event):
        """
        Implementation of event normalization - to be overridden by subclasses.
        This method should apply the specific normalization logic for each event type.
        """
        raise NotImplementedError

    def _get_important_fields(self):
        """
        Get the list of important fields for this event type - to be overridden by subclasses.
        Used for formatting events for logging.
        """
        return ['timestamp', 'duration_ms']

    def run_job(self):
        """Run the XE session collection job"""
        job_start_time = time()
        self._log.info(f"Running job for {self.session_name} session")
        if not self.session_exists():
            self._log.warning(f"XE session {self.session_name} not found or not running")
            return

        # Get the XML data and timing info
        xml_data, query_time, parse_time = self._query_ring_buffer()
        # xml_data, query_time, parse_time = self._query_event_file()  # Alternate data source

        if not xml_data:
            self._log.debug(f"No data found for session {self.session_name}")
            return

        # Time the event processing
        process_start_time = time()
        events = self._process_events(xml_data)
        process_time = time() - process_start_time

        if not events:
            self._log.debug(f"No events processed from {self.session_name} session")
            return

        # Update timestamp tracking with the last event (events are ordered by timestamp)
        if events and 'timestamp' in events[-1]:
            self._last_event_timestamp = events[-1]['timestamp']
            self._log.debug(f"Updated checkpoint to {self._last_event_timestamp}")

        total_time = time() - job_start_time
        self._log.info(
            f"Found {len(events)} events from {self.session_name} session - "
            f"Times: query={query_time:.3f}s parse={parse_time:.3f}s process={process_time:.3f}s total={total_time:.3f}s"
        )

        # Log a sample of events (up to 3) for debugging
        sample_size = min(3, len(events))
        important_fields = self._get_important_fields()
        sample_events = [self._format_event_for_log(event, important_fields) for event in events[:sample_size]]

        try:
            formatted_json = json_module.dumps(sample_events, indent=2, default=str)
            self._log.info(f"Sample events from {self.session_name} session:\n{formatted_json}")
        except Exception as e:
            self._log.error(f"Error formatting events for logging: {e}")

        # Process each event individually
        event_type = f"xe_{self.session_name.replace('datadog_', '')}"
        normalized_event_field = f"sqlserver_{self.session_name.replace('datadog_', '')}_event"

        for event in events:
            try:
                # Create a properly structured payload for this specific event
                payload = self._create_event_payload(event, event_type, normalized_event_field)
                # For now, just log it instead of sending
                self._log.debug(f"Created payload for {self.session_name} event (not sending)")

                # Log the first event payload in each batch for validation
                if event == events[0]:
                    try:
                        payload_json = json_module.dumps(payload, default=str, indent=2)
                        self._log.debug(f"Sample event payload:\n{payload_json}")
                    except Exception as e:
                        self._log.error(f"Error serializing payload for logging: {e}")

                # Uncomment to enable sending to Datadog in the future:
                # serialized_payload = json.dumps(payload, default=default_json_event_encoding)
                # self._check.database_monitoring_query_activity(serialized_payload)
            except Exception as e:
                self._log.error(f"Error processing event: {e}")
                continue
