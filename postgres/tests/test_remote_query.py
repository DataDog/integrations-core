# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from datadog_checks.postgres.remote_query import (
    StaticPostgresCheckRegistry,
    execute_agent_rpc_json,
    execute_agent_rpc_stream_copy,
    execute_remote_query,
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

    def fetchmany(self, size):
        return self.rows[:size]

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


def valid_request(host='LOCALHOST.', port=5432, dbname='datadog_test', **extra):
    request = {
        'target': {'host': host, 'port': port, 'dbname': dbname},
        'query': 'SELECT 1 AS value',
        'limits': {'maxRows': 10, 'maxBytes': 1048576, 'timeoutMs': 5000},
    }
    request.update(extra)
    return request


class ExplodingRegistry:
    def iter_postgres_checks(self):
        pytest.fail('registry must not be iterated')


def assert_failed(response, code, message_contains=None):
    assert response['status'] == 'FAILED'
    assert response['error']['code'] == code
    if message_contains is not None:
        assert message_contains in response['error']['message']


def execute_agent_rpc_response(request_json, check):
    response_json = execute_agent_rpc_json(request_json, check)

    assert isinstance(response_json, str)
    return json.loads(response_json)


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
def test_rejects_unknown_request_fields_before_resolution(caplog, field):
    request = valid_request(**{field: 'SECRET_DO_NOT_LOG'})

    response = execute_remote_query(request, ExplodingRegistry())

    assert_failed(response, 'invalid_request', field)
    assert 'SECRET_DO_NOT_LOG' not in str(response)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_rejects_unknown_target_fields_before_resolution():
    request = valid_request()
    request['target']['password'] = 'SECRET_DO_NOT_LOG'

    response = execute_remote_query(request, ExplodingRegistry())

    assert_failed(response, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(response)


def test_rejects_unknown_limits_fields_before_resolution():
    request = valid_request()
    request['limits']['password'] = 'SECRET_DO_NOT_LOG'

    response = execute_remote_query(request, ExplodingRegistry())

    assert_failed(response, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(response)


@pytest.mark.parametrize('field', ['maxRows', 'maxBytes', 'timeoutMs'])
def test_rejects_string_limit_values_before_resolution(field):
    request = valid_request()
    request['limits'][field] = '10'

    response = execute_remote_query(request, ExplodingRegistry())

    assert_failed(response, 'invalid_request', field)


@pytest.mark.parametrize(
    'request_json',
    [
        json.dumps(valid_request()),
        json.dumps(valid_request()).encode(),
        bytearray(json.dumps(valid_request()), 'utf-8'),
    ],
)
def test_agent_rpc_json_accepts_json_request_text_and_live_check(request_json):
    pool = FakePool()
    check = make_check(pool=pool)

    response = execute_agent_rpc_response(request_json, check)

    assert response['status'] == 'SUCCEEDED'
    assert response['rows'] == [{'value': 1}]
    assert pool.requested_dbnames == ['datadog_test']


@pytest.mark.parametrize('request_json', ['{"password": "SECRET_DO_NOT_LOG"', b'\xff'])
def test_agent_rpc_json_rejects_malformed_json_without_echoing_input(caplog, request_json):
    pool = FakePool()

    response = execute_agent_rpc_response(request_json, make_check(pool=pool))

    assert_failed(response, 'invalid_request', 'request_json')
    assert 'SECRET_DO_NOT_LOG' not in str(response)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    assert pool.requested_dbnames == []


@pytest.mark.parametrize('request_json', ['[]', 'null', '"SECRET_DO_NOT_LOG"', '1'])
def test_agent_rpc_json_rejects_non_object_json_without_echoing_input(request_json):
    pool = FakePool()

    response = execute_agent_rpc_response(request_json, make_check(pool=pool))

    assert_failed(response, 'invalid_request', 'JSON object')
    assert 'SECRET_DO_NOT_LOG' not in str(response)
    assert pool.requested_dbnames == []


def test_agent_rpc_json_reuses_strict_validation_for_request_shape():
    pool = FakePool()
    request = valid_request(password='SECRET_DO_NOT_LOG')

    response = execute_agent_rpc_response(json.dumps(request), make_check(pool=pool))

    assert_failed(response, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(response)
    assert pool.requested_dbnames == []


def test_agent_rpc_json_uses_only_supplied_live_check_for_target_matching():
    matching_pool = FakePool()
    non_matching_pool = FakePool()
    request_json = json.dumps(valid_request(host='configured.internal'))

    response = execute_agent_rpc_response(request_json, make_check(host='localhost', pool=non_matching_pool))

    assert_failed(response, 'target_not_found')
    assert non_matching_pool.requested_dbnames == []

    response = execute_agent_rpc_response(request_json, make_check(host='configured.internal', pool=matching_pool))

    assert response['status'] == 'SUCCEEDED'
    assert matching_pool.requested_dbnames == ['datadog_test']


def test_resolve_matches_exact_host_port_dbname_from_check_config():
    pool = FakePool()
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    response = execute_remote_query(valid_request(host='LOCALHOST.', port=5432), StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'] == [{'name': 'value', 'type': 'integer'}]
    assert response['rows'] == [{'value': 1}]
    assert pool.requested_dbnames == ['datadog_test']


def test_execute_accepts_fixture_table_query_and_serializes_result_rows():
    pool = FakePool(
        rows=[('Beautiful city of lights', 'France'), ('New York', 'USA')],
        description=[SimpleNamespace(name='city'), SimpleNamespace(name='country')],
    )
    check = make_check(pool=pool)

    response = execute_remote_query(
        valid_request(query='SELECT city, country FROM cities ORDER BY city'), StaticPostgresCheckRegistry([check])
    )

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'] == [{'name': 'city', 'type': 'string'}, {'name': 'country', 'type': 'string'}]
    assert response['rows'] == [
        {'city': 'Beautiful city of lights', 'country': 'France'},
        {'city': 'New York', 'country': 'USA'},
    ]
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 2
    assert pool.requested_dbnames == ['datadog_test']


@pytest.mark.parametrize('size', [1048576, 2097152, 4194304, 8388608, 16777216, 33554432])
def test_execute_accepts_large_payload_proof_queries_and_serializes_result_rows(size):
    pool = FakePool(rows=[('x' * size,)], description=[SimpleNamespace(name='payload')])
    check = make_check(pool=pool)

    response = execute_remote_query(
        valid_request(query=f"SELECT repeat('x', {size}) AS payload"), StaticPostgresCheckRegistry([check])
    )

    assert response['status'] == 'SUCCEEDED'
    assert response['columns'] == [{'name': 'payload', 'type': 'string'}]
    assert len(response['rows']) == 1
    assert len(response['rows'][0]['payload']) == size
    assert response['truncated'] is False
    assert response['stats']['rowCount'] == 1
    assert pool.requested_dbnames == ['datadog_test']


@pytest.mark.parametrize(
    'query',
    [
        'SELECT current_database()',
        'SELECT 1 AS value;',
        ' SELECT 1 AS value',
        'SELECT city, country FROM cities ORDER BY city;',
        'SELECT country, city FROM cities ORDER BY city',
    ],
)
def test_execute_rejects_non_canonical_query_before_pool_access(query):
    pool = FakePool()
    request = valid_request(query=query)

    response = execute_remote_query(request, StaticPostgresCheckRegistry([make_check(pool=pool)]))

    assert_failed(response, 'invalid_request', 'query')
    assert pool.requested_dbnames == []


def test_resolve_requires_dbname_match_even_when_host_and_port_match():
    pool = FakePool()
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    response = execute_remote_query(valid_request(dbname='postgres'), StaticPostgresCheckRegistry([check]))

    assert_failed(response, 'target_not_found')
    assert pool.requested_dbnames == []


def test_resolve_ignores_metadata_identity_matches():
    pool = FakePool()
    check = make_check(
        host='configured.internal',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        reported_hostname='reported.internal',
        database_identifier='reported.internal',
    )

    response = execute_remote_query(valid_request(host='reported.internal'), StaticPostgresCheckRegistry([check]))

    assert_failed(response, 'target_not_found')
    assert pool.requested_dbnames == []


def test_resolve_fails_ambiguous_duplicate_configs():
    first_pool = FakePool()
    second_pool = FakePool()
    checks = [make_check(pool=first_pool), make_check(pool=second_pool)]

    response = execute_remote_query(valid_request(), StaticPostgresCheckRegistry(checks))

    assert_failed(response, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_execute_sets_truncated_when_more_than_max_rows_returned():
    pool = FakePool(rows=[(1,), (2,)])
    check = make_check(pool=pool)
    request = valid_request()
    request['limits']['maxRows'] = 1

    response = execute_remote_query(request, StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert response['rows'] == [{'value': 1}]
    assert response['truncated'] is True
    assert response['stats']['rowCount'] == 1


def test_execute_uses_connection_pool_not_existing_query_helpers():
    pool = FakePool()
    check = block_existing_query_helpers(make_check(pool=pool))

    response = execute_remote_query(valid_request(), StaticPostgresCheckRegistry([check]))

    assert response['status'] == 'SUCCEEDED'
    assert pool.requested_dbnames == ['datadog_test']


def test_execute_closed_pool_returns_target_unavailable_without_recreating_credentials():
    pool = FakePool(closed=True)
    check = make_check(pool=pool)

    response = execute_remote_query(valid_request(), StaticPostgresCheckRegistry([check]))

    assert_failed(response, 'target_unavailable')
    assert pool.requested_dbnames == []


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


def collect_copy_events(request, check):
    return list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([check])))


def test_copy_stream_requires_explicit_operation_before_pool_access():
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request()
    request.pop('operation')

    events = collect_copy_events(request, make_check(pool=pool))

    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'invalid_request'
    assert 'operation' in events[-1]['error']['message']
    assert pool.requested_dbnames == []


def test_copy_stream_rejects_unknown_fields_without_echoing_secrets(caplog):
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request(password='SECRET_DO_NOT_LOG')

    events = collect_copy_events(request, make_check(pool=pool))

    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'invalid_request'
    assert 'password' in events[-1]['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    assert pool.requested_dbnames == []


def test_copy_stream_rejects_non_copy_allowlisted_queries_before_pool_access():
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request(query='SELECT current_database()')

    events = collect_copy_events(request, make_check(pool=pool))

    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'invalid_request'
    assert 'query' in events[-1]['error']['message']
    assert pool.requested_dbnames == []


def test_copy_stream_uses_connection_pool_and_emits_chunked_copy_bytes():
    pool = FakePool(copy_blocks=[b'abc', b'defgh', b'ijklmnop', b'qr'])
    check = block_existing_query_helpers(make_check(pool=pool))

    events = collect_copy_events(valid_copy_request(), check)

    assert events[0]['type'] == 'metadata'
    assert events[0]['operation'] == 'copy_stream'
    assert events[0]['format'] == 'csv'
    data_events = [event for event in events if event['type'] == 'data']
    assert [event['sequence'] for event in data_events] == [0, 1, 2]
    assert [event['data'] for event in data_events] == [b'abcdefgh', b'ijklmnop', b'qr']
    assert [event['bytes'] for event in data_events] == [8, 8, 2]
    assert events[-1]['type'] == 'final'
    assert events[-1]['status'] == 'SUCCEEDED'
    assert events[-1]['stats']['bytesEmitted'] == 18
    assert events[-1]['stats']['chunksEmitted'] == 3
    assert pool.requested_dbnames == ['datadog_test']
    assert pool.closed_copies == 1


def test_copy_stream_enforces_max_bytes_without_exceeding_limit():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop'])
    request = valid_copy_request(limits={'chunkBytes': 8, 'maxBytes': 10, 'maxRowBytes': 32, 'timeoutMs': 5000})

    events = collect_copy_events(request, make_check(pool=pool))

    data_events = [event for event in events if event['type'] == 'data']
    assert [event['data'] for event in data_events] == [b'abcdefgh', b'ij']
    assert sum(event['bytes'] for event in data_events) == 10
    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'max_bytes_exceeded'
    assert events[-1]['stats']['bytesEmitted'] == 10
    assert pool.closed_copies == 1


def test_copy_stream_enforces_max_row_bytes_after_copy_block_arrives():
    pool = FakePool(copy_blocks=[b'abc', b'x' * 33])

    events = collect_copy_events(valid_copy_request(), make_check(pool=pool))

    assert [event['data'] for event in events if event['type'] == 'data'] == []
    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'max_row_bytes_exceeded'
    assert 'row granularity' in events[-1]['error']['message']
    assert pool.closed_copies == 1


def test_agent_rpc_stream_copy_adapts_iterator_to_callback():
    pool = FakePool(copy_blocks=[b'1\n'])
    events = []

    execute_agent_rpc_stream_copy(json.dumps(valid_copy_request()), make_check(pool=pool), events.append)

    assert [event['type'] for event in events] == ['metadata', 'data', 'final']
    assert events[1]['data'] == b'1\n'
    assert events[-1]['status'] == 'SUCCEEDED'


def test_agent_rpc_stream_copy_rejects_malformed_json_without_echoing_input(caplog):
    pool = FakePool(copy_blocks=[b'1\n'])
    events = []

    execute_agent_rpc_stream_copy('{"password": "SECRET_DO_NOT_LOG"', make_check(pool=pool), events.append)

    assert events[-1]['status'] == 'FAILED'
    assert events[-1]['error']['code'] == 'invalid_request'
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    assert pool.requested_dbnames == []


def test_agent_rpc_stream_copy_closes_copy_when_callback_raises():
    pool = FakePool(copy_blocks=[b'12345678', b'abcdef'])
    events = []

    def emit(event):
        events.append(event)
        if event['type'] == 'data':
            raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        execute_agent_rpc_stream_copy(json.dumps(valid_copy_request()), make_check(pool=pool), emit)

    assert [event['type'] for event in events] == ['metadata', 'data']
    assert pool.closed_copies == 1
