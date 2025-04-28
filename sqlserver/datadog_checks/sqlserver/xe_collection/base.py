# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import json as json_module
from abc import abstractmethod
from io import BytesIO, StringIO
from time import time

from lxml import etree

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.utils import is_azure_sql_database

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


def agent_check_getter(self):
    return self._check


class TimestampHandler:
    """Utility class for handling timestamps"""

    @staticmethod
    def format_for_output(timestamp_str):
        """
        Format a timestamp for output in a consistent format: YYYY-MM-DDTHH:MM:SS.sssZ
        This is used only for the output payload, not for filtering.

        Args:
            timestamp_str: A timestamp string in ISO format
        Returns:
            A formatted timestamp string or empty string if parsing fails
        """
        if not timestamp_str:
            return ""
        try:
            # Parse the timestamp
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            dt = datetime.datetime.fromisoformat(timestamp_str)
            # Format to consistent format with milliseconds precision
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
        except Exception:
            return timestamp_str

    @staticmethod
    def calculate_start_time(end_timestamp, duration_ms):
        """
        Calculate start time from end time and duration

        Args:
            end_timestamp: The end timestamp in ISO format
            duration_ms: Duration in milliseconds

        Returns:
            Start timestamp in ISO format or empty string if calculation fails
        """
        if not end_timestamp or duration_ms is None:
            return ""
        try:
            # Parse end time
            if end_timestamp.endswith('Z'):
                end_timestamp = end_timestamp[:-1] + '+00:00'
            end_datetime = datetime.datetime.fromisoformat(end_timestamp)

            # Calculate start time
            duration_delta = datetime.timedelta(milliseconds=float(duration_ms))
            start_datetime = end_datetime - duration_delta

            # Format consistently
            return start_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + 'Z'
        except Exception:
            return ""


class XESessionBase(DBMAsyncJob):
    """Base class for all XE session handlers"""

    # Base fields common to most/all event types
    BASE_NUMERIC_FIELDS = {
        "duration_ms": 0.0,
        "session_id": 0,
        "request_id": 0,
    }

    BASE_STRING_FIELDS = [
        "database_name",
        "client_hostname",
        "client_app_name",
        "username",
        "activity_id",
    ]

    BASE_SQL_FIELDS = [
        "statement",
        "sql_text",
        "batch_text",
    ]

    # Fields that should use text representation when available
    TEXT_FIELDS = ["result", "data_stream"]

    def __init__(self, check, config, session_name):
        self.session_name = session_name
        self.tags = [t for t in check.tags if not t.startswith('dd.internal')]
        self._check = check
        self._log = check.log
        self._config = config
        self.collection_interval = 10  # Default for POC
        self.max_events = 1000 # SQL Server XE sessions will limit 1000 events per ring buffer query
        self._last_event_timestamp = None  # Initialize timestamp tracking

        # Configuration for raw query text (RQT) events
        self._collect_raw_query = True  # Will be configurable in the future
        self._raw_statement_text_cache = RateLimitingTTLCache(
            maxsize=1000,  # Will be configurable in the future
            ttl=60 * 60 / 10,  # 10 samples per hour per query - will be configurable
        )

        # Obfuscator options - use the same options as the main check
        self._obfuscator_options = getattr(
            self._config, 'obfuscator_options', {'dbms': 'mssql', 'obfuscation_mode': 'replace'}
        )

        # Register event handlers - subclasses will override this
        self._event_handlers = {}

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

    # Methods to allow subclasses to extend field definitions
    def get_numeric_fields(self, event_type=None):
        """Get numeric fields with defaults for given event type"""
        return self.BASE_NUMERIC_FIELDS.copy()

    def get_string_fields(self, event_type=None):
        """Get string fields for given event type"""
        return self.BASE_STRING_FIELDS.copy()

    def get_sql_fields(self, event_type=None):
        """Get SQL fields for given event type"""
        if event_type == "sql_batch_completed":
            return ["batch_text", "sql_text"]
        elif event_type == "rpc_completed":
            return ["statement", "sql_text"]
        elif event_type == "module_end":
            return ["statement", "sql_text"]
        return self.BASE_SQL_FIELDS.copy()

    def register_event_handler(self, event_name, handler_method):
        """Register a handler method for a specific event type"""
        self._event_handlers[event_name] = handler_method

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

                # Use direct timestamp comparison without normalization
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


                if not self._last_event_timestamp or (timestamp and timestamp > self._last_event_timestamp):
                    event_xml = etree.tostring(elem, encoding='unicode')
                    filtered_events.append(event_xml)

                # Free memory for processed elements
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                if len(filtered_events) >= self.max_events:
                    self._log.debug(f"Filtered {len(filtered_events)} events from ring buffer")
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

    def _extract_field(self, data, event_data, field_name):
        """Extract field value based on its type"""
        if field_name == 'duration':
            self._extract_duration(data, event_data)
        elif field_name in self.get_numeric_fields(event_data.get('event_name')):
            value = self._extract_int_value(data)
            if value is not None:
                event_data[field_name] = value
        elif field_name in self.TEXT_FIELDS:
            # Try to get text representation first
            text_value = self._extract_text_representation(data)
            if text_value is not None:
                event_data[field_name] = text_value
            else:
                event_data[field_name] = self._extract_value(data)
        else:
            event_data[field_name] = self._extract_value(data)

    def _extract_duration(self, data, event_data):
        """Extract duration value and convert to milliseconds"""
        duration_value = self._extract_int_value(data)
        if duration_value is not None:
            event_data["duration_ms"] = duration_value / 1000
        else:
            event_data["duration_ms"] = None

    def _process_events(self, xml_data):
        """Template method for processing events with standardized XML parsing"""
        try:
            root = etree.fromstring(xml_data.encode('utf-8') if isinstance(xml_data, str) else xml_data)
        except Exception as e:
            self._log.error(f"Error parsing XML data: {e}")
            return []

        events = []
        for event in root.findall('./event')[: self.max_events]:
            try:
                # Basic common info from event attributes
                event_data = {"timestamp": event.get('timestamp'), "event_name": event.get('name', '')}

                # Use the strategy pattern to process events
                event_name = event_data["event_name"]
                if event_name in self._event_handlers:
                    handler = self._event_handlers[event_name]
                    if handler(event, event_data):
                        events.append(event_data)
                else:
                    self._log.debug(f"No handler for event type: {event_name}")
            except Exception as e:
                self._log.error(f"Error processing event {event.get('name', 'unknown')}: {e}")
                continue

        return events

    @abstractmethod
    def _normalize_event_impl(self, event):
        """
        Implementation of event normalization - to be overridden by subclasses.
        This method should apply the specific normalization logic for each event type.
        """
        raise NotImplementedError

    def _normalize_event(self, event, custom_numeric_fields=None, custom_string_fields=None):
        """
        Generic method to normalize and validate an event data structure.

        Args:
            event: The raw event data dictionary
            custom_numeric_fields: Optional override of numeric fields
            custom_string_fields: Optional override of string fields

        Returns:
            A normalized event dictionary with consistent types
        """
        normalized = {}

        event_type = event.get("event_name", "")

        # Get the field definitions for this event type
        numeric_fields = custom_numeric_fields or self.get_numeric_fields(event_type)
        string_fields = custom_string_fields or self.get_string_fields(event_type)

        # Add the XE event type to normalized data
        normalized["xe_type"] = event.get("event_name", "")

        # Format the event_fire_timestamp (from event's timestamp)
        raw_timestamp = event.get("timestamp", "")
        normalized["event_fire_timestamp"] = TimestampHandler.format_for_output(raw_timestamp)

        # Calculate and format query_start if duration_ms is available
        if raw_timestamp and "duration_ms" in event and event.get("duration_ms") is not None:
            normalized["query_start"] = TimestampHandler.calculate_start_time(
                raw_timestamp, event.get("duration_ms")
            )
        else:
            normalized["query_start"] = ""

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

        # Add SQL fields (statement, sql_text, batch_text)
        for field in self.get_sql_fields(event_type):
            if field in event:
                normalized[field] = event[field]

        # Add query_signature if present
        if "query_signature" in event:
            normalized["query_signature"] = event["query_signature"]

        return normalized

    def _determine_dbm_type(self):
        """
        Determine the dbm_type based on the session name.
        Returns the appropriate dbm_type for the current session.
        """
        # Sessions that produce query_completion events
        query_completion_sessions = [
            "datadog_query_completions",
            "datadog_sql_statement",
            "datadog_sp_statement",
        ]

        if self.session_name == "datadog_query_errors":
            return "query_error"
        elif self.session_name in query_completion_sessions:
            return "query_completion"
        else:
            self._log.debug(f"Unrecognized session name: {self.session_name}, using default dbm_type")
            return "query_completion"

    def _create_event_payload(self, raw_event):
        """
        Create a structured event payload for a single event with consistent format.

        Args:
            raw_event: The raw event data to normalize
        Returns:
            A dictionary with the standard payload structure
        """
        # Normalize the event - must be implemented by subclass
        normalized_event = self._normalize_event_impl(raw_event)

        # Add SQL metadata and signatures to the normalized event
        if 'query_signature' in raw_event:
            normalized_event['query_signature'] = raw_event['query_signature']

        return {
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": self._determine_dbm_type(),
            "event_source": self.session_name,
            "collection_interval": self.collection_interval,
            "ddtags": self.tags,
            "timestamp": time() * 1000,
            "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "service": self._config.service,
            "query_details": normalized_event,
        }

    def run_job(self):
        """Run the XE session collection job"""
        job_start_time = time()
        self._log.info(f"Running job for {self.session_name} session")
        if not self.session_exists():
            self._log.warning(f"XE session {self.session_name} not found or not running")
            return

        # Get the XML data and timing info
        xml_data, query_time, parse_time = self._query_ring_buffer()
        # Eventually we will use this to get events from an event file, controlled by config
        # xml_data, query_time, parse_time = self._query_event_file()

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

        # Timestamp gap detection - compare the last event timestamp from previous run
        # with the first event timestamp from this run
        if events and self._last_event_timestamp and 'timestamp' in events[0]:
            current_first_timestamp = events[0]['timestamp']
            try:
                prev_dt = datetime.datetime.fromisoformat(self._last_event_timestamp.replace('Z', '+00:00'))
                curr_dt = datetime.datetime.fromisoformat(current_first_timestamp.replace('Z', '+00:00'))
                gap_seconds = (curr_dt - prev_dt).total_seconds()
            except Exception:
                gap_seconds = None
            # Log session name, timestamps, and gap
            self._log.debug(
                f"[{self.session_name}] Timestamp gap: last={self._last_event_timestamp} "
                f"first={current_first_timestamp}" + (f" gap_seconds={gap_seconds}" if gap_seconds is not None else "")
            )

        # Update timestamp tracking with the last event's raw timestamp for next run
        if events and 'timestamp' in events[-1]:
            self._last_event_timestamp = events[-1]['timestamp']
            self._log.debug(f"Updated checkpoint to {self._last_event_timestamp}")

        # Track obfuscation and RQT creation time
        obfuscation_start_time = time()
        obfuscation_time = 0
        rqt_time = 0

        # Log a sample of events (up to 3) for debugging
        sample_size = min(3, len(events))
        sample_events = events[:sample_size]

        try:
            formatted_json = json_module.dumps(sample_events, indent=2, default=str)
            self._log.info(f"Sample events from {self.session_name} session:\n{formatted_json}")
        except Exception as e:
            self._log.error(f"Error formatting events for logging: {e}")

        for event in events:
            try:
                # Time the obfuscation
                obfuscate_start = time()
                # Obfuscate SQL fields and get the raw statement
                obfuscated_event, raw_sql_fields = self._obfuscate_sql_fields(event)
                obfuscation_time += time() - obfuscate_start

                # Check for ALLEN TEST comment in raw SQL fields
                if raw_sql_fields:
                    # Check each field for ALLEN TEST comment
                    for field_name, field_value in raw_sql_fields.items():
                        if (
                            field_name in ['statement', 'sql_text', 'batch_text']
                            and field_value
                            and '-- ALLEN TEST' in field_value
                        ):
                            self._log.info(
                                f"ALLEN TEST QUERY FOUND in XE session {self.session_name}: "
                                f"host={self._check.resolved_hostname}, field={field_name}, "
                                f"session_id={obfuscated_event.get('session_id', 'UNKNOWN')}, "
                                f"event_fire_timestamp={obfuscated_event.get('event_fire_timestamp', 'UNKNOWN')}, "
                                f"query_start={obfuscated_event.get('query_start', 'UNKNOWN')}, "
                                f"duration_ms={obfuscated_event.get('duration_ms', 'UNKNOWN')}, "
                                f"text={field_value[:100]}, full_event={json_module.dumps(obfuscated_event, default=str)}"
                            )
                            break

                # Create a properly structured payload for the main event
                payload = self._create_event_payload(obfuscated_event)
                # Extract normalized query details for use in RQT event
                query_details = payload.get("query_details", {})

                # Log the first event payload in each batch for validation
                if event == events[0]:
                    try:
                        payload_json = json_module.dumps(payload, default=str, indent=2)
                        self._log.debug(f"Sample {self.session_name} event payload:\n{payload_json}")
                    except Exception as e:
                        self._log.error(f"Error serializing payload for logging: {e}")

                # Create and send RQT event if applicable
                if raw_sql_fields:
                    # Time RQT creation
                    rqt_start = time()
                    # Pass normalized query details for proper timing fields
                    rqt_event = self._create_rqt_event(obfuscated_event, raw_sql_fields, query_details)
                    rqt_time += time() - rqt_start

                    if rqt_event:
                        # For now, just log the first RQT event in each batch
                        if event == events[0]:
                            try:
                                rqt_payload_json = json_module.dumps(rqt_event, default=str, indent=2)
                                self._log.debug(f"Sample {self.session_name} RQT event payload:\n{rqt_payload_json}")
                            except Exception as e:
                                self._log.error(f"Error serializing RQT payload for logging: {e}")

                        # Log that we created an RQT event but are not sending it yet
                        self._log.debug(
                            f"Created RQT event for query_signature={obfuscated_event.get('query_signature')} (not sending)"
                        )

                        # Uncomment to enable sending the RQT event in the future:
                        # rqt_payload = json.dumps(rqt_event, default=default_json_event_encoding)
                        # self._check.database_monitoring_query_sample(rqt_payload)

                # Uncomment to enable sending the main event in the future:
                # serialized_payload = json.dumps(payload, default=default_json_event_encoding)
                # self._check.database_monitoring_query_activity(serialized_payload)
            except Exception as e:
                self._log.error(f"Error processing event: {e}")
                continue

        # Calculate post-processing time (obfuscation + RQT)
        post_processing_time = time() - obfuscation_start_time

        total_time = time() - job_start_time
        self._log.info(
            f"Found {len(events)} events from {self.session_name} session - "
            f"Times: query={query_time:.3f}s parse={parse_time:.3f}s process={process_time:.3f}s "
            f"obfuscation={obfuscation_time:.3f}s rqt={rqt_time:.3f}s post_processing={post_processing_time:.3f}s "
            f"total={total_time:.3f}s"
        )

    def _obfuscate_sql_fields(self, event):
        """Simplified SQL field obfuscation"""
        obfuscated_event = event.copy()
        raw_sql_fields = {}

        # Get SQL fields for this event type
        sql_fields = self.get_sql_fields(event.get('event_name', ''))

        # Process each SQL field that exists in the event
        for field in sql_fields:
            if field in event and event[field]:
                raw_sql_fields[field] = event[field]

                try:
                    # Obfuscate the SQL
                    result = obfuscate_sql_with_metadata(
                        event[field], self._obfuscator_options, replace_null_character=True
                    )

                    # Store the obfuscated SQL
                    obfuscated_event[field] = result['query']

                    # Store metadata from the first field with metadata
                    if 'dd_commands' not in obfuscated_event and result['metadata'].get('commands'):
                        obfuscated_event['dd_commands'] = result['metadata']['commands']
                    if 'dd_tables' not in obfuscated_event and result['metadata'].get('tables'):
                        obfuscated_event['dd_tables'] = result['metadata']['tables']
                    if result['metadata'].get('comments'):
                        if 'dd_comments' not in obfuscated_event:
                            obfuscated_event['dd_comments'] = []
                        obfuscated_event['dd_comments'].extend(result['metadata']['comments'])

                    # Set query_signature from the primary field
                    primary_field = self._get_primary_sql_field(event)
                    if field == primary_field or 'query_signature' not in obfuscated_event:
                        obfuscated_event['query_signature'] = compute_sql_signature(result['query'])

                except Exception as e:
                    self._log.debug(f"Error obfuscating {field}: {e}")
                    obfuscated_event[field] = "ERROR: failed to obfuscate"

        # Deduplicate comments if any
        if 'dd_comments' in obfuscated_event:
            obfuscated_event['dd_comments'] = list(set(obfuscated_event['dd_comments']))

        return obfuscated_event, raw_sql_fields if raw_sql_fields else None

    def _get_primary_sql_field(self, event):
        """
        Get the primary SQL field for this event type.
        This is the field that will be used for the main query signature.

        Subclasses should override this method to return their primary field.

        Args:
            event: The event data dictionary

        Returns:
            Name of the primary SQL field
        """
        # Default implementation - will be overridden by subclasses
        # Try statement first, then sql_text, then batch_text
        for field in self.get_sql_fields(event.get('event_name', '')):
            if field in event and event[field]:
                return field
        return None

    def _create_rqt_event(self, event, raw_sql_fields, query_details):
        """
        Create a Raw Query Text (RQT) event for a raw SQL statement.

        Args:
            event: The event data dictionary with obfuscated SQL fields
            raw_sql_fields: Dictionary containing the original SQL fields
            query_details: Dictionary containing normalized query details with timing information

        Returns:
            Dictionary with the RQT event payload or None if the event should be skipped
        """
        if not self._collect_raw_query or not raw_sql_fields:
            self._log.debug("Skipping RQT event creation: raw query collection disabled or no raw SQL fields")
            return None

        # Check if we have the necessary signatures
        query_signature = event.get('query_signature')
        if not query_signature:
            self._log.debug("Skipping RQT event creation: Missing query_signature")
            return None

        # Get the primary SQL field for this event type
        primary_field = self._get_primary_sql_field(event)
        if not primary_field or primary_field not in raw_sql_fields:
            self._log.debug(
                f"Skipping RQT event creation: Primary SQL field {primary_field} not found in raw_sql_fields"
            )
            return None

        # Ensure we have a signature for the primary field
        primary_signature_field = f"{primary_field}_signature"
        if primary_signature_field not in raw_sql_fields:
            self._log.debug(
                f"Skipping RQT event creation: Signature for primary field {primary_field} not found in raw_sql_fields"
            )
            return None

        # Use primary field's signature as the raw_query_signature
        raw_query_signature = raw_sql_fields[primary_signature_field]

        # Use rate limiting cache to control how many RQT events we send
        # cache_key = (query_signature, raw_query_signature)
        # if not self._raw_statement_text_cache.acquire(cache_key):
        #     self._log.debug(f"Skipping RQT event creation: Rate limited by cache for signature {query_signature}")
        #     return None

        # Create basic db fields structure
        db_fields = {
            "instance": event.get('database_name', None),
            "query_signature": query_signature,
            "raw_query_signature": raw_query_signature,
            "statement": raw_sql_fields[primary_field],  # Primary field becomes the statement
            "metadata": {
                "tables": event.get('dd_tables', None),
                "commands": event.get('dd_commands', None),
                "comments": event.get('dd_comments', None),
            },
        }

        # Create the sqlserver section with appropriate fields based on session type
        sqlserver_fields = {
            "session_id": event.get("session_id"),
            "xe_type": event.get("event_name"),
            "event_fire_timestamp": query_details.get("event_fire_timestamp"),
        }

        # Only include duration and query_start for non-error events
        is_error_event = self.session_name == "datadog_query_errors"
        if not is_error_event:
            sqlserver_fields.update({
                "duration_ms": event.get("duration_ms"),
                "query_start": query_details.get("query_start"),
            })
        else:
            # Include error_number and message for error events
            sqlserver_fields.update({
                "error_number": event.get("error_number"),
                "message": event.get("message"),
            })

        # Add additional SQL fields to the sqlserver section
        # but only if they're not the primary field and not empty
        for field in ["statement", "sql_text", "batch_text"]:
            if field != primary_field and field in raw_sql_fields and raw_sql_fields[field]:
                sqlserver_fields[field] = raw_sql_fields[field]

        return {
            "timestamp": time() * 1000,
            "host": self._check.resolved_hostname,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "rqt",
            "event_source": self.session_name,
            "ddtags": ",".join(self.tags),
            'service': self._config.service,
            "db": db_fields,
            "sqlserver": sqlserver_fields,
        }
