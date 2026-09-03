# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import json
import uuid as uuid_module
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from datetime import time as dt_time
from decimal import Decimal
from types import SimpleNamespace

import pytest

from datadog_checks.postgres import remote_query
from datadog_checks.postgres.config_models.instance import RemoteQueries
from datadog_checks.postgres.remote_query import (
    RawJsonNumber,
    RawJsonNumberLoader,
    RawTextLoader,
    StaticPostgresCheckRegistry,
    execute_agent_rpc_stream_copy,
    iter_agent_rpc_stream_events,
    normalize_target,
)

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'
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
    """Plain cursor for BEGIN/SET LOCAL/ROLLBACK and the one format_type catalog lookup."""

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
        pytest.fail('statement_timeout should not be read outside transaction-local settings')


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
    ):
        self.rows = rows or []
        self.description = description or [FakeColumn('value', 23)]
        self.closed = closed
        self.vendor_types = vendor_types or {}
        self.fetch_error = fetch_error
        self.fetch_error_at = fetch_error_at
        self.row_provider = row_provider
        self.fetch_log = fetch_log
        self.requested_dbnames = []
        self.cursors = []

    def is_closed(self):
        return self.closed

    @contextmanager
    def get_connection(self, dbname):
        self.requested_dbnames.append(dbname)
        yield FakeConnection(self)


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


def make_check(
    host='localhost', port=5432, dbname='datadog_test', pool=None, check_database_identifier=None, **metadata
):
    check = SimpleNamespace(
        _config=SimpleNamespace(host=host, port=port, dbname=dbname, **metadata),
        db_pool=pool if pool is not None else FakePool(),
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
# Target normalization and validation
# ---------------------------------------------------------------------------


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
def test_stream_rejects_non_page_operation_before_pool_access(operation):
    pool = FakePool(rows=[(1,)])
    request = valid_request()
    if operation is None:
        del request['operation']
    else:
        request['operation'] = operation

    events = collect_events(request, make_check(pool=pool))

    assert_failed_event(events, 'invalid_request', 'operation')
    assert pool.requested_dbnames == []


@pytest.mark.parametrize('include_schema', ['true', 1, None])
def test_stream_rejects_non_boolean_include_schema_before_pool_access(include_schema):
    pool = FakePool(rows=[(1,)])
    request = valid_request()
    request['includeSchema'] = include_schema

    events = collect_events(request, make_check(pool=pool))

    assert_failed_event(events, 'invalid_request', 'includeSchema')
    assert pool.requested_dbnames == []


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


def test_stream_requires_dbname_match_even_when_host_and_port_match():
    pool = FakePool(rows=[(1,)])
    check = make_check(host='localhost', port=5432, dbname='datadog_test', pool=pool)

    events = collect_events(valid_request(dbname='postgres'), check)

    assert_failed_event(events, 'target_not_found')
    assert pool.requested_dbnames == []


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

    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', get_config)
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
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

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
    limits = remote_query.RemoteQueryUploadLimits.model_validate(valid_limits(timeoutMs=7_777))
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=300_000))

    assert remote_query._resolve_statement_timeout_ms(check, limits) == 300_000


@pytest.mark.parametrize(
    'remote_queries',
    [None, SimpleNamespace(timeout_ms=None), SimpleNamespace(timeout_ms=0)],
    ids=['section-unset', 'timeout-unset', 'timeout-non-positive'],
)
def test_statement_timeout_resolution_falls_back_to_delivery_limit(remote_queries):
    limits = remote_query.RemoteQueryUploadLimits.model_validate(valid_limits(timeoutMs=7_777))
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
    assert fake.page_finalize_calls == [0]
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
        len(prefix_bytes(schema_json=schema_json)) + len(longest_row_bytes) + len(remote_query.PAGE_SUFFIX)
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
    assert fake.page_finalize_calls == [0, 1]
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
    assert fake.put_part_calls == []


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
    assert fake.put_part_calls == []


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
    request = bounded_request(part_bytes=32)
    request['resultDelivery']['limits']['maxFileBytes'] = (
        prefix_len + len(ROW_BYTES) + 1 + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX) + extra_file_bytes
    )
    return request


def test_page_split_exact_boundary_fit_keeps_one_page(monkeypatch):
    request = two_row_boundary_request(monkeypatch)
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

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
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

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
    pool = FakePool(rows=[('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_failed_event(events, 'row_too_large', 'maxFileBytes')
    # Nothing was uploaded: the failure is detected before writing the row.
    assert fake.put_part_calls == []


def test_page_split_row_too_large_when_row_exceeds_max_row_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    request = bounded_request(maxRowBytes=len(ROW_BYTES) - 1)
    pool = FakePool(rows=[('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    assert fake.put_part_calls == []


def test_page_split_enforces_max_pages(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(maxPages=1, maxFileBytes=prefix_len + len(ROW_BYTES) + len(remote_query.PAGE_SUFFIX))
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

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
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_failed_event(events, 'max_result_bytes_exceeded', 'maxResultBytes')
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_part_bookkeeping_rows_span_parts_and_never_count_newlines(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    prefix_len = len(prefix_bytes())
    # partBytes equals the prefix length: part 1 is exactly the prefix (no row completes
    # inside it), the rest of the page -- the row, including embedded newlines, plus the
    # suffix -- forms the final short part. The row completes in the part containing its
    # final byte, and rows are never inferred by counting newlines in part bytes.
    request = bounded_request(part_bytes=prefix_len)
    pool = FakePool(rows=[('a\nb\nc',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    assert [call[1] for call in fake.put_part_calls] == [1, 2]
    assert [call[4] for call in fake.put_part_calls] == [0, 1]
    assert sum(call[4] for call in fake.put_part_calls) == 1
    page = b''.join(call[2] for call in fake.put_part_calls)
    assert json.loads(page)['data']['items'] == [{'payload': 'a\nb\nc'}]
    # Row bytes are tracked exactly once: one row total despite the embedded newlines.
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
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

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


def test_part_upload_streams_before_cursor_is_exhausted(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    prefix_len = len(prefix_bytes())
    request = bounded_request(part_bytes=prefix_len, maxPages=128, maxResultBytes=64 * 1024)

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
    # Parts are uploaded while rows are still being fetched: the producer never buffers
    # the complete result (or a complete page) before uploading.
    first_put = next(index for index, entry in enumerate(order_log) if entry[0] == 'put')
    later_fetch = next(
        index for index, entry in enumerate(order_log[first_put:], start=first_put) if entry[0] == 'fetch'
    )
    assert later_fetch > first_put
    exhausted = next(index for index, entry in enumerate(order_log) if entry[0] == 'exhausted')
    assert exhausted > first_put
    # Pages are contiguous zero-based, every non-final part of every page is exactly
    # partBytes, and all rows are accounted for exactly once.
    page_indexes = sorted({entry[0] for entry in fake.put_part_calls})
    assert page_indexes == list(range(len(page_indexes)))
    assert sum(entry[4] for entry in fake.put_part_calls) == 500
    assert event_metadata(events[-1])['upload_receipt']['totalRows'] == 500
    assert event_metadata(events[-1])['upload_receipt']['pageCount'] == len(page_indexes)
    for batch in page_indexes:
        parts = [call for call in fake.put_part_calls if call[0] == batch]
        # Non-final parts of a page are exactly partBytes; the final part may be shorter.
        assert all(len(call[2]) == prefix_len for call in parts[:-1])
        assert len(parts[-1][2]) <= prefix_len


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
    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
        encode_value(b'\x00\xff\x80', top_type_oid=25)
    assert excinfo.value.code == 'unsupported_value'


@pytest.mark.parametrize('value', [timedelta(days=1), object(), {1}])
def test_value_contract_fails_closed_on_unconvertible_values(value):
    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
        encode_value(value)
    assert excinfo.value.code == 'unsupported_value'


@pytest.mark.parametrize('value', [RawJsonNumber('1.5.2'), RawJsonNumber(''), RawJsonNumber('abc')])
def test_value_contract_fails_closed_on_non_json_numeric_text(value):
    with pytest.raises(remote_query.RemoteQueryFailure) as excinfo:
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
    # Valid names are trimmed and lowercased so the emitted ``test-drive-<name>: 1`` header is
    # deterministic regardless of how the Agent config value is cased or padded.
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
    # Invalid names must fail closed to None so no Test Drive header is emitted: the permanent
    # service is targeted and the Agent config value cannot inject arbitrary headers.
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

    # The Agent-config Test Drive name is read through the dedicated config key and normalized
    # before reaching the uploader; an absent value yields None so the upload keeps the
    # permanent-service path instead of routing to a Test Drive.
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
    pool = FakePool(rows=[('aaaa',), ('aaaa',)], description=[FakeColumn('payload', 25)])
    fake = FakeUploadClient()

    events = collect_events(request, make_check(pool=pool), client=fake)

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
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient(
        raise_on_put=remote_query.RemoteQueryFailure('upload_failed', 'transient exhausted', retryable=True)
    )

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'upload_failed')
    assert len(fake.put_part_calls) == 1
    assert fake.abort_calls == 1
    assert fake.run_finalize_calls == 0
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_stream_fails_closed_on_partial_page_finalization(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient(
        raise_on_page_finalize=remote_query.RemoteQueryFailure('upload_failed', 'page finalize rejected')
    )

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'upload_failed')
    assert fake.page_finalize_calls == [0]
    assert fake.run_finalize_calls == 0
    assert fake.abort_calls == 1
    assert 'upload_receipt' not in event_metadata(events[-1])


def test_stream_fails_closed_on_run_finalize_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)])
    fake = FakeUploadClient(
        raise_on_run_finalize=remote_query.RemoteQueryFailure('upload_failed', 'run finalize rejected')
    )

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
