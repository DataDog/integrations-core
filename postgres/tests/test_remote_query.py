# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from datadog_checks.postgres import remote_query
from datadog_checks.postgres.remote_query import (
    StaticPostgresCheckRegistry,
    _execute_upload_stream,
    _intake_receipt_to_camel,
    execute_agent_rpc_stream_copy,
    iter_agent_rpc_stream_copy_events,
    normalize_target,
)


class FakePool:
    def __init__(self, rows=None, description=None, closed=False, copy_blocks=None, copy_error=None):
        self.rows = rows or [(1,)]
        self.description = description or [SimpleNamespace(name='value')]
        self.closed = closed
        self.copy_blocks = copy_blocks or []
        self.copy_error = copy_error
        self.requested_dbnames = []
        self.closed_copies = 0
        self.cursors = []

    def is_closed(self):
        return self.closed

    @contextmanager
    def get_connection(self, dbname):
        self.requested_dbnames.append(dbname)
        yield FakeConnection(self.rows, self.description, self.copy_blocks, self, self.copy_error)


class FakeConnection:
    def __init__(self, rows, description, copy_blocks, pool, copy_error=None):
        self.rows = rows
        self.description = description
        self.copy_blocks = copy_blocks
        self.copy_error = copy_error
        self.pool = pool

    @contextmanager
    def cursor(self):
        cursor = FakeCursor(self.rows, self.description, self.copy_blocks, self.pool, self.copy_error)
        self.pool.cursors.append(cursor)
        yield cursor


class FakeCursor:
    def __init__(self, rows, description, copy_blocks, pool, copy_error=None):
        self.rows = rows
        self.description = description
        self.copy_blocks = copy_blocks
        self.copy_error = copy_error
        self.pool = pool
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        pytest.fail('statement_timeout should not be read outside transaction-local settings')

    def copy(self, query):
        self.executed.append((query, None))
        return FakeCopy(self.copy_blocks, self.pool, self.copy_error)


class FakeCopy:
    def __init__(self, blocks, pool, copy_error=None):
        self.blocks = blocks
        self.pool = pool
        self.copy_error = copy_error

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.pool.closed_copies += 1

    def __iter__(self):
        if self.copy_error is not None:
            raise self.copy_error
        return iter(self.blocks)


def make_check(
    host='localhost', port=5432, dbname='datadog_test', pool=None, check_database_identifier=None, **metadata
):
    check = SimpleNamespace(
        _config=SimpleNamespace(host=host, port=port, dbname=dbname, **metadata),
        db_pool=pool or FakePool(),
    )
    if check_database_identifier is not None:
        check.database_identifier = check_database_identifier
    return check


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


def valid_database_instance_copy_request(database_instance='postgres-dbi', **extra):
    request = valid_copy_request(**extra)
    request['target'] = {'database_instance': database_instance}
    return request


def valid_result_delivery(**extra):
    result_delivery = {
        'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
        'uploadId': 'upload-01k',
        'baseUrl': 'https://dd.datad0g.com/api/unstable/its-agent-intake',
        'token': 'scoped-upload-token',
        'partBytes': 8,
        'maxBytes': 24,
        'format': 'csv',
        'compression': 'none',
    }
    result_delivery.update(extra)
    return result_delivery


def valid_upload_copy_request(**extra):
    request = valid_copy_request(**extra)
    request['resultDelivery'] = valid_result_delivery()
    return request


class FakeUploadClient:
    def __init__(self, put_status=200, finalize_resp=None, raise_on_put=None):
        self.put_calls = []
        self.finalize_calls = 0
        self.abort_calls = 0
        self.put_status = put_status
        self.raise_on_put = raise_on_put
        self.finalize_resp = finalize_resp or {
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': 0,
            'total_rows': 0,
            'part_count': 0,
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }

    def put_part(self, creds, part_number, payload, sha256_hex, rows):
        self.put_calls.append((part_number, payload, sha256_hex, rows))
        if self.raise_on_put is not None:
            raise self.raise_on_put

    def finalize(self, creds):
        self.finalize_calls += 1
        return self.finalize_resp

    def abort(self, creds):
        self.abort_calls += 1


def patch_upload_credentials(monkeypatch):
    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        return None

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)


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


def test_normalize_target_rejects_missing_port():
    with pytest.raises(ValueError):
        normalize_target({'host': 'localhost', 'dbname': 'postgres'})


def test_normalize_target_accepts_database_instance_without_normalization():
    target = normalize_target({'database_instance': 'Postgres/Primary-A'})

    assert target.database_instance == 'Postgres/Primary-A'
    assert target.host is None
    assert target.dbname is None


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


@pytest.mark.parametrize(
    'target',
    [
        {},
        {'host': 'localhost'},
        {'port': 5432},
        {'dbname': 'postgres'},
        {'host': 'localhost', 'port': 5432},
        {'host': 'localhost', 'dbname': 'postgres'},
        {'port': 5432, 'dbname': 'postgres'},
        {'host': 'localhost', 'dbname': 'postgres', 'database_instance': 'postgres-dbi'},
        {'database_instance': 'postgres-dbi', 'host': 'localhost'},
        {'database_instance': 'postgres-dbi', 'port': 5432},
        {'database_instance': 'postgres-dbi', 'dbname': 'postgres'},
        {'database_instance': 'postgres-dbi', 'host': ''},
        {'database_instance': ''},
        {'database_instance': ' postgres-dbi '},
    ],
)
def test_normalize_target_rejects_missing_partial_mixed_or_invalid_database_instance_target(target):
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


@pytest.mark.parametrize(
    'target',
    [
        {'host': 'localhost', 'dbname': 'postgres'},
        {'host': 'localhost'},
        {'port': 5432},
        {'database_instance': 'x', 'host': ''},
    ],
)
def test_copy_stream_rejects_partial_target_selectors_before_resolution(target):
    request = valid_copy_request()
    request['target'] = target

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request')


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


def test_copy_stream_accepts_non_allowlisted_query_when_allowlist_is_disabled(monkeypatch):
    def is_query_allowlist_enabled() -> bool:
        return False

    monkeypatch.setattr(remote_query, '_is_query_allowlist_enabled', is_query_allowlist_enabled)
    pool = FakePool(copy_blocks=[b'datadog_test\n'])
    request = valid_copy_request(query='SELECT current_database()')

    events = collect_copy_events(request, make_check(pool=pool))

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert pool.requested_dbnames == ['datadog_test']
    assert ('COPY (SELECT current_database()) TO STDOUT WITH (FORMAT CSV)', None) in pool.cursors[0].executed


@pytest.mark.parametrize('config_value', ['', None, True, 1, 'true', 'yes', 'on', '1', 'TRUE', ' Yes '])
def test_query_allowlist_enabled_by_default_and_affirmative_values(monkeypatch, config_value):
    requested_keys: list[str] = []

    def get_config(key: str) -> object:
        requested_keys.append(key)
        return config_value

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)

    assert remote_query._is_query_allowlist_enabled() is True
    assert requested_keys == [remote_query.REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY]


@pytest.mark.parametrize('config_value', [False, 0, 'false', 'no', 'off', '0', 'FALSE', ' No '])
def test_query_allowlist_disabled_by_explicit_negative_values(monkeypatch, config_value):
    def get_config(key: str) -> object:
        assert key == remote_query.REMOTE_QUERY_ENABLE_ALLOWLIST_CONFIG_KEY
        return config_value

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)

    assert remote_query._is_query_allowlist_enabled() is False


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


def test_copy_stream_host_port_dbname_target_still_succeeds_when_check_has_database_identifier():
    pool = FakePool(copy_blocks=[b'1\n'])
    check = make_check(
        host='localhost',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        check_database_identifier='postgres-dbi',
    )

    events = collect_copy_events(valid_copy_request(host='LOCALHOST.', port=5432), check)

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert pool.requested_dbnames == ['datadog_test']


def test_copy_stream_resolves_unique_database_instance_from_check_identifier():
    matching_pool = FakePool(copy_blocks=[b'1\n'])
    non_matching_pool = FakePool(copy_blocks=[b'1\n'])
    checks = [
        make_check(dbname='analytics', pool=matching_pool, check_database_identifier='Postgres/Primary-A'),
        make_check(dbname='postgres', pool=non_matching_pool, check_database_identifier='Postgres/Primary-B'),
    ]

    events = list(
        iter_agent_rpc_stream_copy_events(
            valid_database_instance_copy_request('Postgres/Primary-A'), StaticPostgresCheckRegistry(checks)
        )
    )

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert matching_pool.requested_dbnames == ['analytics']
    assert non_matching_pool.requested_dbnames == []


def test_copy_stream_database_instance_miss_fails_without_pool_access():
    pool = FakePool(copy_blocks=[b'1\n'])
    check = make_check(pool=pool, check_database_identifier='Postgres/Primary-A')

    events = collect_copy_events(valid_database_instance_copy_request('Postgres/Primary-B'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_copy_stream_database_instance_ambiguous_fails_without_pool_access():
    first_pool = FakePool(copy_blocks=[b'1\n'])
    second_pool = FakePool(copy_blocks=[b'1\n'])
    checks = [
        make_check(dbname='postgres_a', pool=first_pool, check_database_identifier='Postgres/Primary-A'),
        make_check(dbname='postgres_b', pool=second_pool, check_database_identifier='Postgres/Primary-A'),
    ]

    events = list(
        iter_agent_rpc_stream_copy_events(
            valid_database_instance_copy_request('Postgres/Primary-A'), StaticPostgresCheckRegistry(checks)
        )
    )

    assert_failed_event(events, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_copy_stream_default_template_database_instance_collapse_is_ambiguous():
    first_pool = FakePool(copy_blocks=[b'1\n'])
    second_pool = FakePool(copy_blocks=[b'1\n'])
    checks = [
        make_check(dbname='postgres_a', pool=first_pool, check_database_identifier='resolved-hostname'),
        make_check(dbname='postgres_b', pool=second_pool, check_database_identifier='resolved-hostname'),
    ]

    events = list(
        iter_agent_rpc_stream_copy_events(
            valid_database_instance_copy_request('resolved-hostname'), StaticPostgresCheckRegistry(checks)
        )
    )

    assert_failed_event(events, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_copy_stream_rejects_mixed_database_instance_and_host_selector_before_resolution():
    request = valid_database_instance_copy_request('postgres-dbi')
    request['target']['host'] = 'localhost'

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_copy_stream_rejects_database_instance_with_partial_host_selector_before_resolution():
    request = valid_database_instance_copy_request('postgres-dbi')
    request['target']['port'] = 5432

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_copy_stream_rejects_empty_database_instance_before_resolution():
    request = valid_database_instance_copy_request(' postgres-dbi ')

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'database_instance')


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


def test_copy_stream_host_port_dbname_target_ignores_database_instance_matches():
    pool = FakePool(copy_blocks=[b'1\n'])
    check = make_check(
        host='configured.internal',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        reported_hostname='reported.internal',
        check_database_identifier='reported.internal',
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


def test_copy_stream_starts_read_only_transaction_sets_local_timeout_and_rolls_back_on_success():
    pool = FakePool(copy_blocks=[b'1\n'])
    request = valid_copy_request(limits={'chunkBytes': 8, 'maxBytes': 64, 'maxRowBytes': 32, 'timeoutMs': 1234})

    events = collect_copy_events(request, make_check(pool=pool))

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert pool.cursors[0].executed == [
        ('BEGIN READ ONLY', None),
        ('SET LOCAL statement_timeout = %s', (1234,)),
        ('COPY (SELECT 1 AS value) TO STDOUT WITH (FORMAT CSV)', None),
        ('ROLLBACK', None),
    ]


def test_copy_stream_rolls_back_read_only_transaction_on_failure():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop'])
    request = valid_copy_request(limits={'chunkBytes': 8, 'maxBytes': 10, 'maxRowBytes': 32, 'timeoutMs': 5000})

    events = collect_copy_events(request, make_check(pool=pool))

    assert_failed_event(events, 'max_bytes_exceeded')
    assert pool.cursors[0].executed[-1] == ('ROLLBACK', None)


def test_copy_stream_rolls_back_read_only_transaction_when_callback_raises():
    pool = FakePool(copy_blocks=[b'12345678', b'abcdef'])
    events = []

    def emit(event_type, metadata_json, payload):
        events.append((event_type, metadata_json, payload))
        if event_type == 'data':
            raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        execute_agent_rpc_stream_copy(json.dumps(valid_copy_request()), make_check(pool=pool), emit)

    assert pool.cursors[0].executed[-1] == ('ROLLBACK', None)


def test_copy_stream_fixture_table_query_emits_copy_bytes():
    pool = FakePool(copy_blocks=[b'Beautiful city of lights,France\n', b'New York,USA\n'])
    request = valid_copy_request(query='SELECT city, country FROM cities ORDER BY city')

    events = collect_copy_events(request, make_check(pool=pool))

    data = b''.join(event_payload(event) for event in events if event.event_type == 'data')
    assert b'Beautiful city of lights,France\n' in data
    assert b'New York,USA\n' in data
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'


def test_copy_stream_remote_query_identity_query_emits_copy_bytes():
    pool = FakePool(
        copy_blocks=[b'postgres_a1_db1,rq-proof-agent-a,localhost,15432,postgres_a1_db1,rq-proof-agent-a\n']
    )
    request = valid_copy_request(
        query=(
            'SELECT current_database() AS current_db, expected_agent_hostname, expected_postgres_host, '
            'expected_postgres_port, expected_dbname, marker FROM remote_query_identity'
        ),
        limits={'chunkBytes': 1024, 'maxBytes': 4096, 'maxRowBytes': 4096, 'timeoutMs': 5000},
    )

    events = collect_copy_events(request, make_check(pool=pool))

    data = b''.join(event_payload(event) for event in events if event.event_type == 'data')
    assert b'postgres_a1_db1,rq-proof-agent-a,localhost,15432,postgres_a1_db1,rq-proof-agent-a\n' in data
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
    assert pool.cursors[0].executed[-1] == ('ROLLBACK', None)


def test_copy_stream_upload_mode_emits_started_result_delivery_data_sha256_and_receipt():
    pool = FakePool(copy_blocks=[b'abc', b'defgh', b'ijklmnop', b'qr'])
    check = block_existing_query_helpers(make_check(pool=pool))
    request = valid_upload_copy_request()

    events = collect_copy_events(request, check)

    assert events[0].event_type == 'metadata'
    started = event_metadata(events[0])
    assert started['status'] == 'STARTED'
    assert started['resultDelivery']['mode'] == 'POC_PUBLIC_MULTIPART_UPLOAD'
    assert started['resultDelivery']['uploadId'] == 'upload-01k'
    assert started['resultDelivery']['partBytes'] == 8
    assert started['resultDelivery']['maxBytes'] == 24
    assert 'baseUrl' not in started['resultDelivery']
    assert 'token' not in started['resultDelivery']
    assert started['chunkBytes'] == 8
    assert started['maxBytes'] == 24
    assert started['maxRowBytes'] == 32

    data_events = [event for event in events if event.event_type == 'data']
    assert [event_metadata(event)['sequence'] for event in data_events] == [0, 1, 2]
    assert [event_metadata(event)['bytes'] for event in data_events] == [8, 8, 2]
    for event in data_events:
        payload = event_payload(event)
        assert event_metadata(event)['sha256'] == hashlib.sha256(payload).hexdigest()
        assert len(payload) <= 8
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['uploadReceipt'] == {
        'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
        'uploadId': 'upload-01k',
        'totalBytes': 18,
        'partCount': 3,
    }
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == 18
    assert event_metadata(events[-1])['stats']['chunksEmitted'] == 3
    assert pool.closed_copies == 1


def test_copy_stream_omitted_result_delivery_keeps_inline_streaming_behavior():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])
    request = valid_copy_request()

    events = collect_copy_events(request, make_check(pool=pool))

    assert 'resultDelivery' not in event_metadata(events[0])
    data_events = [event for event in events if event.event_type == 'data']
    for event in data_events:
        assert 'sha256' not in event_metadata(event)
    assert 'uploadReceipt' not in event_metadata(events[-1])
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'


def test_copy_stream_upload_mode_enforces_result_delivery_max_bytes():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop'])
    request = valid_upload_copy_request()
    request['resultDelivery']['maxBytes'] = 10

    events = collect_copy_events(request, make_check(pool=pool))

    data_events = [event for event in events if event.event_type == 'data']
    assert [event_payload(event) for event in data_events] == [b'abcdefgh', b'ij']
    assert sum(event_metadata(event)['bytes'] for event in data_events) == 10
    assert_failed_event(events, 'max_bytes_exceeded')
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == 10
    assert 'uploadReceipt' not in event_metadata(events[-1])
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_enforces_timeout(monkeypatch):
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop'])
    request = valid_upload_copy_request()
    request['limits']['timeoutMs'] = 1000
    values = iter([0.0, 0.0, 0.0] + [10.0] * 50)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: next(values))

    events = collect_copy_events(request, make_check(pool=pool))

    data_events = [event for event in events if event.event_type == 'data']
    assert [event_payload(event) for event in data_events] == [b'abcdefgh']
    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert 'uploadReceipt' not in event_metadata(events[-1])
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_rejects_binary_format_mismatch_with_result_delivery():
    arbitrary_bytes = b'PGCOPY\n\xff\r\n\x00\x00\xff\x80abc\n'
    pool = FakePool(copy_blocks=[arbitrary_bytes])
    request = valid_upload_copy_request()
    request['format'] = 'binary'
    request['query'] = "SELECT decode('00ff80', 'hex') AS payload"
    request['resultDelivery']['partBytes'] = 1024
    request['resultDelivery']['maxBytes'] = 4096
    request['limits'] = {'chunkBytes': 1024, 'maxBytes': 4096, 'maxRowBytes': 4096, 'timeoutMs': 5000}

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'format must match resultDelivery.format')
    assert pool.requested_dbnames == []


def test_copy_stream_upload_mode_accepts_csv_format_matching_result_delivery():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])
    request = valid_upload_copy_request()
    request['format'] = 'csv'
    request['resultDelivery']['format'] = 'csv'

    events = collect_copy_events(request, make_check(pool=pool))

    assert event_metadata(events[0])['format'] == 'csv'
    assert event_metadata(events[0])['resultDelivery']['format'] == 'csv'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'


def test_copy_stream_upload_mode_never_buffers_more_than_one_chunk(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(copy_blocks=[b'aaaa', b'bbbb', b'cccc', b'dddd', b'eeee', b'ffff'])
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = 4
    request['resultDelivery']['maxBytes'] = 28
    request['limits'] = {'chunkBytes': 4, 'maxBytes': 28, 'maxRowBytes': 32, 'timeoutMs': 5000}
    fake = FakeUploadClient()
    events = []

    _execute_upload_stream(request, make_check(pool=pool), lambda *event: events.append(event), http_client=fake)

    # Bulk data goes directly to the intake via HTTP, not through the emit callback.
    assert [event[0] for event in events] == ['metadata', 'final']
    assert all(len(call[1]) <= 4 for call in fake.put_calls)
    assert sum(len(call[1]) for call in fake.put_calls) == 24
    assert len(fake.put_calls) == 6
    assert fake.finalize_calls == 1


def test_copy_stream_upload_mode_emits_stable_sequence_and_sha256_for_idempotent_retry():
    blocks = [b'abcdefgh', b'ijklmnop', b'qr']
    request = valid_upload_copy_request()
    events = collect_copy_events(request, make_check(pool=FakePool(copy_blocks=blocks)))
    data_events = [event for event in events if event.event_type == 'data']
    sequences = [event_metadata(event)['sequence'] for event in data_events]
    assert sequences == list(range(len(data_events)))
    checksums = [event_metadata(event)['sha256'] for event in data_events]

    replayed = collect_copy_events(request, make_check(pool=FakePool(copy_blocks=blocks)))
    replayed_data = [event for event in replayed if event.event_type == 'data']
    assert [event_metadata(event)['sequence'] for event in replayed_data] == sequences
    assert [event_metadata(event)['sha256'] for event in replayed_data] == checksums


def test_copy_stream_upload_mode_emits_query_failed_and_no_receipt_on_copy_failure():
    pool = FakePool(copy_blocks=[], copy_error=Exception('copy stream broke'))
    request = valid_upload_copy_request()

    events = collect_copy_events(request, make_check(pool=pool))

    assert_failed_event(events, 'query_failed')
    assert 'uploadReceipt' not in event_metadata(events[-1])
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_accepts_baseurl_and_token():
    pool = FakePool(copy_blocks=[b'abcdefgh'])
    request = valid_upload_copy_request()
    request['resultDelivery']['baseUrl'] = 'https://dd.datad0g.com/api/unstable/its-agent-intake'
    request['resultDelivery']['token'] = 'scoped-upload-token'

    events = collect_copy_events(request, make_check(pool=pool))

    # baseUrl/token are accepted model fields now; the request proceeds to pool access
    # and the STARTED metadata does not echo them back.
    assert event_metadata(events[0])['status'] == 'STARTED'
    assert 'baseUrl' not in event_metadata(events[0])['resultDelivery']
    assert 'token' not in event_metadata(events[0])['resultDelivery']
    assert pool.requested_dbnames != []


def test_agent_rpc_stream_copy_upload_mode_uploads_parts_directly(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])
    # The intake computes the aggregate sha256 over the finalized object (the concatenated part
    # bodies); in debug/readback-on mode it returns a valid 64-char hex digest that is forwarded.
    aggregate_sha256 = hashlib.sha256(b'abcdefghijklmnopqr').hexdigest()
    fake = FakeUploadClient(
        finalize_resp={
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': 18,
            'total_rows': 0,
            'part_count': 3,
            'sha256': aggregate_sha256,
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }
    )
    events = []

    _execute_upload_stream(
        valid_upload_copy_request(), make_check(pool=pool), lambda *event: events.append(event), http_client=fake
    )

    # Only metadata and final reach the emit callback; bulk data goes directly via HTTP.
    assert [event[0] for event in events] == ['metadata', 'final']
    started = json.loads(events[0][1])
    assert started['status'] == 'STARTED'
    assert 'baseUrl' not in started['resultDelivery']
    assert 'token' not in started['resultDelivery']

    # Three parts uploaded directly with contiguous 1-based part numbers, each carrying its
    # sha256 and byte count.
    assert len(fake.put_calls) == 3
    assert [call[0] for call in fake.put_calls] == [1, 2, 3]
    for _part_number, payload, sha256_hex, _rows in fake.put_calls:
        assert sha256_hex == hashlib.sha256(payload).hexdigest()
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 0

    # The final receipt is the Agent-shaped camelCase receipt carried under the
    # server-expected snake_case outer key.
    receipt = json.loads(events[-1][1])['upload_receipt']
    assert receipt == {
        'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
        'uploadId': 'upload-01k',
        'bucketName': 'rq-bucket',
        'objectPath': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        'totalBytes': 18,
        'totalRows': 0,
        'partCount': 3,
        'sha256': aggregate_sha256,
    }


def test_copy_stream_upload_mode_stops_on_http_failure_and_aborts(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qrstuvwx'])
    fake = FakeUploadClient(
        raise_on_put=remote_query._CopyStreamFailure('upload_failed', 'transient exhausted', retryable=True)
    )
    events = []

    _execute_upload_stream(
        valid_upload_copy_request(), make_check(pool=pool), lambda *event: events.append(event), http_client=fake
    )

    # The first chunk upload fails; an error event is emitted and the session is aborted.
    assert len(fake.put_calls) == 1
    assert fake.abort_calls == 1
    assert events[-1][0] == 'error'
    assert json.loads(events[-1][1])['error']['code'] == 'upload_failed'
    assert pool.closed_copies == 1
    assert pool.cursors[0].executed[-1] == ('ROLLBACK', None)


@pytest.mark.parametrize(
    'mutation, expected',
    [
        ({'apiKey': 'SECRET_API_KEY'}, 'apiKey'),
        ({'baseUrl': ''}, 'baseUrl'),
        ({'token': ''}, 'token'),
        ({'mode': 'PRESIGNED_URL'}, 'mode'),
        ({'format': 'json'}, 'format'),
        ({'compression': 'gzip'}, 'compression'),
        ({'partBytes': 0}, 'partBytes'),
        ({'maxBytes': 0}, 'maxBytes'),
        ({'partBytes': '8'}, 'partBytes'),
        ({'partBytes': 64, 'maxBytes': 32}, 'partBytes must not exceed maxBytes'),
    ],
)
def test_copy_stream_upload_mode_rejects_invalid_result_delivery(mutation, expected):
    request = valid_upload_copy_request()
    request['resultDelivery'].update(mutation)
    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))
    assert_failed_event(events, 'invalid_request', expected)
    assert 'SECRET_API_KEY' not in str(events)
    assert 'scoped-upload-token' not in str(events)


def test_copy_stream_upload_mode_rejects_missing_upload_id():
    request = valid_upload_copy_request()
    del request['resultDelivery']['uploadId']
    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))
    assert_failed_event(events, 'invalid_request', 'uploadId')


@pytest.mark.parametrize(
    'delivery, limits, expected',
    [
        (
            {'maxBytes': 128},
            {'chunkBytes': 8, 'maxBytes': 64},
            'resultDelivery.maxBytes must not exceed limits.maxBytes',
        ),
    ],
)
def test_copy_stream_upload_mode_rejects_upload_cap_widening(delivery, limits, expected):
    request = valid_upload_copy_request()
    request['resultDelivery'].update(delivery)
    request['limits'].update(limits)
    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))
    assert_failed_event(events, 'invalid_request', expected)


def test_copy_stream_upload_mode_part_bytes_may_exceed_copy_chunk_bytes():
    # partBytes (the multipart part size) and limits.chunkBytes (the COPY streaming chunk size)
    # are distinct concepts: partBytes may exceed chunkBytes. The request validates without
    # widening the COPY maxBytes cap and the stream proceeds to SUCCEEDED.
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])  # 18 bytes
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = 16
    request['resultDelivery']['maxBytes'] = 64
    request['limits'] = {'chunkBytes': 8, 'maxBytes': 64, 'maxRowBytes': 32, 'timeoutMs': 5000}

    events = collect_copy_events(request, make_check(pool=pool))

    started = event_metadata(events[0])
    assert started['status'] == 'STARTED'
    assert started['chunkBytes'] == 8  # COPY streaming chunk size
    assert started['resultDelivery']['partBytes'] == 16  # multipart part size, exceeds chunkBytes
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    # The COPY stream emits 3 chunkBytes-sized chunks, but the upload aggregates them into
    # ceil(18/16) = 2 parts: the provisional receipt reports the part count, not the chunk count.
    assert event_metadata(events[-1])['stats']['chunksEmitted'] == 3
    assert event_metadata(events[-1])['uploadReceipt']['partCount'] == 2


def test_copy_stream_upload_mode_accepts_equal_upload_caps():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = 8
    request['resultDelivery']['maxBytes'] = 64
    request['limits'] = {'chunkBytes': 8, 'maxBytes': 64, 'maxRowBytes': 32, 'timeoutMs': 5000}

    events = collect_copy_events(request, make_check(pool=pool))

    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert event_metadata(events[-1])['uploadReceipt']['totalBytes'] == 18


def test_copy_stream_upload_mode_enforces_smaller_upload_cap_over_wider_limit():
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qrstuvwx'])
    request = valid_upload_copy_request()
    request['resultDelivery']['maxBytes'] = 16
    request['limits'] = {'chunkBytes': 8, 'maxBytes': 64, 'maxRowBytes': 32, 'timeoutMs': 5000}

    events = collect_copy_events(request, make_check(pool=pool))

    data_events = [event for event in events if event.event_type == 'data']
    assert sum(event_metadata(event)['bytes'] for event in data_events) == 16
    assert_failed_event(events, 'max_bytes_exceeded')
    assert event_metadata(events[-1])['stats']['bytesEmitted'] == 16


# ---------------------------------------------------------------------------
# M3/M4 deterministic direct-HTTP upload proof (test-only tooling)
#
# These tests drive the real Postgres direct-HTTP upload path
# (``_execute_upload_stream``) in optional ``resultDelivery`` upload mode with
# the allowlisted 8 MiB and 32 MiB proof queries. The COPY byte stream is
# generated incrementally (1 MiB blocks) so no multi-MiB static fixture or full
# duplicate payload is ever materialized: the bridge pulls one block at a time,
# matching real psycopg COPY row/block streaming.
#
# Real Postgres appends a CSV row terminator (``\n``) to a single-column text
# row, so ``repeat('x', 8388608)`` would emit 8388609 bytes and miss the exact
# 8 MiB boundary. To hit exactly 8 MiB (8388608) and 32 MiB (33554432), the
# fake COPY stream below yields a deterministic RAW byte stream of exactly
# those byte counts (the CSV ``\n`` terminator is elided); this is documented
# here and asserted by the total-bytes assertions.
#
# Unlike the prior emit-bridge proof, bulk part bytes go directly to
# its-agent-intake over HTTP via an injectable ``_UploadClient`` (a fake here),
# NOT through the native emit callback. Only metadata/final/error events cross
# the callback. This proves the integration owns the upload and the Agent is
# out of the data path.
# ---------------------------------------------------------------------------

PROOF_MIB = 1024 * 1024
M3_PROOF_QUERY = "SELECT repeat('x', 8388608) AS payload"  # 8 MiB allowlisted proof query
M4_PROOF_QUERY = "SELECT repeat('x', 33554432) AS payload"  # 32 MiB allowlisted proof query


def incremental_copy_blocks(total_bytes, block_size=PROOF_MIB):
    """Yield ``block_size`` blocks of ``b'x'`` until ``total_bytes`` are produced.

    Blocks are generated on demand (a generator, not a static list) so the full
    payload is never materialized as a single fixture; the consumer pulls one
    block at a time, matching real psycopg COPY row/block streaming.
    """
    if total_bytes % block_size != 0:
        raise ValueError('total_bytes must be a multiple of block_size for an exact raw byte count')
    for _ in range(total_bytes // block_size):
        yield b'x' * block_size


def incremental_reference_sha256(total_bytes, block_size=PROOF_MIB):
    """Compute the reference SHA-256 of the raw byte stream one block at a time."""
    hasher = hashlib.sha256()
    for _ in range(total_bytes // block_size):
        hasher.update(b'x' * block_size)
    return hasher.hexdigest()


def mib_upload_request(
    query, total_bytes, part_bytes=PROOF_MIB, upload_max_bytes=None, copy_max_bytes=None, copy_chunk_bytes=None
):
    """Build a valid ``resultDelivery`` multipart upload request sized for MiB-scale proof."""
    upload_cap = upload_max_bytes if upload_max_bytes is not None else total_bytes
    copy_cap = copy_max_bytes if copy_max_bytes is not None else total_bytes
    # The COPY read chunk size is independent of the multipart part size; default it to the part
    # size to preserve prior proof behavior, but allow a smaller chunk to prove aggregation.
    chunk_bytes = copy_chunk_bytes if copy_chunk_bytes is not None else part_bytes
    request = valid_upload_copy_request()
    request['query'] = query
    request['format'] = 'csv'
    request['resultDelivery']['format'] = 'csv'
    request['resultDelivery']['partBytes'] = part_bytes
    request['resultDelivery']['maxBytes'] = upload_cap
    request['limits'] = {
        'chunkBytes': chunk_bytes,
        'maxBytes': copy_cap,
        'maxRowBytes': PROOF_MIB,
        'timeoutMs': 30000,
    }
    return request


def run_direct_upload_stream(request, pool, fake, monkeypatch=None):
    """Drive the real direct-HTTP upload path and collect proof metrics.

    Bulk part bytes are hashed and discarded as the fake intake accepts them, so the
    full multi-MiB payload is never accumulated in memory. Returns the STARTED/FINAL
    metadata emitted on the callback, plus the fake intake's recorded put/finalize/abort
    calls, the total uploaded bytes, part count, max part size, and the incremental
    SHA-256 of the uploaded part bodies.
    """
    if monkeypatch is not None:
        patch_upload_credentials(monkeypatch)
    started = final = None
    hasher = hashlib.sha256()
    total_bytes = 0

    def emit(event_type, metadata_json, payload):
        nonlocal started, final, total_bytes
        if event_type == 'metadata':
            started = json.loads(metadata_json)
        elif event_type in ('final', 'error'):
            final = json.loads(metadata_json)

    _execute_upload_stream(request, make_check(pool=pool), emit, http_client=fake)

    for _part_number, payload, _sha256_hex, _rows in fake.put_calls:
        hasher.update(payload)
        total_bytes += len(payload)

    return SimpleNamespace(
        started=started,
        final=final,
        put_calls=fake.put_calls,
        finalize_calls=fake.finalize_calls,
        abort_calls=fake.abort_calls,
        total_bytes=total_bytes,
        part_count=len(fake.put_calls),
        max_part=max((len(c[1]) for c in fake.put_calls), default=0),
        digest=hasher.hexdigest(),
    )


@pytest.mark.parametrize(
    'total_mib, query',
    [
        (8, M3_PROOF_QUERY),
        (32, M4_PROOF_QUERY),
    ],
)
def test_copy_stream_upload_mode_uploads_exact_mib_directly_to_intake(total_mib, query, monkeypatch):
    total_bytes = total_mib * PROOF_MIB
    request = mib_upload_request(query, total_bytes)
    pool = FakePool(copy_blocks=incremental_copy_blocks(total_bytes))
    fake = FakeUploadClient(
        finalize_resp={
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': total_bytes,
            'total_rows': 0,
            'part_count': total_bytes // PROOF_MIB,
            'sha256': incremental_reference_sha256(total_bytes),
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }
    )

    proof = run_direct_upload_stream(request, pool, fake, monkeypatch)

    # Bulk bytes go directly to the intake over HTTP, not through the emit callback.
    assert proof.part_count == total_bytes // PROOF_MIB
    assert proof.total_bytes == total_bytes
    assert proof.max_part == PROOF_MIB
    # Each uploaded part carries its per-part SHA-256 over the raw body.
    for _part_number, payload, _sha256_hex, _rows in proof.put_calls:
        assert _sha256_hex == hashlib.sha256(payload).hexdigest()
        assert len(payload) == PROOF_MIB
    # The aggregate SHA-256 of uploaded part bodies matches the incremental reference.
    assert proof.digest == incremental_reference_sha256(total_bytes)
    # Finalize is called exactly once; no abort on the happy path.
    assert proof.finalize_calls == 1
    assert proof.abort_calls == 0

    # Only metadata and final reach the emit callback; no bulk data events cross it.
    assert proof.started['status'] == 'STARTED'
    assert proof.started['resultDelivery']['mode'] == 'POC_PUBLIC_MULTIPART_UPLOAD'
    assert proof.started['resultDelivery']['uploadId'] == 'upload-01k'
    assert 'baseUrl' not in proof.started['resultDelivery']
    assert 'token' not in proof.started['resultDelivery']
    assert proof.final['status'] == 'SUCCEEDED'
    # The final receipt is the Agent-shaped camelCase receipt under the snake_case outer key.
    assert proof.final['upload_receipt']['uploadId'] == 'upload-01k'
    assert proof.final['upload_receipt']['totalBytes'] == total_bytes
    assert proof.final['upload_receipt']['partCount'] == total_bytes // PROOF_MIB
    assert proof.final['upload_receipt']['sha256'] == incremental_reference_sha256(total_bytes)
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_backpressure_fences_copy_reads_during_http_upload(monkeypatch):
    total_bytes = 8 * PROOF_MIB
    total_blocks = total_bytes // PROOF_MIB
    read_state = {'count': 0}

    def counting_block_stream():
        for _ in range(total_blocks):
            read_state['count'] += 1
            yield b'x' * PROOF_MIB

    request = mib_upload_request(M3_PROOF_QUERY, total_bytes)
    pool = FakePool(copy_blocks=counting_block_stream())
    # Record how many COPY blocks have been read at the moment each part is uploaded.
    reads_at_put = []

    class LockstepFakeClient(FakeUploadClient):
        def put_part(self, creds, part_number, payload, sha256_hex, rows):
            reads_at_put.append(read_state['count'])
            super().put_part(creds, part_number, payload, sha256_hex, rows)

    fake = LockstepFakeClient(
        finalize_resp={
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': total_bytes,
            'total_rows': 0,
            'part_count': total_blocks,
            'sha256': incremental_reference_sha256(total_bytes),
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }
    )

    proof = run_direct_upload_stream(request, pool, fake, monkeypatch)

    # Lockstep backpressure: when part i is uploaded, exactly i blocks have been read and
    # block i+1 is fenced (not yet read). The full 8 MiB is never buffered ahead of the
    # HTTP upload.
    assert reads_at_put == list(range(1, total_blocks + 1))
    assert read_state['count'] == total_blocks
    assert proof.part_count == total_blocks
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_aborts_on_http_failure_at_mib_scale(monkeypatch):
    total_bytes = 8 * PROOF_MIB
    request = mib_upload_request(M3_PROOF_QUERY, total_bytes)
    pool = FakePool(copy_blocks=incremental_copy_blocks(total_bytes))
    fake = FakeUploadClient(
        raise_on_put=remote_query._CopyStreamFailure('upload_failed', 'transient exhausted', retryable=True)
    )

    proof = run_direct_upload_stream(request, pool, fake, monkeypatch)

    # The first part upload fails; the session is aborted and an error event is emitted.
    assert len(proof.put_calls) == 1
    assert proof.abort_calls == 1
    assert proof.final['status'] == 'FAILED'
    assert proof.final['error']['code'] == 'upload_failed'
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_enforces_max_bytes_at_mib_scale(monkeypatch):
    total_bytes = 8 * PROOF_MIB
    upload_cap = 4 * PROOF_MIB
    # The copy limit is wider than the upload cap; the tighter upload cap must win.
    request = mib_upload_request(M3_PROOF_QUERY, total_bytes, upload_max_bytes=upload_cap, copy_max_bytes=total_bytes)
    pool = FakePool(copy_blocks=incremental_copy_blocks(total_bytes))
    fake = FakeUploadClient()

    proof = run_direct_upload_stream(request, pool, fake, monkeypatch)

    # maxBytes enforced: exactly the upload cap is uploaded, then the stream fails.
    assert proof.total_bytes == upload_cap
    assert proof.part_count == upload_cap // PROOF_MIB
    assert proof.max_part == PROOF_MIB
    assert proof.final['status'] == 'FAILED'
    assert proof.final['error']['code'] == 'max_bytes_exceeded'
    # No receipt is emitted when the upload cap is exceeded.
    assert 'upload_receipt' not in proof.final
    assert pool.closed_copies == 1


# ---------------------------------------------------------------------------
# Multipart HTTP contract, retry, sizing, and empty-result behavior
#
# These tests pin the exact POC_PUBLIC_MULTIPART_UPLOAD data-plane contract
# (routes, 1-based part numbers, X-DD-Part-* headers) against the real
# ``_RequestsUploadClient`` by stubbing ``requests.request``, plus the
# integration-level multipart sizing and zero-row finalization behavior.
# ---------------------------------------------------------------------------


def _upload_creds(**overrides):
    defaults = {
        'base_url': 'https://dd.datad0g.com/api/unstable/its-agent-intake',
        'upload_id': 'upload-01k',
        'api_key': 'TEST_API_KEY',
        'app_key': 'TEST_APP_KEY',
        'token': 'scoped-upload-token',
        'test_drive_selector': 'its-agent-intake-poc',
    }
    defaults.update(overrides)
    return remote_query._UploadCredentials(**defaults)


def test_requests_upload_client_uses_exact_multipart_http_contract(monkeypatch):
    import requests

    captured = []

    def fake_request(method, url, headers=None, data=None, timeout=None):
        captured.append(
            SimpleNamespace(method=method, url=url, headers=dict(headers or {}), data=data, timeout=timeout)
        )
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', fake_request)
    monkeypatch.setattr(remote_query.time, 'sleep', lambda _seconds: None)

    creds = _upload_creds()
    client = remote_query._RequestsUploadClient()
    payload = b'abcdefgh'
    client.put_part(creds, 2, payload, hashlib.sha256(payload).hexdigest(), 1)

    # PUT to the 1-based part route with the exact multipart headers and auth.
    put = captured[0]
    assert put.method == 'PUT'
    assert put.url == 'https://dd.datad0g.com/api/unstable/its-agent-intake/uploads/upload-01k/parts/2'
    assert put.headers['Content-Type'] == 'application/octet-stream'
    assert put.headers['X-DD-Part-SHA256'] == hashlib.sha256(payload).hexdigest()
    assert put.headers['X-DD-Part-Bytes'] == '8'
    assert put.headers['X-DD-Part-Rows'] == '1'
    assert put.headers['dd-api-key'] == 'TEST_API_KEY'
    assert put.headers['dd-application-key'] == 'TEST_APP_KEY'
    assert put.headers['Authorization'] == 'Bearer scoped-upload-token'
    assert put.headers[remote_query.REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER] == 'its-agent-intake-poc'
    assert put.data == payload
    # The HTTP timeout is an explicit (connect, read) tuple with a 5-minute read timeout.
    assert put.timeout == remote_query.REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT
    assert put.timeout == (
        remote_query.REMOTE_QUERY_UPLOAD_HTTP_CONNECT_TIMEOUT_SECONDS,
        remote_query.REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS,
    )
    assert remote_query.REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS == 300

    # finalize -> POST .../finalize with an empty JSON body.
    client.finalize(creds)
    finalize = captured[1]
    assert finalize.method == 'POST'
    assert finalize.url == 'https://dd.datad0g.com/api/unstable/its-agent-intake/uploads/upload-01k/finalize'
    assert finalize.headers['Content-Type'] == 'application/json'
    assert finalize.data == b'{}'

    # abort -> POST .../abort with an empty JSON body (best-effort).
    client.abort(creds)
    abort = captured[2]
    assert abort.method == 'POST'
    assert abort.url == 'https://dd.datad0g.com/api/unstable/its-agent-intake/uploads/upload-01k/abort'
    assert abort.data == b'{}'


@pytest.mark.parametrize('trigger', ['transient_status', 'connection_error'])
def test_requests_upload_client_retries_part_idempotently(monkeypatch, trigger):
    import requests

    calls = []

    def fake_request(method, url, headers=None, data=None, timeout=None):
        calls.append(SimpleNamespace(url=url, headers=dict(headers or {}), data=data))
        if len(calls) == 1 and trigger == 'transient_status':
            return SimpleNamespace(status_code=503, content=b'')
        if len(calls) == 1 and trigger == 'connection_error':
            raise requests.exceptions.RequestException('boom')
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', fake_request)
    monkeypatch.setattr(remote_query.time, 'sleep', lambda _seconds: None)

    creds = _upload_creds(test_drive_selector=None)
    client = remote_query._RequestsUploadClient()
    payload = b'ijklmnop'
    client.put_part(creds, 1, payload, hashlib.sha256(payload).hexdigest(), 0)

    # The same part request (same 1-based part URL, same checksum header, same body) is
    # retried verbatim after a transient failure, so a server-side idempotent replay by
    # (part_number, sha256) cannot double-count bytes.
    assert len(calls) == 2
    assert calls[0].url == calls[1].url
    assert calls[0].url == 'https://dd.datad0g.com/api/unstable/its-agent-intake/uploads/upload-01k/parts/1'
    assert calls[0].headers['X-DD-Part-SHA256'] == calls[1].headers['X-DD-Part-SHA256']
    assert calls[0].data == calls[1].data == payload


def test_requests_upload_client_fails_closed_on_non_transient_status(monkeypatch):
    import requests

    calls = []

    def fake_request(method, url, headers=None, data=None, timeout=None):
        calls.append(url)
        return SimpleNamespace(status_code=400, content=b'')

    monkeypatch.setattr(requests, 'request', fake_request)
    monkeypatch.setattr(remote_query.time, 'sleep', lambda _seconds: None)

    creds = _upload_creds(test_drive_selector=None)
    client = remote_query._RequestsUploadClient()

    with pytest.raises(remote_query._CopyStreamFailure) as excinfo:
        client.put_part(creds, 1, b'x', 'deadbeef', 0)
    assert excinfo.value.code == 'upload_failed'
    assert excinfo.value.retryable is False
    # A non-transient rejection is not retried.
    assert len(calls) == 1


def test_copy_stream_upload_mode_sizes_multipart_parts_with_final_short_part(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # 20 bytes total with 8-byte parts -> two full parts and one final short part.
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'mnop'])
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = 8
    request['resultDelivery']['maxBytes'] = 24
    request['limits'] = {'chunkBytes': 8, 'maxBytes': 24, 'maxRowBytes': 32, 'timeoutMs': 5000}
    fake = FakeUploadClient()

    _execute_upload_stream(request, make_check(pool=pool), lambda *event: None, http_client=fake)

    # Contiguous 1-based part numbers; non-final parts are exactly partBytes and the
    # final part is allowed to be shorter.
    assert [call[0] for call in fake.put_calls] == [1, 2, 3]
    assert [len(call[1]) for call in fake.put_calls] == [8, 8, 4]
    assert sum(len(call[1]) for call in fake.put_calls) == 20
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 0
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_finalizes_empty_result_with_zero_parts(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(copy_blocks=[])
    request = valid_upload_copy_request()
    fake = FakeUploadClient(
        finalize_resp={
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': 0,
            'total_rows': 0,
            'part_count': 0,
            'sha256': hashlib.sha256(b'').hexdigest(),
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }
    )
    events = []

    _execute_upload_stream(request, make_check(pool=pool), lambda *event: events.append(event), http_client=fake)

    # Zero-row result: no parts are uploaded, but finalize is called once so the intake
    # takes the explicit empty-object finalization path. Only metadata and final cross
    # the callback; the receipt reports partCount 0 and a result.csv object path.
    assert fake.put_calls == []
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 0
    assert [event[0] for event in events] == ['metadata', 'final']
    receipt = json.loads(events[-1][1])['upload_receipt']
    assert receipt['mode'] == 'POC_PUBLIC_MULTIPART_UPLOAD'
    assert receipt['partCount'] == 0
    assert receipt['totalBytes'] == 0
    assert receipt['totalRows'] == 0
    assert receipt['objectPath'].endswith('result.csv')
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_aggregates_copy_chunks_into_partbytes_parts(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # partBytes (8) exceeds limits.chunkBytes (4): the COPY stream emits 4-byte chunks and the
    # upload client aggregates them into 8-byte parts. Two full parts plus a final short part.
    pool = FakePool(copy_blocks=[b'aaaa', b'bbbb', b'cccc', b'dddd', b'ee'])
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = 8
    request['resultDelivery']['maxBytes'] = 24
    request['limits'] = {'chunkBytes': 4, 'maxBytes': 64, 'maxRowBytes': 32, 'timeoutMs': 5000}
    fake = FakeUploadClient()

    _execute_upload_stream(request, make_check(pool=pool), lambda *event: None, http_client=fake)

    # Contiguous 1-based part numbers; each non-final part is exactly partBytes (8) and aggregates
    # two 4-byte COPY chunks; the final part is the short remainder.
    assert [call[0] for call in fake.put_calls] == [1, 2, 3]
    assert [call[1] for call in fake.put_calls] == [b'aaaabbbb', b'ccccdddd', b'ee']
    assert [len(call[1]) for call in fake.put_calls] == [8, 8, 2]
    assert sum(len(call[1]) for call in fake.put_calls) == 18
    # Each part carries the SHA-256 of its aggregated body, not of the individual COPY chunks.
    for _part_number, payload, sha256_hex, _rows in fake.put_calls:
        assert sha256_hex == hashlib.sha256(payload).hexdigest()
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 0
    assert pool.closed_copies == 1


# ---------------------------------------------------------------------------
# Phase 2: 10 GiB capacity, 128 MiB part ceiling, and 5-minute HTTP timeout
#
# These tests prove the server-owned maximums (10 GiB total, 128 MiB per part) are accepted
# up to the boundary and rejected one byte past it, that partBytes stays independent of the
# 1 MiB COPY read chunk, that many 1 MiB COPY reads aggregate into 64 MiB parts without
# materializing the full result, and that the per-upload HTTP timeout is a 5-minute
# (connect, read) tuple. No test allocates 10 GiB; the boundary tests are pure validation,
# and the aggregation test uses a generated 1 MiB-block stream with a discarding client.
# ---------------------------------------------------------------------------

GIB = 1024 * 1024 * 1024
TEN_GIB = 10 * GIB
MAX_PART_BYTES = 128 * 1024 * 1024


def test_copy_stream_upload_mode_accepts_ten_gib_max_bytes_when_extraction_cap_matches():
    # A large int64 maxBytes (10 GiB) is accepted when the COPY extraction cap matches. No data is
    # allocated: an empty result finalizes with zero bytes, proving the caps validate without
    # materializing 10 GiB.
    pool = FakePool(copy_blocks=[])
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = MAX_PART_BYTES
    request['resultDelivery']['maxBytes'] = TEN_GIB
    request['limits'] = {'chunkBytes': PROOF_MIB, 'maxBytes': TEN_GIB, 'maxRowBytes': PROOF_MIB, 'timeoutMs': 30000}

    events = collect_copy_events(request, make_check(pool=pool))

    started = event_metadata(events[0])
    assert started['status'] == 'STARTED'
    assert started['resultDelivery']['partBytes'] == MAX_PART_BYTES
    assert started['resultDelivery']['maxBytes'] == TEN_GIB
    assert started['maxBytes'] == TEN_GIB
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    assert event_metadata(events[-1])['uploadReceipt']['totalBytes'] == 0
    assert event_metadata(events[-1])['uploadReceipt']['partCount'] == 0
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_rejects_max_bytes_above_ten_gib():
    # Plus-one safety: one byte past the 10 GiB server-owned maximum is rejected before any pool
    # access. No allocation.
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = MAX_PART_BYTES
    request['resultDelivery']['maxBytes'] = TEN_GIB + 1
    request['limits'] = {'chunkBytes': PROOF_MIB, 'maxBytes': TEN_GIB + 1, 'maxRowBytes': PROOF_MIB, 'timeoutMs': 30000}

    events = list(iter_agent_rpc_stream_copy_events(request, ExplodingRegistry()))

    assert_failed_event(events, 'invalid_request', 'maxBytes')


@pytest.mark.parametrize('part_bytes', [MAX_PART_BYTES, MAX_PART_BYTES + 1])
def test_copy_stream_upload_mode_part_bytes_boundary(part_bytes):
    request = valid_upload_copy_request()
    request['resultDelivery']['partBytes'] = part_bytes
    request['resultDelivery']['maxBytes'] = TEN_GIB
    request['limits'] = {'chunkBytes': PROOF_MIB, 'maxBytes': TEN_GIB, 'maxRowBytes': PROOF_MIB, 'timeoutMs': 30000}
    # An empty registry separates validation from resolution: a valid request reaches target
    # resolution (target_not_found), while an invalid one fails at validation (invalid_request)
    # before the registry is touched. No data is allocated in either case.
    events = list(iter_agent_rpc_stream_copy_events(request, StaticPostgresCheckRegistry([])))
    if part_bytes <= MAX_PART_BYTES:
        assert_failed_event(events, 'target_not_found')
    else:
        assert_failed_event(events, 'invalid_request', 'partBytes')


def test_copy_stream_upload_mode_aggregates_many_copy_reads_into_64_mib_parts(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # 128 MiB total, 1 MiB COPY reads, 64 MiB parts: 128 reads form 2 parts of 64 MiB each. The
    # full 128 MiB is never materialized; at most one 64 MiB part is buffered at a time.
    total_bytes = 128 * PROOF_MIB
    part_bytes = 64 * PROOF_MIB
    read_state = {'count': 0}

    def counting_block_stream():
        for _ in range(total_bytes // PROOF_MIB):
            read_state['count'] += 1
            yield b'x' * PROOF_MIB

    request = mib_upload_request(M4_PROOF_QUERY, total_bytes, part_bytes=part_bytes, copy_chunk_bytes=PROOF_MIB)
    pool = FakePool(copy_blocks=counting_block_stream())
    reads_at_put = []

    # Discard part bodies immediately so the fake never accumulates the full 128 MiB; record only
    # the part number, size, checksum, and how many COPY blocks had been read when it uploaded.
    class DiscardingCountingClient:
        def __init__(self):
            self.put_calls = []
            self.finalize_calls = 0
            self.abort_calls = 0

        def put_part(self, creds, part_number, payload, sha256_hex, rows):
            reads_at_put.append(read_state['count'])
            self.put_calls.append((part_number, len(payload), sha256_hex, rows))
            assert sha256_hex == hashlib.sha256(payload).hexdigest()

        def finalize(self, creds):
            self.finalize_calls += 1
            return {
                'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
                'upload_id': 'upload-01k',
                'bucket_name': 'rq-bucket',
                'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
                'total_bytes': total_bytes,
                'total_rows': 0,
                'part_count': 2,
                'sha256': incremental_reference_sha256(total_bytes),
                'format': 'csv',
                'compression': 'none',
                'completed_at': '2026-08-21T00:00:00Z',
            }

        def abort(self, creds):
            self.abort_calls += 1

    fake = DiscardingCountingClient()
    _execute_upload_stream(request, make_check(pool=pool), lambda *event: None, http_client=fake)

    # Two 64 MiB parts aggregated from 128 one-MiB COPY reads; each part is exactly partBytes.
    assert [call[0] for call in fake.put_calls] == [1, 2]
    assert [call[1] for call in fake.put_calls] == [part_bytes, part_bytes]
    # Lockstep bounding: part 1 uploads after exactly 64 reads (the next 64 not yet read), and
    # part 2 uploads at finalize after all 128 reads. The full 128 MiB is never held at once.
    assert reads_at_put == [64, 128]
    assert read_state['count'] == 128
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 0
    assert pool.closed_copies == 1


@pytest.mark.parametrize(
    'resp, expected_object_path',
    [
        (
            {
                'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
                'upload_id': 'upload-01k',
                'bucket_name': 'rq-bucket',
                'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
                'total_bytes': 18,
                'total_rows': 3,
                'part_count': 1,
                'sha256': hashlib.sha256(b'').hexdigest(),
            },
            'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        ),
        ({'object_path': 'solo/path/result.csv'}, 'solo/path/result.csv'),
    ],
)
def test_intake_receipt_to_camel_maps_object_path_to_objectPath(resp, expected_object_path):
    # The intake finalize route serializes the canonical final path as the snake-case
    # ``object_path`` field; the AP receipt must carry it as the camelCase ``objectPath``.
    receipt = _intake_receipt_to_camel(resp)
    assert receipt['objectPath'] == expected_object_path
    assert receipt['objectPath'] != ''


def test_intake_receipt_to_camel_does_not_preserve_obsolete_object_key():
    # Remote Queries is greenfield: the obsolete ``object_key`` alias is not preserved, so an
    # intake response that only carries ``object_key`` yields an empty ``objectPath``.
    resp = {
        'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
        'upload_id': 'upload-01k',
        'bucket_name': 'rq-bucket',
        'object_key': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        'total_bytes': 18,
        'total_rows': 3,
        'part_count': 1,
        'sha256': hashlib.sha256(b'').hexdigest(),
    }
    assert _intake_receipt_to_camel(resp)['objectPath'] == ''


# ---------------------------------------------------------------------------
# Optional aggregate SHA-256 in the intake finalize receipt
#
# Full-object readback is debug-only/default-off, so the intake finalize response may omit
# the aggregate sha256 or return it empty. These tests pin the parsing and emission behavior:
# the field is omitted from the receipt when absent/empty, forwarded when valid, and rejected
# (fail closed) when malformed. Per-part X-DD-Part-SHA256 behavior is unchanged either way.
# ---------------------------------------------------------------------------


def test_intake_receipt_to_camel_omits_aggregate_sha256_when_absent():
    resp = {
        'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
        'upload_id': 'upload-01k',
        'bucket_name': 'rq-bucket',
        'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        'total_bytes': 18,
        'total_rows': 0,
        'part_count': 1,
    }
    receipt = _intake_receipt_to_camel(resp)
    assert 'sha256' not in receipt


def test_intake_receipt_to_camel_omits_aggregate_sha256_when_empty():
    resp = {
        'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        'sha256': '',
    }
    assert 'sha256' not in _intake_receipt_to_camel(resp)


def test_intake_receipt_to_camel_forwards_valid_aggregate_sha256():
    digest = hashlib.sha256(b'abcdefghijklmnopqr').hexdigest()
    resp = {
        'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        'sha256': digest,
    }
    assert _intake_receipt_to_camel(resp)['sha256'] == digest


@pytest.mark.parametrize(
    'bad_value',
    [
        'aggregate-sha',  # non-hex, wrong length
        'a' * 63,  # too short
        'a' * 65,  # too long
        'g' * 64,  # 64 chars but non-hex
        'A' * 64,  # 64 uppercase hex chars: valid hex but not the lowercase its-agent/intake contract
        'a' * 63 + ' ',  # 64 chars with trailing whitespace (not stripped)
        12345,  # non-string
        ['not-a-string'],  # non-string (list)
    ],
)
def test_intake_receipt_to_camel_fails_on_malformed_aggregate_sha256(bad_value):
    resp = {
        'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
        'sha256': bad_value,
    }
    with pytest.raises(remote_query._CopyStreamFailure) as excinfo:
        _intake_receipt_to_camel(resp)
    assert excinfo.value.code == 'invalid_receipt'


def test_copy_stream_upload_mode_omits_aggregate_sha256_when_intake_omits_it(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])
    # The intake omits the aggregate sha256 (default-off readback); the emitted receipt omits
    # the field entirely rather than carrying an empty placeholder.
    fake = FakeUploadClient(
        finalize_resp={
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': 18,
            'total_rows': 0,
            'part_count': 3,
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }
    )
    events = []

    _execute_upload_stream(
        valid_upload_copy_request(), make_check(pool=pool), lambda *event: events.append(event), http_client=fake
    )

    # The final receipt omits sha256; the rest of the Agent-shaped receipt is unchanged.
    receipt = json.loads(events[-1][1])['upload_receipt']
    assert 'sha256' not in receipt
    assert receipt['partCount'] == 3
    assert receipt['totalBytes'] == 18
    assert receipt['uploadId'] == 'upload-01k'

    # Per-part checksums are unchanged: each part still carries the SHA-256 of its own body,
    # independent of whether the intake supplied an aggregate digest.
    assert len(fake.put_calls) == 3
    for _part_number, payload, sha256_hex, _rows in fake.put_calls:
        assert sha256_hex == hashlib.sha256(payload).hexdigest()
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 0
    assert pool.closed_copies == 1


def test_copy_stream_upload_mode_fails_on_malformed_aggregate_sha256(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(copy_blocks=[b'abcdefgh', b'ijklmnop', b'qr'])
    fake = FakeUploadClient(
        finalize_resp={
            'mode': 'POC_PUBLIC_MULTIPART_UPLOAD',
            'upload_id': 'upload-01k',
            'bucket_name': 'rq-bucket',
            'object_path': 'its-agent-intake/poc/org-1/task-t/run-r/upload-upload-01k/result.csv',
            'total_bytes': 18,
            'total_rows': 0,
            'part_count': 3,
            'sha256': 'aggregate-sha',
            'format': 'csv',
            'compression': 'none',
            'completed_at': '2026-08-20T00:00:00Z',
        }
    )
    events = []

    _execute_upload_stream(
        valid_upload_copy_request(), make_check(pool=pool), lambda *event: events.append(event), http_client=fake
    )

    # All parts upload and finalize is called, but the malformed aggregate sha256 fails closed:
    # the session is aborted and an error event (not a final receipt) is emitted.
    assert len(fake.put_calls) == 3
    assert fake.finalize_calls == 1
    assert fake.abort_calls == 1
    assert events[-1][0] == 'error'
    final_metadata = json.loads(events[-1][1])
    assert final_metadata['error']['code'] == 'invalid_receipt'
    assert 'upload_receipt' not in final_metadata
    assert pool.closed_copies == 1
