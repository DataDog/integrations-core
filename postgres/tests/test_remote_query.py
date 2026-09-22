# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json
import logging
import socket
from contextlib import contextmanager
from types import SimpleNamespace

import psycopg.errors as psycopg_errors
import pytest

from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing
from datadog_checks.postgres import PostgreSql, remote_query
from datadog_checks.postgres.config_models.instance import RemoteQueries

from .remote_query_fakes import (
    AGENT_HOSTNAME,
    BASE_URL,
    BOUND_RECORD,
    RUN_ID,
    TASK_ID,
    UPLOAD_ID,
    ExplodingCheck,
    FakeColumn,
    FakePlainCursor,
    FakePool,
    FakeServerCursor,
    FakeUploadClient,
    assembled_pages,
    assert_failed_event,
    assert_success,
    bounded_request,
    collect_events,
    event_metadata,
    make_check,
    native_record,
    patch_allowlist_disabled,
    patch_upload_credentials,
    prefix_bytes,
    resolve_request,
    two_row_boundary_request,
    valid_request,
    wide_row_pool,
)


@pytest.fixture
def runtime_check():
    check = PostgreSql('postgres', {}, [{'host': 'localhost', 'dbname': 'datadog_test', 'username': 'datadog'}])
    check.db_pool = FakePool(rows=[(1,)])
    return check


@pytest.fixture(autouse=True)
def null_native_producer_tracing(monkeypatch):
    """Keep native ddtrace producer spans out of every test in this module.

    The produce lifecycle opens real producer spans through
    `open_remote_query_producer_tracing` whenever ddtrace is importable — including in
    this suite's process — so the module-wide default here is the null tracing. The
    span-boundary behavior is pinned by the recording tracing test below and by the
    shared checks-base suite; no test here emits real spans or depends on a trace agent.
    """
    monkeypatch.setattr(
        rq_tracing,
        'open_remote_query_producer_tracing',
        lambda trace_context, integration: rq_tracing.NULL_PRODUCER_TRACING,
    )


@pytest.mark.parametrize('field', ['extra', 'password'])
def test_stream_rejects_unknown_request_fields_before_resolution(caplog, field):
    request = valid_request(**{field: 'SECRET_DO_NOT_LOG'})

    events = collect_events(request, ExplodingCheck())

    assert_failed_event(events, 'invalid_request', field)
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


@pytest.mark.parametrize(
    'request_json', ['{"password": "SECRET_DO_NOT_LOG"', b'\xff', '[]', 'null', '"SECRET_DO_NOT_LOG"', '1']
)
def test_entry_rejects_unusable_request_json_without_echoing_input(caplog, request_json, runtime_check):
    # The entry-point wiring for the shared request parse: malformed and non-object JSON
    # each emit exactly one fixed invalid_request event, never echoing the input and
    # never touching the check's database pool.
    pool = runtime_check.db_pool
    events = []

    runtime_check.run_remote_query(request_json, lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert len(events) == 1
    assert events[-1][0] == 'error'
    assert metadata['status'] == 'FAILED'
    assert metadata['error']['code'] == 'invalid_request'
    assert 'JSON object' in metadata['error']['message']
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    assert pool.requested_dbnames == []


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


def test_stream_credentials_unavailable_without_agent_keys(monkeypatch):
    def get_config(key):
        return None

    monkeypatch.setattr(rq_events.datadog_agent, 'get_config', get_config)
    pool = FakePool(rows=[(1,)])

    events = collect_events(valid_request(), make_check(pool=pool), client=FakeUploadClient())

    assert_failed_event(events, 'credentials_unavailable')
    assert events[0].event_type == 'error'
    assert pool.requested_dbnames == []


def test_stream_missing_pool_returns_credentials_unavailable(monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = make_check()
    check.db_pool = None

    events = collect_events(valid_request(), check, client=FakeUploadClient())

    assert_failed_event(events, 'credentials_unavailable')


def test_entry_dispatches_resolve_target_by_operation(runtime_check):
    runtime_check._database_identifier = 'Postgres/Primary-A'
    events = []

    runtime_check.run_remote_query(json.dumps(resolve_request()), lambda *event: events.append(event))

    assert len(events) == 1
    event_type, metadata_json, payload = events[0]
    assert event_type == 'final'
    assert payload == b''
    metadata = json.loads(metadata_json)
    assert metadata['status'] == 'MATCHED'
    assert metadata['match']['databaseInstance'] == 'Postgres/Primary-A'


def test_entry_rejects_unknown_operation_without_pool_access(runtime_check):
    pool = runtime_check.db_pool
    request = valid_request()
    request['operation'] = 'bogus_operation'
    events = []

    runtime_check.run_remote_query(json.dumps(request), lambda *event: events.append(event))

    metadata = json.loads(events[-1][1])
    assert events[-1][0] == 'error'
    assert metadata['error']['code'] == 'invalid_request'
    assert pool.requested_dbnames == []


def test_check_interface_executes_and_uploads(monkeypatch, runtime_check):
    # The actual loaded check must reach the producer with its own configured pool.
    patch_upload_credentials(monkeypatch)
    client = FakeUploadClient()
    monkeypatch.setattr(remote_query.rq_upload, 'RequestsUploadClient', lambda **kwargs: client)
    events = []

    runtime_check.run_remote_query(json.dumps(valid_request()), lambda *event: events.append(event))

    assert [event[0] for event in events] == ['metadata', 'final']
    assert json.loads(events[-1][1])['status'] == 'SUCCEEDED'
    assert all(event[2] == b'' for event in events)
    assert runtime_check.db_pool.requested_dbnames == ['datadog_test']
    assert client.run_finalize_calls == 1


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
    assert remote_query.PostgresRemoteQueryHandler(check)._resolve_statement_timeout_ms(deadline) == 5_000

    # An override shorter than the remaining wall is honored as the statement timeout.
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=3_000))
    assert remote_query.PostgresRemoteQueryHandler(check)._resolve_statement_timeout_ms(deadline) == 3_000

    # Without a positive instance override, the remaining wall applies.
    check = make_check(remote_queries=SimpleNamespace(timeout_ms=None))
    assert remote_query.PostgresRemoteQueryHandler(check)._resolve_statement_timeout_ms(deadline) == 5_000

    # An expired wall must not disable the database-side protection: the remainder clamps
    # to 1 ms instead of reaching a zero statement timeout.
    assert remote_query.PostgresRemoteQueryHandler(check)._resolve_statement_timeout_ms(99.0) == 1


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
    budget = len(prefix_bytes(schema_json=schema_json)) + len(rq_pages.PAGE_SUFFIX) + 2
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


@pytest.mark.parametrize('rows_per_block', [1, 500])
def test_page_upload_streams_before_the_copy_is_exhausted(monkeypatch, rows_per_block):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    order_log = []
    request = bounded_request(maxPages=128, maxResultBytes=64 * 1024)

    def block_provider():
        for _index in range(0, 500, rows_per_block):
            yield native_record('aaaa') * rows_per_block
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
    exhausted = next(index for index, entry in enumerate(order_log) if entry[0] == 'exhausted')
    assert exhausted > first_put
    # Pages are contiguous zero-based and every row is declared exactly once across the
    # page PUTs; the compact receipt repeats intake's finalize totals.
    page_indexes = sorted({call.batch_index for call in fake.put_page_calls})
    assert page_indexes == list(range(len(page_indexes)))
    assert sum(call.rows for call in fake.put_page_calls) == 500
    assert b''.join(call.payload for call in fake.put_page_calls) == native_record('aaaa') * 500
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


@pytest.mark.parametrize('chunk_size', [1, 2, 7, 64, 4096])
@pytest.mark.parametrize('reject_page', [False, True])
def test_producer_frames_native_records_across_block_boundaries(monkeypatch, chunk_size, reject_page):
    """The producer carries CSV framing
    state across block boundaries: a record split between blocks, records batched into one
    block, and embedded commas, quotes, and newlines all arrive as one whole, verbatim
    source page."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    first = native_record('a,b', 'He said "Hi"', 'line1\nline2')
    second = native_record(None, '', '\\N')

    def block_provider():
        source = first + second
        for offset in range(0, len(source), chunk_size):
            yield source[offset : offset + chunk_size]

    pool = FakePool(
        block_provider=block_provider,
        description=[FakeColumn('a', 25), FakeColumn('b', 25), FakeColumn('c', 25)],
        vendor_types={(25, -1): 'text'},
    )
    fake = FakeUploadClient(reject_first_page_too_large=reject_page)

    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_success(events)
    calls = fake.put_page_calls
    assert b''.join(call.payload for call in calls) == first + second
    assert sum(call.rows for call in calls) == 2
    assert [(call.batch_index, call.record_offset) for call in calls] == ([(0, 0), (1, 1)] if reject_page else [(0, 0)])


@pytest.mark.parametrize('block, code', [(b'"abc', 'query_failed'), (b'"' + b'x' * 1024, 'row_too_large')])
def test_producer_rejects_incomplete_or_oversized_copy_records(monkeypatch, block, code):
    """A COPY stream that ends inside a record never produces a page for it: the run fails
    closed after the read-only transaction rolls back."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)

    def block_provider():
        yield block
        yield b''

    pool = FakePool(
        block_provider=block_provider,
        description=[FakeColumn('a', 25)],
        vendor_types={(25, -1): 'text'},
    )
    fake = FakeUploadClient()

    events = collect_events(bounded_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, code)
    assert fake.put_page_calls == []
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


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


def test_process_termination_aborts_upload_and_rolls_back(monkeypatch):
    patch_upload_credentials(monkeypatch)
    pool = FakePool(rows=[(1,)], copy_error=SystemExit(2))
    uploads = FakeUploadClient()
    with pytest.raises(SystemExit):
        collect_events(valid_request(), make_check(pool=pool), client=uploads)
    assert uploads.abort_calls == 1
    assert pool.cursors[0].executed[-1][0] == 'ROLLBACK'


def test_source_byte_limit_stops_upload_before_exceeding_result_budget(monkeypatch):
    patch_upload_credentials(monkeypatch)
    record = native_record('x' * 217)
    pool = FakePool(rows=[('x' * 217,)] * 2, description=[FakeColumn('v', 25)], vendor_types={(25, -1): 'text'})
    request = bounded_request(maxFileBytes=250, maxRowBytes=250, maxSchemaBytes=1, maxResultBytes=439)
    uploads = FakeUploadClient()
    events = collect_events(request, make_check(pool=pool), client=uploads)
    assert_failed_event(events, 'max_result_bytes_exceeded')
    assert [call.payload for call in uploads.put_page_calls] == [record]
    assert uploads.run_finalize_calls == 0
    assert uploads.abort_calls == 1


def test_stream_maps_server_statement_cancellation_to_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)

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


def test_entry_propagates_callback_failure_without_upload(monkeypatch, runtime_check):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = runtime_check.db_pool

    def emit(event_type, metadata_json, payload):
        raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        runtime_check.run_remote_query(json.dumps(valid_request()), emit)

    # The callback failed on the STARTED metadata event, before any page bytes existed.
    assert pool.requested_dbnames == []


# ---------------------------------------------------------------------------
# Native producer spans
# ---------------------------------------------------------------------------


class RecordingTracing(rq_tracing.NullRemoteQueryProducerTracing):
    """A null tracing that records the producer's span-boundary calls in order."""

    def __init__(self):
        self.calls = []

    def open_root(self, delivery):
        self.calls.append(('open_root', delivery.run_id, delivery.upload_id))

    def succeed(self, stats):
        self.calls.append(('succeed', stats.pages_emitted))

    def fail(self, error_code, stats):
        self.calls.append(('fail', error_code, stats.pages_emitted))

    def enter_phase(self, name):
        self.calls.append(('enter', name))
        return None

    def enter_fetch(self):
        self.calls.append('fetch')

    def note_page_acknowledged(self):
        self.calls.append('page_ack')

    @contextmanager
    def finalize_span(self):
        self.calls.append('finalize')
        yield

    @contextmanager
    def abort_span(self):
        self.calls.append('abort_span:open')
        try:
            yield
        finally:
            self.calls.append('abort_span:close')

    def close(self):
        self.calls.append('close')


def recording_tracing_factory(tracing):
    """A factory replacement answering the recording tracing and capturing its arguments."""

    def factory(trace_context, integration):
        tracing.calls.append(('factory', trace_context, integration))
        return tracing

    return factory


def test_producer_opens_spans_at_each_timing_phase_boundary(monkeypatch):
    request = two_row_boundary_request(monkeypatch)
    pool = wide_row_pool()
    fake = FakeUploadClient()
    tracing = RecordingTracing()
    monkeypatch.setattr(rq_tracing, 'open_remote_query_producer_tracing', recording_tracing_factory(tracing))

    events = collect_events(request, make_check(pool=pool), client=fake)

    assert_success(events)
    # The native spans open at exactly the accumulator's phase boundaries: the root before
    # the run, setup through the COPY dispatch, encode around the read loop with one fetch
    # boundary per copy.read, a page acknowledgment per accepted page, and the finalize
    # span around run finalization — closed by the terminal success and the single close.
    assert tracing.calls == [
        ('factory', None, 'postgres'),
        ('open_root', RUN_ID, UPLOAD_ID),
        ('enter', 'database_setup'),
        ('enter', 'encode_and_page_build'),
        'fetch',
        'page_ack',
        'fetch',
        'page_ack',
        'fetch',
        'finalize',
        ('succeed', 2),
        'close',
    ]


def test_producer_brackets_the_abort_and_fails_the_root_on_a_produce_failure(monkeypatch, caplog):
    """A produce failure brackets the failure tail's upload abort with the abort span and
    closes the root with the same failure code the event carries, never echoing the
    exception's text on any span."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    pool = FakePool(rows=[(1,)], copy_error=ValueError('SECRET_DO_NOT_LOG row fragment'))
    fake = FakeUploadClient()
    tracing = RecordingTracing()
    monkeypatch.setattr(rq_tracing, 'open_remote_query_producer_tracing', recording_tracing_factory(tracing))

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(pool=pool), client=fake)

    assert_failed_event(events, 'query_failed', 'Remote query execution failed')
    assert fake.abort_calls == 1
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    # The abort span brackets the failure tail's upload abort and closes before the root
    # is marked failed; close runs exactly once, last.
    assert tracing.calls == [
        ('factory', None, 'postgres'),
        ('open_root', RUN_ID, UPLOAD_ID),
        ('enter', 'database_setup'),
        ('enter', 'encode_and_page_build'),
        'fetch',
        'abort_span:open',
        'abort_span:close',
        ('fail', 'query_failed', 0),
        'close',
    ]


def test_producer_fails_the_root_for_an_admission_failure(monkeypatch):
    patch_upload_credentials(monkeypatch)
    tracing = RecordingTracing()
    monkeypatch.setattr(rq_tracing, 'open_remote_query_producer_tracing', recording_tracing_factory(tracing))

    events = collect_events(valid_request(dbname='other_database'), make_check(), client=FakeUploadClient())

    assert_failed_event(events, 'target_not_found')
    # The admission failure still closes the root with the failure code and zero
    # counters; no page, abort, or produce boundary was ever reached.
    assert tracing.calls == [
        ('factory', None, 'postgres'),
        ('open_root', RUN_ID, UPLOAD_ID),
        ('fail', 'target_not_found', 0),
        'close',
    ]
