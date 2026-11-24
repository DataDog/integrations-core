# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import re
import time
from contextlib import contextmanager
from copy import deepcopy

import mock
import pytest
from lxml import etree

from datadog_checks.base.utils.db.sql import compute_sql_signature
from datadog_checks.sqlserver import SQLServer
from datadog_checks.sqlserver.const import (
    ENGINE_EDITION_AZURE_MANAGED_INSTANCE,
    ENGINE_EDITION_ENTERPRISE,
    ENGINE_EDITION_SQL_DATABASE,
    STATIC_INFO_ENGINE_EDITION,
)
from datadog_checks.sqlserver.utils import construct_use_statement
from datadog_checks.sqlserver.xe_collection.base import SESSION_TARGETS_QUERY
from datadog_checks.sqlserver.xe_collection.event_file_reader import (
    ALL_RETAINED_FILES,
    EVENT_FILE_FETCH_BATCH_SIZE,
    EVENT_FILE_LAST_BUFFER_QUERY,
    EVENT_FILE_OLDEST_FILE_QUERY,
    EVENT_FILE_READ_FROM_CHECKPOINT_QUERY,
    EVENT_FILE_READ_FROM_START_FILE_QUERY,
    EVENT_FILE_READ_QUERY,
    event_file_pattern,
)
from datadog_checks.sqlserver.xe_collection.query_plan_events import (
    DEFAULT_MAX_PLAN_SIZE_BYTES,
    FRAME_STATEMENT_QUERY,
    PLAN_EVENT_ENVELOPE_BYTES,
    PROCEDURE_QUERY,
    QUERY_STATS_STATEMENT_QUERY,
    QueryPlanEventsHandler,
    parse_showplan_xml,
)
from datadog_checks.sqlserver.xe_collection.registry import get_xe_session_handlers

from .common import CHECK_NAME
from .conftest import SelfHealingConnection

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'xml_xe_events')
PLAN_PROFILE_FIXTURE = 'query_post_execution_plan_profile.xml'
SHOWPLAN_FIXTURE = 'query_post_execution_showplan.xml'
# The plan of an automatic statistics update that SQL Server ran while it compiled a user statement, whose query_hash
# action is the user statement's, and whose query_plan_hash action is 0.
STATISTICS_UPDATE_FIXTURE = 'query_post_execution_plan_profile_statman.xml'
# The statement of both fixtures, as sys.dm_exec_sql_text returns it.
STATEMENT = (
    "SELECT /*poc:sp_executesql_rpc_pytds*/ o.order_id, o.amount FROM dbo.orders o "
    "WHERE o.customer_id = @P1 AND o.status >= @P2 ORDER BY o.amount DESC"
)
# A statement SQL Server parameterizes, but caches unparameterized as it isn't safe to parameterize: query metrics see
# its text, while the tsql_frame action's sql handle is the parameterized text, cut at the statement's offsets in the
# original batch.
AUTO_PARAMETERIZED_STATEMENT = "SELECT COUNT(*) FROM dbo.t WHERE c LIKE 'val5%' AND v <> 6"
AUTO_PARAMETERIZED_FRAME_TEXT = "(@1 tinyint,@2 varchar(8000))SELECT COUNT(*) FROM [dbo].[t] WHE"
PLAN_HANDLE = '0600050012eb2f1b60fced1f1200000001000000000000000000000000000000000000000000000000000000'
SQL_HANDLE = '0x0200000012EB2F1BB0F35DCC64332DC0EB7A17EDFDB853E60000000000000000000000000000000000000000'
CURRENT_FILE = '/var/opt/mssql/log/datadog_query_plans_0_134080000000000000.xel'
BLOB_CURRENT_FILE = 'https://account.blob.core.windows.net/xe/datadog_query_plans_0_134080000000000000.xel'
# The largest event an event_file read fetches, in UTF-16 bytes: twice the default plan size limit, which is in UTF-8
# bytes, and the event's envelope.
DEFAULT_MAX_EVENT_BYTES = 2 * DEFAULT_MAX_PLAN_SIZE_BYTES + PLAN_EVENT_ENVELOPE_BYTES
# The current file, and the path the files are read with, of local and Azure Blob Storage event_file targets.
EVENT_FILE_PATHS = [
    pytest.param(CURRENT_FILE, '/var/opt/mssql/log/datadog_query_plans*.xel', id='local'),
    pytest.param(BLOB_CURRENT_FILE, 'https://account.blob.core.windows.net/xe/datadog_query_plans', id='blob'),
]


def load_event(fixture: str) -> etree._Element:
    with open(os.path.join(FIXTURES_DIR, fixture), 'rb') as f:
        return etree.fromstring(f.read()).find('event')


def make_event(
    fixture: str = PLAN_PROFILE_FIXTURE,
    timestamp: str | None = None,
    duration_us: int | None = None,
    query_plan_hash: int | None = None,
    plan_transform=None,
    activity_id: str | None = None,
    object_type: str | None = None,
) -> str:
    """A fixture event as `fn_xe_file_target_read_file` returns it, with some fields replaced."""
    event = load_event(fixture)
    if object_type:
        event.find("./data[@name='object_type']/text").text = object_type
    if timestamp:
        event.set('timestamp', timestamp)
    if activity_id:
        event.find("./action[@name='attach_activity_id']/value").text = activity_id
    if duration_us is not None:
        event.find("./data[@name='duration']/value").text = str(duration_us)
    if query_plan_hash is not None:
        event.find("./action[@name='query_plan_hash']/value").text = str(query_plan_hash)
    if plan_transform:
        value = event.find("./data[@name='showplan_xml']/value")
        plan = plan_transform(etree.tostring(value[0], encoding='unicode'))
        value.remove(value[0])
        value.append(etree.fromstring(plan))
    return etree.tostring(event, encoding='unicode')


def fixture_plan(fixture: str) -> str:
    return etree.tostring(load_event(fixture).find("./data[@name='showplan_xml']/value")[0], encoding='unicode')


def fixture_plan_handle(fixture: str) -> str:
    return load_event(fixture).find("./action[@name='plan_handle']/value").text


def plan_size(event: str) -> int:
    """The UTF-8 size of an event's plan, as the plans kept are counted."""
    return len(parse_showplan_xml(etree.fromstring(event).find("./data[@name='showplan_xml']")).encode('utf-8'))


def patch_max_kept_plan_bytes(max_kept_plan_bytes: int):
    return mock.patch(
        'datadog_checks.sqlserver.xe_collection.query_plan_events.MAX_KEPT_PLAN_BYTES', max_kept_plan_bytes, create=True
    )


def timestamp(second: int) -> str:
    return '2026-11-09T15:55:{:02d}.000Z'.format(second)


def mock_obfuscate_sql(query, options=None):
    query = re.sub(r"'[^']*'", "?", query)
    return re.sub(r"([^@\w])[0-9]+", r"\1?", query)


# The error of a read from a checkpoint whose file is gone, as ODBC Driver 18 reports it on SQL Server 2022, and as a
# driver without the error number would.
CHECKPOINT_FILE_GONE_MESSAGE = (
    "The operating system returned error 2(The system cannot find the file specified.) while reading from the file "
    "'{}'."
)
CHECKPOINT_FILE_GONE_ERRORS = {
    'odbc': "('42000', \"[42000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
    + CHECKPOINT_FILE_GONE_MESSAGE
    + " (25717) (SQLExecDirectW)\")",
    'without_error_number': CHECKPOINT_FILE_GONE_MESSAGE,
}


class FakeEventFile:
    """
    The files of an event_file target, as `fn_xe_file_target_read_file` reads them, oldest first: a read from a
    checkpoint returns the events of the buffers after it, in its file and the next ones, and fails when its file is
    gone.
    """

    def __init__(self, current_file: str = CURRENT_FILE):
        # file name -> list of (offset, events)
        self.files: dict[str, list[tuple[int, list[str]]]] = {current_file: []}
        self.current_file = current_file
        self.pattern = event_file_pattern(current_file)
        self.file_gone_error = CHECKPOINT_FILE_GONE_ERRORS['odbc']
        # The errors of the next reads from a checkpoint, and of the next lookups of the newest buffer.
        self.checkpoint_read_errors: list[Exception] = []
        self.last_buffer_errors: list[Exception] = []

    def add_buffer(self, *events: str) -> None:
        buffers = self.files[self.current_file]
        buffers.append(((len(buffers) + 1) * 1024, list(events)))

    def start_file(self) -> None:
        """The next file, as at a rollover or a restart of the session."""
        name = re.sub(r'_(\d+)\.xel$', lambda m: '_{}.xel'.format(int(m.group(1)) + 1), self.current_file)
        self.files[name] = []
        self.current_file = name

    def rows(self, files: list[str], after: tuple[str, int] | None = None) -> list[tuple[str, str, int]]:
        rows = []
        for name in files:
            for offset, events in self.files[name]:
                if after and (name, offset) <= after:
                    continue
                rows.extend((event, name, offset) for event in events)
        return rows

    @staticmethod
    def read_rows(rows: list[tuple[str, str, int]], top: int, max_event_bytes: int) -> list[tuple]:
        """The rows of a read: the event, or None over `max_event_bytes` UTF-16 bytes, its buffer and its name."""
        return [
            (
                event if len(event.encode('utf-16-le')) <= max_event_bytes else None,
                name,
                offset,
                etree.fromstring(event).get('name'),
            )
            for event, name, offset in rows[:top]
        ]

    def matching_files(self, path: str) -> list[str]:
        return sorted(self.files) if path == self.pattern else [path]

    def responses(self, sql: str, params: tuple):
        if sql == EVENT_FILE_LAST_BUFFER_QUERY:
            if self.last_buffer_errors:
                raise self.last_buffer_errors.pop(0)
            rows = self.rows([params[0]])
            return [(rows[-1][1], rows[-1][2])] if rows else []
        if sql == EVENT_FILE_OLDEST_FILE_QUERY:
            rows = self.rows(self.matching_files(params[0]))
            return [(rows[0][1],)] if rows else []
        if sql == EVENT_FILE_READ_QUERY:
            top, max_event_bytes, path = params
            return self.read_rows(self.rows(self.matching_files(path)), top, max_event_bytes)
        if sql == EVENT_FILE_READ_FROM_START_FILE_QUERY:
            top, max_event_bytes, path, start_file = params
            rows = self.rows([name for name in self.matching_files(path) if name >= start_file])
            return self.read_rows(rows, top, max_event_bytes)
        if sql == EVENT_FILE_READ_FROM_CHECKPOINT_QUERY:
            top, max_event_bytes, _pattern, file_name, offset = params
            if self.checkpoint_read_errors:
                raise self.checkpoint_read_errors.pop(0)
            if file_name not in self.files:
                raise Exception(self.file_gone_error.format(file_name))
            files = sorted(self.files)
            rows = self.rows(files[files.index(file_name) :], after=(file_name, offset))
            return self.read_rows(rows, top, max_event_bytes)
        return None


class FakeServer:
    """The queries of the handler, answered from an event_file target, or the given target rows."""

    def __init__(self, targets=None, frame_text=STATEMENT, query_stats_text=STATEMENT, current_file=CURRENT_FILE):
        self.event_file = FakeEventFile(current_file)
        self.targets = targets
        self.ring_buffer = None
        self.frame_text = frame_text
        self.query_stats_text = query_stats_text
        # (object_id, database_id) -> (schema name, procedure name, procedure text)
        self.procedures: dict[tuple[int, int], tuple[str, str, str]] = {}
        self.queries: list[tuple[str, tuple]] = []
        # The rows the cursors returned through `fetchmany`, as the event_file reads fetch them.
        self.rows_fetched = 0
        # The size of the largest event fetched, in UTF-16 bytes.
        self.largest_event_fetched = 0
        # The outcomes of the next `fetchmany` calls: None fetches, an exception is raised.
        self.fetch_errors: list[Exception | None] = []

    def execute(self, sql: str, params: tuple) -> list:
        self.queries.append((sql, params))
        if sql == SESSION_TARGETS_QUERY.format(level=''):
            if self.targets is not None:
                return self.targets
            return [
                (
                    'event_file',
                    '<EventFileTarget><File name="{}"/></EventFileTarget>'.format(self.event_file.current_file),
                )
            ]
        if "t.target_name = 'ring_buffer'" in sql:
            return [(self.ring_buffer,)] if self.ring_buffer else []
        if sql == FRAME_STATEMENT_QUERY:
            return [(self.frame_text,)] if self.frame_text else []
        if sql == QUERY_STATS_STATEMENT_QUERY:
            return [(self.query_stats_text,)] if self.query_stats_text else []
        if sql == PROCEDURE_QUERY:
            object_id, database_id, char_limit, _plan_handle = params
            schema_name, name, text = self.procedures.get((object_id, database_id), (None, None, None))
            return [(schema_name, name, text[:char_limit] if text else None)]
        rows = self.event_file.responses(sql, params)
        if rows is None:
            raise AssertionError("unexpected query: {!r}".format(sql))
        return rows

    def executed(self, sql: str) -> list[tuple]:
        return [params for query, params in self.queries if query == sql]


class FakeCursor:
    def __init__(self, server: FakeServer):
        self._server = server
        self._rows: list = []

    def execute(self, sql, params=()):
        self._rows = self._server.execute(sql, params)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def fetchmany(self, size):
        if self._server.fetch_errors and (error := self._server.fetch_errors.pop(0)):
            raise error
        batch, self._rows = self._rows[:size], self._rows[size:]
        self._server.rows_fetched += len(batch)
        for row in batch:
            if row[0] is not None:
                self._server.largest_event_fetched = max(
                    self._server.largest_event_fetched, len(row[0].encode('utf-16-le'))
                )
        return batch


class FakeConnection:
    connector = 'odbc'

    def __init__(self, server: FakeServer):
        self._server = server

    @contextmanager
    def open_managed_default_connection(self, key_prefix):
        yield

    @contextmanager
    def get_managed_cursor(self, key_prefix):
        yield FakeCursor(self._server)


@pytest.fixture
def xe_instance(instance_docker):
    instance = deepcopy(instance_docker)
    instance['dbm'] = True
    instance['collect_xe'] = {'query_plans': {'enabled': True}}
    return instance


def make_handler(instance, server: FakeServer, collect_raw_query_statement=False, **query_plans_config):
    instance = deepcopy(instance)
    instance['collect_xe']['query_plans'].update(query_plans_config)
    if collect_raw_query_statement:
        instance['collect_raw_query_statement'] = {'enabled': True}
    check = SQLServer(CHECK_NAME, {}, [instance])
    check._connection = FakeConnection(server)
    return QueryPlanEventsHandler(check, check._config)


def plan_events(aggregator, dbm_type='plan'):
    return [e for e in aggregator.get_event_platform_events('dbm-samples') if e['dbm_type'] == dbm_type]


def query_plans_health_events(aggregator):
    return [
        (e['name'], e['status'])
        for e in aggregator.get_event_platform_events('dbm-health')
        if e['name'].startswith('query_plans_xe_')
    ]


def assert_events_metric(aggregator, handler, status, xe_event, count):
    aggregator.assert_metric(
        'dd.sqlserver.xe.query_plans.events',
        value=count,
        tags=handler._check.debug_tags() + ['status:' + status, 'xe_event:' + xe_event],
    )


def run_from_ring_buffer(handler, server, *events):
    server.targets = [('ring_buffer', None)]
    server.ring_buffer = '<RingBufferTarget>{}</RingBufferTarget>'.format(''.join(events))
    handler.run_job()


@pytest.mark.unit
@pytest.mark.parametrize(
    'fixture,expected',
    [
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            {
                'event_name': 'query_post_execution_plan_profile',
                'timestamp': '2026-11-09T15:55:32.210Z',
                'duration_ms': 0.144,
                'cpu_time': 144,
                'dop': 1,
                'granted_memory_kb': 1024,
                'used_memory_kb': 16,
                'requested_memory_kb': 1024,
                'ideal_memory_kb': 544,
                'serial_ideal_memory_kb': 544,
                'nest_level': 2,
                'object_type': 'PREPARED',
                'object_name': 'Dynamic SQL',
                'database_name': 'poc',
                'session_id': 60,
                'request_id': 0,
                'username': 'sa',
                'client_app_name': 'poc-xe-sp_executesql_rpc_pytds',
                'client_hostname': '93a8743337f5',
                'activity_id': '15FA5520-49DF-4FC5-B9B6-2CAD3BF4B827-1',
                'query_hash': '50bc31917b994640',
                'query_plan_hash': 'd42556f4dfd6a9e8',
                'plan_handle': PLAN_HANDLE,
                'sql_handle': SQL_HANDLE,
                'offset_start': 34,
                'offset_end': 324,
            },
            id='plan_profile',
        ),
        pytest.param(
            SHOWPLAN_FIXTURE,
            {
                'event_name': 'query_post_execution_showplan',
                'duration_ms': 0.27,
                'query_hash': '50bc31917b994640',
                'query_plan_hash': 'd42556f4dfd6a9e8',
                'database_name': 'poc',
            },
            id='showplan',
        ),
    ],
)
def test_parse_plan_event(xe_instance, fixture, expected):
    handler = make_handler(xe_instance, FakeServer())

    events = handler._process_events('<events>{}</events>'.format(make_event(fixture)))

    assert len(events) == 1
    event = events[0]
    assert {field: event.get(field) for field in expected} == expected
    assert event['showplan_xml'] == fixture_plan(fixture)
    assert (
        etree.fromstring(event['showplan_xml']).tag
        == '{http://schemas.microsoft.com/sqlserver/2004/07/showplan}ShowPlanXML'
    )
    if fixture == SHOWPLAN_FIXTURE:
        # the session has no tsql_frame action
        assert 'sql_handle' not in event


@pytest.mark.unit
@pytest.mark.parametrize('collect_raw_query_statement', [False, True])
@pytest.mark.parametrize(
    'fixture,source,runtime_values',
    [
        pytest.param(PLAN_PROFILE_FIXTURE, 'xe_query_post_execution_plan_profile', ('(42)', '(0)'), id='plan_profile'),
        pytest.param(SHOWPLAN_FIXTURE, 'xe_query_post_execution_showplan', ('(99999)', '(4)'), id='showplan'),
    ],
)
def test_plan_event(
    aggregator, datadog_agent, xe_instance, fixture, source, runtime_values, collect_raw_query_statement
):
    """Each execution becomes a real plan event with its obfuscated plan and statement, and the execution's context."""
    server = FakeServer()
    handler = make_handler(xe_instance, server, collect_raw_query_statement=collect_raw_query_statement)

    with mock.patch.object(datadog_agent, 'obfuscate_sql', side_effect=mock_obfuscate_sql):
        run_from_ring_buffer(handler, server, make_event(fixture, duration_us=2_000_000))

    events = aggregator.get_event_platform_events('dbm-samples')
    assert [e['dbm_type'] for e in events] == (['rqp', 'plan'] if collect_raw_query_statement else ['plan'])
    event = events[-1]
    obfuscated_statement = mock_obfuscate_sql(STATEMENT)
    assert event['db']['statement'] == obfuscated_statement
    assert event['db']['query_signature'] == compute_sql_signature(obfuscated_statement)
    assert event['db']['instance'] == 'poc'
    plan = event['db']['plan']
    assert {k: plan[k] for k in ('signature', 'type', 'source', 'collection_errors')} == {
        'signature': 'd42556f4dfd6a9e8',
        'type': 'real',
        'source': source,
        'collection_errors': None,
    }
    # runtime and compiled parameter values are obfuscated alike
    assert 'ParameterRuntimeValue="(?)"' in plan['definition']
    assert 'ParameterCompiledValue="(?)"' in plan['definition']
    for value in runtime_values + ('(42)', '(0)'):
        assert value not in plan['definition']
    assert 'db:poc' in event['ddtags'].split(',')
    sqlserver = event['sqlserver']
    assert sqlserver['query_hash'] == '50bc31917b994640'
    assert sqlserver['query_plan_hash'] == 'd42556f4dfd6a9e8'
    assert sqlserver['plan_handle'] == fixture_plan_handle(fixture)
    assert sqlserver['database_name'] == 'poc'
    assert sqlserver['username'] == 'sa'
    assert sqlserver['session_id'] > 0
    assert sqlserver['duration_ms'] == 2000.0
    assert sqlserver['cpu_time'] > 0
    assert sqlserver['activity_id']
    assert sqlserver['dop'] == 1
    assert sqlserver['granted_memory_kb'] == 1024
    # the event fired when the statement ended
    assert sqlserver['event_fire_timestamp'] > sqlserver['query_start']
    assert_events_metric(aggregator, handler, 'collected', fixture.removesuffix('.xml'), 1)

    if collect_raw_query_statement:
        raw_event = events[0]
        assert raw_event['db']['plan']['definition'] == fixture_plan(fixture)
        assert raw_event['db']['statement'] == STATEMENT
        for value in runtime_values:
            assert 'ParameterRuntimeValue="{}"'.format(value) in raw_event['db']['plan']['definition']
        assert raw_event['db']['plan']['raw_signature'] == compute_sql_signature(fixture_plan(fixture))
        assert plan['raw_signature'] == raw_event['db']['plan']['raw_signature']
        assert raw_event['sqlserver'] == sqlserver
    else:
        assert 'raw_signature' not in plan


@pytest.mark.unit
@pytest.mark.parametrize(
    'fixture,plan_transform,query_plans_config,status',
    [
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            lambda plan: re.sub(
                r'<RunTimeInformation>.*?</RunTimeInformation>|<QueryTimeStats[^>]*>(</QueryTimeStats>)?', '', plan
            ),
            {},
            'no_runtime_data',
            id='no_runtime_data',
        ),
        pytest.param(PLAN_PROFILE_FIXTURE, None, {'max_plan_size_bytes': 1000}, 'too_large', id='too_large'),
        pytest.param(STATISTICS_UPDATE_FIXTURE, None, {}, 'statistics_update', id='statistics_update'),
        pytest.param(PLAN_PROFILE_FIXTURE, None, {}, 'collected', id='collected'),
    ],
)
def test_plans_without_runtime_data_too_large_or_of_statistics_updates_are_skipped(
    aggregator, xe_instance, fixture, plan_transform, query_plans_config, status
):
    server = FakeServer()
    handler = make_handler(xe_instance, server, **query_plans_config)

    run_from_ring_buffer(handler, server, make_event(fixture, plan_transform=plan_transform))

    assert len(plan_events(aggregator)) == (1 if status == 'collected' else 0)
    assert_events_metric(aggregator, handler, status, 'query_post_execution_plan_profile', 1)


@pytest.mark.unit
def test_rate_limit_keeps_the_slowest_execution(aggregator, xe_instance):
    """Each query and plan shape gets `samples_per_hour_per_query` plans, from the slowest executions read."""
    server = FakeServer()
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=1)

    run_from_ring_buffer(
        handler,
        server,
        make_event(timestamp=timestamp(1), duration_us=2_000_000),
        make_event(timestamp=timestamp(2), duration_us=5_000_000),
        make_event(timestamp=timestamp(3), duration_us=3_000_000),
        make_event(timestamp=timestamp(4), duration_us=1_000_000, query_plan_hash=1),
    )
    durations = {e['sqlserver']['query_plan_hash']: e['sqlserver']['duration_ms'] for e in plan_events(aggregator)}
    assert durations == {'d42556f4dfd6a9e8': 5000.0, '0000000000000001': 1000.0}
    assert_events_metric(aggregator, handler, 'collected', 'query_post_execution_plan_profile', 2)
    assert_events_metric(aggregator, handler, 'rate_limited', 'query_post_execution_plan_profile', 2)

    aggregator.reset()
    run_from_ring_buffer(handler, server, make_event(timestamp=timestamp(5), duration_us=9_000_000))
    assert plan_events(aggregator) == []
    assert_events_metric(aggregator, handler, 'rate_limited', 'query_post_execution_plan_profile', 1)


@pytest.mark.unit
@pytest.mark.parametrize(
    'extra_budget,expected_duration_ms,memory_limited',
    [
        # the slower plan fits alone, but not with the plan it replaces, nor with another plan
        pytest.param(0, 5000.0, 1, id='replaced_within_budget'),
        pytest.param(-1, 2000.0, 2, id='kept_over_budget'),
    ],
)
def test_slower_execution_replaces_the_kept_plan_within_the_memory_budget(
    aggregator, xe_instance, extra_budget, expected_duration_ms, memory_limited
):
    """
    A slower execution's plan replaces the plan kept of its query and plan shape only if the plans kept stay within
    `MAX_KEPT_PLAN_BYTES`, without the plan replaced. Otherwise the plan kept is sent, and the slower one is memory
    limited, as is a plan of another query and plan shape that doesn't fit.
    """
    server = FakeServer()
    handler = make_handler(xe_instance, server)

    def pad(plan):
        return plan.replace('<ShowPlanXML', '<ShowPlanXML Padding="{}"'.format('x' * 1000))

    slower_event = make_event(timestamp=timestamp(2), duration_us=5_000_000, plan_transform=pad)
    other_shape_event = make_event(timestamp=timestamp(3), query_plan_hash=1, plan_transform=pad)

    with patch_max_kept_plan_bytes(plan_size(slower_event) + extra_budget):
        run_from_ring_buffer(
            handler,
            server,
            make_event(timestamp=timestamp(1), duration_us=2_000_000),
            slower_event,
            other_shape_event,
        )

    assert [e['sqlserver']['duration_ms'] for e in plan_events(aggregator)] == [expected_duration_ms]
    assert_events_metric(aggregator, handler, 'memory_limited', 'query_post_execution_plan_profile', memory_limited)


@pytest.mark.unit
def test_events_read_keep_only_the_plans_that_may_be_sent(xe_instance):
    """A read holds one plan per query and plan shape, the slowest execution's, rather than `max_events` plans."""
    handler = make_handler(xe_instance, FakeServer())

    events = handler._process_events(
        '<events>{}</events>'.format(
            ''.join(
                make_event(timestamp=timestamp(second), duration_us=duration_us)
                for second, duration_us in [(1, 2_000_000), (2, 5_000_000), (3, 3_000_000)]
            )
        )
    )

    assert [event['timestamp'] for event in events if 'showplan_xml' in event] == [timestamp(2)]


@pytest.mark.unit
def test_full_sampling_cache_skips_plan_construction(aggregator, xe_instance):
    """Once the sampling cache is full, the plans it would reject aren't built, which obfuscates them."""
    server = FakeServer()
    with mock.patch('datadog_checks.sqlserver.xe_collection.query_plan_events.RATE_LIMITER_MAX_SIZE', 1):
        handler = make_handler(xe_instance, server)

    with mock.patch(
        'datadog_checks.sqlserver.statements.obfuscate_xml_plan', side_effect=lambda plan, _: plan
    ) as obfuscate_xml_plan:
        run_from_ring_buffer(handler, server, make_event(query_plan_hash=1), make_event(query_plan_hash=2))

    assert len(plan_events(aggregator)) == 1
    assert obfuscate_xml_plan.call_count == 1
    assert_events_metric(aggregator, handler, 'collected', 'query_post_execution_plan_profile', 1)
    assert_events_metric(aggregator, handler, 'rate_limited', 'query_post_execution_plan_profile', 1)


@pytest.mark.unit
@pytest.mark.parametrize('collect_raw_query_statement', [False, True])
def test_plan_that_fails_to_obfuscate_is_sent_without_definition(aggregator, xe_instance, collect_raw_query_statement):
    """
    A plan that fails to obfuscate is still sent, without its definition and with a collection error, as estimated
    plans are, and its raw copy keeps the raw plan.
    """
    server = FakeServer()
    handler = make_handler(xe_instance, server, collect_raw_query_statement=collect_raw_query_statement)

    with mock.patch(
        'datadog_checks.sqlserver.statements.obfuscate_xml_plan', side_effect=ValueError('unparsable plan')
    ):
        run_from_ring_buffer(handler, server, make_event())

    plan = plan_events(aggregator)[0]['db']['plan']
    assert plan['definition'] is None
    assert plan['collection_errors'] == [{'code': 'obfuscate_xml_plan_error', 'message': 'unparsable plan'}]
    if collect_raw_query_statement:
        assert plan_events(aggregator, dbm_type='rqp')[0]['db']['plan']['definition'] == fixture_plan(
            PLAN_PROFILE_FIXTURE
        )
    assert_events_metric(aggregator, handler, 'obfuscate_xml_plan_error', 'query_post_execution_plan_profile', 1)
    assert not [
        metric
        for metric in aggregator.metrics('dd.sqlserver.xe.query_plans.events')
        if 'status:collected' in metric.tags
    ]


@pytest.mark.unit
@pytest.mark.parametrize('value', [None, 0, -1, 'invalid'])
@pytest.mark.parametrize('option', ['samples_per_hour_per_query', 'max_plan_size_bytes'])
def test_unset_or_invalid_options_use_their_default(aggregator, xe_instance, option, value):
    """An empty or invalid option neither stops the XE handlers from starting nor drops every plan."""
    server = FakeServer()
    handler = make_handler(xe_instance, server, **{option: value})

    run_from_ring_buffer(handler, server, make_event())

    assert len(plan_events(aggregator)) == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    'query_plans_config,enabled',
    [
        pytest.param(None, False, id='null'),
        pytest.param({'enabled': 'false'}, False, id='string_false'),
        pytest.param({'enabled': 'true'}, True, id='string_true'),
        pytest.param({'enabled': True}, True, id='true'),
    ],
)
def test_query_plans_handler_registration(xe_instance, query_plans_config, enabled):
    """The handler starts when `diagnose` checks the session, as both read `enabled` alike."""
    xe_instance['collect_xe']['query_plans'] = query_plans_config
    check = SQLServer(CHECK_NAME, {}, [xe_instance])

    handlers = get_xe_session_handlers(check, check._config)

    assert [type(handler) for handler in handlers] == ([QueryPlanEventsHandler] if enabled else [])


@pytest.mark.unit
@pytest.mark.parametrize(
    'fixture,frame_text,query_stats_text,expected_statement,expected_lookups',
    [
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            AUTO_PARAMETERIZED_FRAME_TEXT,
            AUTO_PARAMETERIZED_STATEMENT,
            AUTO_PARAMETERIZED_STATEMENT,
            {QUERY_STATS_STATEMENT_QUERY: 1},
            id='from_query_stats',
        ),
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            STATEMENT,
            None,
            STATEMENT,
            {QUERY_STATS_STATEMENT_QUERY: 1, FRAME_STATEMENT_QUERY: 1},
            id='plan_not_cached',
        ),
        pytest.param(
            SHOWPLAN_FIXTURE, None, STATEMENT, STATEMENT, {QUERY_STATS_STATEMENT_QUERY: 1}, id='no_tsql_frame'
        ),
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            None,
            None,
            None,
            {QUERY_STATS_STATEMENT_QUERY: 1, FRAME_STATEMENT_QUERY: 1},
            id='statement_gone',
        ),
    ],
)
def test_statement_text(
    aggregator, xe_instance, fixture, frame_text, query_stats_text, expected_statement, expected_lookups
):
    """
    The statement is the one query metrics see in the cached plan's statistics, so the plan has their query signature,
    else the tsql_frame action's, and each lookup is cached.
    """
    server = FakeServer(frame_text=frame_text, query_stats_text=query_stats_text)
    handler = make_handler(xe_instance, server)

    # two plan shapes of the same statement
    run_from_ring_buffer(handler, server, make_event(fixture), make_event(fixture, query_plan_hash=1))

    events = plan_events(aggregator)
    assert [e['db']['statement'] for e in events] == [expected_statement] * 2
    lookups = {sql: len(server.executed(sql)) for sql in (FRAME_STATEMENT_QUERY, QUERY_STATS_STATEMENT_QUERY)}
    assert {sql: count for sql, count in lookups.items() if count} == expected_lookups
    if FRAME_STATEMENT_QUERY in expected_lookups:
        assert server.executed(FRAME_STATEMENT_QUERY) == [(34, 324, SQL_HANDLE)]
    if QUERY_STATS_STATEMENT_QUERY in expected_lookups:
        plan_handle, query_hash, offset = server.executed(QUERY_STATS_STATEMENT_QUERY)[0]
        assert plan_handle == '0x' + fixture_plan_handle(fixture)
        assert query_hash == '0x50bc31917b994640'
        # the statement at the frame's offset, when it's known
        assert offset == (34 if fixture == PLAN_PROFILE_FIXTURE else -2)
    if expected_statement is None:
        assert events[0]['db']['query_signature'] is None
        assert [e['code'] for e in events[0]['db']['plan']['collection_errors']] == ['statement_text_unavailable']


# The object and database of the fixtures' events.
FIXTURE_PROCEDURE_KEY = (456125202, 5)
PROCEDURE_TEXT = "CREATE PROCEDURE dbo.Orders_Report @customer_id int AS SELECT 1 WHERE 2 = @customer_id"


@pytest.mark.unit
@pytest.mark.parametrize('object_type', ['PROC', 'PREPARED'])
def test_procedure_fields(aggregator, datadog_agent, xe_instance, object_type):
    """
    The plan of a statement run in a stored procedure has the procedure name and signature of its estimated plans,
    so it links to the procedure, and keeps its own statement. The procedure is looked up once per plan handle.
    """
    server = FakeServer()
    server.procedures[FIXTURE_PROCEDURE_KEY] = ('dbo', 'Orders_Report', PROCEDURE_TEXT)
    xe_instance['stored_procedure_characters_limit'] = 40
    handler = make_handler(xe_instance, server)

    with mock.patch.object(datadog_agent, 'obfuscate_sql', side_effect=mock_obfuscate_sql):
        # two plan shapes of the same statement
        run_from_ring_buffer(
            handler,
            server,
            make_event(object_type=object_type),
            make_event(object_type=object_type, query_plan_hash=1),
        )

    events = plan_events(aggregator)
    assert [e['db']['statement'] for e in events] == [mock_obfuscate_sql(STATEMENT)] * 2
    procedures = {(e['db']['procedure_name'], e['db']['procedure_signature']) for e in events}
    if object_type == 'PROC':
        # the text query metrics compute the procedure signature from: the first characters, obfuscated
        assert procedures == {('dbo.orders_report', compute_sql_signature(mock_obfuscate_sql(PROCEDURE_TEXT[:40])))}
        assert len(server.executed(PROCEDURE_QUERY)) == 1
    else:
        assert procedures == {(None, None)}
        assert server.executed(PROCEDURE_QUERY) == []


def sent_timestamps(aggregator) -> list[str]:
    return [e['sqlserver']['event_fire_timestamp'] for e in plan_events(aggregator)]


def distinct_event(second: int) -> str:
    # a distinct plan shape per event, so the rate limit keeps them all
    return make_event(timestamp=timestamp(second), query_plan_hash=second)


@pytest.mark.unit
@pytest.mark.parametrize(
    'file_name,expected',
    [
        *EVENT_FILE_PATHS,
        pytest.param(
            'C:\\MSSQL\\Log\\datadog_query_plans_0_134080000000000000.xel',
            'C:\\MSSQL\\Log\\datadog_query_plans*.xel',
            id='windows',
        ),
        # Azure Blob Storage paths are a blob name prefix: wildcards aren't allowed there
        pytest.param(
            'HTTPS://account.blob.core.windows.net/xe/datadog_query_plans_0_1.xel',
            'HTTPS://account.blob.core.windows.net/xe/datadog_query_plans',
            id='blob_uppercase_scheme',
        ),
    ],
)
def test_event_file_pattern(file_name, expected):
    assert event_file_pattern(file_name) == expected


@pytest.mark.unit
@pytest.mark.parametrize('current_file,read_path', EVENT_FILE_PATHS)
def test_event_file_first_run_starts_at_the_newest_buffer(aggregator, xe_instance, current_file, read_path):
    server = FakeServer(current_file=current_file)
    handler = make_handler(xe_instance, server)
    server.event_file.add_buffer(distinct_event(1), distinct_event(2))
    server.event_file.add_buffer(distinct_event(3))

    handler.run_job()
    assert plan_events(aggregator) == []

    server.event_file.add_buffer(distinct_event(4), distinct_event(5))
    handler.run_job()
    assert sent_timestamps(aggregator) == [timestamp(4), timestamp(5)]
    assert server.executed(EVENT_FILE_READ_FROM_CHECKPOINT_QUERY)[-1] == (
        1000,
        DEFAULT_MAX_EVENT_BYTES,
        read_path,
        current_file,
        2048,
    )


@pytest.mark.unit
def test_event_file_first_run_on_an_empty_file(aggregator, xe_instance):
    server = FakeServer()
    handler = make_handler(xe_instance, server)

    handler.run_job()
    server.event_file.add_buffer(distinct_event(1))
    handler.run_job()

    assert sent_timestamps(aggregator) == [timestamp(1)]


@pytest.mark.unit
@pytest.mark.parametrize(
    'buffers,expected_runs',
    [
        pytest.param([[1], [2, 3]], [[1, 2], [3], []], id='read_ends_within_a_buffer'),
        pytest.param([[1, 2, 3, 4, 5]], [[1, 2], [3, 4], [5], []], id='buffer_larger_than_max_events'),
        pytest.param([[1], [2, 3, 4, 5], [6]], [[1, 2], [3, 4], [5, 6], []], id='larger_buffer_after_another'),
    ],
)
def test_event_file_reads_max_events_per_run(aggregator, xe_instance, buffers, expected_runs):
    """
    Each run reads at most `max_events` events, and the next run goes on from the last one, within its buffer too,
    although a read from a buffer's offset starts after the whole buffer.
    """
    server = FakeServer()
    # no rate limit, which would also stop the events read before
    handler = make_handler(xe_instance, server, max_events=2, samples_per_hour_per_query=10**9)
    handler.run_job()
    for buffer in buffers:
        server.event_file.add_buffer(*(distinct_event(second) for second in buffer))

    runs = []
    for _ in expected_runs:
        aggregator.reset()
        handler.run_job()
        runs.append(sent_timestamps(aggregator))

    assert runs == [[timestamp(second) for second in run] for run in expected_runs]


@pytest.mark.unit
@pytest.mark.parametrize(
    'steps,expected',
    [
        pytest.param(
            ['run', [1, 2, 3], 'run', 'new_file', [4]], [1, 2, 3, 4], id='first_buffer_read_in_part_then_rollover'
        ),
        pytest.param(['run', [1], [2], 'new_file', [3]], [1, 2, 3], id='empty_file_then_rollover'),
        pytest.param(
            ['run', [1], [2], 'session_stopped_run', 'new_file', [3]], [1, 2, 3], id='empty_file_then_session_restart'
        ),
        pytest.param([[1], 'failing_tail_lookup_run', 'run', [2]], [2], id='tail_lookup_failure'),
    ],
)
def test_event_file_before_the_first_checkpoint(aggregator, xe_instance, steps, expected):
    """
    Until a buffer is read in full, reading goes on from the file the first run started at into the files after it, a
    rollover's or a restarted session's, and not the files before it. A first run whose lookup of the newest buffer
    fails is retried at the next run, rather than the history read. Each execution is sent once.
    """
    server = FakeServer()
    # the history, in a file before the one the first run starts at
    server.event_file.add_buffer(distinct_event(0))
    server.event_file.start_file()
    # no rate limit, which would also stop the events read before
    handler = make_handler(xe_instance, server, max_events=2, samples_per_hour_per_query=10**9)
    for step in steps:
        if step == 'run':
            handler.run_job()
        elif step == 'new_file':
            server.event_file.start_file()
        elif step == 'session_stopped_run':
            server.targets = []
            handler.run_job()
            server.targets = None
        elif step == 'failing_tail_lookup_run':
            server.event_file.last_buffer_errors.append(Exception('Query timeout expired (SQLExecDirectW)'))
            with pytest.raises(Exception, match='Query timeout expired'):
                handler.run_job()
        else:
            server.event_file.add_buffer(*(distinct_event(second) for second in step))
    for _ in range(3):
        handler.run_job()

    assert sent_timestamps(aggregator) == [timestamp(second) for second in expected]


@pytest.mark.unit
@pytest.mark.parametrize(
    'first,second',
    [
        pytest.param(
            make_event(timestamp=timestamp(1), activity_id='A-1'),
            make_event(timestamp=timestamp(1), activity_id='B-1'),
            id='same_timestamp',
        ),
        pytest.param(
            make_event(timestamp=timestamp(5), activity_id='A-1'),
            make_event(timestamp=timestamp(3), activity_id='B-1'),
            id='earlier_timestamp',
        ),
    ],
)
@pytest.mark.parametrize('target', ['event_file', 'ring_buffer'])
def test_each_execution_is_sent_once(aggregator, xe_instance, target, first, second):
    """
    An execution is sent once, even read again from the ring buffer, and an execution read later is sent too, whatever
    its timestamp.
    """
    server = FakeServer()
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    if target == 'event_file':
        handler.run_job()
        server.event_file.add_buffer(first)
        handler.run_job()
        server.event_file.add_buffer(second)
        handler.run_job()
    else:
        run_from_ring_buffer(handler, server, first)
        run_from_ring_buffer(handler, server, first, second)
        run_from_ring_buffer(handler, server, first, second)

    assert [e['sqlserver']['activity_id'] for e in plan_events(aggregator)] == ['A-1', 'B-1']


@pytest.mark.unit
@pytest.mark.parametrize(
    'current_file,read_path',
    [
        *EVENT_FILE_PATHS,
        # the error of the gone file holds its path, which matches a denied read's error
        pytest.param(
            '/var/opt/mssql/xe_permissions/datadog_query_plans_0_134080000000000000.xel',
            '/var/opt/mssql/xe_permissions/datadog_query_plans*.xel',
            id='path_like_a_denied_read',
        ),
    ],
)
@pytest.mark.parametrize('checkpoint_file_removed', [True, False], ids=['rollover', 'session_restart'])
def test_event_file_checkpoint_file_replaced(aggregator, xe_instance, checkpoint_file_removed, current_file, read_path):
    """
    When the checkpoint's file is gone after rollovers, the files retained are read from the oldest, and when a
    restarted session writes a new file, reading goes on into it. Neither sends the events read before again.
    """
    server = FakeServer(current_file=current_file)
    # no rate limit, which would also stop the events read before
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    handler.run_job()
    server.event_file.add_buffer(distinct_event(1))
    handler.run_job()
    assert sent_timestamps(aggregator) == [timestamp(1)]

    old_file = server.event_file.current_file
    server.event_file.start_file()
    if checkpoint_file_removed:
        del server.event_file.files[old_file]
        # an event already read is in the current file too, as a read from a file's start can replay it
        server.event_file.add_buffer(distinct_event(1), distinct_event(2))
    else:
        # nothing after the checkpoint yet, and an empty new file
        handler.run_job()
        server.event_file.add_buffer(distinct_event(2))
    handler.run_job()

    assert sent_timestamps(aggregator) == [timestamp(1), timestamp(2)]
    # checkpoints are files the read returned, and the reads after them cover every file of the target
    assert {params[2:4] for params in server.executed(EVENT_FILE_READ_FROM_CHECKPOINT_QUERY)} == {
        (read_path, current_file)
    }
    if checkpoint_file_removed:
        assert server.executed(EVENT_FILE_READ_FROM_START_FILE_QUERY)[-1] == (
            1000,
            DEFAULT_MAX_EVENT_BYTES,
            read_path,
            ALL_RETAINED_FILES,
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    'read_before,files_after,failure,expected',
    [
        pytest.param(
            [[1]],
            [[[2]], [[3], [4, 5]], [[6, 7]]],
            'odbc',
            [1, 3, 4, 5, 6, 7],
            id='checkpoint_file_deleted',
        ),
        pytest.param(
            [[1]],
            [[[2]], [[3], [4, 5]], [[6, 7]]],
            'without_error_number',
            [1, 3, 4, 5, 6, 7],
            id='checkpoint_file_deleted_without_error_number',
        ),
        pytest.param([[1]], [[[2]], [[3]], [[4]]], 'transient', [1, 2, 3, 4], id='transient_read_error'),
        pytest.param(
            [[1], [2, 3, 4]],
            [[], [[5, 6, 7]]],
            'odbc',
            [1, 2, 5, 6, 7],
            id='partial_buffer_then_checkpoint_file_deleted',
        ),
        # the first buffer read in part, with no checkpoint before it, and its file deleted
        pytest.param(
            [[1, 2, 3]], [[], [[4, 5, 6]]], 'odbc', [1, 2, 4, 5, 6], id='partial_first_buffer_then_its_file_deleted'
        ),
    ],
)
def test_event_file_checkpoint_read_failure(aggregator, xe_instance, read_before, files_after, failure, expected):
    """
    Every execution still in a file of the target is sent once, with at most `max_events` per run: after the
    checkpoint's file is gone, from the oldest file retained rather than the current one, and after a read failing
    otherwise, from the checkpoint at the next run.
    """
    server = FakeServer()
    # no rate limit, which would also stop the events read before
    handler = make_handler(xe_instance, server, max_events=2, samples_per_hour_per_query=10**9)
    handler.run_job()
    for buffer in read_before:
        server.event_file.add_buffer(*(distinct_event(second) for second in buffer))
    handler.run_job()
    # the events after the checkpoint, in its file and the next ones
    checkpoint_file = server.event_file.current_file
    for i, buffers in enumerate(files_after):
        if i:
            server.event_file.start_file()
        for buffer in buffers:
            server.event_file.add_buffer(*(distinct_event(second) for second in buffer))
    if failure == 'transient':
        server.event_file.checkpoint_read_errors.append(Exception('Query timeout expired (SQLExecDirectW)'))
    else:
        server.event_file.file_gone_error = CHECKPOINT_FILE_GONE_ERRORS[failure]
        del server.event_file.files[checkpoint_file]

    for _ in range(len(expected)):
        handler.run_job()

    assert sent_timestamps(aggregator) == [timestamp(second) for second in expected]


def too_large_counts(aggregator) -> int:
    return sum(
        metric.value
        for metric in aggregator.metrics('dd.sqlserver.xe.query_plans.events')
        if 'status:too_large' in metric.tags
    )


@pytest.mark.unit
def test_event_file_events_over_the_size_limit_are_too_large(aggregator, xe_instance):
    """
    An event too large to hold a plan within `max_plan_size_bytes` isn't fetched, and counts as too large once. The
    events around it, in its buffer too, are each sent once, and the checkpoint moves past it.
    """
    max_plan_size_bytes = 20_000
    max_event_bytes = 2 * max_plan_size_bytes + PLAN_EVENT_ENVELOPE_BYTES
    server = FakeServer()
    # no rate limit, which would also stop the events read before
    handler = make_handler(
        xe_instance, server, max_events=2, samples_per_hour_per_query=10**9, max_plan_size_bytes=max_plan_size_bytes
    )
    handler.run_job()
    oversized_event = make_event(
        timestamp=timestamp(2),
        query_plan_hash=2,
        plan_transform=lambda plan: plan.replace(
            '<ShowPlanXML', '<ShowPlanXML Padding="{}"'.format('x' * max_event_bytes)
        ),
    )
    server.event_file.add_buffer(distinct_event(1), oversized_event)
    server.event_file.add_buffer(distinct_event(3), distinct_event(4))
    server.event_file.add_buffer(distinct_event(5))

    runs = []
    for _ in range(4):
        aggregator.reset()
        handler.run_job()
        runs.append((sent_timestamps(aggregator), too_large_counts(aggregator)))

    assert runs == [([timestamp(1)], 1), ([timestamp(3), timestamp(4)], 0), ([timestamp(5)], 0), ([], 0)]
    assert server.largest_event_fetched <= max_event_bytes


@pytest.mark.unit
def test_event_file_events_are_parsed_as_they_are_fetched(aggregator, xe_instance):
    """A read holds one batch of fetched events at a time, rather than all its events at once."""
    server = FakeServer()
    # no rate limit, so that every event is sent
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    handler.run_job()
    count = 3 * EVENT_FILE_FETCH_BATCH_SIZE + 1
    server.event_file.add_buffer(*(distinct_event(second) for second in range(count)))
    fetched_before = server.rows_fetched
    fetched_when_parsed = []
    parse_plan_event = handler._parse_plan_event

    def record_fetched_rows(event, event_data):
        fetched_when_parsed.append(server.rows_fetched - fetched_before)
        return parse_plan_event(event, event_data)

    handler.register_event_handler('query_post_execution_plan_profile', record_fetched_rows)
    handler.run_job()

    # each event is parsed once its batch is fetched, and before the next batch is
    batch = EVENT_FILE_FETCH_BATCH_SIZE
    assert fetched_when_parsed == [min(count, (i // batch + 1) * batch) for i in range(count)]
    assert len(plan_events(aggregator)) == count


@pytest.mark.unit
def test_event_file_plans_over_the_memory_budget_are_memory_limited(aggregator, xe_instance):
    """
    A read keeps distinct plans within `MAX_KEPT_PLAN_BYTES` in total, and counts the others as memory limited. Their
    events are still read, so the next run goes on after them.
    """
    server = FakeServer()
    # no rate limit, so that every plan kept is sent
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    handler.run_job()
    server.event_file.add_buffer(*(distinct_event(second) for second in range(5)))

    with patch_max_kept_plan_bytes(2 * plan_size(distinct_event(0)) + plan_size(distinct_event(0)) // 2):
        handler.run_job()
        assert sent_timestamps(aggregator) == [timestamp(0), timestamp(1)]
        assert_events_metric(aggregator, handler, 'memory_limited', 'query_post_execution_plan_profile', 3)

        aggregator.reset()
        server.event_file.add_buffer(distinct_event(5))
        handler.run_job()
        assert sent_timestamps(aggregator) == [timestamp(5)]


@pytest.mark.unit
def test_event_file_read_failing_after_a_batch_sends_its_events_at_the_next_run(aggregator, xe_instance):
    """
    A read from a file's start that fails after some of its events are parsed sends them at the next run, which reads
    them again and skips the events read before.
    """
    server = FakeServer()
    # no rate limit, so that every event is sent
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    # an empty file, so the next runs read from its start
    handler.run_job()
    count = EVENT_FILE_FETCH_BATCH_SIZE + 2
    server.event_file.add_buffer(*(distinct_event(second) for second in range(count)))
    server.fetch_errors = [None, Exception('Query timeout expired (SQLExecDirectW)')]

    with pytest.raises(Exception, match='Query timeout expired'):
        handler.run_job()
    handler.run_job()

    assert sent_timestamps(aggregator) == [timestamp(second) for second in range(count)]


@pytest.mark.unit
def test_session_health_events(aggregator, xe_instance, caplog):
    """Setup problems send one warning health event and log once, and send OK once fixed."""
    server = FakeServer(targets=[])
    handler = make_handler(xe_instance, server)
    caplog.set_level(logging.WARNING)

    handler.run_job()
    handler.run_job()
    assert query_plans_health_events(aggregator) == [('query_plans_xe_session_missing', 'warning')]
    warnings = [r.getMessage() for r in caplog.records if 'datadog_query_plans' in r.getMessage()]
    assert len(warnings) == 1
    assert "doesn't exist or isn't running" in warnings[0]

    server.targets = [('histogram', None)]
    handler.run_job()
    server.targets = [('ring_buffer', None)]
    handler.run_job()
    handler.run_job()

    assert query_plans_health_events(aggregator) == [
        ('query_plans_xe_session_missing', 'warning'),
        ('query_plans_xe_session_missing', 'ok'),
        ('query_plans_xe_target_unsupported', 'warning'),
        ('query_plans_xe_target_unsupported', 'ok'),
    ]


@pytest.mark.unit
@pytest.mark.parametrize(
    'engine_edition,tab',
    [
        pytest.param(ENGINE_EDITION_ENTERPRISE, 'selfhosted', id='self_hosted'),
        pytest.param(None, 'selfhosted', id='unknown_edition'),
        pytest.param(ENGINE_EDITION_SQL_DATABASE, 'azuresqldatabase', id='azure_sql_database'),
        pytest.param(ENGINE_EDITION_AZURE_MANAGED_INSTANCE, 'azuresqlmanagedinstance', id='azure_sql_managed_instance'),
    ],
)
def test_session_missing_warning_links_to_the_platform_setup(xe_instance, caplog, engine_edition, tab):
    """The warning of a missing session links to the guide's setup of the server's platform, rather than a script."""
    server = FakeServer(targets=[])
    handler = make_handler(xe_instance, server)
    handler._check.static_info_cache[STATIC_INFO_ENGINE_EDITION] = engine_edition
    caplog.set_level(logging.WARNING)

    handler.run_job()

    [warning] = [r.getMessage() for r in caplog.records if 'datadog_query_plans' in r.getMessage()]
    assert warning == (
        "The datadog_query_plans XE session doesn't exist or isn't running, so no real execution plans are collected. "
        "See https://docs.datadoghq.com/database_monitoring/guide/sql_real_execution_plans/?tab={}#create-the-session"
    ).format(tab)


# A read the login isn't allowed, as SQL Server 2022 reports it.
READ_DENIED_ERROR = "VIEW SERVER PERFORMANCE STATE permission was denied on object 'server', database 'master'. (300)"


@pytest.mark.unit
@pytest.mark.parametrize('denied_read', ['newest_buffer_lookup', 'checkpoint_read'])
def test_target_read_denied_health_events(aggregator, xe_instance, caplog, denied_read):
    """
    A denied read of the target sends a warning health event and logs once, until a read works again, which sends OK,
    and the events after the checkpoint are then all sent.
    """
    server = FakeServer()
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    caplog.set_level(logging.WARNING)
    if denied_read == 'checkpoint_read':
        server.event_file.add_buffer(distinct_event(1))
        handler.run_job()
        server.event_file.add_buffer(distinct_event(2))
        errors = server.event_file.checkpoint_read_errors
    else:
        errors = server.event_file.last_buffer_errors
    errors.extend([Exception(READ_DENIED_ERROR), Exception(READ_DENIED_ERROR)])

    handler.run_job()
    handler.run_job()
    assert query_plans_health_events(aggregator) == [('query_plans_xe_target_read_denied', 'warning')]
    warnings = [r.getMessage() for r in caplog.records if "isn't allowed to read" in r.getMessage()]
    assert len(warnings) == 1
    assert 'VIEW SERVER PERFORMANCE STATE on SQL Server 2022' in warnings[0]

    server.event_file.add_buffer(distinct_event(3))
    handler.run_job()
    handler.run_job()

    assert query_plans_health_events(aggregator) == [
        ('query_plans_xe_target_read_denied', 'warning'),
        ('query_plans_xe_target_read_denied', 'ok'),
    ]
    if denied_read == 'checkpoint_read':
        assert sent_timestamps(aggregator) == [timestamp(2), timestamp(3)]


@pytest.mark.unit
def test_lag_and_read_time_metrics(aggregator, xe_instance):
    server = FakeServer()
    handler = make_handler(xe_instance, server)

    run_from_ring_buffer(handler, server, make_event(timestamp='2020-01-01T00:00:00.000Z'))

    tags = handler._check.debug_tags()
    aggregator.assert_metric('dd.sqlserver.xe.query_plans.read_time', tags=tags + ['target:ring_buffer'])
    # the fixture's event is older than now
    lag = aggregator.metrics('dd.sqlserver.xe.query_plans.lag')
    assert len(lag) == 1 and lag[0].value > 0 and lag[0].tags == tags


XE_PLANS_TEST_APP = 'datadog-query-plans-test'


@pytest.fixture
def dbm_instance_xe_plans(instance_docker):
    instance = deepcopy(instance_docker)
    instance['dbm'] = True
    instance['min_collection_interval'] = 1
    instance['query_metrics'] = {'enabled': False}
    instance['query_activity'] = {'enabled': False}
    instance['procedure_metrics'] = {'enabled': False}
    instance['collect_settings'] = {'enabled': False}
    instance['collect_xe'] = {'run_sync': True, 'query_plans': {'enabled': True, 'collection_interval': 0.1}}
    return instance


def parameter_runtime_values(plan: str) -> dict[str, str]:
    return {
        element.get('Column'): element.get('ParameterRuntimeValue')
        for element in etree.fromstring(plan.encode('utf-8')).iter('{*}ColumnReference')
        if element.get('ParameterRuntimeValue') is not None
    }


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize('collect_raw_query_statement', [False, True])
def test_query_plans_from_xe_session(
    aggregator, datadog_agent, dd_run_check, dbm_instance_xe_plans, bob_conn_str, collect_raw_query_statement
):
    """
    The test servers run the datadog_query_plans session for one application's statements: an execution of a
    parameterized query gets a real plan with that execution's runtime parameter values, obfuscated in the plan event
    and raw in its raw copy.
    """
    if collect_raw_query_statement:
        dbm_instance_xe_plans['collect_raw_query_statement'] = {'enabled': True}
    check = SQLServer(CHECK_NAME, {}, [dbm_instance_xe_plans])
    # the first run starts after the events already in the session
    dd_run_check(check, cancel=False)

    # an alias unique to this run, which obfuscation keeps
    alias = 'xe_plans_{}'.format(int(time.time() * 1000))
    query = "SELECT id AS {} FROM ϑings WHERE id >= ? AND name <> ?".format(alias)
    executions = {('(1)', 'baz'), ('(2)', 'qux')}
    conn = SelfHealingConnection(bob_conn_str + 'APP={};'.format(XE_PLANS_TEST_APP))
    try:
        for params in ((1, 'baz'), (2, 'qux')):
            conn.execute_with_retries(query, params, database='datadog_test-1')
    finally:
        conn.close()

    expected_dbm_types = ['rqp', 'plan'] if collect_raw_query_statement else ['plan']
    events = []
    deadline = time.time() + 30
    while time.time() < deadline:
        # the session dispatches its events to its file every second
        time.sleep(2)
        # the Agent's obfuscator is a stub in tests
        with mock.patch.object(datadog_agent, 'obfuscate_sql', side_effect=mock_obfuscate_sql):
            dd_run_check(check, cancel=False)
        events = [
            e
            for e in aggregator.get_event_platform_events('dbm-samples')
            if e['dbm_type'] in ('plan', 'rqp') and alias in (e['db']['statement'] or '')
        ]
        if len(events) >= len(expected_dbm_types):
            break

    # both executions have the same query and plan shape, so one of them is sent
    assert [e['dbm_type'] for e in events] == expected_dbm_types
    plan_event = events[-1]
    plan = plan_event['db']['plan']
    assert plan['type'] == 'real'
    assert plan['source'] == 'xe_query_post_execution_plan_profile'
    assert plan['signature'] == plan_event['sqlserver']['query_plan_hash']
    assert plan_event['sqlserver']['client_app_name'] == XE_PLANS_TEST_APP
    assert plan_event['db']['instance'] == 'datadog_test-1'
    runtime_values = parameter_runtime_values(plan['definition'])
    assert set(runtime_values) == {'@P1', '@P2'}
    assert not any(re.search(r'[0-9]|baz|qux', value) for value in runtime_values.values()), runtime_values
    if collect_raw_query_statement:
        raw_event = events[0]
        assert raw_event['db']['plan']['raw_signature'] == plan['raw_signature']
        raw_values = parameter_runtime_values(raw_event['db']['plan']['definition'])
        # the values of one execution: the plans of the other executions are rate limited
        assert (raw_values['@P1'], re.sub(r"^N?'(.*)'$", r"\1", raw_values['@P2'])) in executions, raw_values


# 1,000 rows of distinct names, from an offset.
INSERT_STATISTICS_ROWS = """\
WITH d AS (SELECT n FROM (VALUES (0), (1), (2), (3), (4), (5), (6), (7), (8), (9)) v(n))
INSERT INTO #statistics_update (id, name)
SELECT ? + a.n * 100 + b.n * 10 + c.n, CONCAT('name', ? + a.n * 100 + b.n * 10 + c.n)
FROM d a CROSS JOIN d b CROSS JOIN d c
"""
# A join, as the trivial plan of a single-table query creates no statistics.
SELECT_STATISTICS_ROWS = (
    "SELECT COUNT(*) AS {} FROM #statistics_update a JOIN #statistics_update b ON b.id = a.id WHERE a.name = '{}'"
)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_query_plans_of_statistics_updates_are_skipped(
    aggregator, datadog_agent, dd_run_check, dbm_instance_xe_plans, bob_conn_str
):
    """
    A statement compiled without statistics on its columns, or with stale ones, makes SQL Server build them in the
    application's session, and the session captures the plans of those builds: they're counted as statistics updates
    rather than sent, and the statement's own plan is sent with its statement.
    """
    check = SQLServer(CHECK_NAME, {}, [dbm_instance_xe_plans])
    # the first run starts after the events already in the session
    dd_run_check(check, cancel=False)

    # an alias unique to this run, which obfuscation keeps
    alias = 'xe_statistics_{}'.format(int(time.time() * 1000))
    conn = SelfHealingConnection(bob_conn_str + 'APP={};'.format(XE_PLANS_TEST_APP))
    try:
        with conn.conn.cursor() as cursor:
            cursor.execute("CREATE TABLE #statistics_update (id int, name varchar(20))")
            cursor.execute(INSERT_STATISTICS_ROWS, (0, 0))
            # the first statement on the columns creates their statistics
            cursor.execute(SELECT_STATISTICS_ROWS.format(alias + '_created', 'name1'))
            cursor.fetchall()
            # more changes than the 500 rows and 20% of the table that make the statistics stale, which the next
            # statement compiled updates
            cursor.execute(INSERT_STATISTICS_ROWS, (1000, 1000))
            cursor.execute(SELECT_STATISTICS_ROWS.format(alias + '_updated', 'name2'))
            cursor.fetchall()
    finally:
        conn.close()

    def statistics_updates() -> int:
        return sum(
            metric.value
            for metric in aggregator.metrics('dd.sqlserver.xe.query_plans.events')
            if 'status:statistics_update' in metric.tags
        )

    events: list[dict] = []
    deadline = time.time() + 30
    while time.time() < deadline:
        # the session dispatches its events to its file every second
        time.sleep(2)
        with mock.patch.object(datadog_agent, 'obfuscate_sql', side_effect=mock_obfuscate_sql):
            dd_run_check(check, cancel=False)
        events = plan_events(aggregator)
        if statistics_updates() and any(alias in (e['db']['statement'] or '') for e in events):
            break

    assert statistics_updates() > 0
    assert [e for e in events if 'STATMAN' in (e['db']['plan']['definition'] or '')] == []
    assert any(alias in (e['db']['statement'] or '') for e in events)


def call_procedure(conn_str: str, sql: str, params: tuple = ()) -> None:
    """Runs a procedure call, and reads all its result sets, as its statements run while they're read."""
    conn = SelfHealingConnection(conn_str)
    try:
        with conn.conn.cursor() as cursor:
            cursor.execute(construct_use_statement('datadog_test-1'))
            cursor.execute(sql, params)
            while True:
                if cursor.description:
                    cursor.fetchall()
                if not cursor.nextset():
                    break
    finally:
        conn.close()


# The statements of the bobProcParams procedure of the test setup.
PROCEDURE_STATEMENTS = ["SELECT * FROM ϑings WHERE id = @P1", "SELECT id FROM ϑings WHERE name = @P2"]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytest.mark.parametrize(
    'call,params',
    [
        pytest.param("{CALL bobProcParams (?, ?)}", (1, 'foo'), id='rpc'),
        pytest.param("EXEC bobProcParams @P1 = 2, @P2 = 'bar'", (), id='exec_in_batch'),
    ],
)
def test_query_plans_of_stored_procedure_statements(
    aggregator, datadog_agent, dd_run_check, dbm_instance_xe_plans, bob_conn_str, call, params
):
    """
    A two-statement procedure, called by RPC or with EXEC in a batch, gets one real plan per statement inside it,
    with the statement and its query signature, and the procedure's name and signature, which link it to the
    procedure as its estimated plans are.
    """
    check = SQLServer(CHECK_NAME, {}, [dbm_instance_xe_plans])
    # the first run starts after the events already in the session
    dd_run_check(check, cancel=False)

    call_procedure(bob_conn_str + 'APP={};'.format(XE_PLANS_TEST_APP), call, params)

    events = []
    deadline = time.time() + 30
    while time.time() < deadline:
        # the session dispatches its events to its file every second
        time.sleep(2)
        with mock.patch.object(datadog_agent, 'obfuscate_sql', side_effect=mock_obfuscate_sql):
            dd_run_check(check, cancel=False)
        events = [e for e in plan_events(aggregator) if e['db'].get('procedure_name') == 'dbo.bobprocparams']
        if len(events) >= len(PROCEDURE_STATEMENTS):
            break

    # the statement as query metrics delimit it, which can include its semicolon
    assert sorted(e['db']['statement'].rstrip(';') for e in events) == sorted(PROCEDURE_STATEMENTS)
    for event in events:
        assert event['db']['plan']['type'] == 'real'
        assert event['db']['query_signature'] == compute_sql_signature(event['db']['statement'])
        assert event['sqlserver']['object_type'] == 'PROC'
        assert event['sqlserver']['object_name'] == 'bobProcParams'
        assert event['sqlserver']['nest_level'] == 1
        assert event['sqlserver']['client_app_name'] == XE_PLANS_TEST_APP
        # each plan is the plan of its statement, not of the whole procedure
        assert event['db']['plan']['definition'].count('<StmtSimple') == 1
    procedure_signatures = {e['db']['procedure_signature'] for e in events}
    assert len(procedure_signatures) == 1 and None not in procedure_signatures
