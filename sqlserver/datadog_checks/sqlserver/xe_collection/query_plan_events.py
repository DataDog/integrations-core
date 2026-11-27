# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Iterator

from cachetools import TTLCache
from dateutil import parser
from lxml import etree

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.base.utils.db.utils import (
    RateLimitingTTLCache,
    default_json_event_encoding,
    obfuscate_sql_with_metadata,
)
from datadog_checks.base.utils.serialization import json
from datadog_checks.base.utils.tracking import tracked_method
from datadog_checks.sqlserver.const import STATIC_INFO_ENGINE_EDITION
from datadog_checks.sqlserver.health import SqlServerHealthEvent
from datadog_checks.sqlserver.statements import build_plan_events
from datadog_checks.sqlserver.utils import is_azure_database, is_azure_sql_database, raise_if_cancelled

from .base import EVENT_FILE_TARGET, XESessionBase, agent_check_getter, is_target_read_denied
from .event_file_reader import EventFileEvent, EventFileReader
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

DEFAULT_SAMPLES_PER_HOUR_PER_QUERY = 4
DEFAULT_MAX_PLAN_SIZE_BYTES = 1_000_000
# The plans kept in one run, in UTF-8 bytes, until they're sent: at most one per query and plan shape, which can still
# be `max_events` plans of `max_plan_size_bytes`, about 1 GB by default. The plans beyond it are skipped until the next
# run. It isn't an option: it guards the Agent's memory rather than tuning the collection, and a budget raised to fit
# `max_events` large plans would no longer guard it.
MAX_KEPT_PLAN_BYTES = 64 * 1024 * 1024
# What an event holds besides its plan: its other fields and actions, and the XML around them.
PLAN_EVENT_ENVELOPE_BYTES = 64 * 1024
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
# The StatMan aggregate is only in the plans of the statistics builds SQL Server runs while it compiles a statement, or
# for UPDATE STATISTICS. They aren't the plan of a user statement, and their text and plan are gone from the server
# before the session is read, so they would be sent without a statement.
STATISTICS_UPDATE_PLAN = etree.XPath(
    'boolean(.//sp:Aggregate[@AggType="STATMAN"])',
    namespaces={'sp': 'http://schemas.microsoft.com/sqlserver/2004/07/showplan'},
)
STATISTICS_UPDATE_PLAN_TEXT = 'AggType="STATMAN"'
# Used when the session has no query_hash or query_plan_hash action.
PLAN_QUERY_HASH_PATTERN = re.compile(r'\bQueryHash="0x([0-9A-Fa-f]+)"')
PLAN_QUERY_PLAN_HASH_PATTERN = re.compile(r'\bQueryPlanHash="0x([0-9A-Fa-f]+)"')

QUERY_PLANS_DOCS_URL = "https://docs.datadoghq.com/database_monitoring/guide/sql_real_execution_plans/"
# The guide's platform tabs, by title, and their `tab` parameter: the title in lowercase without spaces and punctuation.
QUERY_PLANS_SETUP_DOCS_TABS = {
    "Self-hosted": "selfhosted",
    "Azure SQL Database": "azuresqldatabase",
    "Azure SQL Managed Instance": "azuresqlmanagedinstance",
}

# The statement of a tsql_frame action, for plans no longer in the cache: its sql handle's text, cut at its offsets as
# query metrics cut the text of a cached plan.
FRAME_STATEMENT_QUERY = """\
SELECT SUBSTRING(qt.text, (o.start_offset / 2) + 1,
    ((CASE o.end_offset WHEN -1 THEN DATALENGTH(qt.text) ELSE o.end_offset END - o.start_offset) / 2) + 1)
FROM (SELECT CAST(? AS int) AS start_offset, CAST(? AS int) AS end_offset) o
CROSS APPLY sys.dm_exec_sql_text(CONVERT(varbinary(64), ?, 1)) qt
"""
# The statement of a cached plan, from the `sys.dm_exec_query_stats` row query metrics read, so they compute the same
# query signature. A plan can have several statements with the same query hash, so the one at the frame's offset comes
# first when it's known.
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
# The stored procedure a plan's statement ran in, as query metrics resolve it for estimated plans: its schema and name,
# and the start of its text, from the plan handle, whose text is the procedure's.
PROCEDURE_QUERY = """\
SELECT OBJECT_SCHEMA_NAME(o.object_id, o.database_id), OBJECT_NAME(o.object_id, o.database_id),
    SUBSTRING(qt.text, 1, o.char_limit)
FROM (SELECT CAST(? AS int) AS object_id, CAST(? AS int) AS database_id, CAST(? AS int) AS char_limit) o
OUTER APPLY sys.dm_exec_sql_text(CONVERT(varbinary(64), ?, 1)) qt
"""
# The object type of the statements executed in a stored procedure.
PROCEDURE_OBJECT_TYPE = "PROC"
# The procedure signature of estimated plans whose procedure text fails to obfuscate.
PROCEDURE_OBFUSCATION_ERROR = "__procedure_obfuscation_error__"

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


def is_statistics_update(plan_data: etree._Element) -> bool:
    """Whether the showplan_xml field of an event is the plan of a statistics build."""
    value = plan_data.find('./value')
    if value is None:
        return False
    if len(value):
        return bool(STATISTICS_UPDATE_PLAN(value))
    # The value is the plan as text.
    return STATISTICS_UPDATE_PLAN_TEXT in (value.text or '')


def event_key(event: etree._Element) -> tuple:
    """The identity of an execution's event, to recognize it when it's read again."""
    actions = {action.get('name'): extract_value(action) for action in event.findall('./action')}
    duration = extract_value(event.find("./data[@name='duration']"))
    return (event.get('timestamp'), duration, *(actions.get(name) for name in EVENT_KEY_ACTIONS))


def query_plans_setup_docs_url(engine_edition: int | None) -> str:
    """The guide's section on creating the session, on the tab of the server's platform."""
    if is_azure_sql_database(engine_edition):
        platform = "Azure SQL Database"
    elif is_azure_database(engine_edition):
        platform = "Azure SQL Managed Instance"
    else:
        platform = "Self-hosted"
    return "{}?tab={}#create-the-session".format(QUERY_PLANS_DOCS_URL, QUERY_PLANS_SETUP_DOCS_TABS[platform])


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


class QueryPlanEventsHandler(XESessionBase):
    """
    Collects real execution plans from the `datadog_query_plans` XE session, which customers create and start, with
    either the `query_post_execution_plan_profile` or the `query_post_execution_showplan` event.

    Each event is the actual plan of one statement execution, with its runtime parameter values. The session is read
    from its event_file target, or its ring_buffer target where there's no event_file target.
    """

    SESSION_MISSING_HEALTH_EVENT = SqlServerHealthEvent.QUERY_PLANS_XE_SESSION_MISSING
    TARGET_UNSUPPORTED_HEALTH_EVENT = SqlServerHealthEvent.QUERY_PLANS_XE_TARGET_UNSUPPORTED
    TARGET_READ_DENIED_HEALTH_EVENT = SqlServerHealthEvent.QUERY_PLANS_XE_TARGET_READ_DENIED
    COLLECTED_DATA_NAME = "real execution plans"
    SESSION_DOCS_URL = QUERY_PLANS_DOCS_URL

    def __init__(self, check: SQLServer, config: SQLServerConfig):
        super().__init__(check, config, SESSION_NAME)
        query_plans_config = getattr(config, 'xe_collection_config', {}).get('query_plans', {}) or {}
        samples_per_hour = self._positive_int_option(
            query_plans_config, 'samples_per_hour_per_query', DEFAULT_SAMPLES_PER_HOUR_PER_QUERY
        )
        self._max_plan_size_bytes = self._positive_int_option(
            query_plans_config, 'max_plan_size_bytes', DEFAULT_MAX_PLAN_SIZE_BYTES
        )
        # One plan per query and plan shape per interval, as the query_hash and query_plan_hash pair.
        self._seen_plans_ratelimiter = RateLimitingTTLCache(
            maxsize=RATE_LIMITER_MAX_SIZE, ttl=60 * 60 / samples_per_hour
        )
        # The event of the slowest execution read per query_hash and query_plan_hash pair, the only one whose plan is
        # kept, as the others aren't sent, with its plan's UTF-8 size, and the total size of the plans kept.
        self._slowest_plan_events: dict[tuple, tuple[dict, int]] = {}
        self._kept_plan_bytes = 0
        self._statement_text_cache: TTLCache = TTLCache(
            maxsize=STATEMENT_TEXT_CACHE_MAX_SIZE, ttl=STATEMENT_TEXT_CACHE_TTL_SECONDS
        )
        self._event_file_reader = EventFileReader(
            self.session_name,
            self.max_events,
            self._max_event_bytes(self._max_plan_size_bytes),
            self._log,
            self._cancel_event,
        )
        self._statuses: Counter = Counter()
        # The keys of the events read, the newest last, and whether the current read skips the events read before. The
        # ring buffer returns all its events at every read, and so can a read from a file's start without checkpoint,
        # while a read after the checkpoint only returns new events.
        self._seen_event_keys: OrderedDict[tuple, None] = OrderedDict()
        self._skip_seen_events = False

        self.register_event_handler(PLAN_PROFILE_EVENT, self._parse_plan_event)
        self.register_event_handler(SHOWPLAN_EVENT, self._parse_plan_event)

    def _session_setup_docs_url(self) -> str:
        return query_plans_setup_docs_url(self._check.static_info_cache.get(STATIC_INFO_ENGINE_EDITION))

    def _positive_int_option(self, query_plans_config: dict, name: str, default: int) -> int:
        """A `collect_xe.query_plans` option that must be at least 1, or its default when it's unset or invalid."""
        value = query_plans_config.get(name)
        if value is None:
            return default
        try:
            value = int(value)
        except (TypeError, ValueError):
            value = 0
        if value < 1:
            self._log.warning("`collect_xe.query_plans.%s` must be at least 1, using %s", name, default)
            return default
        return value

    @staticmethod
    def _max_event_bytes(max_plan_size_bytes: int) -> int:
        """
        The largest event_file event read, in the UTF-16 bytes `DATALENGTH` counts, so that the events whose plan is
        too large aren't fetched. A plan's UTF-16 size is at most twice its UTF-8 size, which `max_plan_size_bytes`
        limits, and the event adds its envelope. An event that passes can still hold a plan that's too large, which is
        then skipped once parsed.
        """
        return 2 * max_plan_size_bytes + PLAN_EVENT_ENVELOPE_BYTES

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
        plan_data = None
        try:
            for data in event.findall('./data'):
                name = data.get('name')
                if name == 'showplan_xml':
                    plan_data = data
                elif name == 'object_type':
                    event_data['object_type'] = extract_text_representation(data) or extract_value(data)
                elif name:
                    extract_field(data, event_data, name, PLAN_EVENT_NUMERIC_FIELDS, [], self._log)
            # Skipped before sampling, so that these plans take neither a sample nor the memory budget. The event is
            # still read: its key is already recorded, and an event_file read moves past it.
            if plan_data is not None and is_statistics_update(plan_data):
                self._statuses[("statistics_update", event_data.get('event_name'))] += 1
                return True
            self._process_action_elements(event, event_data)
            for action in event.findall("./action[@name='tsql_frame']"):
                event_data.pop('tsql_frame', None)
                event_data.update(parse_tsql_frame(action))
            event_data['query_hash'] = hash_to_hex(event_data.get('query_hash'))
            event_data['query_plan_hash'] = hash_to_hex(event_data.get('query_plan_hash'))
            plan = None
            if not (event_data['query_hash'] and event_data['query_plan_hash']):
                # Without the query_hash or query_plan_hash action, the hashes are read from the plan.
                plan = parse_showplan_xml(plan_data) if plan_data is not None else None
                event_data['query_hash'] = event_data['query_hash'] or self._plan_hash(
                    PLAN_QUERY_HASH_PATTERN, plan or ''
                )
                event_data['query_plan_hash'] = event_data['query_plan_hash'] or self._plan_hash(
                    PLAN_QUERY_PLAN_HASH_PATTERN, plan or ''
                )
            if event_data.get('plan_handle'):
                event_data['plan_handle'] = event_data['plan_handle'].lower().removeprefix('0x')
            self._keep_slowest_plan(event_data, plan_data, plan)
        except Exception as e:
            self._log.debug("Failed to parse %s event: %s", event_data.get('event_name'), e)
            self._statuses[("error", event_data.get('event_name'))] += 1
            return False
        return True

    def _keep_slowest_plan(self, event_data: dict, plan_data: etree._Element | None, plan: str | None) -> None:
        """
        Keeps the event's plan, as `showplan_xml`, when it's the slowest execution read so far of its query and plan
        shape and isn't rate limited. The plan is serialized only then, as a read can hold `max_events` plans, and kept
        only while the plans kept total at most `MAX_KEPT_PLAN_BYTES`.
        """
        event_name = event_data.get('event_name')
        key = (event_data.get('query_hash'), event_data.get('query_plan_hash'))
        slowest, slowest_plan_bytes = self._slowest_plan_events.get(key, (None, 0))
        if self._is_rate_limited(key) or (
            slowest is not None and (event_data.get('duration_ms') or 0) <= (slowest.get('duration_ms') or 0)
        ):
            self._statuses[("rate_limited", event_name)] += 1
            return
        if plan is None and plan_data is not None:
            plan = parse_showplan_xml(plan_data)
        if not plan or not any(element in plan for element in RUNTIME_ELEMENTS):
            self._statuses[("no_runtime_data", event_name)] += 1
            return
        plan_bytes = len(plan.encode('utf-8'))
        if plan_bytes > self._max_plan_size_bytes:
            self._statuses[("too_large", event_name)] += 1
            return
        # A slower execution replaces the plan kept of its query and plan shape.
        kept_plan_bytes = self._kept_plan_bytes - slowest_plan_bytes + plan_bytes
        if kept_plan_bytes > MAX_KEPT_PLAN_BYTES:
            self._statuses[("memory_limited", event_name)] += 1
            return
        if slowest is not None:
            del slowest['showplan_xml']
            self._statuses[("rate_limited", slowest.get('event_name'))] += 1
        event_data['showplan_xml'] = plan
        self._slowest_plan_events[key] = event_data, plan_bytes
        self._kept_plan_bytes = kept_plan_bytes

    def _take_kept_plans(self) -> dict[tuple, tuple[dict, int]]:
        """The events whose plans are kept, with their plans' sizes, which are no longer kept."""
        kept, self._slowest_plan_events, self._kept_plan_bytes = self._slowest_plan_events, {}, 0
        return kept

    def _is_rate_limited(self, key: tuple) -> bool:
        """Whether a plan of this query and plan shape can't be sent now, so building it would be wasted work."""
        return (
            key in self._seen_plans_ratelimiter
            or len(self._seen_plans_ratelimiter) >= self._seen_plans_ratelimiter.maxsize
        )

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
        try:
            events = self._read_events(cursor)
        except Exception as e:
            if not is_target_read_denied(e):
                raise
            raise_if_cancelled(self._cancel_event)
            self._report_target_read(e)
            return
        self._report_target_read(None)
        if not events:
            return
        self._submit_lag(events)
        for plan_event in self._plan_events(cursor):
            self._check.database_monitoring_query_sample(json.dumps(plan_event, default=default_json_event_encoding))

    def _read_events(self, cursor: Any) -> list[dict]:
        """The new events of the session's target, read and parsed."""
        target_name, file_name = self._session_target(cursor)
        if target_name is None:
            return []
        started = time.time()
        self._take_kept_plans()
        if target_name == EVENT_FILE_TARGET:
            file_events, self._skip_seen_events = (
                self._read_event_file(cursor, file_name) if file_name else (iter(()), False)
            )
            # A read failing after some of its events are parsed doesn't move the position, so the next run reads them
            # again, and mustn't skip them as seen.
            seen_event_keys = self._seen_event_keys.copy()
            try:
                # The events are fetched as they're parsed, so the read time of an event_file target includes the
                # parsing.
                events = self._process_event_file_events(file_events)
            except Exception:
                self._seen_event_keys = seen_event_keys
                # The next run reads the events again, and keeps their plans then.
                self._take_kept_plans()
                raise
            self._submit_read_time(target_name, started)
        else:
            xml_data, self._skip_seen_events = self._read_ring_buffer(cursor), True
            self._submit_read_time(target_name, started)
            events = self._process_events(xml_data) if xml_data else []
        return events

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

    def _submit_read_time(self, target_name: str, started: float) -> None:
        self._check.histogram(
            "dd.sqlserver.xe.query_plans.read_time",
            (time.time() - started) * 1000,
            **self._check.debug_stats_kwargs(tags=["target:" + target_name]),
        )

    @tracked_method(agent_check_getter=agent_check_getter)
    def _read_event_file(self, cursor: Any, current_file: str) -> tuple[Iterator[EventFileEvent], bool]:
        return self._event_file_reader.read(cursor, current_file)

    @tracked_method(agent_check_getter=agent_check_getter, track_result_length=True)
    def _process_event_file_events(self, file_events: Iterator[EventFileEvent]) -> list[dict]:
        """
        The data of the events of an event_file read, each parsed on its own as it's fetched, so that a read holds one
        batch of events and the plans kept, at most `MAX_KEPT_PLAN_BYTES`, rather than all its events. Every event is
        iterated, which moves the read's position past them, its plan kept or not.
        """
        events = []
        for file_event in file_events:
            if file_event.data is None:
                self._statuses[("too_large", file_event.name)] += 1
                continue
            try:
                element = etree.fromstring(self._xml_bytes(file_event.data))
            except (etree.XMLSyntaxError, UnicodeEncodeError) as e:
                self._log.debug("Failed to parse %s event: %s", file_event.name, e)
                self._statuses[("error", file_event.name)] += 1
                continue
            event_data = self._process_event(element)
            if event_data is not None:
                events.append(event_data)
        return events

    def _plan_events(self, cursor: Any) -> Iterator[dict]:
        """The plan events, and their raw copies, of the events read, the slowest execution per query and plan."""
        for key, (event, _plan_bytes) in self._take_kept_plans().items():
            event_name = event.get('event_name')
            # The sampling cache can fill up while this read's plans are sent.
            if self._is_rate_limited(key):
                self._statuses[("rate_limited", event_name)] += 1
                continue
            raise_if_cancelled(self._cancel_event)
            try:
                plan_events, plan_obfuscated = self._create_plan_events(cursor, event)
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
            # A plan that fails to obfuscate is sent without its definition, with a collection error.
            self._statuses[("collected" if plan_obfuscated else "obfuscate_xml_plan_error", event_name)] += 1
            yield from plan_events

    def _create_plan_events(self, cursor: Any, event: dict) -> tuple[list[dict], bool]:
        """The plan event of an execution, and its raw copy, and whether its plan was obfuscated."""
        raw_plan = event['showplan_xml']
        raw_statement = self._statement_text(cursor, event)
        collection_errors = []
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
            collection_errors.append(
                {'code': "statement_text_unavailable", 'message': "the statement is no longer in the plan cache"}
            )

        procedure_name, procedure_signature = self._procedure(cursor, event)
        database_name = event.get('database_name') or None
        tags = list(self._check.tag_manager.get_tags())
        if database_name:
            tags.append("db:{}".format(database_name))
        # The per-execution fields, named as in the other XE events.
        execution = self._normalize_event(event)
        execution.pop('xe_type', None)
        obfuscation_errors: list[Exception] = []
        plan_events = build_plan_events(
            self._check,
            self._config,
            raw_plan=raw_plan,
            plan={
                "signature": event.get('query_plan_hash'),
                "type": "real",
                "source": PLAN_SOURCES[event['event_name']],
            },
            instance=database_name,
            db={
                "query_signature": query_signature,
                "procedure_signature": procedure_signature,
                "procedure_name": procedure_name,
                "statement": obfuscated_statement,
            },
            metadata={
                "tables": metadata.get('tables'),
                "commands": metadata.get('commands'),
                "comments": metadata.get('comments'),
            },
            sqlserver={
                "query_hash": event.get('query_hash'),
                "query_plan_hash": event.get('query_plan_hash'),
                "plan_handle": event.get('plan_handle'),
                **execution,
            },
            tags=tags,
            collect_raw=self._collect_raw_query,
            log_context="query_hash=[{}] query_plan_hash=[{}] plan_handle=[{}]".format(
                event.get('query_hash'), event.get('query_plan_hash'), event.get('plan_handle')
            ),
            on_obfuscation_error=obfuscation_errors.append,
            collection_errors=collection_errors,
            raw_db={"statement": raw_statement},
        )
        return plan_events, not obfuscation_errors

    def _statement_text(self, cursor: Any, event: dict) -> str | None:
        """
        The statement the plan executed, since XE plans have no statement text: the one query metrics see for the plan
        in `sys.dm_exec_query_stats`, or else, for a plan no longer in the cache, the tsql_frame action's through
        `sys.dm_exec_sql_text`. The query metrics statement comes first, as the frame's can differ: for a statement
        SQL Server parameterizes but caches unparameterized, the frame's sql handle is the parameterized text, while
        its offsets are in the original batch.
        """
        offset_start = event.get('offset_start')
        plan_handle = event.get('plan_handle')
        query_hash = event.get('query_hash')
        if plan_handle and query_hash:
            offset = offset_start if offset_start is not None else UNKNOWN_OFFSET
            text = self._cached_statement_text(
                cursor,
                ("query_stats", plan_handle, query_hash, offset),
                QUERY_STATS_STATEMENT_QUERY,
                ("0x" + plan_handle, "0x" + query_hash, offset),
            )
            if text:
                return text
        sql_handle = event.get('sql_handle')
        if sql_handle and offset_start is not None:
            offset_end = event.get('offset_end', -1)
            return self._cached_statement_text(
                cursor,
                ("frame", sql_handle, offset_start, offset_end),
                FRAME_STATEMENT_QUERY,
                (offset_start, offset_end, sql_handle),
            )
        return None

    def _procedure(self, cursor: Any, event: dict) -> tuple[str | None, str | None]:
        """
        The name and signature of the stored procedure the plan's statement ran in, computed as query metrics compute
        them for estimated plans, so that the plan links to its procedure. None outside procedures.
        """
        if event.get('object_type') != PROCEDURE_OBJECT_TYPE:
            return None, None
        try:
            object_id = int(event['object_id'])
            database_id = int(event['source_database_id'])
        except (KeyError, TypeError, ValueError):
            return None, None
        plan_handle = event.get('plan_handle') or ''
        key = ("procedure", object_id, database_id, plan_handle)
        if key in self._statement_text_cache:
            return self._statement_text_cache[key]
        limit = self._config.stored_procedure_characters_limit
        try:
            cursor.execute(
                PROCEDURE_QUERY, (object_id, database_id, limit, "0x" + plan_handle if plan_handle else None)
            )
            schema_name, name, text = cursor.fetchone() or (None, None, None)
        except Exception as e:
            raise_if_cancelled(self._cancel_event)
            self._log.debug("Failed to look up procedure object_id=%s database_id=%s: %s", object_id, database_id, e)
            return None, None
        procedure_name = "{}.{}".format(schema_name, name).lower() if schema_name and name else None
        procedure_signature = None
        if text:
            try:
                obfuscated_text = obfuscate_sql_with_metadata(
                    text, self._config.obfuscator_options, replace_null_character=True
                )['query']
                procedure_signature = compute_sql_signature(obfuscated_text)
            except Exception as e:
                self._log.debug("Failed to obfuscate the text of procedure %s: %s", procedure_name, e)
                procedure_signature = PROCEDURE_OBFUSCATION_ERROR
        self._statement_text_cache[key] = procedure_name, procedure_signature
        return procedure_name, procedure_signature

    def _cached_statement_text(self, cursor: Any, key: tuple, query: str, params: tuple) -> str | None:
        if key in self._statement_text_cache:
            return self._statement_text_cache[key]
        cursor.execute(query, params)
        row = cursor.fetchone()
        text = row[0] if row and row[0] else None
        self._statement_text_cache[key] = text
        return text
