# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import json
from decimal import Decimal
from types import SimpleNamespace

import pytest
import urllib3.exceptions
from clickhouse_connect.driver.exceptions import DatabaseError, OperationalError

from datadog_checks.clickhouse import remote_query
from datadog_checks.clickhouse.remote_query import (
    StaticClickhouseCheckRegistry,
    execute_agent_rpc_stream_copy,
    iter_agent_rpc_stream_events,
    normalize_target,
)

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'
BASE_URL = 'https://dd.datad0g.com/api/unstable/its-agent-intake'
TOKEN = 'scoped-upload-token'


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


def stream_body(names, types, rows):
    """A JSONCompactEachRowWithNamesAndTypes body: names row, types row, then data rows."""
    lines = [json.dumps(list(names)), json.dumps(list(types))]
    lines.extend(json.dumps(list(row)) for row in rows)
    return ('\n'.join(lines) + '\n').encode('utf-8')


def raw_stream_body(*lines):
    """A body from raw lines, for malformed-stream cases."""
    return b'\n'.join(line if isinstance(line, bytes) else line.encode('utf-8') for line in lines) + b'\n'


class FakeStream:
    """urllib3 HTTPResponse stand-in: bounded reads over the body, close tracking."""

    def __init__(self, body, chunk_size=32, read_error=None, error_at=None, read_log=None):
        self._body = body
        self._offset = 0
        self._chunk_size = chunk_size
        self.read_count = 0
        self.read_sizes = []
        self.closed = False
        self.read_error = read_error
        self.error_at = error_at
        self.read_log = read_log

    def read(self, amount):
        self.read_count += 1
        self.read_sizes.append(amount)
        if self.read_log is not None:
            self.read_log.append(('read', self._offset))
        if self.read_error is not None and (self.error_at is None or self.read_count >= self.error_at):
            raise self.read_error
        chunk = self._body[self._offset : self._offset + amount]
        self._offset += len(chunk)
        return chunk

    def close(self):
        self.closed = True

    @property
    def offset(self):
        return self._offset

    @property
    def exhausted(self):
        return self._offset >= len(self._body)


class FakeClickhouseClient:
    """Per-run client stand-in: one raw_stream call returning the configured stream."""

    def __init__(self, body, readonly_level=0, chunk_size=32, raw_stream_error=None, read_error=None, read_log=None):
        self.server_settings = (
            {'readonly': SimpleNamespace(value=str(readonly_level))} if readonly_level is not None else {}
        )
        self._body = body
        self._chunk_size = chunk_size
        self._raw_stream_error = raw_stream_error
        self._read_error = read_error
        self._read_log = read_log
        self.raw_stream_calls = []
        self.stream = None
        self.closed = False

    def raw_stream(self, query, settings=None, fmt=None):
        self.raw_stream_calls.append({'query': query, 'settings': dict(settings or {}), 'fmt': fmt})
        if self._raw_stream_error is not None:
            raise self._raw_stream_error
        self.stream = FakeStream(
            self._body, chunk_size=self._chunk_size, read_error=self._read_error, read_log=self._read_log
        )
        return self.stream

    def close(self):
        self.closed = True


class FakeUploadClient:
    def __init__(
        self,
        run_finalize_response=None,
        raise_on_put=None,
        raise_on_page_finalize=None,
        raise_on_run_finalize=None,
        put_log=None,
    ):
        # (batch_index, part_number, payload, sha256_hex, rows)
        self.put_part_calls = []
        self.page_finalize_calls = []
        self.run_finalize_calls = 0
        self.abort_calls = 0
        self.raise_on_put = raise_on_put
        self.raise_on_page_finalize = raise_on_page_finalize
        self.raise_on_run_finalize = raise_on_run_finalize
        self.run_finalize_response = (
            run_finalize_response if run_finalize_response is not None else {'upload_id': UPLOAD_ID}
        )
        self.put_log = put_log

    def put_part(self, creds, batch_index, part_number, payload, sha256_hex, rows):
        self.put_part_calls.append((batch_index, part_number, payload, sha256_hex, rows))
        if self.put_log is not None:
            self.put_log.append(('put', batch_index, part_number, len(payload), rows))
        if self.raise_on_put is not None:
            raise self.raise_on_put

    def finalize_page(self, creds, batch_index):
        self.page_finalize_calls.append(batch_index)
        if self.raise_on_page_finalize is not None:
            raise self.raise_on_page_finalize

    def finalize_run(self, creds):
        self.run_finalize_calls += 1
        if self.raise_on_run_finalize is not None:
            raise self.raise_on_run_finalize
        return self.run_finalize_response

    def abort(self, creds):
        self.abort_calls += 1


def make_check(server='localhost', port=8123, db='default', pool_manager=None, check_database_identifier=None):
    check = SimpleNamespace(
        _config=SimpleNamespace(server=server, port=port, db=db),
        _pool_manager=pool_manager if pool_manager is not None else object(),
    )
    if check_database_identifier is not None:
        check.database_identifier = check_database_identifier
    return check


def make_client(names=('value',), types=('UInt8',), rows=(), readonly_level=0, **stream_kwargs):
    return FakeClickhouseClient(stream_body(names, types, rows), readonly_level=readonly_level, **stream_kwargs)


def valid_request(query='SELECT 1 AS value', include_schema=False, **extra):
    target = {
        'host': extra.pop('host', 'LOCALHOST.'),
        'port': extra.pop('port', 8123),
        'dbname': extra.pop('dbname', 'default'),
    }
    request = {
        'operation': 'produce_json_pages',
        'target': target,
        'query': query,
        'resultDelivery': valid_result_delivery(),
    }
    if include_schema:
        request['includeSchema'] = True
    request.update(extra)
    return request


def valid_result_delivery(**extra):
    result_delivery = {
        'runId': RUN_ID,
        'taskId': TASK_ID,
        'artifactVersion': 1,
        'uploadId': UPLOAD_ID,
        'baseUrl': BASE_URL,
        'token': TOKEN,
        'partBytes': 64 * 1024 * 1024,
        'limits': valid_limits(),
    }
    result_delivery.update(extra)
    return result_delivery


def valid_limits(**extra):
    limits = {
        'maxFileBytes': 104857600,
        'maxResultBytes': 10 * 1024**3,
        'maxRowBytes': 16 * 1024**2,
        'maxColumns': 1024,
        'maxSchemaBytes': 1024**2,
        'maxPages': 128,
        'timeoutMs': 5000,
    }
    limits.update(extra)
    return limits


def bounded_request(query='SELECT 1 AS value', part_bytes=64, **limit_overrides):
    """A request with small limits so page/part boundaries are cheap to exercise."""
    limits = valid_limits(
        maxFileBytes=1024, maxResultBytes=8192, maxRowBytes=64, maxColumns=8, maxSchemaBytes=256, maxPages=4
    )
    limits.update(limit_overrides)
    request = valid_request(query=query)
    request['resultDelivery']['partBytes'] = part_bytes
    request['resultDelivery']['limits'] = limits
    return request


def patch_upload_credentials(monkeypatch):
    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        return None

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)


def patch_allowlist_disabled(monkeypatch):
    monkeypatch.setattr(remote_query, '_is_query_allowlist_enabled', lambda: False)


class ExplodingRegistry:
    def iter_clickhouse_checks(self):
        pytest.fail('registry must not be iterated')


def collect_events(request, check, upload_client=None, registry=None, clickhouse_client=None):
    """Run the producer with fakes and collect its events.

    ``clickhouse_client`` is injected as the per-run client factory result. With no
    client injected, a default body (``SELECT 1 AS value``) is used, so tests that need a
    specific result stream always pass one explicitly.
    """
    client_factory = None
    if clickhouse_client is not None:

        def client_factory(_check, _limits):
            return clickhouse_client

    if upload_client is None:
        upload_client = FakeUploadClient()
    return list(
        iter_agent_rpc_stream_events(
            request,
            registry if registry is not None else StaticClickhouseCheckRegistry([check]),
            upload_client,
            client_factory,
        )
    )


def event_metadata(event):
    return event.metadata


def assert_failed_event(events, code, message_contains=None):
    assert events[-1].event_type == 'error'
    assert event_metadata(events[-1])['status'] == 'FAILED'
    assert event_metadata(events[-1])['error']['code'] == code
    if message_contains is not None:
        assert message_contains in event_metadata(events[-1])['error']['message']


def assert_success(events):
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    return event_metadata(events[-1])


def prefix_bytes(batch_index=0, record_offset=0, schema_json=None):
    return remote_query.page_prefix(
        run_id=RUN_ID, task_id=TASK_ID, batch_index=batch_index, record_offset=record_offset, schema_json=schema_json
    )


def assembled_pages(fake_client):
    """Reassemble each completed page from its sequentially uploaded parts."""
    parts = {}
    for batch_index, _part_number, payload, _sha256_hex, _rows in fake_client.put_part_calls:
        parts.setdefault(batch_index, []).append(payload)
    return {batch_index: b''.join(payloads) for batch_index, payloads in parts.items()}


def part_row_sums(fake_client):
    sums = {}
    for batch_index, _part_number, _payload, _sha256_hex, rows in fake_client.put_part_calls:
        sums[batch_index] = sums.get(batch_index, 0) + rows
    return sums


# ---------------------------------------------------------------------------
# Statement gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'query',
    [
        'SELECT 1 AS value',
        'select * from system.databases',
        'SELECT 1',
        'SELECT 1;',
        'SELECT 1 ;   ',
        '-- leading comment\nSELECT 1',
        '/* leading comment */ SELECT 1',
        '/* outer /* nested */ comment */ SELECT 1',
        'SHOW TABLES',
        'DESCRIBE system.databases',
        'DESC system.databases',
        'EXPLAIN SELECT 1',
        'EXISTS TABLE t',
        "SELECT ';' AS semi, 'drop table' AS words",
        "SELECT 'unterminated comment /* inside a string'",
        'SELECT 1 -- trailing comment with ; inside',
        'SELECT `a;b` FROM t',
        'WITH 1 AS x SELECT x',
        'WITH 1 AS x, 2 AS y SELECT x + y',
        'WITH cte AS (SELECT 1 AS a) SELECT a FROM cte',
        'WITH a AS (SELECT 1), b AS (SELECT 2) SELECT * FROM a, b',
        'WITH t(x) AS (SELECT 1) SELECT x FROM t',
        'WITH t (x, y) AS (SELECT 1, 2) SELECT x FROM t',
        'WITH cte AS (SELECT 1 AS a) SELECT a FROM cte;',
    ],
)
def test_statement_gate_accepts_read_only_statements(query):
    remote_query.validate_read_only_statement(query)


@pytest.mark.parametrize(
    'query',
    [
        '',
        '/* only a comment */',
        '/* never closed SELECT 1',
        "SELECT 'never closed",
        'INSERT INTO t VALUES (1)',
        'DROP TABLE t',
        'ALTER TABLE t DELETE WHERE 1',
        'ALTER TABLE t UPDATE x = 1 WHERE 1',
        'DELETE FROM t WHERE 1',
        'UPDATE t SET x = 1 WHERE 1',
        'TRUNCATE TABLE t',
        'RENAME TABLE a TO b',
        'EXCHANGE TABLES a AND b',
        'OPTIMIZE TABLE t',
        'CREATE TABLE t (x UInt8) ENGINE = Memory',
        'SET max_execution_time = 1',
        'USE default',
        'GRANT SELECT ON * TO u',
        'KILL QUERY WHERE 1',
        'SYSTEM FLUSH LOGS',
        'select 1; drop table t',
        'DROP TABLE t -- after a select',
        'SELECT 1; /* trailing comment is fine but this is a second statement */ SELECT 2',
        'WITH cte AS (SELECT 1) INSERT INTO t SELECT * FROM cte',
        'WITH cte AS (SELECT 1) DELETE FROM t',
        'WITH ( FROM t SELECT 1',
        'WITH cte AS (unclosed SELECT 1',
        'WITH 1 AS SELECT 2',
    ],
)
def test_statement_gate_rejects_mutations_and_malformed_statements(query):
    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
        remote_query.validate_read_only_statement(query)
    assert excinfo.value.code == 'invalid_request'
    # The message is one of the two fixed spellings: it never echoes the query text.
    assert excinfo.value.message in (
        'Invalid remote query request: query must be a single read-only statement.',
        'Invalid remote query request: query is not a read-only statement.',
    )


@pytest.mark.parametrize(
    'query',
    [
        'INSERT INTO t VALUES (1)',
        'DROP TABLE t',
        'select 1; drop table t',
        "SELECT 'unterminated",
    ],
)
def test_stream_rejects_non_read_only_queries_before_resolution(query):
    request = valid_request(query=query)

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'read-only')
    # The failing query text never appears in the emitted events.
    assert query not in str(events)


def test_stream_accepts_with_select_statement_when_allowlist_disabled(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(names=('x',), types=('UInt8',), rows=[[7]])
    request = valid_request(query='WITH one AS (SELECT 7 AS x) SELECT x FROM one')

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    final = assert_success(events)
    assert final['upload_receipt']['totalRows'] == 1
    assert clickhouse_client.raw_stream_calls[0]['query'] == request['query']


# ---------------------------------------------------------------------------
# Target normalization and validation
# ---------------------------------------------------------------------------


def test_normalize_target_trims_lowercases_host_and_removes_one_trailing_dot():
    target = normalize_target({'host': ' Example.INTERNAL. ', 'port': 8123, 'dbname': 'default'})

    assert target.host == 'example.internal'
    assert target.port == 8123
    assert target.dbname == 'default'


def test_normalize_target_rejects_missing_port():
    with pytest.raises(ValueError):
        normalize_target({'host': 'localhost', 'dbname': 'default'})


def test_normalize_target_accepts_database_instance_without_normalization():
    target = normalize_target({'database_instance': 'Clickhouse/Primary-A'})

    assert target.database_instance == 'Clickhouse/Primary-A'
    assert target.host is None
    assert target.dbname is None


@pytest.mark.parametrize('port', [True, '8123', 'abc', '0', 0, -1, 65536, None])
def test_normalize_target_rejects_invalid_port_values(port):
    with pytest.raises(ValueError):
        normalize_target({'host': 'localhost', 'port': port, 'dbname': 'default'})


@pytest.mark.parametrize(
    'target',
    [
        {'host': '', 'port': 8123, 'dbname': 'default'},
        {'host': '  ', 'port': 8123, 'dbname': 'default'},
        {'host': 'localhost', 'port': 8123, 'dbname': ''},
        {'host': 'localhost', 'port': 8123, 'dbname': ' default '},
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
        {'port': 8123},
        {'dbname': 'default'},
        {'host': 'localhost', 'port': 8123},
        {'host': 'localhost', 'dbname': 'default'},
        {'port': 8123, 'dbname': 'default'},
        {'host': 'localhost', 'dbname': 'default', 'database_instance': 'clickhouse-dbi'},
        {'database_instance': 'clickhouse-dbi', 'host': 'localhost'},
        {'database_instance': 'clickhouse-dbi', 'port': 8123},
        {'database_instance': 'clickhouse-dbi', 'dbname': 'default'},
        {'database_instance': 'clickhouse-dbi', 'host': ''},
        {'database_instance': ''},
        {'database_instance': ' clickhouse-dbi '},
    ],
)
def test_normalize_target_rejects_missing_partial_mixed_or_invalid_database_instance_target(target):
    with pytest.raises(ValueError):
        normalize_target(target)


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('field', ['extra', 'password'])
def test_stream_rejects_unknown_request_fields_before_resolution(caplog, field):
    request = valid_request(**{field: 'SECRET_DO_NOT_LOG'})

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', field)
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_stream_rejects_unknown_target_fields_before_resolution():
    request = valid_request()
    request['target']['password'] = 'SECRET_DO_NOT_LOG'

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(events)


def test_stream_rejects_unknown_limits_fields_before_resolution():
    request = valid_request()
    request['resultDelivery']['limits']['password'] = 'SECRET_DO_NOT_LOG'

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'password')
    assert 'SECRET_DO_NOT_LOG' not in str(events)


@pytest.mark.parametrize(
    'field', ['maxFileBytes', 'maxResultBytes', 'maxRowBytes', 'maxColumns', 'maxSchemaBytes', 'maxPages', 'timeoutMs']
)
def test_stream_rejects_string_limit_values_before_resolution(field):
    request = valid_request()
    request['resultDelivery']['limits'][field] = '10'

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', field)


@pytest.mark.parametrize(
    'field', ['runId', 'taskId', 'artifactVersion', 'uploadId', 'baseUrl', 'token', 'partBytes', 'limits']
)
def test_stream_rejects_missing_delivery_fields_before_resolution(field):
    request = valid_request()
    del request['resultDelivery'][field]

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', field)


@pytest.mark.parametrize(
    'mutation, expected',
    [
        ({'apiKey': 'SECRET_API_KEY'}, 'apiKey'),
        ({'mode': 'POC_PUBLIC_MULTIPART_UPLOAD'}, 'mode'),
        ({'format': 'csv'}, 'format'),
        ({'compression': 'none'}, 'compression'),
        ({'artifactVersion': 2}, 'artifactVersion'),
        ({'artifactVersion': '1'}, 'artifactVersion'),
        ({'runId': ''}, 'runId'),
        ({'taskId': ''}, 'taskId'),
        ({'baseUrl': ''}, 'baseUrl'),
        ({'token': ''}, 'token'),
        ({'uploadId': ''}, 'uploadId'),
        ({'partBytes': 0}, 'partBytes'),
        ({'partBytes': '8'}, 'partBytes'),
    ],
)
def test_stream_rejects_invalid_delivery_fields_before_resolution(mutation, expected):
    request = valid_request()
    request['resultDelivery'].update(mutation)

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', expected)
    assert 'SECRET_API_KEY' not in str(events)
    assert 'scoped-upload-token' not in str(events)


@pytest.mark.parametrize(
    'limits, expected',
    [
        ({'maxFileBytes': 128 * 1024 * 1024 + 1}, 'maxFileBytes'),
        ({'maxResultBytes': 10 * 1024**3 + 1}, 'maxResultBytes'),
        ({'maxRowBytes': 0}, 'maxRowBytes'),
        ({'maxColumns': 0}, 'maxColumns'),
        ({'maxSchemaBytes': 0}, 'maxSchemaBytes'),
        ({'maxPages': 0}, 'maxPages'),
        ({'timeoutMs': 0}, 'timeoutMs'),
        (
            {'maxRowBytes': 2097152, 'maxFileBytes': 1048576},
            'maxRowBytes must not exceed maxFileBytes',
        ),
        # A schema budget beyond the page budget (here, beyond the 128 MiB platform
        # ceiling) would let the header buffer grow past the page ceiling.
        ({'maxSchemaBytes': 209715200}, 'maxSchemaBytes must not exceed maxFileBytes'),
        (
            {'maxFileBytes': 104857600, 'maxResultBytes': 1048576},
            'maxFileBytes must not exceed maxResultBytes',
        ),
    ],
)
def test_stream_rejects_invalid_limits_before_resolution(limits, expected):
    request = valid_request()
    request['resultDelivery']['limits'].update(limits)

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', expected)


def test_stream_accepts_max_schema_bytes_equal_to_max_file_bytes(monkeypatch):
    # Equality is the boundary, not a violation: a schema budget equal to the page budget
    # is valid, and the run proceeds with the header bound at its largest allowed value.
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    request = valid_request(include_schema=True)
    limits = request['resultDelivery']['limits']
    limits['maxSchemaBytes'] = limits['maxFileBytes']

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    final = assert_success(events)
    assert final['upload_receipt']['pageCount'] == 1


def test_stream_rejects_part_bytes_larger_than_a_page():
    request = valid_request()
    request['resultDelivery']['partBytes'] = 2097152
    request['resultDelivery']['limits']['maxFileBytes'] = 1048576
    request['resultDelivery']['limits']['maxRowBytes'] = 65536

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'partBytes must not exceed limits.maxFileBytes')


def test_stream_requires_result_delivery():
    request = valid_request()
    del request['resultDelivery']

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'resultDelivery')


@pytest.mark.parametrize('operation', [None, 'copy_stream', 'query', 1])
def test_stream_rejects_non_page_operation_before_client_access(operation):
    clickhouse_client = make_client(rows=[[1]])
    request = valid_request()
    if operation is None:
        del request['operation']
    else:
        request['operation'] = operation

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'invalid_request', 'operation')
    assert clickhouse_client.raw_stream_calls == []


@pytest.mark.parametrize('include_schema', ['true', 1, None])
def test_stream_rejects_non_boolean_include_schema_before_client_access(include_schema):
    clickhouse_client = make_client(rows=[[1]])
    request = valid_request()
    request['includeSchema'] = include_schema

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'invalid_request', 'includeSchema')
    assert clickhouse_client.raw_stream_calls == []


@pytest.mark.parametrize('request_json', ['{"password": "SECRET_DO_NOT_LOG"', b'\xff'])
def test_entry_rejects_malformed_json_without_echoing_input(caplog, request_json):
    events = []

    execute_agent_rpc_stream_copy(request_json, make_check(), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['status'] == 'FAILED'
    assert metadata['error']['code'] == 'invalid_request'
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


@pytest.mark.parametrize('request_json', ['[]', 'null', '"SECRET_DO_NOT_LOG"', '1'])
def test_entry_rejects_non_object_json_without_echoing_input(request_json):
    events = []

    execute_agent_rpc_stream_copy(request_json, make_check(), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['error']['code'] == 'invalid_request'
    assert 'JSON object' in metadata['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(events)


# ---------------------------------------------------------------------------
# Query allowlist
# ---------------------------------------------------------------------------


def test_stream_rejects_non_allowlisted_query_before_client_access():
    clickhouse_client = make_client(rows=[[1]])
    request = valid_request(query='SELECT currentDatabase()')

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'invalid_request', 'query is not allowlisted')
    assert clickhouse_client.raw_stream_calls == []


def test_stream_accepts_non_allowlisted_query_when_allowlist_is_disabled(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(names=('database',), types=('String',), rows=[['datadog_test']])
    request = valid_request(query='SELECT currentDatabase()')

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    final = assert_success(events)
    assert final['upload_receipt']['totalRows'] == 1


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


def test_stream_accepts_large_payload_proof_queries(monkeypatch):
    patch_upload_credentials(monkeypatch)
    for size in (1048576, 2097152, 4194304, 8388608, 16777216, 33554432):
        clickhouse_client = make_client(names=('payload',), types=('String',), rows=[['x']])
        request = valid_request(query=f"SELECT repeat('x', {size}) AS payload")

        events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

        assert_success(events)


def test_stream_accepts_identity_and_binary_proof_queries(monkeypatch):
    patch_upload_credentials(monkeypatch)
    for query in (
        'SELECT hostName() AS host, currentUser() AS user, version() AS version',
        "SELECT unhex('00ff80') AS payload",
    ):
        clickhouse_client = make_client(names=('v',), types=('String',), rows=[['x']])
        request = valid_request(query=query)

        events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

        assert_success(events)


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def test_stream_resolves_server_port_db_from_check_config(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_success(events)


def test_stream_host_port_dbname_target_still_succeeds_when_check_has_database_identifier(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    check = make_check(check_database_identifier='clickhouse-dbi')

    events = collect_events(valid_request(), check, clickhouse_client=clickhouse_client)

    assert_success(events)


def test_stream_resolves_unique_database_instance_from_check_identifier(monkeypatch):
    patch_upload_credentials(monkeypatch)
    matching_client = make_client(rows=[[1]])
    non_matching_client = make_client(rows=[[1]])
    checks = [
        make_check(server='analytics.internal', db='analytics', check_database_identifier='Clickhouse/Primary-A'),
        make_check(server='logs.internal', db='logs', check_database_identifier='Clickhouse/Primary-B'),
    ]

    request = valid_request()
    request['target'] = {'database_instance': 'Clickhouse/Primary-A'}
    events = collect_events(
        request, None, registry=StaticClickhouseCheckRegistry(checks), clickhouse_client=matching_client
    )

    assert_success(events)
    assert matching_client.raw_stream_calls
    assert non_matching_client.raw_stream_calls == []


def test_stream_database_instance_miss_fails_without_client_access():
    clickhouse_client = make_client(rows=[[1]])
    check = make_check(check_database_identifier='Clickhouse/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Clickhouse/Primary-B'}
    events = collect_events(request, check, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'target_not_found')
    assert clickhouse_client.raw_stream_calls == []


def test_stream_database_instance_ambiguous_fails_without_client_access():
    clickhouse_client = make_client(rows=[[1]])
    checks = [
        make_check(server='a.internal', check_database_identifier='Clickhouse/Primary-A'),
        make_check(server='b.internal', check_database_identifier='Clickhouse/Primary-A'),
    ]

    request = valid_request()
    request['target'] = {'database_instance': 'Clickhouse/Primary-A'}
    events = collect_events(
        request, None, registry=StaticClickhouseCheckRegistry(checks), clickhouse_client=clickhouse_client
    )

    assert_failed_event(events, 'target_ambiguous')
    assert clickhouse_client.raw_stream_calls == []


def test_stream_rejects_mixed_database_instance_and_host_selector_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': 'clickhouse-dbi', 'host': 'localhost'}

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_stream_rejects_empty_database_instance_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': ' clickhouse-dbi '}

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'database_instance')


def test_stream_uses_only_supplied_live_check_for_target_matching(monkeypatch):
    patch_upload_credentials(monkeypatch)
    request = valid_request(host='configured.internal')

    events = collect_events(request, make_check(server='localhost'))
    assert_failed_event(events, 'target_not_found')

    events = collect_events(request, make_check(server='configured.internal'), clickhouse_client=make_client())
    assert_success(events)


def test_stream_requires_dbname_match_even_when_host_and_port_match():
    check = make_check(server='localhost', port=8123, db='default')

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_not_found')


def test_stream_fails_ambiguous_duplicate_configs():
    checks = [make_check(server='localhost'), make_check(server='localhost')]

    events = collect_events(valid_request(), None, registry=StaticClickhouseCheckRegistry(checks))

    assert_failed_event(events, 'target_ambiguous')


def test_stream_missing_pool_manager_returns_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = make_check()
    check._pool_manager = None

    events = collect_events(valid_request(), check)

    assert_failed_event(events, 'target_unavailable')


def test_stream_credentials_unavailable_without_agent_keys(monkeypatch):
    def get_config(key):
        return None

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)

    events = collect_events(valid_request(), make_check())

    assert_failed_event(events, 'credentials_unavailable')
    assert events[0].event_type == 'error'


# ---------------------------------------------------------------------------
# Producer core: envelope, single execution, read-only settings, receipt
# ---------------------------------------------------------------------------


def test_producer_emits_started_and_final_with_compact_receipt(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(names=('value',), types=('UInt8',), rows=[[1], [2]])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert [event.event_type for event in events] == ['metadata', 'final']
    started = event_metadata(events[0])
    assert started['status'] == 'STARTED'
    assert started['operation'] == 'produce_json_pages'
    assert started['includeSchema'] is False
    assert started['resultDelivery']['uploadId'] == UPLOAD_ID
    assert started['resultDelivery']['runId'] == RUN_ID
    assert started['resultDelivery']['taskId'] == TASK_ID
    assert started['resultDelivery']['artifactVersion'] == 1
    assert started['resultDelivery']['partBytes'] == 64 * 1024 * 1024
    assert started['resultDelivery']['limits'] == {
        'maxFileBytes': 104857600,
        'maxResultBytes': 10 * 1024**3,
        'maxRowBytes': 16 * 1024**2,
        'maxColumns': 1024,
        'maxSchemaBytes': 1024**2,
        'maxPages': 128,
        'timeoutMs': 5000,
    }
    # baseUrl/token are accepted request fields but never echoed back.
    assert 'baseUrl' not in started['resultDelivery']
    assert 'token' not in started['resultDelivery']

    final = assert_success(events)
    # Only the compact receipt crosses the callback: no schema, no bulk bytes.
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 1,
        'totalRows': 2,
        'totalBytes': len(assembled_pages(fake)[0]),
    }
    assert final['stats']['rowsEmitted'] == 2
    assert final['stats']['pagesEmitted'] == 1
    assert 'elapsedMs' in final['stats']
    # Event payloads are empty: bulk bytes never cross the emit bridge.
    assert all(event.payload == b'' for event in events)


def test_producer_writes_exact_v1_envelope_json(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # Schema disabled: the schema key is omitted entirely, never null/[].
    assert page == (prefix_bytes() + b'{"value":1}' + remote_query.PAGE_SUFFIX)
    parsed = json.loads(page)
    assert parsed == {
        'version': 1,
        'run_id': RUN_ID,
        'task_id': TASK_ID,
        'batch_index': 0,
        'record_offset': 0,
        'data': {'items': [{'value': 1}]},
    }
    assert 'schema' not in parsed
    assert 'total_records' not in parsed


def test_producer_executes_query_exactly_once_verbatim_with_readonly_settings(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient()
    request = valid_request()
    request['resultDelivery']['limits']['timeoutMs'] = 5000

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # The query is executed exactly once, verbatim, with the one-stream row format appended
    # by the client; the injected settings enforce read-only plus a server-side timeout.
    assert clickhouse_client.raw_stream_calls == [
        {
            'query': 'SELECT 1 AS value',
            'settings': {'readonly': 1, 'max_execution_time': 5.0},
            'fmt': remote_query.REMOTE_QUERY_STREAM_FORMAT,
        }
    ]
    assert clickhouse_client.stream.read_sizes  # rows were read in bounded chunks
    assert clickhouse_client.stream.closed
    assert clickhouse_client.closed


def test_producer_omits_settings_for_readonly_profile_users(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]], readonly_level=1)

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_success(events)
    # A read-only-profile user cannot change settings: injecting would fail their queries.
    assert clickhouse_client.raw_stream_calls[0]['settings'] == {}


@pytest.mark.parametrize('readonly_level', [None, 2, 99])
def test_producer_omits_settings_for_unknown_or_readonly_levels(monkeypatch, readonly_level):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]], readonly_level=readonly_level)

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_success(events)
    assert clickhouse_client.raw_stream_calls[0]['settings'] == {}


def test_producer_zero_rows_with_schema_disabled_writes_no_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    final = assert_success(events)
    assert fake.put_part_calls == []
    assert fake.page_finalize_calls == []
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 0
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 0,
        'totalRows': 0,
        'totalBytes': 0,
    }


def test_producer_zero_rows_with_schema_enabled_writes_one_schema_bearing_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[])
    fake = FakeUploadClient()

    events = collect_events(
        valid_request(include_schema=True), make_check(), upload_client=fake, clickhouse_client=clickhouse_client
    )

    final = assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0]
    parsed = json.loads(pages[0])
    assert parsed['batch_index'] == 0
    assert parsed['record_offset'] == 0
    assert parsed['schema'] == [{'column_name': 'value', 'vendor_data_type': 'UInt8'}]
    assert parsed['data'] == {'items': []}
    assert final['upload_receipt']['pageCount'] == 1
    assert final['upload_receipt']['totalRows'] == 0
    assert final['upload_receipt']['totalBytes'] == len(pages[0])
    assert fake.page_finalize_calls == [0]
    assert fake.run_finalize_calls == 1


def test_producer_rejects_header_missing_type_row(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["value"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'header rows')
    assert fake.put_part_calls == []


def test_producer_rejects_header_with_mismatched_column_counts(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["value", "extra"]', '["UInt8"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'header rows')
    assert fake.put_part_calls == []


@pytest.mark.parametrize('header', ['["value", ""]', '[1, 2]', '"value"', 'not json'])
def test_producer_rejects_malformed_header_rows(monkeypatch, header):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body(header, '["UInt8"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed')
    assert fake.put_part_calls == []


def test_producer_rejects_duplicate_result_column_names_before_row_data(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(names=('value', 'value'), types=('UInt8', 'UInt8'), rows=[[1, 1]])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'duplicate_columns', 'value')
    assert fake.put_part_calls == []


def test_producer_rejects_duplicate_columns_even_with_schema_disabled(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(names=('v', 'v', 'v'), types=('UInt8', 'UInt8', 'UInt8'), rows=[[1, 2, 3]])

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'duplicate_columns')


def test_producer_rejects_columns_beyond_max_columns(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(names=('a', 'b', 'c'), types=('UInt8', 'UInt8', 'UInt8'), rows=[[1, 2, 3]])
    request = bounded_request(maxColumns=2)

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'max_columns_exceeded')


# ---------------------------------------------------------------------------
# Schema production
# ---------------------------------------------------------------------------


def test_producer_schema_enabled_repeats_identical_ordered_schema_across_pages(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(
        names=('city', 'country'), types=('String', 'String'), rows=[['New York', 'USA'], ['Paris', 'France']]
    )
    request = bounded_request(query='SELECT city, country FROM cities ORDER BY city')
    request['includeSchema'] = True
    schema_entries = [
        {'column_name': 'city', 'vendor_data_type': 'String'},
        {'column_name': 'country', 'vendor_data_type': 'String'},
    ]
    schema_json = json.dumps(schema_entries, separators=(',', ':')).encode('utf-8')
    longest_row_bytes = b'{"city":"New York","country":"USA"}'
    # maxFileBytes fits the schema-bearing prefix plus exactly one of the rows, so the
    # second row forces a second page.
    request['resultDelivery']['limits']['maxFileBytes'] = (
        len(prefix_bytes(schema_json=schema_json)) + len(longest_row_bytes) + len(remote_query.PAGE_SUFFIX)
    )
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0, 1]
    parsed_pages = [json.loads(page) for page in pages.values()]
    assert parsed_pages[0]['batch_index'] == 0
    assert parsed_pages[0]['record_offset'] == 0
    assert parsed_pages[0]['data']['items'] == [{'city': 'New York', 'country': 'USA'}]
    assert parsed_pages[1]['batch_index'] == 1
    assert parsed_pages[1]['record_offset'] == 1
    assert parsed_pages[1]['data']['items'] == [{'city': 'Paris', 'country': 'France'}]
    # The schema repeats identically and in result-column order on every page.
    assert parsed_pages[0]['schema'] == parsed_pages[1]['schema'] == schema_entries
    assert fake.page_finalize_calls == [0, 1]
    assert event_metadata(events[0])['includeSchema'] is True


def test_producer_schema_carries_clickhouse_type_strings(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(
        names=('count', 'name', 'flag'),
        types=('Nullable(UInt64)', 'LowCardinality(String)', 'Bool'),
        rows=[[None, 'x', True]],
    )
    fake = FakeUploadClient()

    events = collect_events(
        valid_request(include_schema=True), make_check(), upload_client=fake, clickhouse_client=clickhouse_client
    )

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    parsed = json.loads(page)
    # The vendor data types are the exact ClickHouse type strings from the stream header.
    assert parsed['schema'] == [
        {'column_name': 'count', 'vendor_data_type': 'Nullable(UInt64)'},
        {'column_name': 'name', 'vendor_data_type': 'LowCardinality(String)'},
        {'column_name': 'flag', 'vendor_data_type': 'Bool'},
    ]
    assert parsed['data']['items'] == [{'count': None, 'name': 'x', 'flag': True}]


def test_producer_enforces_max_schema_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    request = bounded_request(maxSchemaBytes=4, maxFileBytes=1024)
    request['includeSchema'] = True

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'max_schema_bytes_exceeded')


def test_producer_enforces_max_file_bytes_for_schema_bearing_pages(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    # The schema-bearing minimal frame cannot fit even an empty page.
    request = bounded_request(maxFileBytes=len(prefix_bytes()) - 1, maxRowBytes=8)
    request['includeSchema'] = True

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'max_file_bytes_exceeded', 'repeated schema')


# ---------------------------------------------------------------------------
# Page splitting, boundaries, and part bookkeeping
# ---------------------------------------------------------------------------


ROW_BYTES = b'{"payload":"aaaa"}'  # 18 bytes for names ['payload'], types ['String']


def two_row_boundary_request(monkeypatch, extra_file_bytes=0):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(part_bytes=32)
    request['resultDelivery']['limits']['maxFileBytes'] = (
        prefix_len + len(ROW_BYTES) + 1 + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX) + extra_file_bytes
    )
    return request


def two_row_client(**stream_kwargs):
    return make_client(names=('payload',), types=('String',), rows=[['aaaa'], ['aaaa']], **stream_kwargs)


def test_page_split_exact_boundary_fit_keeps_one_page(monkeypatch):
    request = two_row_boundary_request(monkeypatch)
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    final = assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0]
    assert json.loads(pages[0])['data']['items'] == [{'payload': 'aaaa'}, {'payload': 'aaaa'}]
    assert final['upload_receipt']['pageCount'] == 1
    assert final['upload_receipt']['totalRows'] == 2
    assert final['upload_receipt']['totalBytes'] == len(pages[0])


def test_page_split_boundary_plus_one_row_starts_next_page(monkeypatch):
    # One byte short of fitting both rows: the second row starts a new page at the
    # cumulative row offset.
    request = two_row_boundary_request(monkeypatch, extra_file_bytes=-1)
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    final = assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0, 1]
    parsed_pages = [json.loads(page) for page in pages.values()]
    assert parsed_pages[0]['batch_index'] == 0
    assert parsed_pages[0]['record_offset'] == 0
    assert parsed_pages[0]['data']['items'] == [{'payload': 'aaaa'}]
    assert parsed_pages[1]['batch_index'] == 1
    assert parsed_pages[1]['record_offset'] == 1
    assert parsed_pages[1]['data']['items'] == [{'payload': 'aaaa'}]
    # No page exceeds maxFileBytes.
    max_file_bytes = request['resultDelivery']['limits']['maxFileBytes']
    assert all(len(page) <= max_file_bytes for page in pages.values())
    assert final['upload_receipt']['pageCount'] == 2
    assert final['upload_receipt']['totalRows'] == 2
    assert final['upload_receipt']['totalBytes'] == sum(len(page) for page in pages.values())
    assert fake.page_finalize_calls == [0, 1]


def test_page_split_row_too_large_when_row_plus_envelope_exceeds_max_file_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(maxFileBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX) - 1)
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'row_too_large', 'maxFileBytes')
    # Nothing was uploaded: the failure is detected before writing the row.
    assert fake.put_part_calls == []
    assert clickhouse_client.stream.closed


def test_page_split_row_too_large_when_row_exceeds_max_row_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = bounded_request(maxRowBytes=len(ROW_BYTES) - 1)
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    assert fake.put_part_calls == []


def test_page_split_row_too_large_when_line_exceeds_the_buffer_ceiling(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A single row line far beyond the row budget: the run fails during the read, without
    # buffering the whole line and without reading the rest of the stream.
    big_value = 'x' * 4096
    clickhouse_client = make_client(names=('payload',), types=('String',), rows=[[big_value]])
    request = bounded_request(maxRowBytes=64, maxFileBytes=1024)

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    stream = clickhouse_client.stream
    header_bound = max(64, 256) + remote_query.REMOTE_QUERY_HEADER_LINE_SLACK
    # Reads are sized to the line bound, so only the header-sized prefix was fetched.
    assert all(size <= header_bound for size in stream.read_sizes)
    assert stream.offset <= header_bound
    assert not stream.exhausted
    assert clickhouse_client.closed


def test_stream_fails_closed_on_row_line_larger_than_any_read_chunk(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A row line far larger than the 256 KiB read chunk: the buffered line never grows
    # without bound and the run fails deterministically (never truncated silently).
    big_value = 'x' * (512 * 1024)
    clickhouse_client = make_client(names=('payload',), types=('String',), rows=[[big_value]])
    request = bounded_request(maxRowBytes=128, maxFileBytes=1024)

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    stream = clickhouse_client.stream
    assert not stream.exhausted
    header_bound = max(128, 256) + remote_query.REMOTE_QUERY_HEADER_LINE_SLACK
    assert stream.offset <= header_bound + remote_query.REMOTE_QUERY_STREAM_CHUNK_BYTES


def test_stream_fails_closed_on_oversized_header_row(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A column name far beyond the header bound (the larger of the schema and row
    # budgets): the header row fails deterministically instead of being buffered whole.
    big_alias = 'a' * (64 * 1024)
    clickhouse_client = make_client(names=(big_alias,), types=('UInt8',), rows=[[1]])
    request = bounded_request(maxRowBytes=64, maxFileBytes=1024, maxSchemaBytes=256)

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'header row exceeded the allowed size')
    stream = clickhouse_client.stream
    assert not stream.exhausted
    header_bound = max(64, 256) + remote_query.REMOTE_QUERY_HEADER_LINE_SLACK
    assert stream.offset <= header_bound + remote_query.REMOTE_QUERY_STREAM_CHUNK_BYTES


def test_page_split_enforces_max_pages(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(maxPages=1, maxFileBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX))
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'max_pages_exceeded')
    # Page 0 was fully produced and finalized before the cap tripped, but the run fails:
    # no receipt is emitted and the session is aborted.
    assert fake.page_finalize_calls == [0]
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_page_split_enforces_max_result_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(
        maxFileBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX),
        maxResultBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX),
    )
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'max_result_bytes_exceeded', 'maxResultBytes')
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_part_bookkeeping_rows_span_parts_and_never_count_newlines(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    # partBytes equals the prefix length: part 1 is exactly the prefix (no row completes
    # inside it), the rest of the page -- the row, including its escaped \\n sequences,
    # plus the suffix -- forms the final short part. The row completes in the part
    # containing its final byte, and rows are never inferred by counting newlines.
    request = bounded_request(part_bytes=prefix_len)
    clickhouse_client = make_client(names=('payload',), types=('String',), rows=[['a\nb\nc']])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    assert [call[1] for call in fake.put_part_calls] == [1, 2]
    assert [call[4] for call in fake.put_part_calls] == [0, 1]
    assert sum(call[4] for call in fake.put_part_calls) == 1
    page = b''.join(call[2] for call in fake.put_part_calls)
    assert json.loads(page)['data']['items'] == [{'payload': 'a\nb\nc'}]
    # Row bytes are tracked exactly once: one row total despite the embedded newline.
    assert event_metadata(events[-1])['stats']['rowsEmitted'] == 1


def test_part_bookkeeping_contiguous_part_numbers_restart_per_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    # Two pages of one row each; small parts so each page spans several parts.
    request = bounded_request(
        part_bytes=8,
        maxFileBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX),
    )
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    calls = [(batch, part) for batch, part, _payload, _sha, _rows in fake.put_part_calls]
    page0_parts = [part for batch, part in calls if batch == 0]
    page1_parts = [part for batch, part in calls if batch == 1]
    # 1-based contiguous part numbers, restarting on each page.
    assert page0_parts == list(range(1, len(page0_parts) + 1))
    assert page1_parts == list(range(1, len(page1_parts) + 1))
    # Non-final parts are exactly partBytes; the final part of each page may be shorter.
    for batch in (0, 1):
        payloads = [payload for b, _p, payload, _sha, _rows in fake.put_part_calls if b == batch]
        assert all(len(payload) == 8 for payload in payloads[:-1])
        assert len(payloads[-1]) <= 8
    # Each part carries the SHA-256 of its own body.
    for _batch, _part, payload, sha256_hex, _rows in fake.put_part_calls:
        assert sha256_hex == hashlib.sha256(payload).hexdigest()
    # Row completions per page sum to the page's rows and to the run total.
    assert part_row_sums(fake) == {0: 1, 1: 1}
    assert event_metadata(events[-1])['upload_receipt']['totalRows'] == 2


def test_part_upload_streams_before_the_result_stream_is_exhausted(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    request = bounded_request(
        part_bytes=65536,
        maxFileBytes=1024 * 1024,
        maxResultBytes=16 * 1024 * 1024,
        maxRowBytes=1024,
        maxPages=128,
    )
    # Enough rows that the body spans several 256 KiB stream reads, so part uploads must
    # interleave with reads instead of buffering the whole result first.
    rows = [[index] for index in range(40000)]
    clickhouse_client = FakeClickhouseClient(stream_body(('payload',), ('UInt32',), rows), read_log=order_log)
    fake = FakeUploadClient(put_log=order_log)

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # Parts are uploaded while rows are still being read from the result stream: the
    # producer never buffers the complete result (or a complete page) before uploading.
    first_put = next(index for index, entry in enumerate(order_log) if entry[0] == 'put')
    last_read = max(index for index, entry in enumerate(order_log) if entry[0] == 'read')
    assert first_put < last_read
    assert clickhouse_client.stream.read_count > 2
    # Pages are contiguous zero-based, and all rows are accounted for exactly once.
    page_indexes = sorted({call[0] for call in fake.put_part_calls})
    assert page_indexes == list(range(len(page_indexes)))
    assert sum(call[4] for call in fake.put_part_calls) == 40000
    assert event_metadata(events[-1])['upload_receipt']['totalRows'] == 40000


# ---------------------------------------------------------------------------
# ClickHouse value contract (pinned, cross-language)
# ---------------------------------------------------------------------------


def encode_stream_row(names, types, values):
    columns = remote_query.build_columns(list(names), list(types))
    out = bytearray()
    remote_query.encode_row(list(values), columns, out)
    return bytes(out)


def test_value_contract_encodes_scalars_exactly():
    assert encode_stream_row(('v',), ('UInt64',), [18446744073709551615]) == b'{"v":18446744073709551615}'
    assert encode_stream_row(('v',), ('Int64',), [-42]) == b'{"v":-42}'
    # Quoted 64-bit+ integers (servers that quote big ints) normalize back to numbers.
    assert encode_stream_row(('v',), ('UInt64',), ['18446744073709551615']) == b'{"v":18446744073709551615}'
    assert encode_stream_row(('v',), ('Int64',), ['-42']) == b'{"v":-42}'
    # Unconvertible quoted text in a numeric column stays a string for the encoder to
    # accept verbatim rather than corrupting.
    assert encode_stream_row(('v',), ('UInt64',), ['not-a-number']) == b'{"v":"not-a-number"}'
    # Floats and decimals keep their exact server text: no binary-float round-trip.
    assert encode_stream_row(('v',), ('Float64',), ['0.1']) == b'{"v":0.1}'
    assert encode_stream_row(('v',), ('Decimal(38, 10)',), ['12345678901234567890.1234567890']) == (
        b'{"v":12345678901234567890.1234567890}'
    )
    assert encode_stream_row(('v',), ('Nullable(Float64)',), [None]) == b'{"v":null}'
    # Non-finite floats: the server renders them as null by default (a documented deviation
    # from the Postgres "NaN"/"Infinity" string spellings); a server that quotes them
    # (output_format_json_quote_denormals) delivers strings, which pass through verbatim
    # rather than being reinterpreted.
    assert encode_stream_row(('v',), ('Float64',), [None]) == b'{"v":null}'
    assert encode_stream_row(('v',), ('Float64',), ['inf']) == b'{"v":"inf"}'
    assert encode_stream_row(('v',), ('Float64',), ['-nan']) == b'{"v":"-nan"}'
    # A String column holding digits is never reinterpreted as a number.
    assert encode_stream_row(('v',), ('String',), ['12345']) == b'{"v":"12345"}'
    # Booleans; legacy numeric spellings normalize by type.
    assert encode_stream_row(('v',), ('Bool',), [True]) == b'{"v":true}'
    assert encode_stream_row(('v',), ('Bool',), [0]) == b'{"v":false}'
    assert encode_stream_row(('v',), ('Bool',), [1]) == b'{"v":true}'
    assert encode_stream_row(('v',), ('Bool',), ['false']) == b'{"v":false}'
    # Strings with JSON escapes survive verbatim.
    assert encode_stream_row(('v',), ('String',), ['he said "hi"\nend']) == b'{"v":"he said \\"hi\\"\\nend"}'
    assert encode_stream_row(('v',), ('Nullable(String)',), [None]) == b'{"v":null}'
    # Temporal/UUID/IP families arrive as server-rendered strings.
    assert encode_stream_row(('d',), ('Date',), ['2026-08-28']) == b'{"d":"2026-08-28"}'
    assert encode_stream_row(('u',), ('UUID',), ['8b6fb1b5-94dd-447b-95a4-91f4ef118f4b']) == (
        b'{"u":"8b6fb1b5-94dd-447b-95a4-91f4ef118f4b"}'
    )


def test_value_contract_encodes_composite_types_as_nested_json():
    assert encode_stream_row(('a',), ('Array(String)',), [['x', None, 'y']]) == b'{"a":["x",null,"y"]}'
    assert encode_stream_row(('m',), ('Map(String, UInt64)',), [{'k': 1}]) == b'{"m":{"k":1}}'
    assert encode_stream_row(('t',), ('Tuple(UInt8, String)',), [None]) == b'{"t":null}'
    assert encode_stream_row(('t',), ('Tuple(UInt8, String)',), [[1, 'x']]) == b'{"t":[1,"x"]}'
    assert encode_stream_row(('j',), ('JSON',), [{'nested': [1, True]}]) == b'{"j":{"nested":[1,true]}}'
    assert encode_stream_row(('n',), ('Array(Array(Nullable(UInt8)))',), [[[1, None], []]]) == (b'{"n":[[1,null],[]]}')


def test_value_contract_producer_emits_pinned_row_json(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(
        names=(
            'null_value',
            'bool_value',
            'int_value',
            'big_int_value',
            'float_value',
            'decimal_value',
            'text_value',
            'date_value',
            'json_value',
            'array_value',
            'map_value',
        ),
        types=(
            'Nullable(String)',
            'Bool',
            'Int64',
            'UInt64',
            'Float64',
            'Decimal(38, 10)',
            'String',
            'Date',
            'JSON',
            'Array(Nullable(String))',
            'Map(String, UInt64)',
        ),
        rows=[
            [
                None,
                True,
                42,
                '18446744073709551615',
                '0.1',
                '12345678901234567890.1234567890',
                'héllo "quoted"',
                '2026-08-28',
                {'nested': [1, None, True], 'price': 1.10},
                ['x', None, ['y', 'z']],
                {'a': 1},
            ]
        ],
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    parsed = json.loads(page, parse_float=Decimal)['data']['items'][0]
    assert parsed == {
        'null_value': None,
        'bool_value': True,
        'int_value': 42,
        'big_int_value': 18446744073709551615,
        'float_value': Decimal('0.1'),
        'decimal_value': Decimal('12345678901234567890.1234567890'),
        'text_value': 'héllo "quoted"',
        'date_value': '2026-08-28',
        'json_value': {'nested': [1, None, True], 'price': Decimal('1.1')},
        'array_value': ['x', None, ['y', 'z']],
        'map_value': {'a': 1},
    }
    # Exact text preservation is byte-pinned for the numeric families.
    assert b'"big_int_value":18446744073709551615' in page
    assert b'"decimal_value":12345678901234567890.1234567890' in page
    assert b'"float_value":0.1' in page
    assert b'"json_value":{"nested":[1,null,true],"price":1.1}' in page


def test_value_contract_rejects_row_lines_that_are_not_json_arrays(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["value"]', '["UInt8"]', '{"value": 1}'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'not a JSON array')


def test_value_contract_fails_closed_on_invalid_utf8_row_lines(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["value"]', '["String"]', b'["\xff\xfe"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed')
    # The offending row bytes never appear in the emitted events.
    assert b'\xff\xfe' not in json.dumps([event.metadata for event in events]).encode('utf-8', 'surrogateescape')


def test_value_contract_rejects_row_width_mismatch(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["a", "b"]', '["UInt8", "UInt8"]', '[1]'))

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'row width')


@pytest.mark.parametrize(
    'type_string, expected',
    [
        ('UInt64', 'integer'),
        ('Nullable(UInt64)', 'integer'),
        ('LowCardinality(Nullable(Int128))', 'integer'),
        ('SimpleAggregateFunction(sum, UInt64)', 'integer'),
        ('Decimal(10, 2)', 'decimal'),
        ('Decimal128(4)', 'decimal'),
        ('Nullable(Decimal(38, 10))', 'decimal'),
        ('Float64', 'float'),
        ('Nullable(Float32)', 'float'),
        ('Bool', 'bool'),
        ('String', 'other'),
        ('Array(UInt64)', 'other'),
        ('Date', 'other'),
        ('UUID', 'other'),
    ],
)
def test_type_family_classifies_type_strings(type_string, expected):
    assert remote_query.type_family(type_string) == expected


def test_base_type_name_peels_wrappers():
    assert remote_query.base_type_name('Nullable(LowCardinality(String))') == 'String'
    # Wrappers peel transitively, through SimpleAggregateFunction's second argument too.
    assert remote_query.base_type_name('SimpleAggregateFunction(any, Nullable(UInt8))') == 'UInt8'
    assert remote_query.base_type_name('Array(String)') == 'Array(String)'


# ---------------------------------------------------------------------------
# Upload client HTTP contract
# ---------------------------------------------------------------------------


def _upload_creds(**overrides):
    defaults = {
        'base_url': BASE_URL,
        'upload_id': UPLOAD_ID,
        'api_key': 'TEST_API_KEY',
        'app_key': 'TEST_APP_KEY',
        'token': TOKEN,
        'test_drive': 'its-agent-intake-poc',
    }
    defaults.update(overrides)
    return remote_query.UploadCredentials(**defaults)


def test_requests_upload_client_uses_exact_page_aware_http_contract(monkeypatch):
    import requests

    captured = []

    def fake_request(method, url, headers=None, data=None, timeout=None):
        captured.append(
            SimpleNamespace(method=method, url=url, headers=dict(headers or {}), data=data, timeout=timeout)
        )
        return SimpleNamespace(status_code=200, content=b'{"upload_id": "upload-01k"}')

    monkeypatch.setattr(requests, 'request', fake_request)
    monkeypatch.setattr(remote_query.time, 'sleep', lambda _seconds: None)

    creds = _upload_creds()
    client = remote_query.RequestsUploadClient()
    payload = b'abcdefgh'
    client.put_part(creds, 2, 3, payload, hashlib.sha256(payload).hexdigest(), 4)

    test_drive_header = 'test-drive-its-agent-intake-poc'

    put = captured[0]
    assert put.method == 'PUT'
    assert put.url == '{}/uploads/{}/pages/2/parts/3'.format(BASE_URL, UPLOAD_ID)
    assert put.headers['Content-Type'] == 'application/octet-stream'
    assert put.headers['X-DD-Part-SHA256'] == hashlib.sha256(payload).hexdigest()
    assert put.headers['X-DD-Part-Bytes'] == '8'
    assert put.headers['X-DD-Part-Rows'] == '4'
    assert put.headers['dd-api-key'] == 'TEST_API_KEY'
    assert put.headers['dd-application-key'] == 'TEST_APP_KEY'
    assert put.headers['Authorization'] == 'Bearer ' + TOKEN
    # The Test Drive routing header is derived from the validated Agent-config name as
    # ``test-drive-<name>: 1`` and rides on every upload request: part PUT, page finalize,
    # run finalize, and abort.
    assert put.headers[test_drive_header] == '1'
    assert put.data == payload
    assert put.timeout == remote_query.REMOTE_QUERY_UPLOAD_HTTP_TIMEOUT
    assert remote_query.REMOTE_QUERY_UPLOAD_HTTP_READ_TIMEOUT_SECONDS == 300

    client.finalize_page(creds, 2)
    page_finalize = captured[1]
    assert page_finalize.method == 'POST'
    assert page_finalize.url == '{}/uploads/{}/pages/2/finalize'.format(BASE_URL, UPLOAD_ID)
    assert page_finalize.headers['Content-Type'] == 'application/json'
    assert page_finalize.headers[test_drive_header] == '1'
    assert page_finalize.data == b'{}'

    response = client.finalize_run(creds)
    run_finalize = captured[2]
    assert run_finalize.method == 'POST'
    assert run_finalize.url == '{}/uploads/{}/finalize'.format(BASE_URL, UPLOAD_ID)
    assert run_finalize.headers[test_drive_header] == '1'
    assert run_finalize.data == b'{}'
    assert response == {'upload_id': 'upload-01k'}

    client.abort(creds)
    abort = captured[3]
    assert abort.method == 'POST'
    assert abort.url == '{}/uploads/{}/abort'.format(BASE_URL, UPLOAD_ID)
    assert abort.headers[test_drive_header] == '1'
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

    creds = _upload_creds(test_drive=None)
    client = remote_query.RequestsUploadClient()
    payload = b'ijklmnop'
    client.put_part(creds, 1, 1, payload, hashlib.sha256(payload).hexdigest(), 1)

    # The same part request (same page/part URL, same checksum header, same body) is
    # retried verbatim, so an idempotent server-side replay by (part, checksum) cannot
    # double-count bytes.
    assert len(calls) == 2
    assert calls[0].url == calls[1].url
    assert calls[0].url == '{}/uploads/{}/pages/1/parts/1'.format(BASE_URL, UPLOAD_ID)
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

    creds = _upload_creds(test_drive=None)
    client = remote_query.RequestsUploadClient()

    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
        client.put_part(creds, 0, 1, b'x', 'deadbeef', 0)
    assert excinfo.value.code == 'upload_failed'
    assert excinfo.value.retryable is False
    assert len(calls) == 1


@pytest.mark.parametrize(
    'raw, expected',
    [
        ('its-agent-intake-poc', 'its-agent-intake-poc'),
        ('  its-agent-intake-poc  ', 'its-agent-intake-poc'),
        ('ITS-AGENT-INTAKE-POC', 'its-agent-intake-poc'),
        ('its-agent-intake-2', 'its-agent-intake-2'),
    ],
)
def test_validate_test_drive_name_normalizes_valid_test_drive_names(raw, expected):
    assert remote_query._validate_test_drive_name(raw) == expected


@pytest.mark.parametrize(
    'raw',
    [
        None,
        '',
        '   ',
        'its-agent-intake-poc:1',
        'its-agent-intake-poc\r\nX-Other: 1',
        'its agent intake poc',
        '-its-agent-intake-poc',
        'its-agent-intake-poc-',
        'a' * 64,
    ],
)
def test_validate_test_drive_name_rejects_invalid_names_fail_closed(raw):
    assert remote_query._validate_test_drive_name(raw) is None


def test_requests_upload_client_omits_test_drive_header_when_not_configured(monkeypatch):
    import requests

    captured = []

    def fake_request(method, url, headers=None, data=None, timeout=None):
        captured.append(SimpleNamespace(headers=dict(headers or {})))
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', fake_request)
    monkeypatch.setattr(remote_query.time, 'sleep', lambda _seconds: None)

    creds = _upload_creds(test_drive=None)
    client = remote_query.RequestsUploadClient()
    client.put_part(creds, 0, 1, b'x', 'deadbeef', 0)

    # With no Test Drive configured the permanent-service path is preserved: no header whose
    # name starts with the test-drive prefix is sent on the upload request.
    put = captured[0]
    assert not any(name.startswith(remote_query.REMOTE_QUERY_UPLOAD_TEST_DRIVE_HEADER_PREFIX) for name in put.headers)


@pytest.mark.parametrize(
    'config_value, expected',
    [
        ('  ITS-AGENT-INTAKE-POC  ', 'its-agent-intake-poc'),
        ('', None),
    ],
)
def test_resolve_upload_credentials_reads_validated_test_drive_from_agent_config(monkeypatch, config_value, expected):
    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        if key == remote_query.REMOTE_QUERY_UPLOAD_TEST_DRIVE_CONFIG_KEY:
            return config_value
        return None

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)

    creds = remote_query._resolve_upload_credentials(
        remote_query.RemoteQueryResultDelivery.model_validate(valid_result_delivery())
    )

    assert creds.test_drive == expected
    assert creds.api_key == 'TEST_API_KEY'
    assert creds.app_key == 'TEST_APP_KEY'
    assert creds.base_url == BASE_URL
    assert creds.upload_id == UPLOAD_ID
    assert creds.token == TOKEN


@pytest.mark.parametrize(
    'body, expected',
    [
        (b'', {}),
        (b'{}', {}),
        (b'{"upload_id": "upload-01k", "pages": []}', {'upload_id': 'upload-01k', 'pages': []}),
    ],
)
def test_parse_finalize_run_body_accepts_json_objects(body, expected):
    assert remote_query.parse_finalize_run_body(body) == expected


@pytest.mark.parametrize('body', [b'not json', b'[]', b'"x"'])
def test_parse_finalize_run_body_fails_closed_on_unusable_bodies(body):
    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
        remote_query.parse_finalize_run_body(body)
    assert excinfo.value.code == 'invalid_receipt'


def test_verify_run_finalize_response_fails_closed_on_identity_mismatch():
    remote_query.verify_run_finalize_response({}, UPLOAD_ID)
    remote_query.verify_run_finalize_response({'upload_id': ''}, UPLOAD_ID)
    remote_query.verify_run_finalize_response({'upload_id': UPLOAD_ID}, UPLOAD_ID)
    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
        remote_query.verify_run_finalize_response({'upload_id': 'other-upload'}, UPLOAD_ID)
    assert excinfo.value.code == 'invalid_receipt'


# ---------------------------------------------------------------------------
# Failure, timeout, and cancellation flows
# ---------------------------------------------------------------------------


def test_stream_uploads_pages_and_finalizes_run_in_order(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(
        part_bytes=8,
        maxFileBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX),
    )
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # All parts of page 0 precede its page finalize; page 1 parts follow; run finalize is
    # the last call and happens exactly once.
    batches = [call[0] for call in fake.put_part_calls]
    assert batches == sorted(batches)
    assert fake.page_finalize_calls == [0, 1]
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 0


def test_stream_aborts_on_part_upload_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient(
        raise_on_put=remote_query.RemoteQueryFailure('upload_failed', 'transient exhausted', retryable=True)
    )

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'upload_failed')
    assert len(fake.put_part_calls) == 1
    assert fake.abort_calls == 1
    assert fake.run_finalize_calls == 0
    # The response stream is closed even though the query itself succeeded.
    assert clickhouse_client.stream.closed


def test_stream_fails_closed_on_partial_page_finalization(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient(
        raise_on_page_finalize=remote_query.RemoteQueryFailure('upload_failed', 'page finalize rejected')
    )

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'upload_failed')
    assert fake.page_finalize_calls == [0]
    assert fake.run_finalize_calls == 0
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_fails_closed_on_run_finalize_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient(
        raise_on_run_finalize=remote_query.RemoteQueryFailure('upload_failed', 'run finalize rejected')
    )

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'upload_failed')
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_fails_closed_on_run_finalize_identity_mismatch(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient(run_finalize_response={'upload_id': 'other-upload'})

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'invalid_receipt')
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_enforces_timeout_with_retryable_error(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1], [2], [3]])
    request = valid_request()
    request['resultDelivery']['limits']['timeoutMs'] = 1000
    values = iter([0.0, 0.0] + [10.0] * 50)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: next(values))

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert clickhouse_client.stream.closed
    assert clickhouse_client.closed


def test_stream_maps_server_error_to_query_failed(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1]]),
        raw_stream_error=DatabaseError('Code: 60. DB::Exception: Table default.remote_query_identity does not exist'),
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    # The server's message (table names, query text) never crosses the callback.
    assert_failed_event(events, 'query_failed')
    assert 'remote_query_identity' not in str(events)
    assert fake.abort_calls == 1


def test_stream_maps_transport_error_to_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1]]),
        raw_stream_error=OperationalError('Error HTTPSConnectionPool ... Max retries exceeded'),
    )

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'target_unavailable')
    assert 'HTTPSConnectionPool' not in str(events)


def test_stream_maps_client_creation_failure_to_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)

    def broken_factory(_check, _limits):
        raise OperationalError('connection refused with SECRET_DO_NOT_LOG')

    request = valid_request()
    events = list(
        iter_agent_rpc_stream_events(
            request, StaticClickhouseCheckRegistry([make_check()]), FakeUploadClient(), broken_factory
        )
    )

    assert_failed_event(events, 'target_unavailable')
    assert 'SECRET_DO_NOT_LOG' not in str(events)


def test_stream_maps_mid_stream_connection_drop_to_retryable_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1], [2], [3]]),
        read_error=urllib3.exceptions.ProtocolError('Connection broken: server closed mid-stream'),
    )

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout', 'interrupted')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert clickhouse_client.stream.closed


def test_stream_maps_mid_stream_read_timeout_to_retryable_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1], [2], [3]]),
        read_error=urllib3.exceptions.ReadTimeoutError(None, 'http://test', 'timed out'),
    )

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True


@pytest.mark.parametrize('is_cancelled', [lambda: True, True], ids=['callable', 'bool'])
def test_stream_reports_cancellation_as_retryable(monkeypatch, is_cancelled):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1], [2]])
    check = make_check()
    # Both runtime shapes: the Agent check object carries a bool ``is_cancelled`` attribute;
    # a callable hook is the other supported shape. Both must fail the run as retryable.
    check.is_cancelled = is_cancelled

    events = collect_events(valid_request(), check, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'cancelled')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert clickhouse_client.stream.closed


def test_stream_proceeds_when_bool_is_cancelled_is_false(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    check = make_check()
    check.is_cancelled = False

    events = collect_events(valid_request(), check, clickhouse_client=make_client(rows=[[1]]))

    assert_success(events)


def test_stream_ignores_check_without_cancel_hook(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # make_check deliberately has no is_cancelled attribute.

    events = collect_events(valid_request(), make_check(), clickhouse_client=make_client(rows=[[1]]))

    assert_success(events)


def test_stream_target_unavailable_when_check_cannot_create_clients(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # No create_remote_query_client on the fake check and no factory injected.
    request = valid_request()
    events = list(
        iter_agent_rpc_stream_events(request, StaticClickhouseCheckRegistry([make_check()]), FakeUploadClient(), None)
    )

    assert_failed_event(events, 'target_unavailable')
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_entry_propagates_callback_failure_without_upload(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)

    def emit(event_type, metadata_json, payload):
        raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        execute_agent_rpc_stream_copy(json.dumps(valid_request()), make_check(), emit)


# ---------------------------------------------------------------------------
# Integration: one focused case against a real ClickHouse (docker fixture)
# ---------------------------------------------------------------------------

# Remote query execution needs the JSONCompactEachRowWithNamesAndTypes format, whose
# WithNamesAndTypes variants only exist from 22.7 on (21.8 registers the plain format).
UNSUPPORTED_REMOTE_QUERY_VERSIONS = {'18', '19', '20', '21.8'}


def _is_remote_query_supported():
    from .common import CLICKHOUSE_VERSION

    if CLICKHOUSE_VERSION == 'latest':
        return True
    return CLICKHOUSE_VERSION not in UNSUPPORTED_REMOTE_QUERY_VERSIONS


pytestmark_integration = pytest.mark.skipif(
    not _is_remote_query_supported(),
    reason='Remote queries need the JSONCompactEachRowWithNamesAndTypes format (ClickHouse 22.7+)',
)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
def test_remote_query_produces_json_pages_against_real_clickhouse(instance, monkeypatch):
    """End-to-end producer path against a real server: schema, values, parts, receipt."""
    from datadog_checks.clickhouse import ClickhouseCheck

    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        return None

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)
    check = ClickhouseCheck('clickhouse', {}, [instance])

    request = {
        'operation': 'produce_json_pages',
        'target': {'host': instance['server'], 'port': int(instance['port']), 'dbname': 'default'},
        'query': 'SELECT 1 AS value',
        'includeSchema': True,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 1,
            'uploadId': UPLOAD_ID,
            'baseUrl': BASE_URL,
            'token': TOKEN,
            'partBytes': 32,
            'limits': valid_limits(),
        },
    }
    fake = FakeUploadClient()

    # No client factory is injected: the real check creates the per-run client itself.
    events = list(iter_agent_rpc_stream_events(request, StaticClickhouseCheckRegistry([check]), fake, None))

    final = assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0]
    page = json.loads(pages[0])
    assert page['version'] == 1
    assert page['run_id'] == RUN_ID
    assert page['task_id'] == TASK_ID
    assert page['batch_index'] == 0
    assert page['record_offset'] == 0
    assert page['schema'] == [{'column_name': 'value', 'vendor_data_type': 'UInt8'}]
    assert page['data']['items'] == [{'value': 1}]
    # Page bytes streamed in bounded parts; part numbers 1-based and contiguous; rows exact.
    assert [call[1] for call in fake.put_part_calls] == list(range(1, len(fake.put_part_calls) + 1))
    assert sum(call[4] for call in fake.put_part_calls) == 1
    assert fake.page_finalize_calls == [0]
    assert fake.run_finalize_calls == 1
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 1,
        'totalRows': 1,
        'totalBytes': len(pages[0]),
    }
