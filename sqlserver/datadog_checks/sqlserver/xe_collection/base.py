# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import json as json_module
import logging
from abc import abstractmethod
from io import BytesIO
from time import time

from dateutil import parser
from lxml import etree

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    DBMAsyncJob,
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.utils import is_azure_sql_database

from .xml_tools import extract_int_value, extract_value

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


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
            dt = parser.isoparse(timestamp_str)
            return dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
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
            end_dt = parser.isoparse(end_timestamp)
            duration_delta = datetime.timedelta(milliseconds=float(duration_ms))
            start_dt = end_dt - duration_delta
            return start_dt.isoformat(timespec='milliseconds').replace('+00:00', 'Z')
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
        "activity_id_xfer",
    ]

    BASE_SQL_FIELDS = [
        "statement",
        "sql_text",
        "batch_text",
    ]

    # Fields that should use text representation when available
    # Both rpc_completed and batch_completed use the result field
    TEXT_FIELDS = ["result"]

    def __init__(self, check, config, session_name):
        self.session_name = session_name
        self._check = check
        self._log = check.log
        self._config = config

        # Get configuration based on session name
        xe_config = getattr(self._config, 'xe_collection_config', {})
        if session_name == "datadog_query_completions":
            session_config = xe_config.get('query_completions', {})
        elif session_name == "datadog_query_errors":
            session_config = xe_config.get('query_errors', {})
        else:
            session_config = {}

        # Set collection interval from config or use default
        self.collection_interval = session_config.get('collection_interval', 10)

        # Set debug sample size from global XE config
        self.debug_sample_events = xe_config.get('debug_sample_events', 3)

        # Set max events from session-specific config (capped at 1000 by SQL Server)
        self.max_events = min(session_config.get('max_events', 1000), 1000)
        self._last_event_timestamp = None  # Initialize timestamp tracking

        # Configuration for raw query text (RQT) events
        self._collect_raw_query = self._config.collect_raw_query_statement.get("enabled", False)

        self._raw_statement_text_cache = RateLimitingTTLCache(
            maxsize=self._config.collect_raw_query_statement["cache_max_size"],
            ttl=60 * 60 / self._config.collect_raw_query_statement["samples_per_hour_per_query"],
        )

        # Register event handlers - subclasses will override this
        self._event_handlers = {}

        # We already know it's enabled since the registry only creates enabled handlers
        self._enabled = True

        # Log configuration details
        self._log.info(
            f"Initializing XE session {session_name} with interval={self.collection_interval}s, "
            f"max_events={self.max_events}, collect_raw_query={self._collect_raw_query}"
        )

        super(XESessionBase, self).__init__(
            check,
            run_sync=True,
            enabled=True,
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

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _query_ring_buffer(self):
        """
        Query the ring buffer data and parse the XML on the client side.
        This avoids expensive server-side XML parsing for better performance.
        """
        raw_xml = None
        with self._check.connection.open_managed_default_connection(key_prefix=self._conn_key_prefix):
            with self._check.connection.get_managed_cursor(key_prefix=self._conn_key_prefix) as cursor:
                # For Azure SQL Database support
                level = ""
                if self._is_azure_sql_database:
                    level = "database_"

                # Determine if we need to use CONVERT based on connector type
                use_convert = False
                if self._check.connection.connector == "adodbapi":
                    use_convert = True
                    self._log.debug("Using CONVERT syntax for Windows/adodbapi compatibility")

                try:
                    # Choose the appropriate query based on connector type
                    if use_convert:
                        query = f"""
                            SELECT CONVERT(NVARCHAR(MAX), t.target_data) AS target_xml
                            FROM sys.dm_xe_{level}sessions s
                            JOIN sys.dm_xe_{level}session_targets t
                                ON s.address = t.event_session_address
                            WHERE s.name = ?
                            AND t.target_name = 'ring_buffer'
                        """
                    else:
                        query = f"""
                            SELECT CAST(t.target_data AS XML) AS target_xml
                            FROM sys.dm_xe_{level}sessions s
                            JOIN sys.dm_xe_{level}session_targets t
                                ON s.address = t.event_session_address
                            WHERE s.name = ?
                            AND t.target_name = 'ring_buffer'
                        """

                    cursor.execute(query, (self.session_name,))
                    row = cursor.fetchone()
                    if row and row[0]:
                        raw_xml = str(row[0])
                except Exception as e:
                    self._log.error(f"Error querying ring buffer: {e}")

        if not raw_xml:
            return None

        return raw_xml

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _process_events(self, xml_data):
        """
        Parse and process ring buffer XML data in a single pass using lxml.etree.iterparse.
        Filters events by timestamp and processes them directly.

        Returns:
            List of processed event dictionaries
        """
        if not xml_data:
            return []

        processed_events = []
        try:
            try:
                xml_stream = BytesIO(xml_data.encode('utf-8'))
            except UnicodeEncodeError:
                self._log.debug("UTF-8 encoding failed, falling back to UTF-16")
                xml_stream = BytesIO(xml_data.encode('utf-16'))

            # Only parse 'end' events for <event> tags
            context = etree.iterparse(xml_stream, events=('end',), tag='event')

            for _, elem in context:
                try:
                    # Get basic timestamp for filtering
                    timestamp = elem.get('timestamp')

                    # Filter by timestamp
                    if not self._last_event_timestamp or (timestamp and timestamp > self._last_event_timestamp):
                        # Extract event attributes
                        event_data = {"timestamp": timestamp, "event_name": elem.get('name', '')}

                        # Process the event using appropriate handler
                        event_name = event_data["event_name"]
                        if event_name in self._event_handlers:
                            handler = self._event_handlers[event_name]
                            if handler(elem, event_data):
                                processed_events.append(event_data)
                        else:
                            self._log.debug(f"No handler for event type: {event_name}")
                except Exception as e:
                    self._log.error(f"Error processing event {elem.get('name', 'unknown')}: {e}")

                # Free memory for processed elements
                elem.clear()
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

                # Stop if we've reached the maximum number of events
                if len(processed_events) >= self.max_events:
                    self._log.debug(
                        f"Processed {len(processed_events)} events from ring buffer (limit of {self.max_events})"
                    )
                    break

            return processed_events

        except Exception as e:
            self._log.error(f"Error processing ring buffer events: {e}")
            return []

    def _process_action_elements(self, event, event_data):
        """Process common action elements for all event types"""
        for action in event.findall('./action'):
            action_name = action.get('name')
            if not action_name:
                continue

            if action_name == 'attach_activity_id':
                event_data['activity_id'] = extract_value(action)
            elif action_name == 'attach_activity_id_xfer':
                event_data['activity_id_xfer'] = extract_value(action)
            elif action_name == 'session_id' or action_name == 'request_id':
                # These are numeric values in the actions
                value = extract_int_value(action)
                if value is not None:
                    event_data[action_name] = value
            else:
                event_data[action_name] = extract_value(action)

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
            normalized["query_start"] = TimestampHandler.calculate_start_time(raw_timestamp, event.get("duration_ms"))
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

        # Add raw_query_signature if present and raw query collection is enabled
        if self._collect_raw_query and "raw_query_signature" in event:
            normalized["raw_query_signature"] = event["raw_query_signature"]

        return normalized

    def _determine_dbm_type(self):
        """
        Determine the dbm_type based on the session name.
        Returns the appropriate dbm_type for the current session.
        """

        if self.session_name == "datadog_query_errors":
            return "query_error"
        elif self.session_name == "datadog_query_completions":
            return "query_completion"
        else:
            self._log.warning(f"Unrecognized session name: {self.session_name}, using default dbm_type")
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

        # Add primary_sql_field if available
        if 'primary_sql_field' in raw_event:
            normalized_event['primary_sql_field'] = raw_event['primary_sql_field']

        # Add metadata if available
        normalized_event['metadata'] = {
            'tables': raw_event.get('dd_tables'),
            'commands': raw_event.get('dd_commands'),
            'comments': raw_event.get('dd_comments'),
        }

        return {
            "host": self._check.resolved_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": self._determine_dbm_type(),
            "collection_interval": self.collection_interval,
            "ddtags": self._check.tag_manager.get_tags(),
            "timestamp": time() * 1000,
            "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "cloud_metadata": self._config.cloud_metadata,
            "service": self._config.service,
            "query_details": normalized_event,
        }

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def run_job(self):
        """Run the XE session collection job"""
        self._log.info(f"Running job for {self.session_name} session")
        if not self.session_exists():
            self._log.warning(f"XE session {self.session_name} not found or not running.")
            return

        # Get the raw XML data
        xml_data = self._query_ring_buffer()

        if not xml_data:
            self._log.debug(f"No data found for session {self.session_name}")
            return

        # Process the events
        events = self._process_events(xml_data)

        if not events:
            self._log.debug(f"No events processed from {self.session_name} session")
            return

        # Timestamp gap detection - compare the last event timestamp from previous run
        # with the first event timestamp from this run
        if events and self._last_event_timestamp and 'timestamp' in events[0]:
            current_first_timestamp = events[0]['timestamp']
            try:
                prev_dt = parser.isoparse(self._last_event_timestamp)
                curr_dt = parser.isoparse(current_first_timestamp)
                gap_seconds = (curr_dt - prev_dt).total_seconds()
            except Exception:
                gap_seconds = None
            self._log.debug(
                f"[{self.session_name}] Timestamp gap: last={self._last_event_timestamp} "
                f"first={current_first_timestamp}" + (f" gap_seconds={gap_seconds}" if gap_seconds is not None else "")
            )

        # Update timestamp tracking with the last event's raw timestamp for next run
        if events and 'timestamp' in events[-1]:
            self._last_event_timestamp = events[-1]['timestamp']
            self._log.debug(f"Updated checkpoint to {self._last_event_timestamp}")

        # Log a sample of events (up to max configured limit) for debugging
        if self._log.isEnabledFor(logging.DEBUG):
            sample_size = min(self.debug_sample_events, len(events))
            sample_events = events[:sample_size]

            try:
                formatted_json = json_module.dumps(sample_events, indent=2, default=str)
                self._log.debug(
                    f"Sample events from {self.session_name} session (limit={self.debug_sample_events}):\n"
                    f"{formatted_json}"
                )
            except Exception as e:
                self._log.error(f"Error formatting events for logging: {e}")

        # Determine the key for the batched events array based on session name
        batch_key = (
            "sqlserver_query_errors" if self.session_name == "datadog_query_errors" else "sqlserver_query_completions"
        )

        # Create a list to collect all query details
        all_query_details = []

        # Track if we've logged an RQT sample for this batch
        rqt_sample_logged = False

        # Process all events and collect them for batching
        for event in events:
            try:
                # Obfuscate SQL fields and get the raw statement
                obfuscated_event, raw_sql_fields, primary_sql_field = self._obfuscate_sql_fields(event)

                # Add primary SQL field to the event if available
                if primary_sql_field:
                    obfuscated_event['primary_sql_field'] = primary_sql_field

                # Create a properly structured payload for the individual event
                payload = self._create_event_payload(obfuscated_event)

                # Extract query details to add to the batch
                query_details = payload.get("query_details", {})
                all_query_details.append({"query_details": query_details})

                # Process RQT events individually
                if self._collect_raw_query and raw_sql_fields:
                    # Create RQT event
                    rqt_event = self._create_rqt_event(obfuscated_event, raw_sql_fields, query_details)

                    if rqt_event:
                        # Log the first successful RQT event we encounter in this batch
                        if not rqt_sample_logged and self._log.isEnabledFor(logging.DEBUG):
                            try:
                                rqt_payload_json = json_module.dumps(rqt_event, default=str, indent=2)
                                self._log.debug(f"Sample {self.session_name} RQT event payload:\n{rqt_payload_json}")
                                rqt_sample_logged = True
                            except Exception as e:
                                self._log.error(f"Error serializing RQT payload for logging: {e}")

                        self._log.debug(
                            f"Created RQT event for query_signature={obfuscated_event.get('query_signature')}"
                        )

                        rqt_payload = json.dumps(rqt_event, default=default_json_event_encoding)
                        # Log RQT payload size
                        self._log.debug(f"RQT event payload size: {len(rqt_payload)} bytes")
                        self._check.database_monitoring_query_sample(rqt_payload)

            except Exception as e:
                self._log.error(f"Error processing event: {e}")
                continue

        # Create a single batched payload for all events if we have any
        if all_query_details:
            # Create base payload from the common fields (using the same structure as _create_event_payload)
            batched_payload = {
                "host": self._check.resolved_hostname,
                "database_instance": self._check.database_identifier,
                "ddagentversion": datadog_agent.get_version(),
                "ddsource": "sqlserver",
                "dbm_type": self._determine_dbm_type(),
                "collection_interval": self.collection_interval,
                "ddtags": self._check.tag_manager.get_tags(),
                "timestamp": time() * 1000,
                "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
                "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
                "cloud_metadata": self._config.cloud_metadata,
                "service": self._config.service,
                # Add the array of query details with the appropriate key
                batch_key: all_query_details,
            }

            # Log the batched payload for debugging
            if self._log.isEnabledFor(logging.DEBUG):
                try:
                    # Only include up to max configured limit events in the log
                    log_payload = batched_payload.copy()
                    if len(all_query_details) > self.debug_sample_events:
                        log_payload[batch_key] = all_query_details[: self.debug_sample_events]
                        remaining_events = len(all_query_details) - self.debug_sample_events
                        log_payload[batch_key].append({"truncated": f"...and {remaining_events} more events"})

                    payload_json = json_module.dumps(log_payload, default=str, indent=2)
                    self._log.debug(
                        f"Batched {self.session_name} payload with {len(all_query_details)} events "
                        f"(showing {self.debug_sample_events}):\n{payload_json}"
                    )
                except Exception as e:
                    self._log.error(f"Error serializing batched payload for logging: {e}")

            # Send the batched payload
            self._check.database_monitoring_query_activity(batched_payload)

        self._log.info(f"Found {len(events)} events from {self.session_name} session")

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _obfuscate_sql_fields(self, event):
        """SQL field obfuscation and signature creation"""
        obfuscated_event = event.copy()
        raw_sql_fields = {}
        primary_sql_field = None

        # Get SQL fields for this event type
        sql_fields = self.get_sql_fields(event.get('event_name', ''))

        # Process each SQL field that exists in the event
        for field in sql_fields:
            if field in event and event[field]:
                raw_sql_fields[field] = event[field]

                try:
                    # Obfuscate the SQL
                    result = obfuscate_sql_with_metadata(
                        event[field], self._config.obfuscator_options, replace_null_character=True
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

                    # Compute query_signature and raw_query_signature from the primary field
                    current_primary_field = self._get_primary_sql_field(event)
                    if field == current_primary_field or 'query_signature' not in obfuscated_event:
                        primary_sql_field = field  # Store the field used for signature
                        obfuscated_event['query_signature'] = compute_sql_signature(result['query'])
                        raw_signature = compute_sql_signature(event[field])
                        raw_sql_fields['raw_query_signature'] = raw_signature
                        if self._collect_raw_query:
                            obfuscated_event['raw_query_signature'] = raw_signature

                except Exception as e:
                    self._log.debug(f"Error obfuscating {field}: {e}")
                    obfuscated_event[field] = "ERROR: failed to obfuscate"

        # Deduplicate comments if any
        if 'dd_comments' in obfuscated_event:
            obfuscated_event['dd_comments'] = list(set(obfuscated_event['dd_comments']))

        return obfuscated_event, raw_sql_fields if raw_sql_fields else None, primary_sql_field

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

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
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
        primary_field = event.get('primary_sql_field') or self._get_primary_sql_field(event)
        if not primary_field or primary_field not in raw_sql_fields:
            self._log.debug(
                f"Skipping RQT event creation: Primary SQL field {primary_field} not found in raw_sql_fields"
            )
            return None

        # Use rate limiting cache to control how many RQT events we send
        cache_key = (query_signature, raw_sql_fields['raw_query_signature'])
        if not self._raw_statement_text_cache.acquire(cache_key):
            self._log.debug(f"Skipping RQT event creation: Rate limited by cache for signature {query_signature}")
            return None

        # Create basic db fields structure
        db_fields = {
            "instance": event.get('database_name', None),
            "query_signature": query_signature,
            "raw_query_signature": raw_sql_fields['raw_query_signature'],
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
            "primary_sql_field": primary_field,
        }

        # Only exclude duration and query_start for error_reported events, not attention events
        is_error_reported = event.get("event_name") == "error_reported"
        if not is_error_reported:
            sqlserver_fields.update(
                {
                    "duration_ms": event.get("duration_ms"),
                    "query_start": query_details.get("query_start"),
                }
            )

        # Include error_number and message if they're present in the event
        if event.get("error_number") is not None:
            sqlserver_fields["error_number"] = event.get("error_number")
        if event.get("message"):
            sqlserver_fields["message"] = event.get("message")

        # Add additional SQL fields to the sqlserver section
        # but only if they're not the primary field and not empty
        for field in ["statement", "sql_text", "batch_text"]:
            if field != primary_field and field in raw_sql_fields and raw_sql_fields[field]:
                sqlserver_fields[field] = raw_sql_fields[field]

        return {
            "timestamp": time() * 1000,
            "host": self._check.resolved_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": datadog_agent.get_version(),
            "ddsource": "sqlserver",
            "dbm_type": "rqt",
            "ddtags": ",".join(self._check.tag_manager.get_tags()),
            'service': self._config.service,
            "db": db_fields,
            "sqlserver": sqlserver_fields,
        }
