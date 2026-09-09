# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import json
import re
from decimal import Decimal
from types import SimpleNamespace

import pytest
import urllib3.exceptions
from clickhouse_connect.driver.exceptions import DatabaseError, OperationalError

from datadog_checks.base.utils import remote_queries as rq
from datadog_checks.clickhouse import remote_query
from datadog_checks.clickhouse.remote_query import (
    StaticClickhouseCheckRegistry,
    execute_agent_rpc_stream_copy,
    iter_agent_rpc_stream_events,
)

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'
BASE_URL = 'https://dd.datad0g.com/api/unstable/its-agent-intake'
TOKEN = 'scoped-upload-token'
# The Agent-reported hostname every fake check carries, stamped into every page envelope.
AGENT_HOSTNAME = 'rq-proof-agent-a'


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

    def __init__(
        self,
        body,
        readonly_level=0,
        chunk_size=32,
        raw_stream_error=None,
        read_error=None,
        error_at=None,
        read_log=None,
    ):
        self.server_settings = (
            {'readonly': SimpleNamespace(value=str(readonly_level))} if readonly_level is not None else {}
        )
        self._body = body
        self._chunk_size = chunk_size
        self._raw_stream_error = raw_stream_error
        self._read_error = read_error
        self._error_at = error_at
        self._read_log = read_log
        self.raw_stream_calls = []
        self.stream = None
        self.closed = False

    def raw_stream(self, query, settings=None, fmt=None):
        self.raw_stream_calls.append({'query': query, 'settings': dict(settings or {}), 'fmt': fmt})
        if self._raw_stream_error is not None:
            raise self._raw_stream_error
        self.stream = FakeStream(
            self._body,
            chunk_size=self._chunk_size,
            read_error=self._read_error,
            error_at=self._error_at,
            read_log=self._read_log,
        )
        return self.stream

    def close(self):
        self.closed = True


class FakeUploadClient:
    def __init__(
        self,
        run_finalize_response=None,
        put_page_response=None,
        raise_on_put_page=None,
        raise_on_run_finalize=None,
        put_log=None,
    ):
        # SimpleNamespace(batch_index, record_offset, page_bytes, rows, sha256_hex, payload)
        self.put_page_calls = []
        self.run_finalize_calls = 0
        self.abort_calls = 0
        self.raise_on_put_page = raise_on_put_page
        self.raise_on_run_finalize = raise_on_run_finalize
        self.run_finalize_response = (
            run_finalize_response if run_finalize_response is not None else {'upload_id': UPLOAD_ID}
        )
        # When unset, the authoritative receipt echoes the producer's own page metadata;
        # tests pass a mapping (or a callable taking the page metadata) to mutate it.
        self.put_page_response = put_page_response
        self.put_log = put_log

    def put_page(self, creds, page, body):
        payload = body.read()
        self.put_page_calls.append(
            SimpleNamespace(
                batch_index=page.batch_index,
                record_offset=page.record_offset,
                page_bytes=page.page_bytes,
                rows=page.rows,
                sha256_hex=page.sha256_hex,
                payload=payload,
            )
        )
        if self.put_log is not None:
            self.put_log.append(('put', page.batch_index, page.page_bytes, page.rows))
        if self.raise_on_put_page is not None:
            raise self.raise_on_put_page
        if self.put_page_response is not None:
            response = self.put_page_response
            if callable(response):
                response = response(page)
        else:
            response = {
                'batch_index': page.batch_index,
                'key': 'agent-intake-test/pages/{}.json'.format(page.batch_index),
                'record_offset': page.record_offset,
                'bytes': page.page_bytes,
                'rows': page.rows,
                'sha256': page.sha256_hex,
            }
        return response

    def finalize_run(self, creds):
        self.run_finalize_calls += 1
        if self.raise_on_run_finalize is not None:
            raise self.raise_on_run_finalize
        return self.run_finalize_response

    def abort(self, creds):
        self.abort_calls += 1


def make_check(
    server='localhost',
    port=8123,
    db='default',
    pool_manager=None,
    check_database_identifier=None,
    hostname=AGENT_HOSTNAME,
):
    check = SimpleNamespace(
        _config=SimpleNamespace(server=server, port=port, db=db),
        _pool_manager=pool_manager if pool_manager is not None else object(),
        hostname=hostname,
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
        'artifactVersion': 2,
        'uploadId': UPLOAD_ID,
        'baseUrl': BASE_URL,
        'token': TOKEN,
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


def bounded_request(query='SELECT 1 AS value', **limit_overrides):
    """A request with small limits so page boundaries are cheap to exercise."""
    limits = valid_limits(
        maxFileBytes=1024, maxResultBytes=8192, maxRowBytes=64, maxColumns=8, maxSchemaBytes=256, maxPages=4
    )
    limits.update(limit_overrides)
    # Overrides may shrink maxFileBytes below the default schema budget; the executor
    # rejects a schema budget beyond the page budget, so keep the pair consistent.
    limits['maxSchemaBytes'] = min(limits['maxSchemaBytes'], limits['maxFileBytes'])
    request = valid_request(query=query)
    request['resultDelivery']['limits'] = limits
    return request


def patch_upload_credentials(monkeypatch):
    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        return None

    monkeypatch.setattr(rq.datadog_agent, 'get_config', get_config)


def patch_allowlist_disabled(monkeypatch):
    monkeypatch.setattr(rq, 'is_query_allowlist_enabled', lambda: False)


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


def prefix_bytes(record_offset=0, agent_hostname=AGENT_HOSTNAME, schema_json=None):
    return rq.page_prefix(
        run_id=RUN_ID,
        task_id=TASK_ID,
        record_offset=record_offset,
        agent_hostname=agent_hostname,
        schema_json=schema_json,
    )


def assembled_pages(fake_client):
    """Each completed page's exact uploaded bytes, keyed by batch index."""
    return {call.batch_index: call.payload for call in fake_client.put_page_calls}


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
    with pytest.raises(rq.RemoteQueryFailure) as excinfo:
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


def test_query_allowlist_holds_exactly_nine_proof_queries():
    # The Agent-side allowlist mirrors these queries one for one, so the count and the
    # three fixed queries are cross-repo contract, not local convenience.
    assert len(remote_query.REMOTE_QUERY_QUERY_ALLOWLIST) == 9
    for query in (
        remote_query.REMOTE_QUERY_SEED_QUERY,
        remote_query.REMOTE_QUERY_IDENTITY_QUERY,
        remote_query.REMOTE_QUERY_BINARY_QUERY,
    ):
        assert query in remote_query.REMOTE_QUERY_QUERY_ALLOWLIST


def test_proof_payload_queries_are_deterministic_bounded_and_exact():
    # The intended sizes are the pinned power-of-two byte counts, 1 MiB through 32 MiB.
    assert remote_query.REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES == tuple(1024 * 1024 << shift for shift in range(6))
    for size_bytes in remote_query.REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES:
        query = remote_query._proof_payload_query(size_bytes)
        # Deterministic construction: one size builds one stable SQL string, and the
        # allowlist carries exactly that string.
        assert query == remote_query._proof_payload_query(size_bytes)
        assert query in remote_query.REMOTE_QUERY_QUERY_ALLOWLIST
        repeat_arguments = [int(match) for match in re.findall(r"repeat\('x', (\d+)\)", query)]
        # Real servers reject repeat() counts above the hard 1,000,000 cap (Code 131).
        assert repeat_arguments
        assert all(argument <= remote_query.REMOTE_QUERY_REPEAT_CAP for argument in repeat_arguments)
        # The concatenated parts sum to exactly the intended payload byte count.
        assert sum(repeat_arguments) == size_bytes


def test_proof_payload_query_rejects_non_positive_sizes():
    with pytest.raises(ValueError):
        remote_query._proof_payload_query(0)


def test_stream_accepts_large_payload_proof_queries(monkeypatch):
    patch_upload_credentials(monkeypatch)
    for size_bytes in remote_query.REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES:
        clickhouse_client = make_client(names=('payload',), types=('String',), rows=[['x']])
        request = valid_request(query=remote_query._proof_payload_query(size_bytes))

        events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

        assert_success(events)


def test_stream_accepts_identity_and_binary_proof_queries(monkeypatch):
    patch_upload_credentials(monkeypatch)
    for query in (remote_query.REMOTE_QUERY_IDENTITY_QUERY, remote_query.REMOTE_QUERY_BINARY_QUERY):
        clickhouse_client = make_client(names=('v',), types=('String',), rows=[['x']])
        request = valid_request(query=query)

        events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

        assert_success(events)


def test_stream_accepts_every_allowlisted_query(monkeypatch):
    patch_upload_credentials(monkeypatch)
    for query in sorted(remote_query.REMOTE_QUERY_QUERY_ALLOWLIST):
        clickhouse_client = make_client(names=('payload',), types=('String',), rows=[['x']])
        request = valid_request(query=query)

        events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

        assert_success(events)


@pytest.mark.parametrize(
    'query',
    [
        # Within the repeat cap and executable on a real server, but not allowlisted.
        "SELECT repeat('x', 1000000) AS payload",
        # The same 1 MiB total as an allowlisted query but built differently: the allowlist
        # matches exact query strings, not payload sizes.
        "SELECT concat(repeat('x', 500000), repeat('x', 548576)) AS payload",
    ],
)
def test_stream_rejects_nearby_non_allowlisted_queries(query):
    clickhouse_client = make_client(rows=[[1]])
    request = valid_request(query=query)

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'invalid_request', 'query is not allowlisted')
    assert clickhouse_client.raw_stream_calls == []


def test_stream_binary_proof_query_preserves_nul_payload_exactly(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # Real ClickHouse (22.7/24.8/26.3) renders unhex('006162') in the stream format as
    # ["\u0000ab"]: the NUL is JSON-escaped, never a raw control byte. The executor must
    # keep the payload exactly, with the NUL still escaped in the page JSON.
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["payload"]', '["String"]', '["\\u0000ab"]'))
    fake = FakeUploadClient()

    events = collect_events(
        valid_request(query=remote_query.REMOTE_QUERY_BINARY_QUERY),
        make_check(),
        upload_client=fake,
        clickhouse_client=clickhouse_client,
    )

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert json.loads(page)['data'] == [{'payload': '\x00ab'}]
    assert b'"payload":"\\u0000ab"' in page


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

    monkeypatch.setattr(rq.datadog_agent, 'get_config', get_config)

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
    assert started['resultDelivery']['artifactVersion'] == 2
    assert 'partBytes' not in started['resultDelivery']
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


def test_producer_writes_exact_v2_envelope_json(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # Schema disabled: the schema key is omitted entirely, never null/[].
    assert page == (prefix_bytes() + b'{"value":1}' + rq.PAGE_SUFFIX)
    parsed = json.loads(page)
    assert parsed == {
        'contract_version': 2,
        'crawl_id': RUN_ID,
        'task_id': TASK_ID,
        'agent_hostname': AGENT_HOSTNAME,
        'record_offset': 0,
        'data': [{'value': 1}],
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
    assert fake.put_page_calls == []
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
    assert 'batch_index' not in parsed
    assert parsed['record_offset'] == 0
    assert parsed['schema'] == [{'column_name': 'value', 'vendor_data_type': 'UInt8'}]
    assert parsed['data'] == []
    assert final['upload_receipt']['pageCount'] == 1
    assert final['upload_receipt']['totalRows'] == 0
    assert final['upload_receipt']['totalBytes'] == len(pages[0])
    assert [call.batch_index for call in fake.put_page_calls] == [0]
    assert fake.run_finalize_calls == 1


def test_producer_rejects_header_missing_type_row(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["value"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'header rows')
    assert fake.put_page_calls == []


def test_producer_rejects_header_with_mismatched_column_counts(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body('["value", "extra"]', '["UInt8"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'header rows')
    assert fake.put_page_calls == []


@pytest.mark.parametrize('header', ['["value", ""]', '[1, 2]', '"value"', 'not json'])
def test_producer_rejects_malformed_header_rows(monkeypatch, header):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(raw_stream_body(header, '["UInt8"]'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed')
    assert fake.put_page_calls == []


def test_producer_rejects_duplicate_result_column_names_before_row_data(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(names=('value', 'value'), types=('UInt8', 'UInt8'), rows=[[1, 1]])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'duplicate_columns', 'value')
    assert fake.put_page_calls == []


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
        len(prefix_bytes(schema_json=schema_json)) + len(longest_row_bytes) + len(rq.PAGE_SUFFIX)
    )
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0, 1]
    parsed_pages = [json.loads(page) for page in pages.values()]
    assert 'batch_index' not in parsed_pages[0]
    assert parsed_pages[0]['record_offset'] == 0
    assert parsed_pages[0]['data'] == [{'city': 'New York', 'country': 'USA'}]
    assert parsed_pages[1]['record_offset'] == 1
    assert parsed_pages[1]['data'] == [{'city': 'Paris', 'country': 'France'}]
    # The schema repeats identically and in result-column order on every page.
    assert parsed_pages[0]['schema'] == parsed_pages[1]['schema'] == schema_entries
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
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
    assert parsed['data'] == [{'count': None, 'name': 'x', 'flag': True}]


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
    request = bounded_request()
    limits = request['resultDelivery']['limits']
    limits['maxFileBytes'] = prefix_len + len(ROW_BYTES) + 1 + len(ROW_BYTES) + len(rq.PAGE_SUFFIX) + extra_file_bytes
    # Same constraint as bounded_request: the schema budget must stay within the page budget.
    limits['maxSchemaBytes'] = min(limits['maxSchemaBytes'], limits['maxFileBytes'])
    return request


def two_row_client(**stream_kwargs):
    return make_client(names=('payload',), types=('String',), rows=[['aaaa'], ['aaaa']], **stream_kwargs)


def test_page_split_row_too_large_when_row_exceeds_max_row_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = bounded_request(maxRowBytes=len(ROW_BYTES) - 1)
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    assert fake.put_page_calls == []


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


def test_page_upload_streams_before_the_result_stream_is_exhausted(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    request = bounded_request(
        maxFileBytes=1024,
        maxResultBytes=16 * 1024 * 1024,
        maxRowBytes=1024,
        maxPages=4096,
    )
    # Enough rows that the body spans several 256 KiB stream reads, so page uploads must
    # interleave with reads instead of buffering the whole result first.
    rows = [[index] for index in range(40000)]
    clickhouse_client = FakeClickhouseClient(stream_body(('payload',), ('UInt32',), rows), read_log=order_log)
    fake = FakeUploadClient(put_log=order_log)

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # Pages are uploaded while rows are still being read from the result stream: the
    # producer never buffers the complete result before uploading, only one bounded
    # page at a time.
    first_put = next(index for index, entry in enumerate(order_log) if entry[0] == 'put')
    last_read = max(index for index, entry in enumerate(order_log) if entry[0] == 'read')
    assert first_put < last_read
    assert clickhouse_client.stream.read_count > 2
    # Pages are contiguous zero-based, and all rows are accounted for exactly once.
    page_indexes = sorted({call.batch_index for call in fake.put_page_calls})
    assert page_indexes == list(range(len(page_indexes)))
    assert sum(call.rows for call in fake.put_page_calls) == 40000
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
    parsed = json.loads(page, parse_float=Decimal)['data'][0]
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


# ---------------------------------------------------------------------------
# Failure, timeout, and cancellation flows
# ---------------------------------------------------------------------------


def test_stream_uploads_pages_and_finalizes_run_in_order(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(maxFileBytes=prefix_len + len(ROW_BYTES) + len(rq.PAGE_SUFFIX))
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # Pages are uploaded in order, each exactly once, and run finalize is the last call.
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 0


def test_stream_aborts_on_page_upload_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient(
        raise_on_put_page=rq.RemoteQueryFailure('upload_failed', 'transient exhausted', retryable=True)
    )

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'upload_failed')
    assert len(fake.put_page_calls) == 1
    assert fake.abort_calls == 1
    assert fake.run_finalize_calls == 0
    # The response stream is closed even though the query itself succeeded.
    assert clickhouse_client.stream.closed


def test_stream_fails_closed_on_page_receipt_mismatch(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = two_row_boundary_request(monkeypatch, extra_file_bytes=-1)
    clickhouse_client = two_row_client()
    bad_receipt = {
        'batch_index': 0,
        'key': 'agent-intake-test/pages/0.json',
        'record_offset': 0,
        'bytes': 123,
        'rows': 1,
        'sha256': 'f' * 64,
    }
    fake = FakeUploadClient(put_page_response=bad_receipt)

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    # A receipt that disagrees with the produced page fails the run: page 1 is never
    # produced, the session is aborted, and no partial receipt is emitted.
    assert_failed_event(events, 'invalid_receipt')
    assert [call.batch_index for call in fake.put_page_calls] == [0]
    assert fake.run_finalize_calls == 0
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_fails_closed_on_run_finalize_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient(raise_on_run_finalize=rq.RemoteQueryFailure('upload_failed', 'run finalize rejected'))

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
# Integration: focused cases against a real ClickHouse (docker fixture)
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


def real_server_request(instance, query, include_schema=False):
    """A request whose limits admit single-row multi-MiB proof payloads.

    ``maxRowBytes``/``maxFileBytes`` are sized for one 32 MiB payload row plus its envelope,
    and the timeout allows the largest payload to stream through.
    """
    limits = valid_limits(maxRowBytes=40 * 1024 * 1024, maxFileBytes=64 * 1024 * 1024, timeoutMs=30_000)
    request = {
        'operation': 'produce_json_pages',
        'target': {'host': instance['server'], 'port': int(instance['port']), 'dbname': 'default'},
        'query': query,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 2,
            'uploadId': UPLOAD_ID,
            'baseUrl': BASE_URL,
            'token': TOKEN,
            'limits': limits,
        },
    }
    if include_schema:
        request['includeSchema'] = True
    return request


def patch_real_check(monkeypatch, instance):
    """Configure Agent credentials and build a real check for the running fixture."""
    from datadog_checks.clickhouse import ClickhouseCheck

    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        return None

    monkeypatch.setattr(rq.datadog_agent, 'get_config', get_config)
    return ClickhouseCheck('clickhouse', {}, [instance])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
def test_remote_query_produces_json_pages_against_real_clickhouse(instance, monkeypatch):
    """End-to-end producer path against a real server: schema, values, page upload, receipt."""
    check = patch_real_check(monkeypatch, instance)

    request = {
        'operation': 'produce_json_pages',
        'target': {'host': instance['server'], 'port': int(instance['port']), 'dbname': 'default'},
        'query': 'SELECT 1 AS value',
        'includeSchema': True,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 2,
            'uploadId': UPLOAD_ID,
            'baseUrl': BASE_URL,
            'token': TOKEN,
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
    assert page['contract_version'] == 2
    assert page['crawl_id'] == RUN_ID
    assert page['task_id'] == TASK_ID
    assert 'batch_index' not in page
    assert page['record_offset'] == 0
    assert page['schema'] == [{'column_name': 'value', 'vendor_data_type': 'UInt8'}]
    assert page['data'] == [{'value': 1}]
    # One complete page uploaded as one direct PUT: exact whole-page identity, rows exact.
    (page_call,) = fake.put_page_calls
    assert page_call.batch_index == 0
    assert page_call.record_offset == 0
    assert page_call.page_bytes == len(pages[0])
    assert page_call.rows == 1
    assert page_call.sha256_hex == hashlib.sha256(pages[0]).hexdigest()
    assert fake.run_finalize_calls == 1
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 1,
        'totalRows': 1,
        'totalBytes': len(pages[0]),
    }


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
def test_remote_query_binary_proof_query_preserves_nul_payload_against_real_clickhouse(instance, monkeypatch):
    """The binary proof query's NUL payload survives the real server's JSON stream exactly."""
    check = patch_real_check(monkeypatch, instance)
    fake = FakeUploadClient()

    request = real_server_request(instance, remote_query.REMOTE_QUERY_BINARY_QUERY)
    events = list(iter_agent_rpc_stream_events(request, StaticClickhouseCheckRegistry([check]), fake, None))

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # The payload is the exact three bytes NUL, 'a', 'b': the page JSON value equals the
    # decoded payload, with the NUL escaped the same way the server rendered it.
    assert json.loads(page)['data'] == [{'payload': '\x00ab'}]
    assert b'"payload":"\\u0000ab"' in page


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
@pytest.mark.parametrize(
    'query, expected_payload_bytes, include_schema',
    [
        (remote_query.REMOTE_QUERY_SEED_QUERY, None, False),
        (remote_query.REMOTE_QUERY_IDENTITY_QUERY, None, True),
        (remote_query.REMOTE_QUERY_BINARY_QUERY, None, False),
    ]
    + [
        (remote_query._proof_payload_query(size_bytes), size_bytes, False)
        for size_bytes in remote_query.REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES
    ],
    ids=['seed', 'identity-schema', 'binary', '1mib', '2mib', '4mib', '8mib', '16mib', '32mib'],
)
def test_remote_query_allowlisted_proof_queries_execute_against_real_clickhouse(
    instance, monkeypatch, query, expected_payload_bytes, include_schema
):
    """Every allowlisted proof query executes on a real server and produces one exact row."""
    check = patch_real_check(monkeypatch, instance)
    fake = FakeUploadClient()

    request = real_server_request(instance, query, include_schema=include_schema)
    events = list(iter_agent_rpc_stream_events(request, StaticClickhouseCheckRegistry([check]), fake, None))

    final = assert_success(events)
    pages = assembled_pages(fake)
    # Every proof query is a single row: one page uploaded as one direct PUT, bounded by
    # maxFileBytes, with the exact whole-page identity declared on the request.
    assert list(pages) == [0]
    assert final['upload_receipt']['totalRows'] == 1
    assert final['upload_receipt']['totalBytes'] == len(pages[0])
    (page_call,) = fake.put_page_calls
    assert page_call.page_bytes == len(pages[0])
    assert page_call.page_bytes <= 64 * 1024 * 1024
    assert page_call.rows == 1
    assert page_call.sha256_hex == hashlib.sha256(pages[0]).hexdigest()
    assert fake.run_finalize_calls == 1
    (item,) = json.loads(pages[0])['data']
    if expected_payload_bytes is not None:
        # The single payload column carries exactly the intended byte count of 'x' bytes.
        assert item == {'payload': 'x' * expected_payload_bytes}
    elif query == remote_query.REMOTE_QUERY_IDENTITY_QUERY:
        # The identity query proves the matched server without a fixture: real host, user,
        # and version strings ride through the pinned String value contract.
        assert set(item) == {'host', 'user', 'version'}
        assert all(isinstance(value, str) and value for value in item.values())
