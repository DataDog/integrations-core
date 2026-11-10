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
from datadog_checks.sqlserver.xe_collection.query_plan_events import (
    EVENT_FILE_LAST_BUFFER_QUERY,
    EVENT_FILE_READ_FROM_CHECKPOINT_QUERY,
    EVENT_FILE_READ_QUERY,
    FRAME_STATEMENT_QUERY,
    QUERY_STATS_STATEMENT_QUERY,
    SESSION_TARGETS_QUERY,
    QueryPlanEventsHandler,
)

from .common import CHECK_NAME
from .conftest import SelfHealingConnection

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'xml_xe_events')
PLAN_PROFILE_FIXTURE = 'query_post_execution_plan_profile.xml'
SHOWPLAN_FIXTURE = 'query_post_execution_showplan.xml'
# The statement of both fixtures, as sys.dm_exec_sql_text returns it.
STATEMENT = (
    "SELECT /*poc:sp_executesql_rpc_pytds*/ o.order_id, o.amount FROM dbo.orders o "
    "WHERE o.customer_id = @P1 AND o.status >= @P2 ORDER BY o.amount DESC"
)
PLAN_HANDLE = '0600050012eb2f1b60fced1f1200000001000000000000000000000000000000000000000000000000000000'
SQL_HANDLE = '0x0200000012EB2F1BB0F35DCC64332DC0EB7A17EDFDB853E60000000000000000000000000000000000000000'
CURRENT_FILE = '/var/opt/mssql/log/datadog_query_plans_0_134080000000000000.xel'


def load_event(fixture: str) -> etree._Element:
    with open(os.path.join(FIXTURES_DIR, fixture), 'rb') as f:
        return etree.fromstring(f.read()).find('event')


def make_event(
    fixture: str = PLAN_PROFILE_FIXTURE,
    timestamp: str | None = None,
    duration_us: int | None = None,
    query_plan_hash: int | None = None,
    plan_transform=None,
) -> str:
    """A fixture event as `fn_xe_file_target_read_file` returns it, with some fields replaced."""
    event = load_event(fixture)
    if timestamp:
        event.set('timestamp', timestamp)
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


def timestamp(second: int) -> str:
    return '2026-11-09T15:55:{:02d}.000Z'.format(second)


def mock_obfuscate_sql(query, options=None):
    query = re.sub(r"'[^']*'", "?", query)
    return re.sub(r"([^@\w])[0-9]+", r"\1?", query)


class FakeEventFile:
    """
    The files of an event_file target, as `fn_xe_file_target_read_file` reads them: a read from a checkpoint returns
    the events of the buffers after it, in its file and the next ones, and fails when its file is gone.
    """

    def __init__(self):
        # file name -> list of (offset, events)
        self.files: dict[str, list[tuple[int, list[str]]]] = {CURRENT_FILE: []}
        self.current_file = CURRENT_FILE

    def add_buffer(self, *events: str) -> None:
        buffers = self.files[self.current_file]
        buffers.append(((len(buffers) + 1) * 1024, list(events)))

    def start_file(self, name: str) -> None:
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

    def responses(self, sql: str, params: tuple):
        if sql == EVENT_FILE_LAST_BUFFER_QUERY:
            rows = self.rows([params[0]])
            return [(rows[-1][1], rows[-1][2])] if rows else []
        if sql == EVENT_FILE_READ_QUERY:
            top, file_name = params
            return self.rows([file_name])[:top]
        if sql == EVENT_FILE_READ_FROM_CHECKPOINT_QUERY:
            top, _pattern, file_name, offset = params
            if file_name not in self.files:
                raise Exception("The file '{}' is invalid".format(file_name))
            files = sorted(self.files)
            return self.rows(files[files.index(file_name) :], after=(file_name, offset))[:top]
        return None


class FakeServer:
    """The queries of the handler, answered from an event_file target, or the given target rows."""

    def __init__(self, targets=None, frame_text=STATEMENT, query_stats_text=STATEMENT):
        self.event_file = FakeEventFile()
        self.targets = targets
        self.ring_buffer = None
        self.frame_text = frame_text
        self.query_stats_text = query_stats_text
        self.queries: list[tuple[str, tuple]] = []

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
    'plan_transform,query_plans_config,status',
    [
        pytest.param(
            lambda plan: re.sub(
                r'<RunTimeInformation>.*?</RunTimeInformation>|<QueryTimeStats[^>]*>(</QueryTimeStats>)?', '', plan
            ),
            {},
            'no_runtime_data',
            id='no_runtime_data',
        ),
        pytest.param(None, {'max_plan_size_bytes': 1000}, 'too_large', id='too_large'),
        pytest.param(None, {}, 'collected', id='collected'),
    ],
)
def test_plans_without_runtime_data_or_too_large_are_skipped(
    aggregator, xe_instance, plan_transform, query_plans_config, status
):
    server = FakeServer()
    handler = make_handler(xe_instance, server, **query_plans_config)

    run_from_ring_buffer(handler, server, make_event(plan_transform=plan_transform))

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
    'fixture,frame_text,query_stats_text,expected_statement,expected_lookups',
    [
        pytest.param(
            PLAN_PROFILE_FIXTURE, STATEMENT, None, STATEMENT, {FRAME_STATEMENT_QUERY: 1}, id='from_tsql_frame'
        ),
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            None,
            STATEMENT,
            STATEMENT,
            {FRAME_STATEMENT_QUERY: 1, QUERY_STATS_STATEMENT_QUERY: 1},
            id='sql_handle_gone',
        ),
        pytest.param(
            SHOWPLAN_FIXTURE, None, STATEMENT, STATEMENT, {QUERY_STATS_STATEMENT_QUERY: 1}, id='no_tsql_frame'
        ),
        pytest.param(
            PLAN_PROFILE_FIXTURE,
            None,
            None,
            None,
            {FRAME_STATEMENT_QUERY: 1, QUERY_STATS_STATEMENT_QUERY: 1},
            id='statement_gone',
        ),
    ],
)
def test_statement_text(
    aggregator, xe_instance, fixture, frame_text, query_stats_text, expected_statement, expected_lookups
):
    """
    The statement comes from the tsql_frame action, else from the cached plan's statistics, and each lookup is
    cached.
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


def sent_timestamps(aggregator) -> list[str]:
    return [e['sqlserver']['event_fire_timestamp'] for e in plan_events(aggregator)]


def distinct_event(second: int) -> str:
    # a distinct plan shape per event, so the rate limit keeps them all
    return make_event(timestamp=timestamp(second), query_plan_hash=second)


@pytest.mark.unit
def test_event_file_first_run_starts_at_the_newest_buffer(aggregator, xe_instance):
    server = FakeServer()
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
        '/var/opt/mssql/log/datadog_query_plans*.xel',
        CURRENT_FILE,
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
def test_event_file_reads_complete_buffers(aggregator, xe_instance):
    """
    A read stopped by `max_events` within a buffer leaves that buffer for the next read, since a read from a buffer's
    offset starts after the buffer.
    """
    server = FakeServer()
    handler = make_handler(xe_instance, server, max_events=3)
    handler.run_job()
    server.event_file.add_buffer(distinct_event(1), distinct_event(2))
    server.event_file.add_buffer(distinct_event(3), distinct_event(4))

    handler.run_job()
    assert sent_timestamps(aggregator) == [timestamp(1), timestamp(2)]

    handler.run_job()
    assert sent_timestamps(aggregator) == [timestamp(1), timestamp(2), timestamp(3), timestamp(4)]


@pytest.mark.unit
@pytest.mark.parametrize('checkpoint_file_removed', [True, False], ids=['rollover', 'session_restart'])
def test_event_file_checkpoint_file_replaced(aggregator, xe_instance, checkpoint_file_removed):
    """
    When the checkpoint's file is gone after rollovers, or the restarted session writes a new file, the current file
    is read from its start, without sending the events read before again.
    """
    server = FakeServer()
    # no rate limit, which would also stop the events read before
    handler = make_handler(xe_instance, server, samples_per_hour_per_query=10**9)
    handler.run_job()
    server.event_file.add_buffer(distinct_event(1))
    handler.run_job()
    assert sent_timestamps(aggregator) == [timestamp(1)]

    old_file = server.event_file.current_file
    server.event_file.start_file('/var/opt/mssql/log/datadog_query_plans_0_134080000000000001.xel')
    if checkpoint_file_removed:
        del server.event_file.files[old_file]
    else:
        # nothing after the checkpoint yet, and an empty new file
        handler.run_job()
    # an event already read is in the new file too: a read from the start replays it
    server.event_file.add_buffer(distinct_event(1), distinct_event(2))
    handler.run_job()

    assert sent_timestamps(aggregator) == [timestamp(1), timestamp(2)]


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
    assert 'CREATE EVENT SESSION datadog_query_plans' in warnings[0]

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
    aggregator, dd_run_check, dbm_instance_xe_plans, bob_conn_str, collect_raw_query_statement
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
