# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import upload as rq_upload
from datadog_checks.postgres.remote_query import PostgresRemoteQueryHandler


class FakeUploadClient:
    """Intake-side fake: one descriptor registration, page acceptance receipts, finalize totals.

    Page PUTs answer the pinned acceptance receipt — no per-page final metadata exists at
    acceptance — and the default finalize returns authoritative totals over the recorded
    pages, so the producer's stats and compact receipt come from finalization.
    ``reject_first_page_too_large`` answers page 0's first PUT with intake's defensive
    final_page_too_large rejection, so a run exercises the split-and-retry path; every
    attempt (rejected or accepted) is recorded in ``put_attempts``.
    """

    def __init__(
        self,
        put_page_response=None,
        put_log=None,
        reject_first_page_too_large=False,
    ):
        # SimpleNamespace(batch_index, record_offset, source_bytes, rows, payload)
        self.descriptor_bodies = []
        self.put_page_calls = []
        self.put_attempts = []
        self.run_finalize_calls = 0
        self.finalize_expected_page_counts = []
        self.abort_calls = 0
        self.reject_first_page_too_large = reject_first_page_too_large
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
        self.put_attempts.append(page.batch_index)
        if self.reject_first_page_too_large and page.batch_index == 0 and self.put_attempts.count(0) == 1:
            raise rq_contract.RemoteQueryFailure(
                rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake rejected the final page size.'
            )
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
        return {
            'upload_id': creds.upload_id,
            'page_count': len(self.put_page_calls),
            'total_rows': sum(call.rows for call in self.put_page_calls),
            'total_bytes': sum(call.source_bytes for call in self.put_page_calls),
        }

    def abort(self, creds):
        self.abort_calls += 1

    def pages(self):
        """Each completed page's exact uploaded source bytes, keyed by batch index."""
        return {call.batch_index: call.payload for call in self.put_page_calls}


def native_field(value: Any) -> str:
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


def native_record(*values: Any) -> bytes:
    """The expected native COPY CSV record for one row of values."""
    return (','.join(native_field(value) for value in values) + '\n').encode('utf-8')


def event_metadata(event):
    return event.metadata


def assert_success(events):
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    return event_metadata(events[-1])


RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'


TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'


UPLOAD_ID = 'upload-01k'


AGENT_HOSTNAME = 'rq-proof-agent-a'


BASE_URL = 'https://dd.datad0g.com/api/unstable/its-agent-intake'


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

    monkeypatch.setattr(rq_upload.datadog_agent, 'get_config', get_config)


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
    return list(PostgresRemoteQueryHandler(check).execute(request, http_client=client))


def assert_failed_event(events, code, message_contains=None):
    assert events[-1].event_type == 'error'
    assert event_metadata(events[-1])['status'] == 'FAILED'
    assert event_metadata(events[-1])['error']['code'] == code
    if message_contains is not None:
        assert message_contains in event_metadata(events[-1])['error']['message']


def prefix_bytes(record_offset=0, agent_hostname=AGENT_HOSTNAME, schema_json=None):
    return rq_pages.page_prefix(
        run_id=RUN_ID,
        task_id=TASK_ID,
        record_offset=record_offset,
        agent_hostname=agent_hostname,
        schema_json=schema_json,
    )


def assembled_pages(fake_client):
    """Each completed page's exact uploaded source bytes, keyed by batch index."""
    return {call.batch_index: call.payload for call in fake_client.put_page_calls}


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
    return list(PostgresRemoteQueryHandler(check).resolve(request))


def assert_matched_verdict(events):
    """A verdict is exactly one MATCHED final event with no payload and no STARTED event."""
    assert len(events) == 1
    event = events[0]
    assert event.event_type == 'final'
    assert event.payload == b''
    metadata = event_metadata(event)
    assert metadata['status'] == 'MATCHED'
    return metadata['match']


BOUND_NAMES = ['payload']


BOUND_RECORD = native_record('a' * 167)  # 170 bytes


def two_row_boundary_request(monkeypatch):
    """A budget whose source-page target closes exactly one wide record per page."""
    patch_upload_credentials(monkeypatch)
    return bounded_request(maxFileBytes=200, maxRowBytes=200, maxSchemaBytes=1, maxPages=128, maxResultBytes=64 * 1024)


def wide_row_pool():
    """A pool whose two wide rows each close their own page under the boundary request."""
    return FakePool(
        rows=[('a' * 167,), ('a' * 167,)],
        description=[FakeColumn('payload', 25)],
        vendor_types={(25, -1): 'text'},
    )
