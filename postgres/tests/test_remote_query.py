# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import json
import logging
import socket
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg.errors as psycopg_errors
import pytest

from datadog_checks.base.utils import remote_queries as rq
from datadog_checks.postgres import remote_query
from datadog_checks.postgres.config_models.instance import RemoteQueries
from datadog_checks.postgres.remote_query import (
    execute_agent_rpc_stream_copy,
    iter_agent_resolve_events,
    iter_agent_rpc_stream_events,
)

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'
# The Agent-reported hostname every fake check carries, stamped into every page envelope.
AGENT_HOSTNAME = 'rq-proof-agent-a'
BASE_URL = 'https://dd.datad0g.com/api/unstable/its-agent-intake'


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeColumn:
    def __init__(self, name, type_oid=25, type_modifier=-1):
        self.name = name
        self.type_code = type_oid
        self._fmod = type_modifier


class FakePlainCursor:
    """Plain cursor: control statements, the vendor-type lookup, and the COPY stream."""

    def __init__(self, pool):
        self.pool = pool
        self.executed = []
        self.copy_statements = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        assert self.executed, 'fetchall called before any execute'
        query, params = self.executed[-1]
        assert 'pg_catalog.format_type' in query, 'fetchall is only expected for the schema lookup'
        assert isinstance(params, tuple) and len(params) == 2
        rows = []
        for oid_text, type_mod_text in zip(params[0], params[1]):
            key = (int(oid_text), int(type_mod_text))
            resolved = self.pool.vendor_types.get(key)
            if resolved is None:
                continue
            if isinstance(resolved, str):
                # A plain vendor name: a non-array type.
                rows.append((key[0], key[1], resolved, False, None))
            else:
                # (vendor name, element delimiter character): a catalog array type.
                name, delimiter = resolved
                rows.append((key[0], key[1], name, True, ord(delimiter)))
        return rows

    @contextmanager
    def copy(self, sql):
        self.copy_statements.append(sql)
        yield FakeCopy(self.pool)


class FakeCopy:
    """psycopg COPY TO STDOUT double: raw reads whose block granularity is test-controlled."""

    def __init__(self, pool):
        self.pool = pool
        self.reads = 0
        self._blocks = iter(pool.copy_blocks) if pool.block_provider is None else pool.block_provider()

    def read(self):
        self.reads += 1
        if self.pool.copy_error is not None and (
            self.pool.copy_error_at is None or self.reads >= self.pool.copy_error_at
        ):
            raise self.pool.copy_error
        try:
            block = next(self._blocks)
        except StopIteration:
            block = b''
        if self.pool.read_log is not None:
            self.pool.read_log.append(('read', len(block)))
        return block


class FakeServerCursor:
    """Named server-side cursor: one DECLARE for the result description, never a fetch.

    The customer query's values must be evaluated exactly once, by the COPY alone, so a
    fetch on this cursor fails the test outright instead of silently evaluating the query
    a second time.
    """

    def __init__(self, pool):
        self.pool = pool
        self.description = pool.description
        self.executed = []
        self.closed = False

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchmany(self, size):
        raise AssertionError('the descriptor cursor must never be fetched: the COPY is the only execution')

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, pool):
        self.pool = pool

    @contextmanager
    def cursor(self, name=None):
        if name is None:
            cursor = FakePlainCursor(self.pool)
        else:
            cursor = FakeServerCursor(self.pool)
        self.pool.cursors.append(cursor)
        yield cursor
        if name is not None:
            cursor.close()


class FakePool:
    def __init__(
        self,
        rows=None,
        copy_blocks=None,
        block_provider=None,
        description=None,
        closed=False,
        vendor_types=None,
        copy_error=None,
        copy_error_at=None,
        read_log=None,
    ):
        # Plain result rows are framed into one-record COPY blocks — the database, not the
        # producer, frames native CSV — while copy_blocks and block_provider give tests
        # exact control over block granularity (split records, batched records, streaming).
        if rows is not None:
            assert copy_blocks is None and block_provider is None
            copy_blocks = [native_record(*row) for row in rows]
        self.copy_blocks = list(copy_blocks) if copy_blocks is not None else []
        self.block_provider = block_provider
        self.description = description or [FakeColumn('value', 23)]
        self.closed = closed
        # The descriptor always resolves vendor types, so the default covers the default
        # int4 description; tests with custom descriptions pass their own catalog entries.
        self.vendor_types = vendor_types if vendor_types is not None else {(23, -1): 'integer'}
        self.copy_error = copy_error
        self.copy_error_at = copy_error_at
        self.read_log = read_log
        self.requested_dbnames = []
        self.cursors = []

    def is_closed(self):
        return self.closed

    @contextmanager
    def get_connection(self, dbname):
        self.requested_dbnames.append(dbname)
        yield FakeConnection(self)


class FakeUploadClient:
    """Intake-side fake: one descriptor registration, page acceptance receipts, finalize totals.

    Page PUTs answer the pinned acceptance receipt — no per-page final metadata exists at
    acceptance — and the default finalize returns authoritative totals over the recorded
    pages, so the producer's stats and compact receipt come from finalization.
    """

    def __init__(
        self,
        run_finalize_response=None,
        put_page_response=None,
        raise_on_put_page=None,
        raise_on_run_finalize=None,
        put_log=None,
    ):
        # SimpleNamespace(batch_index, record_offset, source_bytes, rows, payload)
        self.descriptor_bodies = []
        self.put_page_calls = []
        self.run_finalize_calls = 0
        self.finalize_expected_page_counts = []
        self.abort_calls = 0
        self.raise_on_put_page = raise_on_put_page
        self.raise_on_run_finalize = raise_on_run_finalize
        self.run_finalize_response = run_finalize_response
        # When unset, the receipt carries shape-valid intake-derived metadata; tests pass a
        # mapping (or a callable taking the page metadata) to mutate or reject it.
        self.put_page_response = put_page_response
        self.put_log = put_log

    def register_descriptor(self, creds, body):
        self.descriptor_bodies.append(body)
        registered = json.loads(body)
        return {
            'upload_id': creds.upload_id,
            'format_version': registered['format_version'],
            'include_schema': registered['include_schema'],
            'columns': len(registered['columns']),
            'sha256': hashlib.sha256(body).hexdigest(),
        }

    def put_source_page(self, creds, page, body):
        payload = body.read()
        self.put_page_calls.append(
            SimpleNamespace(
                batch_index=page.batch_index,
                record_offset=page.record_offset,
                source_bytes=page.source_bytes,
                rows=page.rows,
                payload=payload,
            )
        )
        if self.put_log is not None:
            self.put_log.append(('put', page.batch_index, page.source_bytes, page.rows))
        if self.raise_on_put_page is not None:
            raise self.raise_on_put_page
        if self.put_page_response is not None:
            response = self.put_page_response
            if callable(response):
                response = response(page)
        else:
            response = {
                'upload_id': creds.upload_id,
                'batch_index': page.batch_index,
                'record_offset': page.record_offset,
                'source_rows': page.rows,
                'status': 'accepted',
            }
        return response

    def finalize_run(self, creds, expected_page_count):
        self.run_finalize_calls += 1
        self.finalize_expected_page_counts.append(expected_page_count)
        if self.raise_on_run_finalize is not None:
            raise self.raise_on_run_finalize
        if self.run_finalize_response is not None:
            return self.run_finalize_response
        return {
            'upload_id': creds.upload_id,
            'page_count': len(self.put_page_calls),
            'total_rows': sum(call.rows for call in self.put_page_calls),
            'total_bytes': sum(call.source_bytes for call in self.put_page_calls),
        }

    def abort(self, creds):
        self.abort_calls += 1


class FakeAutodiscovery:
    """Stands in for the check's integration-owned PostgresAutodiscovery."""

    def __init__(self, databases=None, error=None):
        self.databases = databases if databases is not None else []
        self.error = error
        self.get_items_calls = 0

    def get_items(self):
        self.get_items_calls += 1
        if self.error is not None:
            raise self.error
        return list(self.databases)


def make_check(
    host='localhost',
    port=5432,
    dbname='datadog_test',
    pool=None,
    check_database_identifier=None,
    hostname=AGENT_HOSTNAME,
    autodiscovery=None,
    **metadata,
):
    check = SimpleNamespace(
        _config=SimpleNamespace(host=host, port=port, dbname=dbname, **metadata),
        db_pool=pool if pool is not None else FakePool(),
        hostname=hostname,
    )
    if check_database_identifier is not None:
        check.database_identifier = check_database_identifier
    if autodiscovery is not None:
        check.autodiscovery = autodiscovery
    return check


def valid_request(query='SELECT 1 AS value', include_schema=False, **extra):
    target = {
        'host': extra.pop('host', 'LOCALHOST.'),
        'port': extra.pop('port', 5432),
        'dbname': extra.pop('dbname', 'datadog_test'),
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


class MutableClock:
    """A monotonic clock the fakes advance at deterministic phase boundaries.

    Every advance below is a whole-millisecond dyadic fraction of a second, so the
    accumulated float arithmetic stays exact and the expected buckets are integers.
    """

    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def advance_seconds(self, seconds):
        self.now += seconds


def instrument_postgres_fakes(monkeypatch, clock):
    """Advance the mutable clock inside each fake at its phase's boundary.

    Each advance lands wholly inside the producer phase that brackets it, so the emitted
    buckets pin the brackets: connection acquisition, BEGIN, the SET LOCAL pins, the
    vendor-type lookup, the DECLARE, and the COPY dispatch are database setup, copy.read
    is database fetch, put_source_page is page upload, finalize_run is finalize, and the
    ROLLBACK teardown (outside every phase) is the otherMs remainder.
    """

    original_get_connection = FakePool.get_connection

    @contextmanager
    def timed_get_connection(self, dbname):
        clock.advance_seconds(0.125)
        with original_get_connection(self, dbname) as connection:
            yield connection

    monkeypatch.setattr(FakePool, 'get_connection', timed_get_connection)

    original_control_execute = FakePlainCursor.execute

    def timed_control_execute(self, query, params=None):
        clock.advance_seconds(0.25)
        return original_control_execute(self, query, params)

    monkeypatch.setattr(FakePlainCursor, 'execute', timed_control_execute)

    original_declare_execute = FakeServerCursor.execute

    def timed_declare_execute(self, query, params=None):
        clock.advance_seconds(0.5)
        return original_declare_execute(self, query, params)

    monkeypatch.setattr(FakeServerCursor, 'execute', timed_declare_execute)

    original_copy = FakePlainCursor.copy

    @contextmanager
    def timed_copy(self, sql):
        clock.advance_seconds(0.5)
        with original_copy(self, sql) as copy:
            yield copy

    monkeypatch.setattr(FakePlainCursor, 'copy', timed_copy)

    original_read = FakeCopy.read

    def timed_read(self):
        clock.advance_seconds(0.375)
        return original_read(self)

    monkeypatch.setattr(FakeCopy, 'read', timed_read)

    original_put_source_page = FakeUploadClient.put_source_page

    def timed_put_source_page(self, creds, page, body):
        clock.advance_seconds(0.625)
        return original_put_source_page(self, creds, page, body)

    monkeypatch.setattr(FakeUploadClient, 'put_source_page', timed_put_source_page)

    original_finalize_run = FakeUploadClient.finalize_run

    def timed_finalize_run(self, creds, expected_page_count):
        clock.advance_seconds(0.25)
        return original_finalize_run(self, creds, expected_page_count)

    monkeypatch.setattr(FakeUploadClient, 'finalize_run', timed_finalize_run)


class ExplodingCheck:
    """A check that fails any test touching it: request validation must reject first."""

    def __getattr__(self, name):
        pytest.fail('check must not be touched before request validation completes')


def collect_events(request, check, client=None):
    return list(iter_agent_rpc_stream_events(request, check, client))


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
    """Each completed page's exact uploaded source bytes, keyed by batch index."""
    return {call.batch_index: call.payload for call in fake_client.put_page_calls}


def native_field(value):
    """The expected native COPY CSV field for one value, computed independently.

    ``FORCE_QUOTE *`` quotes every non-null value — with internal quotes doubled — and
    NULL is the sole unquoted field, the two-character \\N marker.
    """
    if value is None:
        return '\\N'
    if isinstance(value, bool):
        value = 't' if value else 'f'
    elif isinstance(value, bytes):
        value = '\\x' + value.hex()
    return '"{}"'.format(str(value).replace('"', '""'))


def native_record(*values):
    """The expected native COPY CSV record for one row of values."""
    return (','.join(native_field(value) for value in values) + '\n').encode('utf-8')


# ---------------------------------------------------------------------------
# Target normalization and validation
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('field', ['extra', 'password'])
def test_stream_rejects_unknown_request_fields_before_resolution(caplog, field):
    request = valid_request(**{field: 'SECRET_DO_NOT_LOG'})

    events = collect_events(request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request', field)
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_entry_reports_the_measured_wall_for_malformed_json_request():
    events = []

    execute_agent_rpc_stream_copy('{"password": "SECRET_DO_NOT_LOG"', make_check(), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    # The malformed-request event gains only the diagnostics object: no stats (as today), and
    # a producer section holding exactly what was measured before the parse failed.
    assert set(metadata) == {'status', 'error', 'executionDiagnostics'}
    diagnostics = metadata['executionDiagnostics']
    assert set(diagnostics) == {'contractVersion', 'producer'}
    assert diagnostics['contractVersion'] == 1
    assert set(diagnostics['producer']) == {'totalMs', 'otherMs'}
    assert diagnostics['producer']['totalMs'] >= 0
    assert diagnostics['producer']['otherMs'] >= 0


@pytest.mark.parametrize('request_json', ['{"password": "SECRET_DO_NOT_LOG"', b'\xff'])
def test_entry_rejects_malformed_json_without_echoing_input(caplog, request_json):
    pool = FakePool(rows=[(1,)])
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
def test_entry_rejects_non_object_json_without_echoing_input(request_json):
    pool = FakePool(rows=[(1,)])
    events = []

    execute_agent_rpc_stream_copy(request_json, make_check(pool=pool), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['error']['code'] == 'invalid_request'
    assert 'JSON object' in metadata['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert pool.requested_dbnames == []


# ---------------------------------------------------------------------------
# Query allowlist
# ---------------------------------------------------------------------------


def test_stream_rejects_non_allowlisted_query_before_pool_access():
    pool = FakePool(rows=[(1,)])
    request = valid_request(query='SELECT current_database()')

    events = collect_events(request, make_check(pool=pool))

    assert_failed_event(events, 'invalid_request', 'query is not allowlisted')
    assert pool.requested_dbnames == []


def test_stream_accepts_non_allowlisted_query_when_allowlist_is_disabled(monkeypatch):
    patch_allowlist_disabled(monkeypatch)
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[('datadog_test',)])
    request = valid_request(query='SELECT current_database()')

    events = collect_events(request, make_check(pool=pool), client=FakeUploadClient())

    assert_success(events)
    assert pool.requested_dbnames == ['datadog_test']


def test_stream_accepts_large_payload_proof_queries(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[('x',)])
    for size in (1048576, 2097152, 4194304, 8388608, 16777216, 33554432):
        request = valid_request(query=f"SELECT repeat('x', {size}) AS payload")

        events = collect_events(request, make_check(pool=pool), client=FakeUploadClient())

        assert_success(events)
    assert pool.requested_dbnames == ['datadog_test'] * 6


# ---------------------------------------------------------------------------
# Target resolution
# ---------------------------------------------------------------------------


def test_stream_resolves_exact_host_port_dbname_from_check_config(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_success(events)
    assert pool.requested_dbnames == ['datadog_test']


def test_stream_host_port_dbname_target_still_succeeds_when_check_has_database_identifier(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(
        host='localhost',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        check_database_identifier='postgres-dbi',
    )

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_success(events)
    assert pool.requested_dbnames == ['datadog_test']


def test_stream_database_instance_match_runs_on_the_check_configured_database(monkeypatch):
    patch_upload_credentials(monkeypatch)
    matching_pool = FakePool(rows=[(1,)])
    check = make_check(dbname='analytics', pool=matching_pool, check_database_identifier='Postgres/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A'}
    events = collect_events(request, check, client=FakeUploadClient())

    assert_success(events)
    # A database_instance selector admits the matched check's materialized configured
    # database, never a request-named other one.
    assert matching_pool.requested_dbnames == ['analytics']


def test_stream_database_instance_miss_fails_without_pool_access():
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool, check_database_identifier='Postgres/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-B'}
    events = collect_events(request, check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_rejects_mixed_database_instance_and_host_selector_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': 'postgres-dbi', 'host': 'localhost'}

    events = collect_events(request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_stream_rejects_database_instance_with_partial_host_selector_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': 'postgres-dbi', 'port': 5432}

    events = collect_events(request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_stream_rejects_empty_database_instance_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': ' postgres-dbi '}

    events = collect_events(request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request', 'database_instance')


def test_stream_uses_only_supplied_live_check_for_target_matching(monkeypatch):
    patch_upload_credentials(monkeypatch)
    matching_pool = FakePool(rows=[(1,)])
    non_matching_pool = FakePool(rows=[(1,)])
    request = valid_request(host='configured.internal')

    events = collect_events(request, make_check(host='localhost', pool=non_matching_pool))
    assert_failed_event(events, 'target_not_found')
    assert non_matching_pool.requested_dbnames == []

    events = collect_events(
        request, make_check(host='configured.internal', pool=matching_pool), client=FakeUploadClient()
    )
    assert_success(events)
    assert matching_pool.requested_dbnames == ['datadog_test']


def test_stream_host_port_dbname_target_ignores_database_instance_matches():
    pool = FakePool(rows=[(1,)])
    check = make_check(
        host='configured.internal',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        reported_hostname='reported.internal',
        check_database_identifier='reported.internal',
    )

    events = collect_events(valid_request(host='reported.internal'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_credentials_unavailable_without_agent_keys(monkeypatch):
    def get_config(key):
        return None

    monkeypatch.setattr(rq.datadog_agent, 'get_config', get_config)
    pool = FakePool(rows=[(1,)])

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'credentials_unavailable')
    assert events[0].event_type == 'error'
    assert pool.requested_dbnames == []


def test_stream_closed_pool_returns_target_unavailable_without_recreating_credentials(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(closed=True)

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'target_unavailable')
    assert pool.requested_dbnames == []


def test_stream_missing_pool_returns_credentials_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = make_check()
    check.db_pool = None

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_failed_event(events, 'credentials_unavailable')


# ---------------------------------------------------------------------------
# Configured monitoring scope (tuple targets match a database inside the check's scope)
# ---------------------------------------------------------------------------


def test_stream_tuple_target_never_defaults_a_missing_configured_dbname(monkeypatch):
    """The adapter consumes the materialized config dbname only; it must not re-derive the
    integration's omitted-dbname default itself, or a check whose config never materialized
    a database would match a request naming the default."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname=None, pool=pool)

    events = collect_events(valid_request(dbname='postgres'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_tuple_target_out_of_scope_database_fails_without_pool_access(monkeypatch):
    """A database outside the configured scope is not a match even when the endpoint matches.

    A database that exists but is unconfigured and a database that does not exist are
    deliberately indistinguishable: resolution never connects to the requested database or
    probes its name, so it cannot (and must not) distinguish them.
    """
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='production_ok', pool=pool)

    events = collect_events(valid_request(dbname='unconfigured_existing_or_missing'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []
    assert not pool.cursors
    assert [event.event_type for event in events] == ['error']


def test_stream_tuple_target_matches_current_autodiscovered_database(monkeypatch):
    """With autodiscovery enabled, the eligible set is the check's own admitted discovery set."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0', 'dogs_1'])
    # Autodiscovery with an omitted dbname materializes the global view db as the configured
    # dbname; the request names an autodiscovered database instead.
    check = make_check(host='localhost', port=5432, dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_events(valid_request(dbname='dogs_1'), check, client=FakeUploadClient())

    assert_success(events)
    assert autodiscovery.get_items_calls == 1
    # Execution runs on the matched database only; no connection is opened anywhere else.
    assert pool.requested_dbnames == ['dogs_1']


def test_stream_tuple_target_excluded_by_autodiscovery_fails_without_pool_access(monkeypatch):
    """A database the check's own autodiscovery filters out is out of scope."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0', 'dogs_1'])
    check = make_check(host='localhost', port=5432, dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_events(valid_request(dbname='dogs_5'), check)

    assert_failed_event(events, 'target_not_found')
    assert autodiscovery.get_items_calls == 1
    assert pool.requested_dbnames == []
    assert not pool.cursors


def test_stream_scope_evaluated_only_for_endpoint_matching_checks():
    """Only an endpoint-matching check is scope-evaluated, so an undeterminable discovery set
    on an unrelated check can neither fail nor widen an unrelated request."""
    pool = FakePool(rows=[(1,)])
    other_autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke'))
    check = make_check(
        host='other.internal', port=5432, dbname='postgres', pool=pool, autodiscovery=other_autodiscovery
    )
    request = valid_request(dbname='dogs_1')

    events = collect_events(request, check)

    assert_failed_event(events, 'target_not_found')
    assert other_autodiscovery.get_items_calls == 0
    assert pool.requested_dbnames == []


def test_stream_autodiscovery_failure_is_visible_retryable_target_unavailable(monkeypatch, caplog):
    """An undeterminable discovery set fails closed and visibly, never as a silent no-match."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke: SECRET_DO_NOT_LOG'))
    check = make_check(host='localhost', port=5432, dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(dbname='dogs_1'), check)

    assert_failed_event(events, 'target_unavailable', 'autodiscovered database scope')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert autodiscovery.get_items_calls == 1
    # The customer's SQL never ran: no connection, no cursor, no upload session.
    assert pool.requested_dbnames == []
    assert not pool.cursors
    assert [event.event_type for event in events] == ['error']
    # The discovery failure's text never reaches the error event or the logs.
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_scope_failure_wrapper_keeps_no_path_back_to_the_discovery_exception():
    """The target_unavailable wrapper severs the discovery exception from its chain: a
    later traceback log of the wrapper can only ever see the fixed classification message,
    never the connection strings or identifiers the discovery error can quote."""
    autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke: SECRET_DO_NOT_LOG'))
    check = make_check(dbname='postgres', autodiscovery=autodiscovery)

    with pytest.raises(rq.RemoteQueryFailure) as failure:
        remote_query.database_in_monitoring_scope(check, 'dogs_1')

    assert failure.value.code == 'target_unavailable'
    assert failure.value.retryable
    assert failure.value.__cause__ is None
    assert 'SECRET_DO_NOT_LOG' not in str(failure.value)


def test_stream_rejects_database_instance_with_requested_dbname_before_resolution():
    """dbname must not override the selected check's monitored database."""
    request = valid_request()
    request['target'] = {'database_instance': 'postgres-dbi', 'dbname': 'analytics'}

    events = collect_events(request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_stream_database_instance_without_configured_dbname_fails_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(dbname=None, pool=pool, check_database_identifier='Postgres/Primary-A')
    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A'}

    events = collect_events(request, check, client=FakeUploadClient())

    assert_failed_event(events, 'target_unavailable', 'configured database name')
    assert pool.requested_dbnames == []


# ---------------------------------------------------------------------------
# Resolve operation (per-check verdict events for the Agent's sweep)
# ---------------------------------------------------------------------------


def resolve_request(**target):
    """A strict resolve_target request: operation and target only."""
    if 'database_instance' in target:
        selector = {'database_instance': target['database_instance']}
    else:
        selector = {
            'host': target.pop('host', 'LOCALHOST.'),
            'port': target.pop('port', 5432),
            'dbname': target.pop('dbname', 'datadog_test'),
        }
    return {'operation': 'resolve_target', 'target': selector}


def collect_resolve_events(request, check):
    return list(iter_agent_resolve_events(request, check))


def assert_matched_verdict(events):
    """A verdict is exactly one MATCHED final event with no payload and no STARTED event."""
    assert len(events) == 1
    event = events[0]
    assert event.event_type == 'final'
    assert event.payload == b''
    metadata = event_metadata(event)
    assert metadata['status'] == 'MATCHED'
    return metadata['match']


def test_resolve_verdict_reports_sanitized_match_identity():
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool, check_database_identifier='Postgres/Primary-A')

    events = collect_resolve_events(resolve_request(), check)

    match = assert_matched_verdict(events)
    assert match == {
        'host': 'localhost',
        'port': 5432,
        'configuredDbname': 'datadog_test',
        'resolvedDbname': 'datadog_test',
        'databaseInstance': 'Postgres/Primary-A',
    }
    # Resolve is side-effect free: no connection, no cursor, no upload session.
    assert pool.requested_dbnames == []
    assert not pool.cursors


def test_resolve_verdict_reports_autodiscovered_database_with_configured_dbname():
    """The verdict distinguishes the admitted database from the configured one: the Agent
    binds both into its fingerprint."""
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0', 'dogs_1'])
    check = make_check(dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_resolve_events(resolve_request(dbname='dogs_1'), check)

    match = assert_matched_verdict(events)
    assert match['configuredDbname'] == 'postgres'
    assert match['resolvedDbname'] == 'dogs_1'
    assert pool.requested_dbnames == []


def test_resolve_no_match_is_one_target_not_found_error():
    """Out-of-scope and missing databases share the same verdict: target_not_found."""
    pool = FakePool(rows=[(1,)])
    check = make_check(dbname='production_ok', pool=pool)

    events = collect_resolve_events(resolve_request(dbname='unconfigured_existing_or_missing'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []
    assert not pool.cursors


def test_resolve_database_instance_verdict_reports_materialized_configured_dbname():
    check = make_check(dbname='production_ok', check_database_identifier='Postgres/Primary-A')

    events = collect_resolve_events(resolve_request(database_instance='Postgres/Primary-A'), check)

    match = assert_matched_verdict(events)
    assert match['configuredDbname'] == match['resolvedDbname'] == 'production_ok'
    assert match['databaseInstance'] == 'Postgres/Primary-A'


def test_resolve_database_instance_without_configured_dbname_fails_target_unavailable():
    """A matched check that cannot name its database is an error other than target_not_found,
    so the Agent fails its aggregate resolution instead of skipping the check."""
    check = make_check(dbname=None, check_database_identifier='Postgres/Primary-A')

    events = collect_resolve_events(resolve_request(database_instance='Postgres/Primary-A'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_unavailable', 'configured database name')


@pytest.mark.parametrize(
    'field,value',
    [
        ('query', 'SELECT 1'),
        ('includeSchema', True),
        ('resultDelivery', {'runId': RUN_ID}),
        ('traceContext', {'traceId': '1234567890123456789', 'parentId': '9876543210987654321', 'samplingPriority': 2}),
        ('matchFingerprint', 'deadbeef'),
    ],
)
def test_resolve_rejects_execution_fields_before_resolution(field, value):
    """A resolve dispatch is target-only: SQL, upload instructions, and fingerprints are
    rejected by strict validation before any check is evaluated."""
    request = resolve_request()
    request[field] = value

    events = collect_resolve_events(request, ExplodingCheck())

    assert len(events) == 1
    assert_failed_event(events, 'invalid_request', field)


def test_resolve_discovery_failure_is_visible_target_unavailable():
    """An undeterminable eligible set is an error other than target_not_found: the check is
    never silently skipped from the Agent's sweep."""
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(error=psycopg_errors.OperationalError('discovery broke'))
    check = make_check(dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    events = collect_resolve_events(resolve_request(dbname='dogs_1'), check)

    assert len(events) == 1
    assert_failed_event(events, 'target_unavailable', 'autodiscovered database scope')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert autodiscovery.get_items_calls == 1
    assert pool.requested_dbnames == []


def test_resolve_and_execute_share_the_same_matching_authority(monkeypatch):
    """The resolve verdict must predict execution: a target that resolves MATCHED on one
    check executes on it, and one that resolves target_not_found never executes."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    autodiscovery = FakeAutodiscovery(databases=['dogs_0'])
    check = make_check(dbname='postgres', pool=pool, autodiscovery=autodiscovery)

    assert_matched_verdict(list(iter_agent_resolve_events(resolve_request(dbname='dogs_0'), check)))
    events = collect_events(valid_request(dbname='dogs_0'), check, client=FakeUploadClient())
    assert_success(events)
    assert pool.requested_dbnames == ['dogs_0']

    assert_failed_event(list(iter_agent_resolve_events(resolve_request(dbname='dogs_9'), check)), 'target_not_found')
    events = collect_events(valid_request(dbname='dogs_9'), check, client=FakeUploadClient())
    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == ['dogs_0']


def test_entry_dispatches_resolve_target_by_operation():
    check = make_check(check_database_identifier='Postgres/Primary-A')
    events = []

    execute_agent_rpc_stream_copy(json.dumps(resolve_request()), check, lambda *event: events.append(event))

    assert len(events) == 1
    event_type, metadata_json, payload = events[0]
    assert event_type == 'final'
    assert payload == b''
    metadata = json.loads(metadata_json)
    assert metadata['status'] == 'MATCHED'
    assert metadata['match']['databaseInstance'] == 'Postgres/Primary-A'


def test_entry_rejects_unknown_operation_without_pool_access():
    pool = FakePool(rows=[(1,)])
    request = valid_request()
    request['operation'] = 'bogus_operation'
    events = []

    execute_agent_rpc_stream_copy(json.dumps(request), make_check(pool=pool), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['error']['code'] == 'invalid_request'
    assert pool.requested_dbnames == []


# ---------------------------------------------------------------------------
# Producer core: envelope, single execution, transaction, receipt
# ---------------------------------------------------------------------------


def test_producer_emits_started_and_final_with_compact_receipt(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,), (2,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert [event.event_type for event in events] == ['metadata', 'final']
    started = event_metadata(events[0])
    assert started['status'] == 'STARTED'
    assert started['operation'] == 'produce_json_pages'
    assert started['includeSchema'] is False
    assert started['resultDelivery']['uploadId'] == UPLOAD_ID
    assert started['resultDelivery']['runId'] == RUN_ID
    assert started['resultDelivery']['taskId'] == TASK_ID
    assert started['resultDelivery']['artifactVersion'] == 1
    assert started['resultDelivery']['baseUrl'] == BASE_URL
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
    # The finalize request declared exactly the accepted page count.
    assert fake.finalize_expected_page_counts == [1]
    # Event payloads are empty: bulk bytes never cross the emit bridge.
    assert all(event.payload == b'' for event in events)


def test_producer_writes_exact_source_page_csv_and_descriptor(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # The source page is the native COPY record verbatim — the server's own CSV framing,
    # every field quoted — and no final JSON envelope is built or uploaded here; intake
    # assembles it from the registered descriptor.
    assert page == b'"1"\n'
    assert json.loads(fake.descriptor_bodies[0]) == {
        'format_version': 'postgres-copy-csv-v1',
        'include_schema': False,
        'agent_hostname': AGENT_HOSTNAME,
        'columns': [
            {
                'column_name': 'value',
                'vendor_data_type': 'integer',
                'logical_type': 'integer',
                'array_element_delimiter': None,
            }
        ],
    }


def test_producer_stamps_agent_reported_hostname_from_the_check_instance(monkeypatch):
    """The descriptor carries the check instance's Agent-reported hostname, never the machine's socket name."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()
    # By construction this value differs from the machine's socket name on every host, so a
    # matching stamp can only come from the check instance (what the Agent reported and
    # Fleet matches against the agent node identity), never from socket.gethostname().
    check_hostname = 'stamp-check-{}'.format(socket.gethostname())
    check = make_check(pool=pool, hostname=check_hostname)

    events = collect_events(valid_request(), check, client=fake)

    assert_success(events)
    descriptor = json.loads(fake.descriptor_bodies[0])
    assert descriptor['agent_hostname'] == check_hostname
    assert descriptor['agent_hostname'] != socket.gethostname()


def test_producer_executes_query_exactly_once_in_read_only_transaction_with_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A constant clock keeps the remaining-wall derivation of the statement timeout exact.
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: 100.0)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    control = pool.cursors[0]
    described = pool.cursors[1]
    stream = pool.cursors[2]
    assert isinstance(described, FakeServerCursor)
    assert isinstance(stream, FakePlainCursor)
    # The query text appears exactly twice: as the never-fetched DECLARE's body — which
    # only plans the query and yields its description, evaluating no value — and as the
    # single COPY's body, which evaluates the query once. It is not wrapped in a probe
    # and not executed twice.
    assert described.executed == [('SELECT 1 AS value', None)]
    assert stream.copy_statements == [remote_query.native_copy_sql('SELECT 1 AS value')]
    # BEGIN READ ONLY, the transaction-local statement timeout, the five native-text
    # session pins, one descriptor vendor-type lookup, then ROLLBACK at the end. SET
    # statements do not accept bind parameters, so the validated timeout is inlined.
    executed = [entry[0] for entry in control.executed]
    assert executed[:2] == ['BEGIN READ ONLY', 'SET LOCAL statement_timeout = 5000']
    # The native-text session pins, spelled independently of the producer's constant:
    # timestamptz in UTC, ISO dates, postgres intervals, hex bytea, shortest floats.
    assert executed[2:7] == [
        "SET LOCAL TimeZone = 'UTC'",
        "SET LOCAL DateStyle = 'ISO, MDY'",
        "SET LOCAL IntervalStyle = 'postgres'",
        "SET LOCAL bytea_output = 'hex'",
        'SET LOCAL extra_float_digits = 1',
    ]
    assert executed[-1] == 'ROLLBACK'
    assert len(executed) == 9 and 'pg_catalog.format_type' in executed[7]
    assert control.executed[1][1] is None
    assert described.closed


def test_producer_caps_instance_timeout_at_the_producer_wall(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: 100.0)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()
    # The instance override is larger than the delivered limit, so it cannot lengthen the
    # run: the effective statement timeout is capped at the remaining producer wall.
    check = make_check(pool=pool, remote_queries=RemoteQueries(timeout_ms=300_000))

    events = collect_events(valid_request(), check, client=fake)

    assert_success(events)
    control = pool.cursors[0]
    executed = [entry[0] for entry in control.executed]
    assert executed[:2] == ['BEGIN READ ONLY', 'SET LOCAL statement_timeout = 5000']
    assert executed[-1] == 'ROLLBACK'


def test_producer_honors_instance_timeout_shorter_than_the_wall(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: 100.0)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()
    # The instance override is the smaller value, so it is the effective statement timeout.
    check = make_check(pool=pool, remote_queries=RemoteQueries(timeout_ms=3_000))

    events = collect_events(valid_request(), check, client=fake)

    assert_success(events)
    control = pool.cursors[0]
    executed = [entry[0] for entry in control.executed]
    assert executed[:2] == ['BEGIN READ ONLY', 'SET LOCAL statement_timeout = 3000']
    assert executed[-1] == 'ROLLBACK'


def test_instance_timeout_larger_than_delivery_cannot_lengthen_the_wall(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()
    check = make_check(pool=pool, remote_queries=RemoteQueries(timeout_ms=300_000))
    request = valid_request()
    request['resultDelivery']['limits']['timeoutMs'] = 1000
    # The wall is the delivered 1 s even though the instance override is 300 s: the run must
    # expire at the delivered wall, which is exactly the case the old replacement semantics
    # silently allowed to run past its parent budget. The leading constant values cover every
    # clock read before the page-close guard (started_at, statement-timeout resolution, the
    # setup/encode phase brackets, the copy-read brackets, and the per-block and per-record
    # guards) so the wall still expires at the page-close guard, after the record was
    # produced and the page assembled.
    clock = iter([100.0] * 13 + [101.5] * 50)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: next(clock))

    events = collect_events(request, check, client=fake)

    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    control = pool.cursors[0]
    executed = [entry[0] for entry in control.executed]
    assert executed[:2] == ['BEGIN READ ONLY', 'SET LOCAL statement_timeout = 1000']
    assert executed[-1] == 'ROLLBACK'
    assert fake.abort_calls == 1


def test_statement_timeout_is_the_smaller_of_instance_override_and_remaining_wall(monkeypatch):
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: 100.0)
    deadline = 105.0  # a 5 s wall with 5 s remaining, matching the delivered limit

    # An override larger than the wall is capped: it may shorten the run, never lengthen it.
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=300_000))
    assert remote_query._resolve_statement_timeout_ms(check, deadline) == 5_000

    # An override shorter than the remaining wall is honored as the statement timeout.
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=3_000))
    assert remote_query._resolve_statement_timeout_ms(check, deadline) == 3_000

    # Without a positive instance override, the remaining wall applies.
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=None))
    assert remote_query._resolve_statement_timeout_ms(check, deadline) == 5_000

    # An expired wall must not disable the database-side protection: the remainder clamps
    # to 1 ms instead of reaching a zero statement timeout.
    assert remote_query._resolve_statement_timeout_ms(check, 99.0) == 1


def test_producer_rolls_back_transaction_on_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,), (2,)], copy_error=ValueError('copy broke'))
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'query_failed')
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_producer_zero_rows_with_schema_disabled_writes_no_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

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


def test_producer_reports_phase_diagnostics_for_a_successful_run(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clock = MutableClock()
    monkeypatch.setattr(remote_query.time, 'monotonic', clock.monotonic)
    instrument_postgres_fakes(monkeypatch, clock)
    pool = FakePool(rows=[(1,), (2,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    final = assert_success(events)
    # The final metadata gained exactly one key: the optional execution diagnostics.
    assert set(final) == {'status', 'upload_receipt', 'stats', 'executionDiagnostics'}
    producer = final['executionDiagnostics']['producer']
    assert final['executionDiagnostics']['contractVersion'] == 1
    assert producer == {
        'totalMs': 5375,
        # Connection acquisition, BEGIN, the statement timeout, the five session pins, the
        # DECLARE, the vendor-type lookup, and the COPY dispatch are setup.
        'databaseSetupMs': 3125,
        # Three copy.read calls (the two records and the empty end-of-stream read).
        'databaseFetchMs': 1125,
        # Real record-assembly work with this clock runs in well under a millisecond.
        'encodeAndPageBuildMs': 0,
        'pageUploadMs': 625,
        'finalizeMs': 250,
        # The ROLLBACK teardown runs outside every phase and lands in the remainder.
        'otherMs': 250,
        'timeToFirstPageMs': 4875,
        'pageCount': 1,
        'rowCount': 2,
        'byteCount': len(assembled_pages(fake)[0]),
        'pageUploadMinMs': 625,
        'pageUploadP50Ms': 625,
        'pageUploadP95Ms': 625,
        'pageUploadMaxMs': 625,
    }
    # The diagnostics total and stats.elapsedMs are the same wall.
    assert final['stats']['elapsedMs'] == producer['totalMs']
    # The injected upload client makes no HTTP attempts, so the attempt counters stay
    # unmeasured (absent, never zero).
    assert 'uploadAttemptCount' not in producer
    assert 'uploadRetryCount' not in producer


def test_producer_zero_rows_with_schema_enabled_writes_one_zero_record_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[], vendor_types={(23, -1): 'integer'})
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=True), make_check(pool=pool), client=fake)

    final = assert_success(events)
    pages = assembled_pages(fake)
    # include_schema=true keeps schema discovery for an empty result: exactly one
    # zero-record source page, so intake creates one schema-bearing final page with empty
    # data.
    assert list(pages) == [0]
    assert pages[0] == b''
    (call,) = fake.put_page_calls
    assert (call.batch_index, call.record_offset, call.rows, call.source_bytes) == (0, 0, 0, 0)
    descriptor = json.loads(fake.descriptor_bodies[0])
    assert descriptor['include_schema'] is True
    assert descriptor['columns'] == [
        {
            'column_name': 'value',
            'vendor_data_type': 'integer',
            'logical_type': 'integer',
            'array_element_delimiter': None,
        }
    ]
    assert final['upload_receipt']['pageCount'] == 1
    assert final['upload_receipt']['totalRows'] == 0
    assert final['upload_receipt']['totalBytes'] == 0
    assert fake.run_finalize_calls == 1


# ---------------------------------------------------------------------------
# Schema production
# ---------------------------------------------------------------------------


def test_producer_splits_pages_by_the_source_page_target(monkeypatch):
    """Native pages close at the record boundary that reaches the internal source-page
    target: the schema-bearing envelope no longer bounds the producer's page sizing —
    intake stays authoritative for the transformed final page — so records split purely by
    source bytes, schema or not."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [
        FakeColumn('city', 1043, 255),
        FakeColumn('country', 1043, 255),
    ]
    schema_json = json.dumps(
        [
            {'column_name': 'city', 'vendor_data_type': 'character varying(255)'},
            {'column_name': 'country', 'vendor_data_type': 'character varying(255)'},
        ],
        separators=(',', ':'),
    ).encode('utf-8')
    # The budget fits the schema-bearing envelope plus a little slack: its source-page
    # target (4/5 of it, 268 bytes) sits below one wide record, so every record closes its
    # own page whatever the schema-bearing envelope weighs.
    budget = len(prefix_bytes(schema_json=schema_json)) + len(rq.PAGE_SUFFIX) + 2
    first = native_record('a' * 300, 'USA')  # 309 bytes >= the 268-byte target
    second = native_record('b' * 300, 'France')
    request = bounded_request(maxFileBytes=budget, maxRowBytes=budget)
    request['includeSchema'] = True
    pool = FakePool(
        copy_blocks=[first, second],
        description=columns,
        vendor_types={(1043, 255): 'character varying(255)'},
    )
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0, 1]
    assert pages[0] == first
    assert pages[1] == second
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
    assert [call.record_offset for call in fake.put_page_calls] == [0, 1]
    assert json.loads(fake.descriptor_bodies[0])['include_schema'] is True
    assert event_metadata(events[0])['includeSchema'] is True


def test_producer_resolves_vendor_types_even_when_schema_is_not_requested(monkeypatch):
    """The descriptor needs every vendor type name, schema or not: the catalog lookup always
    runs, and include_schema stays false in the registered descriptor."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], vendor_types={(23, -1): 'integer'})
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=False), make_check(pool=pool), client=fake)

    assert_success(events)
    control_executed = [entry[0] for entry in pool.cursors[0].executed]
    assert sum('pg_catalog.format_type' in query for query in control_executed) == 1
    descriptor = json.loads(fake.descriptor_bodies[0])
    assert descriptor['include_schema'] is False
    assert descriptor['columns'][0]['vendor_data_type'] == 'integer'


def test_producer_resolves_distinct_type_pairs_with_one_parameterized_lookup(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [
        FakeColumn('a', 1043, 255),
        FakeColumn('b', 1043, 255),
        FakeColumn('c', 25, -1),
    ]
    pool = FakePool(
        rows=[('x', 'y', 'z')],
        description=columns,
        vendor_types={(1043, 255): 'character varying(255)', (25, -1): 'text'},
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=True), make_check(pool=pool), client=fake)

    assert_success(events)
    control = pool.cursors[0]
    schema_queries = [entry for entry in control.executed if 'pg_catalog.format_type' in entry[0]]
    # Exactly one schema lookup, in the same transaction scope (before ROLLBACK).
    assert len(schema_queries) == 1
    query, params = schema_queries[0]
    assert 'unnest(%s::text[], %s::text[])' in query
    assert 'pg_catalog.format_type(r.type_oid, r.type_mod)' in query
    assert 'pg_catalog.ascii(e.typdelim::text)' in query
    # Only the DISTINCT (oid, typmod) pairs are resolved (two columns share one pair).
    assert sorted(zip(params[0], params[1])) == [('1043', '255'), ('25', '-1')]
    executed_names = [entry[0] for entry in control.executed]
    assert executed_names.index(schema_queries[0][0]) < executed_names.index('ROLLBACK')
    assert json.loads(fake.descriptor_bodies[0])['columns'] == [
        {
            'column_name': 'a',
            'vendor_data_type': 'character varying(255)',
            'logical_type': 'string',
            'array_element_delimiter': None,
        },
        {
            'column_name': 'b',
            'vendor_data_type': 'character varying(255)',
            'logical_type': 'string',
            'array_element_delimiter': None,
        },
        {
            'column_name': 'c',
            'vendor_data_type': 'text',
            'logical_type': 'string',
            'array_element_delimiter': None,
        },
    ]


def test_producer_rejects_duplicate_result_column_names_before_row_data(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [FakeColumn('value', 23), FakeColumn('value', 23)]
    pool = FakePool(rows=[(1, 1)], description=columns)
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'duplicate_columns', 'value')
    # No row data was streamed or written: the run fails before the COPY is even dispatched.
    assert len(pool.cursors) == 2
    assert fake.put_page_calls == []


def test_producer_rejects_duplicate_columns_even_with_schema_disabled(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [FakeColumn('v', 23), FakeColumn('v', 23), FakeColumn('v', 23)]
    pool = FakePool(rows=[(1, 2, 3)], description=columns)

    events = collect_events(valid_request(include_schema=False), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'duplicate_columns')


def test_producer_rejects_columns_beyond_max_columns(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [FakeColumn('a', 23), FakeColumn('b', 23), FakeColumn('c', 23)]
    pool = FakePool(rows=[(1, 2, 3)], description=columns)
    request = bounded_request(maxColumns=2)

    events = collect_events(request, make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'max_columns_exceeded')


@pytest.mark.parametrize('include_schema', [False, True])
def test_producer_fails_closed_on_unresolvable_vendor_types(monkeypatch, include_schema):
    """The descriptor needs every vendor type name, schema or not: an unresolvable catalog
    lookup fails the run before any row is read, any descriptor is registered, or any page
    is uploaded."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], vendor_types={})
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=include_schema), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'schema_unavailable')
    # The COPY is never dispatched: no cursor beyond the descriptor's DECLARE was opened.
    assert len(pool.cursors) == 2
    assert fake.put_page_calls == []
    assert fake.descriptor_bodies == []


@pytest.mark.parametrize('include_schema', [False, True])
def test_producer_fails_closed_when_description_lacks_type_modifiers(monkeypatch, include_schema):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    column = FakeColumn('value', 23)
    column._fmod = None
    pool = FakePool(rows=[(1,)], description=[column], vendor_types={})

    events = collect_events(
        valid_request(include_schema=include_schema), make_check(pool=pool), client=FakeUploadClient()
    )

    assert_failed_event(events, 'schema_unavailable', 'type modifier')


def test_producer_enforces_max_schema_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], vendor_types={(23, -1): 'integer'})
    request = bounded_request(maxSchemaBytes=4, maxFileBytes=1024)
    request['includeSchema'] = True

    events = collect_events(request, make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'max_schema_bytes_exceeded')


def test_producer_enforces_max_file_bytes_for_schema_bearing_pages(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], vendor_types={(23, -1): 'integer'})
    # The schema-bearing minimal frame cannot fit even an empty page.
    request = bounded_request(maxFileBytes=len(prefix_bytes()) - 1, maxRowBytes=8)
    request['includeSchema'] = True

    events = collect_events(request, make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'max_file_bytes_exceeded', 'repeated schema')


# ---------------------------------------------------------------------------
# Page splitting, boundaries, and part bookkeeping
# ---------------------------------------------------------------------------


# One wide native text row per page: a 170-byte source record over a single text column,
# which closes its own page under a 200-byte maxFileBytes (its 160-byte source-page target).
BOUND_NAMES = ['payload']
BOUND_RECORD = native_record('a' * 167)  # 170 bytes


def two_row_boundary_request(monkeypatch):
    """A budget whose source-page target closes exactly one wide record per page."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    return bounded_request(maxFileBytes=200, maxRowBytes=200, maxSchemaBytes=1, maxPages=128, maxResultBytes=64 * 1024)


def wide_row_pool():
    """A pool whose two wide rows each close their own page under the boundary request."""
    return FakePool(
        rows=[('a' * 167,), ('a' * 167,)],
        description=[FakeColumn('payload', 25)],
        vendor_types={(25, -1): 'text'},
    )


def test_page_split_row_too_large_when_record_exceeds_max_row_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # maxRowBytes bounds one native source record: the 170-byte record for the wide row
    # cannot fit 169.
    request = bounded_request(maxRowBytes=len(BOUND_RECORD) - 1)
    pool = FakePool(rows=[('a' * 167,)], description=[FakeColumn('payload', 25)], vendor_types={(25, -1): 'text'})
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    assert fake.put_page_calls == []


def test_page_upload_streams_before_the_copy_is_exhausted(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    request = bounded_request(maxPages=128, maxResultBytes=64 * 1024)

    def block_provider():
        for _index in range(500):
            yield native_record('aaaa')
        order_log.append(('exhausted',))

    pool = FakePool(
        description=[FakeColumn('payload', 25)],
        vendor_types={(25, -1): 'text'},
        block_provider=block_provider,
        read_log=order_log,
    )
    fake = FakeUploadClient(put_log=order_log)

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    # Pages are uploaded while the COPY stream is still being read: the producer never
    # buffers the complete result before uploading, only one bounded source page at a time.
    first_put = next(index for index, entry in enumerate(order_log) if entry[0] == 'put')
    later_read = next(
        index for index, entry in enumerate(order_log[first_put:], start=first_put) if entry[0] == 'read' and entry[1]
    )
    assert later_read > first_put
    exhausted = next(index for index, entry in enumerate(order_log) if entry[0] == 'exhausted')
    assert exhausted > first_put
    # Pages are contiguous zero-based and every row is declared exactly once across the
    # page PUTs; the compact receipt repeats intake's finalize totals.
    page_indexes = sorted({call.batch_index for call in fake.put_page_calls})
    assert page_indexes == list(range(len(page_indexes)))
    assert sum(call.rows for call in fake.put_page_calls) == 500
    receipt = event_metadata(events[-1])['upload_receipt']
    assert receipt['totalRows'] == 500
    assert receipt['pageCount'] == len(page_indexes)
    assert receipt['totalBytes'] == sum(call.source_bytes for call in fake.put_page_calls)


def test_descriptor_is_registered_before_the_first_source_record(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    pool = FakePool(rows=[(1,)], read_log=order_log)
    fake = FakeUploadClient(put_log=order_log)
    original_register = fake.register_descriptor

    def register_descriptor(creds, body):
        order_log.append('descriptor')
        return original_register(creds, body)

    fake.register_descriptor = register_descriptor

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    # One registration, before any result record is read and before any page is uploaded.
    assert order_log[0] == 'descriptor'
    assert order_log.count('descriptor') == 1
    assert order_log[1] == ('read', len(native_record(1)))
    assert order_log[-1][0] == 'put'


# ---------------------------------------------------------------------------
# Native COPY CSV record assembly (record-complete regardless of block granularity)
# ---------------------------------------------------------------------------


def test_producer_frames_native_records_across_block_boundaries(monkeypatch):
    """The producer feeds raw COPY blocks to the shared writer, which carries the framing
    state across block boundaries: a record split between blocks, records batched into one
    block, and embedded commas, quotes, and newlines all arrive as one whole, verbatim
    source page."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    first = native_record('a,b', 'He said "Hi"', 'line1\nline2')
    second = native_record(None, '', '\\N')

    def block_provider():
        middle = len(first) // 2
        yield first[:middle]
        yield first[middle:] + second[:4]
        yield second[4:]

    pool = FakePool(
        block_provider=block_provider,
        description=[FakeColumn('a', 25), FakeColumn('b', 25), FakeColumn('c', 25)],
        vendor_types={(25, -1): 'text'},
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0]
    assert pages[0] == first + second
    (call,) = fake.put_page_calls
    assert call.rows == 2
    assert call.source_bytes == len(first) + len(second)


def test_producer_fails_closed_when_the_copy_stream_ends_mid_record(monkeypatch):
    """A COPY stream that ends inside a record never produces a page for it: the run fails
    closed after the read-only transaction rolls back."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)

    def block_provider():
        yield b'"abc'
        yield b''

    pool = FakePool(
        block_provider=block_provider,
        description=[FakeColumn('a', 25)],
        vendor_types={(25, -1): 'text'},
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'query_failed', 'open native record')
    assert fake.put_page_calls == []
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


# ---------------------------------------------------------------------------
# Descriptor logical types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'type_oid, vendor_data_type, expected',
    [
        (16, 'boolean', 'boolean'),
        (17, 'bytea', 'binary'),
        (18, 'char', 'string'),
        (19, 'name', 'string'),
        (20, 'bigint', 'integer'),
        (21, 'smallint', 'integer'),
        (23, 'integer', 'integer'),
        (25, 'text', 'string'),
        (26, 'oid', 'integer'),
        (114, 'json', 'json'),
        (700, 'real', 'float'),
        (701, 'double precision', 'float'),
        (790, 'money', 'vendor'),
        (829, 'macaddr', 'vendor'),
        (869, 'inet', 'vendor'),
        (650, 'cidr', 'vendor'),
        (1042, 'character(1)', 'string'),
        (1043, 'character varying(255)', 'string'),
        (1082, 'date', 'temporal'),
        (1083, 'time without time zone', 'temporal'),
        (1114, 'timestamp without time zone', 'temporal'),
        (1184, 'timestamp with time zone', 'temporal'),
        (1186, 'interval', 'temporal'),
        (1266, 'time with time zone', 'temporal'),
        (2249, 'record', 'json'),
        (2950, 'uuid', 'string'),
        (3802, 'jsonb', 'json'),
        # Array families carry JSON arrays whatever the element type, including quoted names.
        (1009, 'text[]', 'json'),
        (1015, 'character varying(255)[]', 'json'),
        (1007, 'integer[]', 'json'),
        # Custom types, domains, and extensions have no stable cross-vendor family.
        (16709, 'mood', 'vendor'),
        (16710, 'my_int_domain', 'vendor'),
        (46001, 'int4range', 'vendor'),
    ],
)
def test_logical_type_mapping_is_deterministic(type_oid, vendor_data_type, expected):
    column = remote_query.ResultColumn('c', type_oid, -1)
    assert remote_query.logical_type_for_column(column, vendor_data_type) == expected


# ---------------------------------------------------------------------------
# Native COPY source wire (pinned)
# ---------------------------------------------------------------------------


def test_native_copy_sql_pins_the_frozen_wire_options():
    # The frozen native wire: COPY of the validated query, CSV format, the two-byte \N
    # NULL marker as the sole unquoted field, and quoting forced for every column.
    assert remote_query.native_copy_sql('SELECT 1 AS value') == (
        "COPY (SELECT 1 AS value) TO STDOUT WITH (FORMAT CSV, NULL '\\N', FORCE_QUOTE *)"
    )


def test_producer_emits_native_copy_records_verbatim(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # One record covering the native families' raw text: NULL, empty string, a literal
    # \N, booleans, an integer, a quoted value with commas and quotes, and a multibyte
    # string. The page must carry the records byte for byte: the producer never decodes,
    # re-encodes, or re-frames a value.
    record = native_record(None, '', '\\N', True, False, 42, 'a,b', 'He said "Hi"', 'héllo')
    pool = FakePool(
        copy_blocks=[record],
        description=[
            FakeColumn('null_value', 25),
            FakeColumn('empty_value', 25),
            FakeColumn('literal_marker', 25),
            FakeColumn('true_value', 16),
            FakeColumn('false_value', 16),
            FakeColumn('int_value', 23),
            FakeColumn('comma_value', 25),
            FakeColumn('quote_value', 25),
            FakeColumn('utf8_value', 25),
        ],
        vendor_types={
            (25, -1): 'text',
            (16, -1): 'boolean',
            (23, -1): 'integer',
        },
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert page == record
    descriptor = json.loads(fake.descriptor_bodies[0])
    assert descriptor['format_version'] == 'postgres-copy-csv-v1'
    assert [(column['column_name'], column['logical_type']) for column in descriptor['columns']] == [
        ('null_value', 'string'),
        ('empty_value', 'string'),
        ('literal_marker', 'string'),
        ('true_value', 'boolean'),
        ('false_value', 'boolean'),
        ('int_value', 'integer'),
        ('comma_value', 'string'),
        ('quote_value', 'string'),
        ('utf8_value', 'string'),
    ]


def test_producer_carries_the_catalog_array_element_delimiter(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A box[] column: box's own pg_type.typdelim is the semicolon, so the descriptor must
    # declare it — intake splits the native {(...);(...)} literal on that and nothing else.
    record = native_record('{(1,2);(3,4)}')
    pool = FakePool(
        copy_blocks=[record],
        description=[FakeColumn('box_array', 1021)],
        vendor_types={(1021, -1): ('box[]', ';')},
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert page == record
    assert json.loads(fake.descriptor_bodies[0])['columns'] == [
        {
            'column_name': 'box_array',
            'vendor_data_type': 'box[]',
            'logical_type': 'json',
            'array_element_delimiter': ';',
        }
    ]


@pytest.mark.parametrize('delimiter', ['"', ' ', '\\', '{', '}'])
def test_producer_fails_closed_on_structural_element_delimiters(monkeypatch, delimiter):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A catalog element delimiter that is structural to the array literal grammar cannot be
    # described: the run fails closed before any COPY or page.
    pool = FakePool(
        copy_blocks=[native_record('{a}')],
        description=[FakeColumn('array_value', 1009)],
        vendor_types={(1009, -1): ('text[]', delimiter)},
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'schema_unavailable')
    assert len(pool.cursors) == 2
    assert fake.put_page_calls == []
    assert fake.descriptor_bodies == []


@pytest.mark.parametrize(
    'vendor_types',
    [
        {(1009, -1): 'text[]'},  # a rendered array the catalog says is not an array
        {(1009, -1): None},  # no catalog resolution at all
    ],
)
def test_producer_fails_closed_on_a_rendered_array_without_catalog_resolution(monkeypatch, vendor_types):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(
        copy_blocks=[native_record('{a}')],
        description=[FakeColumn('array_value', 1009)],
        vendor_types=vendor_types,
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'schema_unavailable')
    assert len(pool.cursors) == 2
    assert fake.put_page_calls == []


def test_producer_describes_a_domain_over_array_without_a_delimiter(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # A domain over an array renders as the bare domain name, so the closed wire grammar
    # classifies it with the vendor family: no delimiter, the exact server text, matching
    # the decoder's own name-based classification.
    record = native_record('{a,b}')
    pool = FakePool(
        copy_blocks=[record],
        description=[FakeColumn('domain_value', 20000)],
        vendor_types={(20000, -1): ('my_domain', ',')},
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert page == record
    assert json.loads(fake.descriptor_bodies[0])['columns'] == [
        {
            'column_name': 'domain_value',
            'vendor_data_type': 'my_domain',
            'logical_type': 'vendor',
            'array_element_delimiter': None,
        }
    ]


def test_stream_uploads_pages_and_finalizes_run_in_order(monkeypatch):
    request = two_row_boundary_request(monkeypatch)
    pool = wide_row_pool()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    # Pages are uploaded in order, each exactly once, and run finalize is the last call.
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 0


def test_stream_aborts_on_page_upload_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient(
        raise_on_put_page=rq.RemoteQueryFailure('upload_failed', 'transient exhausted', retryable=True)
    )

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'upload_failed')
    assert len(fake.put_page_calls) == 1
    assert fake.abort_calls == 1
    assert fake.run_finalize_calls == 0
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_stream_fails_closed_on_page_receipt_identity_mismatch(monkeypatch):
    """The acceptance receipt must echo the accepted page's identity exactly — session,
    index, offset, and source rows; a mismatch fails the run."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = two_row_boundary_request(monkeypatch)
    pool = wide_row_pool()
    fake = FakeUploadClient(
        put_page_response=lambda page: {
            'upload_id': UPLOAD_ID,
            'batch_index': page.batch_index,
            'record_offset': page.record_offset,
            # A row count that disagrees with the accepted page: rejected.
            'source_rows': page.rows + 1,
            'status': 'accepted',
        }
    )

    events = collect_events(request, make_check(pool=pool), client=fake)

    # The receipt disagrees on rows: page 1 is never produced, the session is aborted, and
    # no partial receipt is emitted.
    assert_failed_event(events, 'invalid_receipt')
    assert [call.batch_index for call in fake.put_page_calls] == [0]
    assert fake.run_finalize_calls == 0
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_mid_run_failure_reports_honest_partial_diagnostics(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    clock = MutableClock()
    monkeypatch.setattr(remote_query.time, 'monotonic', clock.monotonic)
    instrument_postgres_fakes(monkeypatch, clock)
    # A two-page boundary whose second page upload fails: the first page is acknowledged
    # and counted, the second attempt's wall is measured but never promoted.
    request = two_row_boundary_request(monkeypatch)
    pool = wide_row_pool()

    def fail_second_page(page):
        if page.batch_index == 1:
            raise rq.RemoteQueryFailure('upload_failed', 'transient exhausted', retryable=True)
        return {
            'upload_id': UPLOAD_ID,
            'batch_index': page.batch_index,
            'record_offset': page.record_offset,
            'source_rows': page.rows,
            'status': 'accepted',
        }

    fake = FakeUploadClient(put_page_response=fail_second_page)

    events = collect_events(request, make_check(pool=pool), client=fake)

    error = event_metadata(events[-1])
    assert_failed_event(events, 'upload_failed')
    # The error metadata gained exactly one key: the optional execution diagnostics.
    assert set(error) == {'status', 'error', 'stats', 'executionDiagnostics'}
    assert fake.abort_calls == 1
    assert fake.run_finalize_calls == 0
    first_page_bytes = len(assembled_pages(fake)[0])
    assert error['stats'] == {
        'rowsEmitted': 1,
        'pagesEmitted': 1,
        'bytesEmitted': first_page_bytes,
        'elapsedMs': 5375,
    }
    assert error['executionDiagnostics'] == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 5375,
            'databaseSetupMs': 3125,
            # Two copy.read calls: the page closes at the target while the second record
            # is fed, so its failed upload aborts the record loop before the empty
            # end-of-stream read.
            'databaseFetchMs': 750,
            'encodeAndPageBuildMs': 0,
            # Both upload walls are kept: the acknowledged page and the failed attempt's.
            'pageUploadMs': 1250,
            # finalizeMs is absent: finalize never ran. uploadAttemptCount/RetryCount are
            # absent too: the injected client makes no HTTP attempts.
            'otherMs': 250,
            'timeToFirstPageMs': 4125,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': first_page_bytes,
            # The distribution holds only the acknowledged page's wall.
            'pageUploadMinMs': 625,
            'pageUploadP50Ms': 625,
            'pageUploadP95Ms': 625,
            'pageUploadMaxMs': 625,
        },
    }


def test_stream_fails_closed_on_run_finalize_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient(raise_on_run_finalize=rq.RemoteQueryFailure('upload_failed', 'run finalize rejected'))

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'upload_failed')
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_fails_closed_on_run_finalize_identity_mismatch(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient(run_finalize_response={'upload_id': 'other-upload'})

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'invalid_receipt')
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_enforces_timeout_with_retryable_error(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    request = valid_request()
    request['resultDelivery']['limits']['timeoutMs'] = 1000
    # The leading zeros cover every clock read before the page-close guard (started_at,
    # statement-timeout resolution, the setup/encode phase brackets, the copy-read brackets,
    # and the per-block and per-record guards) so the wall still expires at the page-close
    # guard, after the record was produced and the page assembled.
    values = iter([0.0] * 13 + [10.0] * 50)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: next(values))

    events = collect_events(request, make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_stream_maps_server_statement_cancellation_to_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    import psycopg.errors as psycopg_errors

    pool = FakePool(
        rows=[(1,)],
        copy_error=psycopg_errors.QueryCanceled('canceling statement due to statement timeout'),
    )

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'timeout', 'statement timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_stream_maps_unexpected_execution_failure_to_fixed_query_failed(monkeypatch, caplog):
    """An unexpected producer failure maps to the fixed query_failed error: the exception's
    text can carry raw row fragments or query text, so neither the event nor the logs
    echo it."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], copy_error=ValueError('SECRET_DO_NOT_LOG row fragment'))
    fake = FakeUploadClient()

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'query_failed', 'Remote query execution failed')
    assert event_metadata(events[-1])['error']['retryable'] is False
    assert fake.abort_calls == 1
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


@pytest.mark.parametrize('is_cancelled', [lambda: True, True], ids=['callable', 'bool'])
def test_stream_reports_cancellation_as_retryable(monkeypatch, is_cancelled):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool)
    # Both runtime shapes: the Agent check object carries a bool ``is_cancelled`` attribute;
    # a callable hook is the other supported shape. Both must fail the run as retryable.
    check.is_cancelled = is_cancelled

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_failed_event(events, 'cancelled')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_stream_proceeds_when_bool_is_cancelled_is_false(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool)
    check.is_cancelled = False

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_success(events)


def test_stream_ignores_check_without_cancel_hook(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # make_check deliberately has no is_cancelled attribute.
    pool = FakePool(rows=[(1,)])

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_success(events)


def test_entry_propagates_callback_failure_without_upload(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])

    def emit(event_type, metadata_json, payload):
        raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        execute_agent_rpc_stream_copy(json.dumps(valid_request()), make_check(pool=pool), emit)

    # The callback failed on the STARTED metadata event, before any page bytes existed.
    assert pool.requested_dbnames == []
