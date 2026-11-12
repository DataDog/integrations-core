# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import copy
import re
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterator

from cachetools import TTLCache
from dateutil import parser
from lxml import etree

from datadog_checks.base.utils.db.health import HealthStatus
from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION, STATIC_INFO_VERSION
from datadog_checks.sqlserver.health import SqlServerHealthEvent
from datadog_checks.sqlserver.statements import obfuscate_xml_plan
from datadog_checks.sqlserver.utils import raise_if_cancelled

from .base import XESessionBase, agent_check_getter
from .xml_tools import extract_field, extract_text_representation, extract_value

if TYPE_CHECKING:
    from datadog_checks.sqlserver import SQLServer
    from datadog_checks.sqlserver.config import SQLServerConfig

SESSION_NAME = "datadog_query_plans"
PLAN_PROFILE_EVENT = "query_post_execution_plan_profile"
SHOWPLAN_EVENT = "query_post_execution_showplan"
# `db.plan.source` of the plans of each event
PLAN_SOURCES = {
    PLAN_PROFILE_EVENT: "xe_query_post_execution_plan_profile",
    SHOWPLAN_EVENT: "xe_query_post_execution_showplan",
}
EVENT_FILE_TARGET = "event_file"
RING_BUFFER_TARGET = "ring_buffer"

DEFAULT_SAMPLES_PER_HOUR_PER_QUERY = 4
DEFAULT_MAX_PLAN_SIZE_BYTES = 1_000_000
RATE_LIMITER_MAX_SIZE = 10_000
STATEMENT_TEXT_CACHE_MAX_SIZE = 10_000
STATEMENT_TEXT_CACHE_TTL_SECONDS = 600
# The events read again are skipped by key. The keys kept outnumber the events of a ring buffer, 1,000 by default, and
# of a read.
SEEN_EVENT_KEYS_MAX_SIZE = 10_000
# An event's key, with its timestamp and duration. The activity ID is unique with TRACK_CAUSALITY, and the other
# actions tell executions apart without it.
EVENT_KEY_ACTIONS = ("attach_activity_id", "session_id", "request_id", "query_hash", "query_plan_hash")
# An actual plan holds at least one of these. Without them, it's a plan with no runtime data.
RUNTIME_ELEMENTS = ("<RunTimeInformation", "<QueryTimeStats")
# Used when the session has no query_hash or query_plan_hash action.
PLAN_QUERY_HASH_PATTERN = re.compile(r'\bQueryHash="0x([0-9A-Fa-f]+)"')
PLAN_QUERY_PLAN_HASH_PATTERN = re.compile(r'\bQueryPlanHash="0x([0-9A-Fa-f]+)"')
# The event_file target writes `<filename>_0_<timestamp>.xel` files, a new one at each rollover or session start.
EVENT_FILE_SUFFIX_PATTERN = re.compile(r"_\d+_\d+\.xel$", re.IGNORECASE)

QUERY_PLANS_DOCS_URL = "https://docs.datadoghq.com/database_monitoring/guide/sql_real_execution_plans/"
QUERY_PLANS_SESSION_SQL = """\
CREATE EVENT SESSION datadog_query_plans ON SERVER
ADD EVENT sqlserver.query_post_execution_plan_profile (
    ACTION (sqlserver.database_name, sqlserver.session_id, sqlserver.request_id, sqlserver.username,
            sqlserver.client_app_name, sqlserver.client_hostname, sqlserver.query_hash, sqlserver.query_plan_hash,
            sqlserver.plan_handle, sqlserver.tsql_frame)
    WHERE duration > 1000000 AND sqlserver.username <> N'datadog'
)
ADD TARGET package0.event_file (SET filename = N'datadog_query_plans', max_file_size = 64, max_rollover_files = 4)
WITH (MAX_MEMORY = 8192 KB, EVENT_RETENTION_MODE = ALLOW_SINGLE_EVENT_LOSS, MAX_DISPATCH_LATENCY = 30 SECONDS,
      TRACK_CAUSALITY = ON, STARTUP_STATE = ON);
ALTER EVENT SESSION datadog_query_plans ON SERVER STATE = START;"""

# The session and its targets. Only the event_file target's data is read: it holds the current file's path, while a
# ring buffer's data is all its events.
SESSION_TARGETS_QUERY = """\
SELECT t.target_name,
    CASE WHEN t.target_name = N'event_file' THEN CAST(t.target_data AS nvarchar(max)) END AS target_data
FROM sys.dm_xe_{level}sessions s
LEFT JOIN sys.dm_xe_{level}session_targets t ON s.address = t.event_session_address
WHERE s.name = ?
"""
# The newest buffer of a file, where the first run starts instead of replaying the history.
EVENT_FILE_LAST_BUFFER_QUERY = """\
SELECT TOP 1 file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL)
ORDER BY file_offset DESC
"""
EVENT_FILE_READ_QUERY = """\
SELECT TOP (?) event_data, file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, NULL, NULL)
"""
# Reading from a checkpoint returns the events of the buffers after it, in this file and the next ones, including the
# file a restarted session starts.
EVENT_FILE_READ_FROM_CHECKPOINT_QUERY = """\
SELECT TOP (?) event_data, file_name, file_offset
FROM sys.fn_xe_file_target_read_file(?, NULL, ?, ?)
"""
# The statement of a tsql_frame action, extracted as query metrics extract it from sys.dm_exec_query_stats, so they
# compute the same query signature.
FRAME_STATEMENT_QUERY = """\
SELECT SUBSTRING(qt.text, (o.start_offset / 2) + 1,
    ((CASE o.end_offset WHEN -1 THEN DATALENGTH(qt.text) ELSE o.end_offset END - o.start_offset) / 2) + 1)
FROM (SELECT CAST(? AS int) AS start_offset, CAST(? AS int) AS end_offset) o
CROSS APPLY sys.dm_exec_sql_text(CONVERT(varbinary(64), ?, 1)) qt
"""
# The statement of a cached plan, for events without a tsql_frame action or whose sql handle is gone. A plan can have
# several statements with the same query hash, so the one at the frame's offset comes first when it's known.
QUERY_STATS_STATEMENT_QUERY = """\
SELECT TOP 1 SUBSTRING(qt.text, (qs.statement_start_offset / 2) + 1,
    ((CASE qs.statement_end_offset WHEN -1 THEN DATALENGTH(qt.text) ELSE qs.statement_end_offset END
        - qs.statement_start_offset) / 2) + 1)
FROM sys.dm_exec_query_stats qs
CROSS APPLY sys.dm_exec_sql_text(qs.plan_handle) qt
WHERE qs.plan_handle = CONVERT(varbinary(64), ?, 1) AND qs.query_hash = CONVERT(binary(8), ?, 1)
ORDER BY CASE WHEN qs.statement_start_offset = ? THEN 0 ELSE 1 END
"""
# No statement starts at this offset.
UNKNOWN_OFFSET = -2

PLAN_EVENT_NUMERIC_FIELDS = {
    "cpu_time": 0,
    "nest_level": 0,
    "dop": 0,
    "granted_memory_kb": 0,
    "used_memory_kb": 0,
    "requested_memory_kb": 0,
    "ideal_memory_kb": 0,
    "serial_ideal_memory_kb": 0,
}
PLAN_EVENT_STRING_FIELDS = ["object_type", "object_name"]


def parse_tsql_frame(action: etree._Element) -> dict:
    """The sql handle and statement offsets of a tsql_frame action, whose value is a `<frame>` element."""
    value = action.find('./value')
    if value is None:
        return {}
    frame = value.find('./frame')
    if frame is None and value.text and '<frame' in value.text:
        # The value is the frame element as text.
        try:
            frame = etree.fromstring(value.text.strip())
        except etree.XMLSyntaxError:
            return {}
    if frame is None or not frame.get('handle'):
        return {}
    try:
        offset_start = int(frame.get('offsetStart', 0))
        offset_end = int(frame.get('offsetEnd', -1))
    except ValueError:
        return {}
    return {"sql_handle": frame.get('handle'), "offset_start": offset_start, "offset_end": offset_end}


def parse_showplan_xml(data: etree._Element) -> str | None:
    """The showplan_xml field of an event, whose value is a `<ShowPlanXML>` element."""
    value = data.find('./value')
    if value is None:
        return None
    for child in value:
        if isinstance(child.tag, str):
            return etree.tostring(child, encoding='unicode', with_tail=False)
    # The value is the plan as text.
    return value.text.strip() if value.text and value.text.strip() else None


def event_key(event: etree._Element) -> tuple:
    """The identity of an execution's event, to recognize it when it's read again."""
    actions = {action.get('name'): extract_value(action) for action in event.findall('./action')}
    duration = extract_value(event.find("./data[@name='duration']"))
    return (event.get('timestamp'), duration, *(actions.get(name) for name in EVENT_KEY_ACTIONS))


def hash_to_hex(value: str | None) -> str | None:
    """
    The query_hash and query_plan_hash actions are unsigned 64-bit integers. They're sent as hex, as query metrics send
    the `sys.dm_exec_query_stats` columns.
    """
    if not value:
        return None
    try:
        return format(int(value), '016x')
    except ValueError:
        return None


def event_file_pattern(file_name: str) -> str:
    """
    The path matching every file of the event_file target whose current file is `file_name`, for
    `sys.fn_xe_file_target_read_file`: a wildcard pattern for local files, and the blob name prefix for Azure Blob
    Storage URLs, as on Azure SQL Database and Managed Instance, where wildcards aren't allowed.
    """
    if file_name.lower().startswith("https://"):
        return EVENT_FILE_SUFFIX_PATTERN.sub("", file_name)
    return EVENT_FILE_SUFFIX_PATTERN.sub("*.xel", file_name)


class QueryPlanEventsHandler(XESessionBase):
    """
    Collects real execution plans from the `datadog_query_plans` XE session, which customers create and start, with
    either the `query_post_execution_plan_profile` or the `query_post_execution_showplan` event.

    Each event is the actual plan of one statement execution, with its runtime parameter values. The session is read
    from its event_file target, or its ring_buffer target where there's no event_file target.
    """

    def __init__(self, check: SQLServer, config: SQLServerConfig):
        super().__init__(check, config, SESSION_NAME)
        query_plans_config = getattr(config, 'xe_collection_config', {}).get('query_plans', {}) or {}
        samples_per_hour = int(query_plans_config.get('samples_per_hour_per_query', DEFAULT_SAMPLES_PER_HOUR_PER_QUERY))
        if samples_per_hour < 1:
            self._log.warning(
                "`collect_xe.query_plans.samples_per_hour_per_query` must be at least 1, using %s",
                DEFAULT_SAMPLES_PER_HOUR_PER_QUERY,
            )
            samples_per_hour = DEFAULT_SAMPLES_PER_HOUR_PER_QUERY
        self._max_plan_size_bytes = int(query_plans_config.get('max_plan_size_bytes', DEFAULT_MAX_PLAN_SIZE_BYTES))
        # One plan per query and plan shape per interval, as the query_hash and query_plan_hash pair.
        self._seen_plans_ratelimiter = RateLimitingTTLCache(
            maxsize=RATE_LIMITER_MAX_SIZE, ttl=60 * 60 / samples_per_hour
        )
        self._statement_text_cache: TTLCache = TTLCache(
            maxsize=STATEMENT_TEXT_CACHE_MAX_SIZE, ttl=STATEMENT_TEXT_CACHE_TTL_SECONDS
        )
        # The event_file checkpoint: the file and offset of the last buffer read in full. Reads start after it, or at
        # the start of the current file without one.
        self._event_file_checkpoint: tuple[str, int] | None = None
        # The buffer a read starts with when the previous runs read it in part, as a run reads at most `max_events`
        # events, and the number of its events read.
        self._event_file_partial_buffer: tuple[tuple[str, int], int] | None = None
        self._event_file_pattern: str | None = None
        self._event_file_started = False
        # The current setup problem, so its warning is logged once and its health event goes back to OK when fixed.
        self._session_problem: SqlServerHealthEvent | None = None
        self._statuses: Counter = Counter()
        # The keys of the events read, the newest last, and whether the current read skips the events read before. The
        # ring buffer returns all its events at every read, and so can a read of the current file without checkpoint,
        # while a read after the checkpoint only returns new events.
        self._seen_event_keys: OrderedDict[tuple, None] = OrderedDict()
        self._skip_seen_events = False

        self.register_event_handler(PLAN_PROFILE_EVENT, self._parse_plan_event)
        self.register_event_handler(SHOWPLAN_EVENT, self._parse_plan_event)

    def get_numeric_fields(self, event_type=None):
        return {**super().get_numeric_fields(event_type), **PLAN_EVENT_NUMERIC_FIELDS}

    def get_string_fields(self, event_type=None):
        return super().get_string_fields(event_type) + PLAN_EVENT_STRING_FIELDS

    def get_sql_fields(self, event_type=None):
        # The statement isn't in the event, and is resolved separately.
        return []

    def _normalize_event_impl(self, event):
        return self._normalize_event(event)

    def _is_new_event(self, event: etree._Element) -> bool:
        key = event_key(event)
        seen = key in self._seen_event_keys
        self._seen_event_keys[key] = None
        self._seen_event_keys.move_to_end(key)
        if len(self._seen_event_keys) > SEEN_EVENT_KEYS_MAX_SIZE:
            self._seen_event_keys.popitem(last=False)
        return not (seen and self._skip_seen_events)

    def _parse_plan_event(self, event: etree._Element, event_data: dict) -> bool:
        try:
            for data in event.findall('./data'):
                name = data.get('name')
                if name == 'showplan_xml':
                    event_data['showplan_xml'] = parse_showplan_xml(data)
                elif name == 'object_type':
                    event_data['object_type'] = extract_text_representation(data) or extract_value(data)
                elif name:
                    extract_field(data, event_data, name, PLAN_EVENT_NUMERIC_FIELDS, [], self._log)
            self._process_action_elements(event, event_data)
            for action in event.findall("./action[@name='tsql_frame']"):
                event_data.pop('tsql_frame', None)
                event_data.update(parse_tsql_frame(action))
            plan = event_data.get('showplan_xml') or ''
            event_data['query_hash'] = hash_to_hex(event_data.get('query_hash')) or self._plan_hash(
                PLAN_QUERY_HASH_PATTERN, plan
            )
            event_data['query_plan_hash'] = hash_to_hex(event_data.get('query_plan_hash')) or self._plan_hash(
                PLAN_QUERY_PLAN_HASH_PATTERN, plan
            )
            if event_data.get('plan_handle'):
                event_data['plan_handle'] = event_data['plan_handle'].lower().removeprefix('0x')
        except Exception as e:
            self._log.debug("Failed to parse %s event: %s", event_data.get('event_name'), e)
            self._statuses[("error", event_data.get('event_name'))] += 1
            return False
        return True

    @staticmethod
    def _plan_hash(pattern: re.Pattern, plan: str) -> str | None:
        match = pattern.search(plan)
        return match.group(1).lower() if match else None

    @tracked_method(agent_check_getter=agent_check_getter)
    def run_job(self):
        self._statuses = Counter()
        try:
            with self._check.connection.open_managed_default_connection(self._conn_key_prefix):
                with self._check.connection.get_managed_cursor(self._conn_key_prefix) as cursor:
                    self._collect(cursor)
        finally:
            for (status, event_name), count in self._statuses.items():
                self._check.count(
                    "dd.sqlserver.xe.query_plans.events",
                    count,
                    **self._check.debug_stats_kwargs(tags=["status:" + status, "xe_event:" + str(event_name)]),
                )

    def _collect(self, cursor: Any) -> None:
        raise_if_cancelled(self._cancel_event)
        target_name, file_name = self._session_target(cursor)
        if target_name is None:
            return
        started = time.time()
        if target_name == EVENT_FILE_TARGET:
            xml_data, self._skip_seen_events = self._read_event_file(cursor, file_name) if file_name else (None, False)
        else:
            xml_data, self._skip_seen_events = self._read_ring_buffer(cursor), True
        self._check.histogram(
            "dd.sqlserver.xe.query_plans.read_time",
            (time.time() - started) * 1000,
            **self._check.debug_stats_kwargs(tags=["target:" + target_name]),
        )
        events = self._process_events(xml_data) if xml_data else []
        if not events:
            return
        self._submit_lag(events)
        for plan_event in self._plan_events(cursor, events):
            self._check.database_monitoring_query_sample(json.dumps(plan_event, default=default_json_event_encoding))

    def _submit_lag(self, events: list[dict]) -> None:
        """The time between the oldest event read and now."""
        try:
            oldest = min(parser.isoparse(event['timestamp']) for event in events if event.get('timestamp'))
        except ValueError:
            return
        if oldest.tzinfo is None:
            oldest = oldest.replace(tzinfo=timezone.utc)
        self._check.gauge(
            "dd.sqlserver.xe.query_plans.lag",
            (datetime.now(timezone.utc) - oldest).total_seconds() * 1000,
            **self._check.debug_stats_kwargs(),
        )

    def _session_target(self, cursor: Any) -> tuple[str | None, str | None]:
        """
        The target to read, event_file first, and the event_file target's current file. Reports setup problems with a
        health event and a warning.
        """
        level = "database_" if self._is_azure_sql_database else ""
        cursor.execute(SESSION_TARGETS_QUERY.format(level=level), (self.session_name,))
        rows = cursor.fetchall() or []
        if not rows:
            self._report_session_problem(
                SqlServerHealthEvent.QUERY_PLANS_XE_SESSION_MISSING,
                "The {} XE session doesn't exist or isn't running, so no real execution plans are collected.",
            )
            return None, None
        targets = {row[0]: row[1] for row in rows if row[0]}
        if EVENT_FILE_TARGET in targets:
            self._report_session_problem(None)
            return EVENT_FILE_TARGET, self._event_file_current_file(targets[EVENT_FILE_TARGET])
        if RING_BUFFER_TARGET in targets:
            self._report_session_problem(None)
            return RING_BUFFER_TARGET, None
        self._report_session_problem(
            SqlServerHealthEvent.QUERY_PLANS_XE_TARGET_UNSUPPORTED,
            "The {} XE session has no event_file or ring_buffer target, so no real execution plans are collected.",
        )
        return None, None

    def _event_file_current_file(self, target_data: str | None) -> str | None:
        if not target_data:
            return None
        try:
            file_element = etree.fromstring(target_data.encode('utf-8')).find('.//File')
        except etree.XMLSyntaxError as e:
            self._log.debug("Failed to parse the event_file target data of %s: %s", self.session_name, e)
            return None
        return file_element.get('name') if file_element is not None else None

    def _report_session_problem(self, problem: SqlServerHealthEvent | None, message: str = "") -> None:
        if problem == self._session_problem:
            return
        if self._session_problem is not None:
            self._check.health.submit_health_event(name=self._session_problem, status=HealthStatus.OK)
        self._session_problem = problem
        if problem is None:
            self._log.info("The %s XE session is running with a supported target", self.session_name)
            return
        self._check.health.submit_health_event(
            name=problem, status=HealthStatus.WARNING, data={"session_name": self.session_name}
        )
        self._log.warning(
            "%s Create and start it as described in %s:\n%s",
            message.format(self.session_name),
            QUERY_PLANS_DOCS_URL,
            QUERY_PLANS_SESSION_SQL,
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _read_event_file(self, cursor: Any, current_file: str) -> tuple[str | None, bool]:
        """
        The new events of the event_file target, as one XML document, and whether it can hold events read before, as a
        read of the current file from its start can. The first run starts at the newest buffer of the current file, so
        it doesn't replay the history.
        """
        pattern = event_file_pattern(current_file)
        if pattern != self._event_file_pattern:
            # A session created again with another file starts over.
            self._event_file_pattern = pattern
            self._event_file_checkpoint = None
            self._event_file_partial_buffer = None
            self._event_file_started = False
        if self._event_file_checkpoint is None and not self._event_file_started:
            self._event_file_started = True
            cursor.execute(EVENT_FILE_LAST_BUFFER_QUERY, (current_file,))
            row = cursor.fetchone()
            if row:
                self._event_file_checkpoint = (row[0], int(row[1]))
                return None, False

        # The events of the partial buffer read before are read again, and skipped.
        limit = self.max_events + (self._event_file_partial_buffer[1] if self._event_file_partial_buffer else 0)
        rows = []
        if self._event_file_checkpoint is not None:
            try:
                cursor.execute(EVENT_FILE_READ_FROM_CHECKPOINT_QUERY, (limit, pattern, *self._event_file_checkpoint))
                rows = cursor.fetchall()
            except Exception as e:
                raise_if_cancelled(self._cancel_event)
                # The checkpoint's file is gone, as after rollovers (error 25717).
                self._log.debug(
                    "Failed to read %s after %s, reading the current file %s: %s",
                    self.session_name,
                    self._event_file_checkpoint,
                    current_file,
                    e,
                )
                self._event_file_checkpoint = None
        read_from_file_start = self._event_file_checkpoint is None
        if read_from_file_start:
            cursor.execute(EVENT_FILE_READ_QUERY, (limit, current_file))
            rows = cursor.fetchall()
        new_rows = self._advance_event_file_checkpoint(rows, limit) if rows else []
        if not new_rows:
            return None, read_from_file_start
        return "<events>{}</events>".format("".join(row[0] for row in new_rows if row[0])), read_from_file_start

    def _advance_event_file_checkpoint(self, rows: list, limit: int) -> list:
        """
        The rows of a read not read before, after the checkpoint moves past them. A checkpoint is a whole buffer, so a
        read stopped by its limit within a buffer checkpoints on the buffer before it, and the next read skips the
        events of that buffer already read.
        """
        buffers = [(row[1], int(row[2])) for row in rows]
        skipped = 0
        if self._event_file_partial_buffer is not None:
            partial_buffer, partial_rows = self._event_file_partial_buffer
            while skipped < min(partial_rows, len(rows)) and buffers[skipped] == partial_buffer:
                skipped += 1
        if len(rows) < limit:
            # The read reached the end of the files, so its last buffer is complete.
            self._event_file_checkpoint = buffers[-1]
            self._event_file_partial_buffer = None
        else:
            last_buffer_start = buffers.index(buffers[-1])
            if last_buffer_start > 0:
                self._event_file_checkpoint = buffers[last_buffer_start - 1]
            # Otherwise the whole read is within its first buffer, and the checkpoint stays before it.
            self._event_file_partial_buffer = (buffers[-1], len(rows) - last_buffer_start)
        return rows[skipped:]

    def _plan_events(self, cursor: Any, events: list[dict]) -> Iterator[dict]:
        """The plan events, and their raw copies, of the events read, the slowest execution per query and plan."""
        slowest: dict[tuple, dict] = {}
        for event in events:
            event_name = event.get('event_name')
            plan = event.get('showplan_xml')
            if not plan or not any(element in plan for element in RUNTIME_ELEMENTS):
                self._statuses[("no_runtime_data", event_name)] += 1
                continue
            if len(plan.encode('utf-8')) > self._max_plan_size_bytes:
                self._statuses[("too_large", event_name)] += 1
                continue
            key = (event.get('query_hash'), event.get('query_plan_hash'))
            current = slowest.get(key)
            if current is None or (event.get('duration_ms') or 0) > (current.get('duration_ms') or 0):
                if current is not None:
                    self._statuses[("rate_limited", current.get('event_name'))] += 1
                slowest[key] = event
            else:
                self._statuses[("rate_limited", event_name)] += 1

        for key, event in slowest.items():
            event_name = event.get('event_name')
            if key in self._seen_plans_ratelimiter:
                self._statuses[("rate_limited", event_name)] += 1
                continue
            raise_if_cancelled(self._cancel_event)
            try:
                plan_events = self._create_plan_events(cursor, event)
            except Exception as e:
                raise_if_cancelled(self._cancel_event)
                self._log.debug(
                    "Failed to create the plan event of query_hash=%s query_plan_hash=%s: %s", key[0], key[1], e
                )
                self._statuses[("error", event_name)] += 1
                continue
            if not self._seen_plans_ratelimiter.acquire(key):
                self._statuses[("rate_limited", event_name)] += 1
                continue
            self._statuses[("collected", event_name)] += 1
            yield from plan_events

    def _create_plan_events(self, cursor: Any, event: dict) -> list[dict]:
        raw_plan = event['showplan_xml']
        try:
            obfuscated_plan = obfuscate_xml_plan(raw_plan, self._config.obfuscator_options)
        except Exception:
            if self._config.log_unobfuscated_plans:
                self._log.warning("Failed to obfuscate plan=[%s]", repr(raw_plan))
            raise

        raw_statement = self._statement_text(cursor, event)
        collection_errors = None
        obfuscated_statement = query_signature = None
        metadata: dict = {}
        if raw_statement:
            try:
                statement = obfuscate_sql_with_metadata(
                    raw_statement, self._config.obfuscator_options, replace_null_character=True
                )
            except Exception:
                if self._config.log_unobfuscated_queries:
                    self._log.warning("Failed to obfuscate query=[%s]", repr(raw_statement))
                raise
            obfuscated_statement = statement['query']
            query_signature = compute_sql_signature(obfuscated_statement)
            metadata = statement['metadata']
        else:
            collection_errors = [
                {'code': "statement_text_unavailable", 'message': "the statement is no longer in the plan cache"}
            ]

        database_name = event.get('database_name') or None
        tags = list(self._check.tag_manager.get_tags())
        if database_name:
            tags.append("db:{}".format(database_name))
        # The per-execution fields, named as in the other XE events.
        execution = self._normalize_event(event)
        execution.pop('xe_type', None)
        plan_event = {
            "host": self._check.reported_hostname,
            "database_instance": self._check.database_identifier,
            "ddagentversion": self._check.agent_version,
            "ddsource": "sqlserver",
            "ddtags": ",".join(tags),
            "timestamp": time.time() * 1000,
            "dbm_type": "plan",
            "cloud_metadata": self._check.cloud_metadata,
            "sqlserver_version": self._check.static_info_cache.get(STATIC_INFO_VERSION, ""),
            "sqlserver_engine_edition": self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION, ""),
            "service": self._config.service,
            "db": {
                "instance": database_name,
                "plan": {
                    "definition": obfuscated_plan,
                    "signature": event.get('query_plan_hash'),
                    "type": "real",
                    "source": PLAN_SOURCES[event['event_name']],
                    "collection_errors": collection_errors,
                },
                "query_signature": query_signature,
                "statement": obfuscated_statement,
                "metadata": {
                    "tables": metadata.get('tables'),
                    "commands": metadata.get('commands'),
                    "comments": metadata.get('comments'),
                },
            },
            "sqlserver": {
                "query_hash": event.get('query_hash'),
                "query_plan_hash": event.get('query_plan_hash'),
                "plan_handle": event.get('plan_handle'),
                **execution,
            },
        }
        if not self._collect_raw_query:
            return [plan_event]
        raw_plan_event = copy.deepcopy(plan_event)
        raw_plan_event["dbm_type"] = "rqp"  # raw query plan
        raw_plan_event["db"]["plan"]["definition"] = raw_plan
        raw_plan_event["db"]["statement"] = raw_statement
        # query_plan_hash only identifies the plan shape, so the raw plan's own hash links the two events.
        raw_plan_signature = compute_sql_signature(raw_plan)
        raw_plan_event["db"]["plan"]["raw_signature"] = raw_plan_signature
        plan_event["db"]["plan"]["raw_signature"] = raw_plan_signature
        return [raw_plan_event, plan_event]

    def _statement_text(self, cursor: Any, event: dict) -> str | None:
        """
        The statement the plan executed: from the tsql_frame action through `sys.dm_exec_sql_text`, or else from
        `sys.dm_exec_query_stats`, since XE plans have no statement text.
        """
        sql_handle = event.get('sql_handle')
        offset_start = event.get('offset_start')
        if sql_handle and offset_start is not None:
            offset_end = event.get('offset_end', -1)
            text = self._cached_statement_text(
                cursor,
                ("frame", sql_handle, offset_start, offset_end),
                FRAME_STATEMENT_QUERY,
                (offset_start, offset_end, sql_handle),
            )
            if text:
                return text
        plan_handle = event.get('plan_handle')
        query_hash = event.get('query_hash')
        if plan_handle and query_hash:
            offset = offset_start if offset_start is not None else UNKNOWN_OFFSET
            return self._cached_statement_text(
                cursor,
                ("query_stats", plan_handle, query_hash, offset),
                QUERY_STATS_STATEMENT_QUERY,
                ("0x" + plan_handle, "0x" + query_hash, offset),
            )
        return None

    def _cached_statement_text(self, cursor: Any, key: tuple, query: str, params: tuple) -> str | None:
        if key in self._statement_text_cache:
            return self._statement_text_cache[key]
        cursor.execute(query, params)
        row = cursor.fetchone()
        text = row[0] if row and row[0] else None
        self._statement_text_cache[key] = text
        return text
