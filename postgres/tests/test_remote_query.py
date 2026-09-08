# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import socket
import uuid as uuid_module
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from datetime import time as dt_time
from decimal import Decimal
from types import SimpleNamespace

import psycopg.errors as psycopg_errors
import pytest

from datadog_checks.base.utils import remote_queries as rq
from datadog_checks.postgres import remote_query
from datadog_checks.postgres.config_models.instance import RemoteQueries
from datadog_checks.postgres.remote_query import (
    RawJsonNumber,
    RawJsonNumberLoader,
    RawTextLoader,
    StaticPostgresCheckRegistry,
    execute_agent_rpc_stream_copy,
    iter_agent_rpc_stream_events,
)

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'
# The Agent-reported hostname every fake check carries, stamped into every page envelope.
AGENT_HOSTNAME = 'rq-proof-agent-a'
BASE_URL = 'https://dd.datad0g.com/api/unstable/its-agent-intake'
TOKEN = 'scoped-upload-token'

BYTEA_OID = remote_query.BYTEA_OID


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeColumn:
    def __init__(self, name, type_oid=25, type_modifier=-1):
        self.name = name
        self.type_code = type_oid
        self._fmod = type_modifier


class FakeAdapters:
    def __init__(self):
        self.registered_loaders = []

    def register_loader(self, oid_or_name, loader):
        self.registered_loaders.append((oid_or_name, loader))


class FakeControlCursor:
    """Plain cursor for BEGIN/SET LOCAL/ROLLBACK, the schema lookup, and the gate existence lookup."""

    def __init__(self, pool):
        self.pool = pool
        self.executed = []

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
            vendor_data_type = self.pool.vendor_types.get(key)
            if vendor_data_type is not None:
                rows.append((key[0], key[1], vendor_data_type))
        return rows

    def fetchone(self):
        assert self.executed, 'fetchone called before any execute'
        query, params = self.executed[-1]
        assert 'pg_catalog.pg_database' in query, 'fetchone is only expected for the gate existence lookup'
        assert isinstance(params, tuple) and len(params) == 1
        if self.pool.existence_query_error is not None:
            raise self.pool.existence_query_error
        # A missing mapping entry means the database does not exist on the endpoint.
        if self.pool.pg_database is None or self.pool.pg_database.get(params[0], False):
            return (1,)
        return None


class FakeServerCursor:
    """Named server-side cursor: one execute, bounded fetchmany batches."""

    def __init__(self, pool):
        self.pool = pool
        self.description = pool.description
        self.adapters = FakeAdapters()
        self.executed = []
        self.fetch_sizes = []
        self.closed = False
        self._rows = iter(pool.rows) if not pool.row_provider else pool.row_provider()

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchmany(self, size):
        self.fetch_sizes.append(size)
        if self.pool.fetch_error is not None and (
            self.pool.fetch_error_at is None or len(self.fetch_sizes) >= self.pool.fetch_error_at
        ):
            raise self.pool.fetch_error
        batch = []
        for _ in range(size):
            try:
                batch.append(next(self._rows))
            except StopIteration:
                break
        if self.pool.fetch_log is not None:
            self.pool.fetch_log.append(('fetch', len(batch)))
        return batch

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self, pool):
        self.pool = pool

    @contextmanager
    def cursor(self, name=None):
        if name is None:
            cursor = FakeControlCursor(self.pool)
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
        description=None,
        closed=False,
        vendor_types=None,
        fetch_error=None,
        fetch_error_at=None,
        row_provider=None,
        fetch_log=None,
        connection_errors=None,
        pg_database=None,
        existence_query_error=None,
    ):
        self.rows = rows or []
        self.description = description or [FakeColumn('value', 23)]
        self.closed = closed
        self.vendor_types = vendor_types or {}
        self.fetch_error = fetch_error
        self.fetch_error_at = fetch_error_at
        self.row_provider = row_provider
        self.fetch_log = fetch_log
        # Per-dbname connection failures raised from get_connection, e.g. psycopg
        # InvalidCatalogName for a database that does not exist on the endpoint.
        self.connection_errors = connection_errors or {}
        # Models pg_catalog.pg_database for the dynamic gate existence lookup: a mapping
        # dbname -> datallowconn, or None for the permissive default (every requested
        # database exists and allows connections).
        self.pg_database = pg_database
        self.existence_query_error = existence_query_error
        self.requested_dbnames = []
        self.cursors = []

    def is_closed(self):
        return self.closed

    @contextmanager
    def get_connection(self, dbname):
        self.requested_dbnames.append(dbname)
        error = self.connection_errors.get(dbname)
        if error is not None:
            raise error
        yield FakeConnection(self)


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
    host='localhost',
    port=5432,
    dbname='datadog_test',
    pool=None,
    check_database_identifier=None,
    hostname=AGENT_HOSTNAME,
    **metadata,
):
    check = SimpleNamespace(
        _config=SimpleNamespace(host=host, port=port, dbname=dbname, **metadata),
        db_pool=pool if pool is not None else FakePool(),
        hostname=hostname,
    )
    if check_database_identifier is not None:
        check.database_identifier = check_database_identifier
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
    def iter_postgres_checks(self):
        pytest.fail('registry must not be iterated')


def collect_events(request, check, client=None, registry=None):
    return list(
        iter_agent_rpc_stream_events(
            request, registry if registry is not None else StaticPostgresCheckRegistry([check]), client
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


def prefix_bytes(batch_index=0, record_offset=0, agent_hostname=AGENT_HOSTNAME, schema_json=None):
    return rq.page_prefix(
        run_id=RUN_ID,
        task_id=TASK_ID,
        batch_index=batch_index,
        record_offset=record_offset,
        agent_hostname=agent_hostname,
        schema_json=schema_json,
    )


def assembled_pages(fake_client):
    """Each completed page's exact uploaded bytes, keyed by batch index."""
    return {call.batch_index: call.payload for call in fake_client.put_page_calls}


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


def test_stream_resolves_unique_database_instance_from_check_identifier(monkeypatch):
    patch_upload_credentials(monkeypatch)
    matching_pool = FakePool(rows=[(1,)])
    non_matching_pool = FakePool(rows=[(1,)])
    checks = [
        make_check(dbname='analytics', pool=matching_pool, check_database_identifier='Postgres/Primary-A'),
        make_check(dbname='postgres', pool=non_matching_pool, check_database_identifier='Postgres/Primary-B'),
    ]

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A'}
    events = collect_events(request, None, client=FakeUploadClient(), registry=StaticPostgresCheckRegistry(checks))

    assert_success(events)
    assert matching_pool.requested_dbnames == ['analytics']
    assert non_matching_pool.requested_dbnames == []


def test_stream_database_instance_miss_fails_without_pool_access():
    pool = FakePool(rows=[(1,)])
    check = make_check(pool=pool, check_database_identifier='Postgres/Primary-A')

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-B'}
    events = collect_events(request, check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


def test_stream_database_instance_ambiguous_fails_without_pool_access():
    first_pool = FakePool(rows=[(1,)])
    second_pool = FakePool(rows=[(1,)])
    checks = [
        make_check(dbname='postgres_a', pool=first_pool, check_database_identifier='Postgres/Primary-A'),
        make_check(dbname='postgres_b', pool=second_pool, check_database_identifier='Postgres/Primary-A'),
    ]

    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A'}
    events = collect_events(request, None, registry=StaticPostgresCheckRegistry(checks))

    assert_failed_event(events, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_stream_default_template_database_instance_collapse_is_ambiguous():
    first_pool = FakePool(rows=[(1,)])
    second_pool = FakePool(rows=[(1,)])
    checks = [
        make_check(dbname='postgres_a', pool=first_pool, check_database_identifier='resolved-hostname'),
        make_check(dbname='postgres_b', pool=second_pool, check_database_identifier='resolved-hostname'),
    ]

    request = valid_request()
    request['target'] = {'database_instance': 'resolved-hostname'}
    events = collect_events(request, None, registry=StaticPostgresCheckRegistry(checks))

    assert_failed_event(events, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


def test_stream_rejects_mixed_database_instance_and_host_selector_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': 'postgres-dbi', 'host': 'localhost'}

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_stream_rejects_database_instance_with_partial_host_selector_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': 'postgres-dbi', 'port': 5432}

    events = collect_events(request, None, registry=ExplodingRegistry())

    assert_failed_event(events, 'invalid_request', 'exactly one selector mode')


def test_stream_rejects_empty_database_instance_before_resolution():
    request = valid_request()
    request['target'] = {'database_instance': ' postgres-dbi '}

    events = collect_events(request, None, registry=ExplodingRegistry())

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


def test_stream_fails_ambiguous_duplicate_configs():
    first_pool = FakePool(rows=[(1,)])
    second_pool = FakePool(rows=[(1,)])
    checks = [make_check(pool=first_pool), make_check(pool=second_pool)]

    events = collect_events(valid_request(), None, registry=StaticPostgresCheckRegistry(checks))

    assert_failed_event(events, 'target_ambiguous')
    assert first_pool.requested_dbnames == []
    assert second_pool.requested_dbnames == []


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
# Dynamic database targeting (a requested dbname on the matched check)
# ---------------------------------------------------------------------------


def test_dynamic_tuple_requested_dbname_executes_on_requested_database(monkeypatch):
    """Tuple selection matches the endpoint only; a different dbname executes there."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='analytics'), check, client=FakeUploadClient())

    assert_success(events)
    # The gate classifies existence on the configured database's connection, warms the pool
    # entry for the requested database, then the producer reuses it.
    assert pool.requested_dbnames == ['datadog_test', 'analytics', 'analytics']
    # The existence lookup ran on the configured connection with the requested name bound.
    assert pool.cursors[0].executed == [(remote_query.REMOTE_QUERY_DATABASE_EXISTENCE_QUERY, ('analytics',))]


def test_dynamic_tuple_requested_dbname_matches_when_configured_dbname_is_absent(monkeypatch):
    """A check configured without a dbname still matches its endpoint; the request names the database."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname=None, pool=pool)

    events = collect_events(valid_request(dbname='datadog_test'), check, client=FakeUploadClient())

    assert_success(events)
    # Probe-only gate path: no configured connection to classify existence on, so the flow
    # goes straight to the probe and the producer on the requested database.
    assert pool.requested_dbnames == ['datadog_test', 'datadog_test']
    assert all('pg_catalog.pg_database' not in entry[0] for cursor in pool.cursors for entry in cursor.executed)


def test_dynamic_gate_missing_database_fails_fast_target_not_found(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)], pg_database={'datadog_test': True})
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_not_found', 'does not exist')
    # The catalog lookup classifies the miss before any connection to the requested
    # database is attempted: one existence lookup on the configured connection and no probe.
    assert pool.requested_dbnames == ['datadog_test']
    assert not any(isinstance(cursor, FakeServerCursor) for cursor in pool.cursors)
    assert [event.event_type for event in events] == ['error']


def test_dynamic_gate_datallowconn_false_fails_target_not_found(monkeypatch):
    """A database that exists but disallows connections is not a query target."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)], pg_database={'datadog_test': True, 'analytics': False})
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_not_found', 'does not allow connections')
    assert pool.requested_dbnames == ['datadog_test']
    assert not any(isinstance(cursor, FakeServerCursor) for cursor in pool.cursors)


def test_dynamic_gate_existence_query_error_fails_closed_target_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)], existence_query_error=psycopg_errors.OperationalError('catalog lookup broke'))
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_unavailable', 'Unable to verify')
    assert event_metadata(events[-1])['error']['retryable'] is True
    # A failing existence lookup never becomes a silent no-match: the request fails
    # visibly before the probe or any producer execution.
    assert pool.requested_dbnames == ['datadog_test']
    assert not any(isinstance(cursor, FakeServerCursor) for cursor in pool.cursors)


def test_dynamic_tuple_probe_invalid_catalog_name_fails_target_not_found(monkeypatch):
    """Defense in depth: a catalog-existing database whose probe surfaces InvalidCatalogName."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(
        rows=[(1,)],
        pg_database={'datadog_test': True, 'postgres': True},
        connection_errors={'postgres': psycopg_errors.InvalidCatalogName('database "postgres" does not exist')},
    )
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='postgres'), check)

    assert_failed_event(events, 'target_not_found', 'does not exist')
    # Existence lookup on the configured connection, then one probe; no producer execution.
    assert pool.requested_dbnames == ['datadog_test', 'postgres']
    assert not any(isinstance(cursor, FakeServerCursor) for cursor in pool.cursors)
    assert [event.event_type for event in events] == ['error']


def test_dynamic_tuple_connection_error_fails_retryable_target_unavailable(monkeypatch):
    """Existence passes but the probe fails: the database exists, connecting to it does not."""
    patch_upload_credentials(monkeypatch)
    pool = FakePool(
        rows=[(1,)],
        pg_database={'datadog_test': True, 'analytics': True},
        connection_errors={'analytics': psycopg_errors.OperationalError('connection refused')},
    )
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_unavailable', 'connection refused')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert pool.requested_dbnames == ['datadog_test', 'analytics']
    assert not any(isinstance(cursor, FakeServerCursor) for cursor in pool.cursors)


def test_dynamic_database_instance_with_requested_dbname_executes_on_requested_database(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(
        host='localhost',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        check_database_identifier='Postgres/Primary-A',
    )
    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A', 'dbname': 'analytics'}

    events = collect_events(request, check, client=FakeUploadClient())

    assert_success(events)
    assert pool.requested_dbnames == ['datadog_test', 'analytics', 'analytics']


def test_dynamic_database_instance_with_unknown_requested_dbname_fails_target_not_found(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(
        rows=[(1,)],
        pg_database={'datadog_test': True, 'analytics': True},
        connection_errors={'analytics': psycopg_errors.InvalidCatalogName('database "analytics" does not exist')},
    )
    check = make_check(
        host='localhost',
        port=5432,
        dbname='datadog_test',
        pool=pool,
        check_database_identifier='Postgres/Primary-A',
    )
    request = valid_request()
    request['target'] = {'database_instance': 'Postgres/Primary-A', 'dbname': 'analytics'}

    events = collect_events(request, check)

    assert_failed_event(events, 'target_not_found', 'does not exist')
    assert pool.requested_dbnames == ['datadog_test', 'analytics']
    assert not any(isinstance(cursor, FakeServerCursor) for cursor in pool.cursors)


def test_dynamic_gate_dbstrict_rejects_requested_database_without_pool_access(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool, dbstrict=True)

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_not_found', 'dbstrict')
    assert pool.requested_dbnames == []


def test_dynamic_gate_ignore_databases_rejects_requested_database_without_pool_access(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool, ignore_databases=('template%',))

    events = collect_events(valid_request(dbname='template0'), check)

    assert_failed_event(events, 'target_not_found', 'ignore_databases')
    assert pool.requested_dbnames == []


@pytest.mark.parametrize(
    'pattern,dbname,expected',
    [
        ('template0', 'template0', True),
        ('template%', 'template0', True),
        ('Template0', 'TEMPLATE0', True),
        ('template_', 'template0', True),
        ('template_', 'template01', False),
        ('rdsadmin', 'rdsadmin_extra', False),
    ],
)
def test_ignore_database_pattern_matches_use_ilike_semantics(pattern, dbname, expected):
    assert remote_query._matches_ignore_database(pattern, dbname) is expected


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


def test_producer_writes_exact_v1_envelope_json(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # Schema disabled: the schema key is omitted entirely, never null/[].
    assert page == (prefix_bytes() + b'{"value":1}' + rq.PAGE_SUFFIX)
    parsed = json.loads(page)
    assert parsed == {
        'version': 1,
        'run_id': RUN_ID,
        'task_id': TASK_ID,
        'agent_hostname': AGENT_HOSTNAME,
        'batch_index': 0,
        'record_offset': 0,
        'data': {'items': [{'value': 1}]},
    }
    assert 'schema' not in parsed
    assert 'total_records' not in parsed


def test_producer_stamps_agent_reported_hostname_from_the_check_instance(monkeypatch):
    """The stamp is the check instance's Agent-reported hostname, never the machine's socket name."""
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
    (page,) = assembled_pages(fake).values()
    envelope = json.loads(page)
    assert envelope['agent_hostname'] == check_hostname
    assert envelope['agent_hostname'] != socket.gethostname()


def test_producer_executes_query_exactly_once_in_read_only_transaction_with_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    control = pool.cursors[0]
    server = pool.cursors[1]
    assert isinstance(server, FakeServerCursor)
    # The query is executed exactly once, verbatim, through the named cursor; it is not
    # wrapped in a probe and not executed twice.
    assert server.executed == [('SELECT 1 AS value', None)]
    assert server.fetch_sizes  # rows were fetched in bounded batches
    # BEGIN READ ONLY, transaction-local statement timeout, then ROLLBACK at the end.
    # SET statements do not accept bind parameters, so the validated timeout is inlined.
    assert [entry[0] for entry in control.executed] == [
        'BEGIN READ ONLY',
        'SET LOCAL statement_timeout = 5000',
        'ROLLBACK',
    ]
    assert control.executed[1][1] is None
    assert server.closed


def test_producer_applies_instance_remote_queries_timeout_over_delivery_limit(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()
    check = make_check(pool=pool, remote_queries=RemoteQueries(timeout_ms=300_000))

    events = collect_events(valid_request(), check, client=fake)

    assert_success(events)
    control = pool.cursors[0]
    # The instance-configured DB-protective timeout overrides the delivery-injected limit.
    assert [entry[0] for entry in control.executed] == [
        'BEGIN READ ONLY',
        'SET LOCAL statement_timeout = 300000',
        'ROLLBACK',
    ]


def test_statement_timeout_resolution_prefers_instance_timeout():
    limits = rq.RemoteQueryUploadLimits.model_validate(valid_limits(timeoutMs=7_777))
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=300_000))

    assert remote_query._resolve_statement_timeout_ms(check, limits) == 300_000


@pytest.mark.parametrize(
    'remote_queries',
    [None, SimpleNamespace(timeout_ms=None), SimpleNamespace(timeout_ms=0)],
    ids=['section-unset', 'timeout-unset', 'timeout-non-positive'],
)
def test_statement_timeout_resolution_falls_back_to_delivery_limit(remote_queries):
    limits = rq.RemoteQueryUploadLimits.model_validate(valid_limits(timeoutMs=7_777))
    check = make_check(remote_queries=remote_queries)

    assert remote_query._resolve_statement_timeout_ms(check, limits) == 7_777


def test_producer_rolls_back_transaction_on_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,), (2,)], fetch_error=ValueError('fetch broke'))
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


def test_producer_zero_rows_with_schema_enabled_writes_one_schema_bearing_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[], vendor_types={(23, -1): 'integer'})
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=True), make_check(pool=pool), client=fake)

    final = assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0]
    parsed = json.loads(pages[0])
    assert parsed['batch_index'] == 0
    assert parsed['record_offset'] == 0
    assert parsed['schema'] == [{'column_name': 'value', 'vendor_data_type': 'integer'}]
    assert parsed['data'] == {'items': []}
    assert final['upload_receipt']['pageCount'] == 1
    assert final['upload_receipt']['totalRows'] == 0
    assert final['upload_receipt']['totalBytes'] == len(pages[0])
    assert [call.batch_index for call in fake.put_page_calls] == [0]
    assert fake.run_finalize_calls == 1


# ---------------------------------------------------------------------------
# Schema production
# ---------------------------------------------------------------------------


def test_producer_schema_enabled_repeats_identical_ordered_schema_across_pages(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [
        FakeColumn('city', 1043, 255),
        FakeColumn('country', 1043, 255),
    ]
    pool = FakePool(
        rows=[('New York', 'USA'), ('Beautiful city of lights', 'France')],
        description=columns,
        vendor_types={(1043, 255): 'character varying(255)'},
    )
    request = bounded_request(query='SELECT city, country FROM cities ORDER BY city')
    request['includeSchema'] = True
    schema_entries = [
        {'column_name': 'city', 'vendor_data_type': 'character varying(255)'},
        {'column_name': 'country', 'vendor_data_type': 'character varying(255)'},
    ]
    schema_json = json.dumps(schema_entries, separators=(',', ':')).encode('utf-8')
    longest_row_bytes = b'{"city":"Beautiful city of lights","country":"France"}'
    # maxFileBytes fits the schema-bearing prefix plus exactly the longer row, so both
    # rows never fit one page and the second row forces a second page.
    request['resultDelivery']['limits']['maxFileBytes'] = (
        len(prefix_bytes(schema_json=schema_json)) + len(longest_row_bytes) + len(rq.PAGE_SUFFIX)
    )
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0, 1]
    parsed_pages = [json.loads(page) for page in pages.values()]
    assert parsed_pages[0]['batch_index'] == 0
    assert parsed_pages[0]['record_offset'] == 0
    assert parsed_pages[0]['data']['items'] == [{'city': 'New York', 'country': 'USA'}]
    assert parsed_pages[1]['batch_index'] == 1
    assert parsed_pages[1]['record_offset'] == 1
    assert parsed_pages[1]['data']['items'] == [{'city': 'Beautiful city of lights', 'country': 'France'}]
    # The schema repeats identically and in result-column order on every page.
    assert (
        parsed_pages[0]['schema']
        == parsed_pages[1]['schema']
        == [
            {'column_name': 'city', 'vendor_data_type': 'character varying(255)'},
            {'column_name': 'country', 'vendor_data_type': 'character varying(255)'},
        ]
    )
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
    assert event_metadata(events[0])['includeSchema'] is True


def test_producer_schema_omitted_entirely_when_not_requested(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], vendor_types={(23, -1): 'integer'})
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=False), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert b'"schema"' not in page
    # The schema lookup is never issued when schema is not requested.
    control_executed = [entry[0] for entry in pool.cursors[0].executed]
    assert 'pg_catalog.format_type' not in ' '.join(control_executed)


def test_producer_resolves_distinct_type_pairs_with_one_parameterized_lookup(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [
        FakeColumn('a', 1043, 255),
        FakeColumn('b', 1043, 255),
        FakeColumn('c', 23, -1),
    ]
    pool = FakePool(
        rows=[('x', 'y', 'z')],
        description=columns,
        vendor_types={(1043, 255): 'character varying(255)', (23, -1): 'text'},
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
    assert 'pg_catalog.format_type(t.type_oid::oid, t.type_mod::int4)' in query
    # Only the DISTINCT (oid, typmod) pairs are resolved (two columns share one pair).
    assert sorted(zip(params[0], params[1])) == [('1043', '255'), ('23', '-1')]
    executed_names = [entry[0] for entry in control.executed]
    assert executed_names.index(schema_queries[0][0]) < executed_names.index('ROLLBACK')
    (page,) = assembled_pages(fake).values()
    assert json.loads(page)['schema'] == [
        {'column_name': 'a', 'vendor_data_type': 'character varying(255)'},
        {'column_name': 'b', 'vendor_data_type': 'character varying(255)'},
        {'column_name': 'c', 'vendor_data_type': 'text'},
    ]


def test_producer_rejects_duplicate_result_column_names_before_row_data(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [FakeColumn('value', 23), FakeColumn('value', 23)]
    pool = FakePool(rows=[(1, 1)], description=columns)
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'duplicate_columns', 'value')
    # No row data was fetched or written: the run fails before any page bytes.
    server = pool.cursors[1]
    assert server.fetch_sizes == []
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


def test_producer_fails_closed_on_incomplete_requested_schema(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # The catalog lookup cannot resolve the described (oid, typmod).
    pool = FakePool(rows=[(1,)], vendor_types={})
    fake = FakeUploadClient()

    events = collect_events(valid_request(include_schema=True), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'schema_unavailable')
    server = pool.cursors[1]
    assert server.fetch_sizes == []
    assert fake.put_page_calls == []


def test_producer_fails_closed_when_description_lacks_type_modifiers(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    column = FakeColumn('value', 23)
    column._fmod = None
    pool = FakePool(rows=[(1,)], description=[column])

    events = collect_events(valid_request(include_schema=True), make_check(pool=pool), client=FakeUploadClient())

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


ROW_BYTES = b'{"payload":"aaaa"}'  # 18 bytes for description [FakeColumn('payload', 25)]


def two_row_boundary_request(monkeypatch, extra_file_bytes=0):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request()
    request['resultDelivery']['limits']['maxFileBytes'] = (
        prefix_len + len(ROW_BYTES) + 1 + len(ROW_BYTES) + len(rq.PAGE_SUFFIX) + extra_file_bytes
    )
    request['resultDelivery']['limits']['maxSchemaBytes'] = 1
    return request


def test_page_split_row_too_large_when_row_exceeds_max_row_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = bounded_request(maxRowBytes=len(ROW_BYTES) - 1)
    pool = FakePool(rows=[('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    assert fake.put_page_calls == []


def test_page_upload_streams_before_cursor_is_exhausted(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    request = bounded_request(maxPages=128, maxResultBytes=64 * 1024)

    def row_provider():
        for _index in range(500):
            yield ('aaaa',)
        order_log.append(('exhausted',))

    pool = FakePool(
        rows=None,
        description=[FakeColumn('payload', 25)],
        row_provider=row_provider,
        fetch_log=order_log,
    )
    fake = FakeUploadClient(put_log=order_log)

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    # Pages are uploaded while rows are still being fetched: the producer never buffers
    # the complete result before uploading, only one bounded page at a time.
    first_put = next(index for index, entry in enumerate(order_log) if entry[0] == 'put')
    later_fetch = next(
        index for index, entry in enumerate(order_log[first_put:], start=first_put) if entry[0] == 'fetch'
    )
    assert later_fetch > first_put
    exhausted = next(index for index, entry in enumerate(order_log) if entry[0] == 'exhausted')
    assert exhausted > first_put
    # Pages are contiguous zero-based, no page exceeds maxFileBytes, and every row is
    # declared exactly once across the page PUTs.
    page_indexes = sorted({call.batch_index for call in fake.put_page_calls})
    assert page_indexes == list(range(len(page_indexes)))
    assert sum(call.rows for call in fake.put_page_calls) == 500
    assert event_metadata(events[-1])['upload_receipt']['totalRows'] == 500
    assert event_metadata(events[-1])['upload_receipt']['pageCount'] == len(page_indexes)
    max_file_bytes = request['resultDelivery']['limits']['maxFileBytes']
    assert all(call.page_bytes <= max_file_bytes for call in fake.put_page_calls)


# ---------------------------------------------------------------------------
# PostgreSQL value contract (pinned, cross-language)
# ---------------------------------------------------------------------------


def encode_value(value, top_type_oid=None, in_array=False):
    out = bytearray()
    remote_query._encode_json_value(out, value, top_type_oid=top_type_oid, in_array=in_array)
    return bytes(out)


@pytest.mark.parametrize(
    'value, expected',
    [
        (None, b'null'),
        (True, b'true'),
        (False, b'false'),
        # Integral numerics keep their exact database digits.
        (1, b'1'),
        (-42, b'-42'),
        (9223372036854775807, b'9223372036854775807'),
        # Arbitrary-precision numerics keep the exact database text: no float round-trip.
        (Decimal('1.5000'), b'1.5000'),
        (Decimal('12345678901234567890.123456789'), b'12345678901234567890.123456789'),
        (Decimal('-0.000001'), b'-0.000001'),
        # Non-finite numerics become the documented strings.
        (Decimal('NaN'), b'"NaN"'),
        (Decimal('Infinity'), b'"Infinity"'),
        (Decimal('-Infinity'), b'"-Infinity"'),
        # Exact server text for float4/float8 (raw text loader output).
        (RawJsonNumber('0.1'), b'0.1'),
        (RawJsonNumber('100000'), b'100000'),  # not '100000.0'
        (RawJsonNumber('1e+16'), b'1e+16'),
        (RawJsonNumber('-0'), b'-0'),
        (RawJsonNumber('NaN'), b'"NaN"'),
        (RawJsonNumber('Infinity'), b'"Infinity"'),
        (RawJsonNumber('-Infinity'), b'"-Infinity"'),
        # Fallback float path: finite repr, non-finite documented strings.
        (0.1, b'0.1'),
        (100000.0, b'100000.0'),
        (float('nan'), b'"NaN"'),
        (float('inf'), b'"Infinity"'),
        (float('-inf'), b'"-Infinity"'),
        # Text/enum/UUID families become JSON strings.
        ('plain', b'"plain"'),
        ('with "quotes" and \\backslash', b'"with \\"quotes\\" and \\\\backslash"'),
        ('héllo', b'"h\\u00e9llo"'),
        ('a\nb\tc', b'"a\\nb\\tc"'),
        (uuid_module.UUID('8b6fb1b5-94dd-447b-95a4-91f4ef118f4b'), b'"8b6fb1b5-94dd-447b-95a4-91f4ef118f4b"'),
        # inet/cidr/interval keep their exact server text (raw text loader output).
        ('192.168.1.5', b'"192.168.1.5"'),
        ('192.168.1.0/24', b'"192.168.1.0/24"'),
        ('1 year 2 mons 3 days 04:05:06', b'"1 year 2 mons 3 days 04:05:06"'),
        # Temporal families become documented ISO-8601 strings.
        (date(2026, 8, 28), b'"2026-08-28"'),
        (dt_time(12, 34, 56, 123456), b'"12:34:56.123456"'),
        (dt_time(12, 34, 56, tzinfo=timezone.utc), b'"12:34:56+00:00"'),
        (datetime(2026, 8, 28, 12, 34, 56, 123456), b'"2026-08-28T12:34:56.123456"'),
        # timestamptz is canonicalized to UTC with a Z suffix, independent of session TZ.
        (
            datetime(2026, 8, 28, 14, 34, 56, 123456, tzinfo=timezone(timedelta(hours=2))),
            b'"2026-08-28T12:34:56.123456Z"',
        ),
        # json/jsonb become nested JSON values; arbitrary-precision numbers survive.
        ({'a': [1, None, True]}, b'{"a":[1,null,true]}'),
        ({'price': Decimal('1.10')}, b'{"price":1.10}'),
        # Arrays become JSON arrays with recursive element conversion.
        (['x', None, ['y', b'\x00']], b'["x",null,["y","AA=="]]'),
        ([RawJsonNumber('0.1'), RawJsonNumber('NaN')], b'[0.1,"NaN"]'),
        ([Decimal('1.5000'), 2, None], b'[1.5000,2,null]'),
        # bytea becomes a base64 string.
        # Ranges and extension types keep their documented string form.
        ('[1,5)', b'"[1,5)"'),
        ('(1,2)', b'"(1,2)"'),
    ],
)
def test_value_contract_encodes_each_family(value, expected):
    assert encode_value(value) == expected


def test_value_contract_bytea_is_base64_only_for_the_bytea_oid():
    assert encode_value(b'\x00\xff\x80', top_type_oid=BYTEA_OID) == b'"AP+A"'
    # A binary buffer from any other column fails closed instead of silently stringifying.
    with pytest.raises(rq.RemoteQueryFailure) as excinfo:
        encode_value(b'\x00\xff\x80', top_type_oid=25)
    assert excinfo.value.code == 'unsupported_value'


@pytest.mark.parametrize('value', [timedelta(days=1), object(), {1}])
def test_value_contract_fails_closed_on_unconvertible_values(value):
    with pytest.raises(rq.RemoteQueryFailure) as excinfo:
        encode_value(value)
    assert excinfo.value.code == 'unsupported_value'


@pytest.mark.parametrize('value', [RawJsonNumber('1.5.2'), RawJsonNumber(''), RawJsonNumber('abc')])
def test_value_contract_fails_closed_on_non_json_numeric_text(value):
    with pytest.raises(rq.RemoteQueryFailure) as excinfo:
        encode_value(value)
    assert excinfo.value.code == 'unsupported_value'


def test_value_contract_producer_emits_pinned_row_json(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    columns = [
        FakeColumn('null_value', 25),
        FakeColumn('bool_value', 16),
        FakeColumn('int_value', 20),
        FakeColumn('numeric_value', 1700),
        FakeColumn('float_value', 701),
        FakeColumn('text_value', 25),
        FakeColumn('uuid_value', 2950),
        FakeColumn('bytea_value', 17),
        FakeColumn('timestamp_value', 1114),
        FakeColumn('timestamptz_value', 1184),
        FakeColumn('date_value', 1082),
        FakeColumn('interval_value', 1186),
        FakeColumn('json_value', 114),
        FakeColumn('array_value', 1009),
    ]
    row = (
        None,
        True,
        42,
        Decimal('12345678901234567890.123456789'),
        RawJsonNumber('0.1'),
        'héllo "quoted"',
        uuid_module.UUID('8b6fb1b5-94dd-447b-95a4-91f4ef118f4b'),
        b'\x00\xff\x80',
        datetime(2026, 8, 28, 12, 34, 56, 123456),
        datetime(2026, 8, 28, 14, 34, 56, 123456, tzinfo=timezone(timedelta(hours=2))),
        date(2026, 8, 28),
        '1 mon 2 days 03:04:05',
        {'nested': [1, None, True], 'price': Decimal('1.10')},
        ['x', None, ['y', b'\x00\xff']],
    )
    pool = FakePool(rows=[row], description=columns)
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    parsed = json.loads(page)['data']['items'][0]
    assert parsed == {
        'null_value': None,
        'bool_value': True,
        'int_value': 42,
        'numeric_value': 12345678901234567890.123456789,
        'float_value': 0.1,
        'text_value': 'héllo "quoted"',
        'uuid_value': '8b6fb1b5-94dd-447b-95a4-91f4ef118f4b',
        'bytea_value': 'AP+A',
        'timestamp_value': '2026-08-28T12:34:56.123456',
        'timestamptz_value': '2026-08-28T12:34:56.123456Z',
        'date_value': '2026-08-28',
        'interval_value': '1 mon 2 days 03:04:05',
        'json_value': {'nested': [1, None, True], 'price': 1.10},
        'array_value': ['x', None, ['y', 'AP8=']],
    }
    # Exact text preservation is byte-pinned for the numeric families.
    assert b'"numeric_value":12345678901234567890.123456789' in page
    assert b'"float_value":0.1' in page
    assert b'"bytea_value":"AP+A"' in page
    assert b'"timestamptz_value":"2026-08-28T12:34:56.123456Z"' in page
    assert b'"json_value":{"nested":[1,null,true],"price":1.10}' in page


# ---------------------------------------------------------------------------
# Cursor-scoped exact-text loaders
# ---------------------------------------------------------------------------


def test_raw_json_number_loader_keeps_exact_server_text():
    loader = RawJsonNumberLoader(701)
    value = loader.load(b'0.1')
    assert isinstance(value, RawJsonNumber)
    assert value == '0.1'
    assert loader.load(b'NaN') == 'NaN'
    assert loader.load(b'-Infinity') == '-Infinity'


def test_raw_text_loader_keeps_exact_server_text():
    loader = RawTextLoader(1186)
    value = loader.load(b'1 year 2 mons')
    assert type(value) is str
    assert value == '1 year 2 mons'


def test_exact_json_loaders_preserve_arbitrary_precision_numbers():
    json_loader = remote_query.ExactJsonLoader(114)
    jsonb_loader = remote_query.ExactJsonbLoader(3802)
    parsed = json_loader.load(b'{"price": 1.10, "big": 123456789012345678901234567890}')
    assert parsed['price'] == Decimal('1.10')
    assert str(parsed['price']) == '1.10'
    assert parsed['big'] == 123456789012345678901234567890
    assert jsonb_loader.load(b'[1.5000, null, "x"]') == [Decimal('1.5000'), None, 'x']


def test_register_exact_loaders_scopes_to_the_query_cursor():
    adapters = FakeAdapters()
    cursor = SimpleNamespace(adapters=adapters)

    remote_query.register_exact_loaders(cursor)

    registered = dict(adapters.registered_loaders)
    assert set(registered) == {'float4', 'float8', 'interval', 'inet', 'cidr', 'json', 'jsonb'} | set(
        remote_query.RANGE_TYPE_NAMES
    )
    assert registered['float4'] is RawJsonNumberLoader
    assert registered['float8'] is RawJsonNumberLoader
    assert registered['interval'] is RawTextLoader
    assert registered['inet'] is RawTextLoader
    assert registered['cidr'] is RawTextLoader
    assert registered['int4range'] is RawTextLoader
    assert registered['numrange'] is RawTextLoader
    assert registered['tstzmultirange'] is RawTextLoader
    assert registered['json'] is remote_query.ExactJsonLoader
    assert registered['jsonb'] is remote_query.ExactJsonbLoader


def test_psycopg_array_loading_uses_the_cursor_scoped_loaders():
    # Real psycopg array loading resolves element loaders through the adapters map of the
    # loading context, so float8[] elements keep their exact server text too.
    import psycopg.postgres as pg_postgres
    from psycopg.adapt import AdaptersMap
    from psycopg.types.array import ArrayLoader

    adapters = AdaptersMap(pg_postgres.adapters)
    adapters.register_loader('float8', RawJsonNumberLoader)
    adapters.register_loader('bytea', remote_query.RawTextLoader)  # any raw-text loader is fine for wiring
    context = SimpleNamespace(adapters=adapters, connection=None)
    float8_array_oid = pg_postgres.types['float8'].array_oid
    loader = type('Float8ArrayLoader', (ArrayLoader,), {'base_oid': 701})(float8_array_oid, context)

    values = loader.load(b'{0.1,NaN,100000,-0}')

    assert values == ['0.1', 'NaN', '100000', '-0']
    assert all(isinstance(value, RawJsonNumber) for value in values)


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
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
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


def test_stream_fails_closed_on_page_receipt_mismatch(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = two_row_boundary_request(monkeypatch, extra_file_bytes=-1)
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    bad_receipt = {
        'batch_index': 0,
        'key': 'agent-intake-test/pages/0.json',
        'record_offset': 0,
        'bytes': 123,
        'rows': 1,
        'sha256': 'f' * 64,
    }
    fake = FakeUploadClient(put_page_response=bad_receipt)

    events = collect_events(request, make_check(pool=pool), client=fake)

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
    values = iter([0.0, 0.0] + [10.0] * 50)
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
        rows=[(1,)], fetch_error=psycopg_errors.QueryCanceled('canceling statement due to statement timeout')
    )

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'timeout', 'statement timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


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
