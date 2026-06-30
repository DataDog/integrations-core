# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from datadog_checks.postgres.remote_query import (
    StaticPostgresCheckRegistry,
    execute_agent_rpc_stream_copy,
    iter_agent_rpc_stream_copy_events,
    normalize_target,
)


class FakePool:
    def __init__(self, rows=None, description=None, closed=False, copy_blocks=None):
        self.rows = rows or [(1,)]
        self.description = description or [SimpleNamespace(name='value')]
        self.closed = closed
        self.copy_blocks = copy_blocks or []
        self.requested_dbnames = []
        self.closed_copies = 0

    def is_closed(self):
        return self.closed

    @contextmanager
    def get_connection(self, dbname):
        self.requested_dbnames.append(dbname)
        yield FakeConnection(self.rows, self.description, self.copy_blocks, self)


class FakeConnection:
    def __init__(self, rows, description, copy_blocks, pool):
        self.rows = rows
        self.description = description
        self.copy_blocks = copy_blocks
        self.pool = pool

    @contextmanager
    def cursor(self):
        yield FakeCursor(self.rows, self.description, self.copy_blocks, self.pool)


class FakeCursor:
    def __init__(self, rows, description, copy_blocks, pool):
        self.rows = rows
        self.description = description
        self.copy_blocks = copy_blocks
        self.pool = pool
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return ('0',)

    def copy(self, query):
        self.executed.append((query, None))
        return FakeCopy(self.copy_blocks, self.pool)


class FakeCopy:
    def __init__(self, blocks, pool):
        self.blocks = blocks
        self.pool = pool

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.pool.closed_copies += 1

    def __iter__(self):
        return iter(self.blocks)


def make_check(host='localhost', port=5432, dbname='datadog_test', pool=None, **metadata):
    return SimpleNamespace(
        _config=SimpleNamespace(host=host, port=port, dbname=dbname, **metadata),
        db_pool=pool or FakePool(),
    )


def block_existing_query_helpers(check):
    check.execute_query_raw = pytest.fail
    check._run_query_scope = pytest.fail
    check.data_observability = SimpleNamespace(run_job=pytest.fail)
    return check


def valid_copy_request(host='LOCALHOST.', port=5432, dbname='datadog_test', **extra):
    request = {
        'operation': 'copy_stream',
        'target': {'host': host, 'port': port, 'dbname': dbname},
        'query': 'SELECT 1 AS value',
        'format': 'csv',
        'limits': {'chunkBytes': 8, 'maxBytes': 64, 'maxRowBytes': 32, 'timeoutMs': 5000},
    }
    request.update(extra)
    return request


class ExplodingRegistry:
    def iter_postgres_checks(self):
        pytest.fail('registry must not be iterated')


def collect_copy_events(request, check):
    return list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check])))


def event_metadata(event):
    return event.metadata


def event_payload(event):
    return event.payload


def assert_failed_event(events, code, message_contains=None):
    assert event_metadata(events[-1])['status'] == 'FAILED'
    assert event_metadata(events[-1])['error']['code'] == code
    if message_contains is not None:
        assert message_contains in event_metadata(events[-1])['error']['message']


def test_normalize_target_trims_lowercases_host_and_removes_one_trailing_dot():
    target = normalize_target({'host': ' Example.INTERNAL. ', 'port': 5432, 'dbname': 'postgres'})

    assert target.host == 'example.internal'
    assert target.port == 5432
    assert target.dbname == 'postgres'


def test_normalize_target_defaults_missing_port_to_5432():
    target = normalize_target({'host': 'localhost', 'dbname': 'postgres'})

    assert target.port == 5432


@pytest.mark.parametrize('port', [True, '5432', 'abc', '0', 0, -1, 65536, None])
def test_normalize_target_rejects_invalid_port_values(port):
    with pytest.raises(ValueError):
        normalize_target({'host': 'localhost', 'port': port, 'dbname': 'postgres'})


@pytest.mark.parametrize(
    'target',
    [
        {'host': '', 'port': 5432, 'dbname': 'postgres'},
        {'host': '  ', 'port': 5432, 'dbname': 'postgres'},
        {'host': 'localhost', 'port': 5432, 'dbname': ''},
        {'host': 'localhost', 'port': 5432, 'dbname': ' postgres '},
    ],
)
def test_normalize_target_rejects_empty_host_or_dbname(target):
    with pytest.raises(ValueError):
        normalize_target(target)


@pytest.mark.parametrize('field', ['extra', 'password'])
def test_copy_stream_rejects_unknown_request_fields_before_resolution(caplog, field):
    request = valid_copy_request(**{field: 'SECRET_DO_NOT_LOG'})

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', field)
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_copy_stream_rejects_unknown_target_fields_before_resolution():
    request = valid_copy_request()
    request['target']['password'] = 'SECRET_DO_NOT_LOG'

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(events)


def test_copy_stream_rejects_unknown_limits_fields_before_resolution():
    request = valid_copy_request()
    request['limits']['password'] = 'SECRET_DO_NOT_LOG'

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(events)


@pytest.mark.parametrize('field', ['chunkBytes', 'maxBytes', 'maxRowBytes', 'timeoutMs'])
def test_copy_stream_rejects_string_limit_values_before_resolution(field):
    request = valid_copy_request()
    request['limits'][field] = '10'

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', field)


def test_copy_stream_requires_explicit_operation_before_pool_access():
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request()
    request.pop('operation')

    events = collect_copy_events(request, make_check(pool=pool))

    assert_failed_event(events, 'invalid_request', 'operation')
    assert pool.requested_dbnames == []


@pytest.mark.parametrize('operation', ['query', 'execute', None])
def test_copy_stream_rejects_non_copy_operation_before_pool_access(operation):
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request(operation=operation)

    events = collect_copy_events(request, make_check(pool=pool))

    assert_failed_event(events, 'invalid_request', 'operation')
    assert pool.requested_dbnames == []


def test_copy_stream_rejects_non_copy_allowlisted_queries_before_pool_access():
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request(query='SELECT current_database()')

    events = collect_copy_events(request, make_check(pool=pool))

    assert_failed_event(events, 'invalid_request', 'query')
    assert pool.requested_dbnames == []


@pytest.mark.parametrize('size', [1048576, 2097152, 4194304, 8388608, 16777216, 33554432])
def test_copy_stream_accepts_large_payload_proof_queries(size):
    pool = FakePool(copy_blocks=[b'x' * 8])
    request = valid_copy_request(query=f"SELECT repeat('x', {size}) AS payload")

    events = collect_copy_events(request, make_check(pool=pool))

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert pool.requested_dbnames == ['datadog_test']


def test_copy_stream_resolves_exact_host_port_dbname_from_check_config():
    pool = FakePool(copy_blocks=[b'1\n'])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_copy_events(valid_copy_request(host='LOCALHOST.', port=5432), check)

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert pool.requested_dbnames == ['datadog_test']


def test_copy_stream_uses_only_supplied_live_check_for_target_matching():
    matching_pool = FakePool(copy_blocks=[b'1\n'])
    non_matching_pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request(host='configured.internal')

    events = collect_copy_events(request, make_check(host='localhost', pool=non_matching_pool))

    assert_failed_event(events, 'target_not_found')
    assert non_matching_pool.requested_dbnames == []

    events = collect_copy_events(request, make_check(host='configured.internal', pool=matching_pool))

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert matching_pool.requested_dbnames == ['datadog_test']


def test_copy_stream_requires_dbname_match_even_when_host_and_port_match():
    pool = FakePool(copy_blocks=[b'1\n'])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_copy_events(valid_copy_request(dbname='postgres'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_copy_stream_ignores_metadata_identity_matches():
    pool = FakePool(copy_blocks=[b'1\n'])
    check = make_check(
        host='configured.internal',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        reported_hostname='reported.internal',
        database_identifier='reported.internal',
    )

    events = collect_copy_events(valid_copy_request(host='reported.internal'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_copy_stream_fails_ambiguous_duplicate_configs():
    first_pool = FakePool(copy_blocks=[b'1\n'])
    second_pool = FakePool(copy_blocks=[b'1\n'])
    checks = [make_check(pool=first_pool), make_check(pool=second_pool)]

    events = list(iter_agent_rpc_stream_copy_events(valid_copy_request(), StaticPostgresCheckRegistry(checks)))

    assert_failed_event(events, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_copy_stream_uses_connection_pool_and_emits_chunked_copy_bytes():
    pool = FakePool(copy_blocks=[b'abc', b'defgh', b'ijklmnop', b'qr'])
    check = block_existing_query_helpers(make_check(pool=pool))

    events = collect_copy_events(valid_copy_request(), check)

    assert events[0].event_type == 'metadata'
    assert event_metadata(events[0])['operation'] == 'copy_stream'
    assert event_metadata(events[0])['format'] == 'csv'
    data_events = [event for event in events if event.event_type == 'data']
    assert [event_metadata(event)['sequence'] for event in data_events] == [0, 1, 2]
    assert [event_metadata(event)['offset'] for event in data_events] == [0, 8, 16]
    assert [event_payload(event) for event in data_events] == [b'abcdefgh', b'ijklmnop', b'qr']
    assert [event_metadata(event)['bytes'] for event in data_events] == [8, 8, 2]
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == 18
    assert event_metadata(events[-1])['stats']['chunksEmitted'] == 3
    assert pool.requested_dbnames == ['datadog_test']
    assert pool.closed_copies == 1


def test_copy_stream_fixture_table_query_emits_copy_bytes():
    pool = FakePool(copy_blocks=[b'Beautiful city of lights,France\n', b'New York,USA\n'])
    request = valid_copy_request(query='SELECT city, country FROM cities ORDER BY city')

    events = collect_copy_events(request, make_check(pool=pool))

    data = b''.join(event_payload(event) for event in events if event.event_type == 'data')
    assert b'Beautiful city of lights,France\n' in data
    assert b'New York,USA\n' in data
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'


def test_copy_stream_binary_format_preserves_arbitrary_bytes():
    arbitrary_bytes = b'PGCOPY\n\xff\r\n\x00\x00\xff\x80abc\n'
    pool = FakePool(copy_blocks=[arbitrary_bytes])
    request = valid_copy_request(
        query="SELECT decode('00ff80', 'hex') AS payload",
        format='binary',
        limits={'chunkBytes': 1024, 'maxBytes': 4096, 'maxRowBytes': 4096, 'timeoutMs': 5000},
    )

    events = collect_copy_events(request, make_check(pool=pool))

    data_events = [event for event in events if event.event_type == 'data']
    assert event_metadata(events[0])['format'] == 'binary'
    assert len(data_events) == 1
    assert event_payload(data_events[0]) == arbitrary_bytes
    assert isinstance(event_payload(data_events[0]), bytes)
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'


def test_copy_stream_enforces_max_bytes_without_exceeding_limit():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop'])
    request = valid_copy_request(limits={'chunkBytes': 8, 'maxBytes': 10, 'maxRowBytes': 32, 'timeoutMs': 5000})

    events = collect_copy_events(request, make_check(pool=pool))

    data_events = [event for event in events if event.event_type == 'data']
    assert [event_payload(event) for event in data_events] == [b'abcdefgh', b'ij']
    assert sum(event_metadata(event)['bytes'] for event in data_events) == 10
    assert_failed_event(events, 'max_bytes_exceeded')
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == 10
    assert pool.closed_copies == 1


def test_copy_stream_enforces_max_row_bytes_after_copy_block_arrives():
    pool = FakePool(copy_blocks=[b'abc', b'x' * 33])

    events = collect_copy_events(valid_copy_request(), make_check(pool=pool))

    assert [event_payload(event) for event in events if event.event_type == 'data'] == []
    assert_failed_event(events, 'max_row_bytes_exceeded', 'row granularity')
    assert pool.closed_copies == 1


def test_copy_stream_closed_pool_returns_target_unavailable_without_recreating_credentials():
    pool = FakePool(closed=True)

    events = collect_copy_events(valid_copy_request(), make_check(pool=pool))

    assert_failed_event(events, 'target_unavailable')
    assert pool.requested_dbnames == []


def test_agent_rpc_stream_copy_adapts_iterator_to_binary_safe_callback():
    arbitrary_bytes = b'\x00\xff\x80abc\n'
    pool = FakePool(copy_blocks=[arbitrary_bytes])
    events = []

    execute_agent_rpc_stream_copy(
        json.dumps(valid_copy_request()), make_check(pool=pool), lambda *event: events.append(event)
    )

    assert [event[0] for event in events] == ['metadata', 'data', 'final']
    assert json.loads(events[1][1])['bytes'] == len(arbitrary_bytes)
    assert events[1][2] == arbitrary_bytes
    assert isinstance(events[1][2], bytes)
    assert json.loads(events[-1][1])['status'] == 'SUCCEEDED'


@pytest.mark.parametrize('request_json', ['{"password": "SECRET_DO_NOT_LOG"', b'\xff'])
def test_agent_rpc_stream_copy_rejects_malformed_json_without_echoing_input(caplog, request_json):
    pool = FakePool(copy_blocks=[b'1\n'])
    events = []

    execute_agent_rpc_stream_copy(request_json, make_check(pool=pool), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['status'] == 'FAILED'
    assert metadata['error']['code'] == 'invalid_request'
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    assert pool.requested_dbnames == []


@pytest.mark.parametrize('request_json', ['[]', 'null', '"SECRET_DO_NOT_LOG"', '1'])
def test_agent_rpc_stream_copy_rejects_non_object_json_without_echoing_input(request_json):
    pool = FakePool(copy_blocks=[b'1\n'])
    events = []

    execute_agent_rpc_stream_copy(request_json, make_check(pool=pool), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['status'] == 'FAILED'
    assert metadata['error']['code'] == 'invalid_request'
    assert 'JSON object' in metadata['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert pool.requested_dbnames == []


def test_agent_rpc_stream_copy_closes_copy_when_callback_raises():
    pool = FakePool(copy_blocks=[b'12345678', b'abcdef'])
    events = []

    def emit(event_type, metadata_json, payload):
        events.append((event_type, metadata_json, payload))
        if event_type == 'data':
            raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        execute_agent_rpc_stream_copy(json.dumps(valid_copy_request()), make_check(pool=pool), emit)

    assert [event[0] for event in events] == ['metadata', 'data']
    assert pool.closed_copies == 1
