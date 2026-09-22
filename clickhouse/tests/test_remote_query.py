# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json
import logging
from contextlib import contextmanager

import pytest
import urllib3.exceptions
from clickhouse_connect.driver.exceptions import DatabaseError

from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import tracing as rq_tracing
from datadog_checks.base.utils.remote_queries import upload as rq_upload
from datadog_checks.clickhouse import ClickhouseCheck, remote_query

from .remote_query_fakes import (
    AGENT_HOSTNAME,
    BASE_URL,
    BOUND_ROW,
    ROW_RECORD,
    RUN_ID,
    TASK_ID,
    UPLOAD_ID,
    ExplodingCheck,
    FakeClickhouseClient,
    FakeUploadClient,
    assembled_pages,
    assert_failed_event,
    assert_success,
    bounded_request,
    collect_events,
    compact_json_line,
    csv_record,
    event_metadata,
    make_check,
    make_client,
    patch_upload_credentials,
    prefix_bytes,
    quoted_numeric_rows_client,
    raw_stream_body,
    row_object_bound,
    stream_body,
    two_row_client,
    valid_request,
)


@pytest.fixture
def runtime_check():
    return ClickhouseCheck('clickhouse', {}, [{'server': 'localhost', 'port': 8123, 'db': 'default'}])


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
    # each emit exactly one fixed invalid_request event, never echoing the input.
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


def test_check_interface_executes_and_uploads(monkeypatch, runtime_check):
    # The actual loaded check must reach its client factory and upload producer.
    patch_upload_credentials(monkeypatch)
    client = FakeUploadClient()
    database_client = make_client(rows=[[1]])
    monkeypatch.setattr(remote_query.rq_upload, 'RequestsUploadClient', lambda **kwargs: client)
    monkeypatch.setattr(runtime_check, 'create_remote_query_client', lambda **kwargs: database_client)
    events = []

    runtime_check.run_remote_query(json.dumps(valid_request()), lambda *event: events.append(event))

    assert [event[0] for event in events] == ['metadata', 'final']
    assert json.loads(events[-1][1])['status'] == 'SUCCEEDED'
    assert all(event[2] == b'' for event in events)
    assert len(database_client.raw_stream_calls) == 1
    assert client.run_finalize_calls == 1


def test_stream_executes_arbitrary_query_end_to_end(monkeypatch):
    """A query outside the proof fixtures runs the whole pipeline: contract validation is
    the only admission gate, so the stream reaches the dedicated client."""
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(names=('database',), types=('String',), rows=[['datadog_test']])
    request = valid_request(query='SELECT currentDatabase()')

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    final = assert_success(events)
    assert final['upload_receipt']['totalRows'] == 1


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
    # The source page carries the cell's canonical token, CSV-framed: the NUL stays
    # JSON-escaped exactly as the server rendered it.
    assert page == csv_record([b'"\\u0000ab"'])


def test_stream_requires_dbname_match_even_when_host_and_port_match():
    check = make_check(server='localhost', port=8123, db='default')

    events = collect_events(valid_request(dbname='analytics'), check)

    assert_failed_event(events, 'target_not_found')


def test_stream_credentials_unavailable_without_agent_keys(monkeypatch):
    def get_config(key):
        return None

    monkeypatch.setattr(rq_upload.datadog_agent, 'get_config', get_config)

    events = collect_events(valid_request(), make_check())

    assert_failed_event(events, 'credentials_unavailable')
    assert events[0].event_type == 'error'


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


def test_producer_writes_exact_rfc_v1_envelope_json(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1]])
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # The source page is pure CSV records of canonical cell tokens: no final JSON envelope
    # is built or uploaded here; intake assembles it from the registered descriptor.
    assert page == b'1\n'
    assert json.loads(fake.descriptor_bodies[0]) == {
        'format_version': 'csv-json-cell-v1',
        'include_schema': False,
        'agent_hostname': AGENT_HOSTNAME,
        'columns': [
            {
                'column_name': 'value',
                'vendor_data_type': 'UInt8',
                'logical_type': 'integer',
                'array_element_delimiter': None,
            }
        ],
    }


def test_producer_executes_query_exactly_once_verbatim_with_readonly_settings(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # A constant clock keeps the remaining-wall derivation of max_execution_time exact.
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: 100.0)
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


def test_client_and_server_timeouts_derive_from_the_remaining_wall(monkeypatch):
    patch_upload_credentials(monkeypatch)
    captured = {}

    def create_remote_query_client(send_receive_timeout=None):
        captured['send_receive_timeout'] = send_receive_timeout
        return captured.setdefault('client', make_client(rows=[[1]]))

    check = make_check()
    check.create_remote_query_client = create_remote_query_client
    request = valid_request()
    request['resultDelivery']['limits']['timeoutMs'] = 30_000
    # 20 s of the 30 s wall are already consumed when the client is created and the stream
    # opens, so the send/receive timeout and max_execution_time must come from the remaining
    # 10 s rather than the full delivered budget.
    clock = iter([100.0, 120.0, 120.0] + [120.0] * 50)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: next(clock))

    events = collect_events(request, check, upload_client=FakeUploadClient())

    assert_success(events)
    assert captured['send_receive_timeout'] == 10
    assert captured['client'].raw_stream_calls == [
        {
            'query': 'SELECT 1 AS value',
            'settings': {'readonly': 1, 'max_execution_time': 10.0},
            'fmt': remote_query.REMOTE_QUERY_STREAM_FORMAT,
        }
    ]


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


def test_producer_zero_rows_with_schema_enabled_writes_one_zero_record_page(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[])
    fake = FakeUploadClient()

    events = collect_events(
        valid_request(include_schema=True), make_check(), upload_client=fake, clickhouse_client=clickhouse_client
    )

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
            'vendor_data_type': 'UInt8',
            'logical_type': 'integer',
            'array_element_delimiter': None,
        }
    ]
    assert final['upload_receipt']['pageCount'] == 1
    assert final['upload_receipt']['totalRows'] == 0
    assert final['upload_receipt']['totalBytes'] == 0
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


def test_producer_splits_pages_by_the_schema_bearing_envelope_bound(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(
        names=('city', 'country'), types=('String', 'String'), rows=[['New York', 'USA'], ['Paris', 'France']]
    )
    request = bounded_request(query='SELECT city, country FROM cities ORDER BY city')
    request['includeSchema'] = True
    schema_json = json.dumps(
        [
            {'column_name': 'city', 'vendor_data_type': 'String'},
            {'column_name': 'country', 'vendor_data_type': 'String'},
        ],
        separators=(',', ':'),
    ).encode('utf-8')
    # Intake stamps the schema into every final page, so the producer's bound carries the
    # schema-bearing envelope: maxFileBytes here fits that envelope plus exactly the
    # longer row, so both rows never fit one page and the second row forces a second page.
    request['resultDelivery']['limits']['maxFileBytes'] = (
        len(prefix_bytes(schema_json=schema_json))
        + row_object_bound({'city': 'New York', 'country': 'USA'})
        + len(rq_pages.PAGE_SUFFIX)
    )
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0, 1]
    assert pages[0] == csv_record([json.dumps('New York').encode('utf-8'), json.dumps('USA').encode('utf-8')])
    assert pages[1] == csv_record([json.dumps('Paris').encode('utf-8'), json.dumps('France').encode('utf-8')])
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
    assert [call.record_offset for call in fake.put_page_calls] == [0, 1]
    descriptor = json.loads(fake.descriptor_bodies[0])
    assert descriptor['include_schema'] is True
    assert descriptor['columns'] == [
        {
            'column_name': 'city',
            'vendor_data_type': 'String',
            'logical_type': 'string',
            'array_element_delimiter': None,
        },
        {
            'column_name': 'country',
            'vendor_data_type': 'String',
            'logical_type': 'string',
            'array_element_delimiter': None,
        },
    ]
    assert event_metadata(events[0])['includeSchema'] is True


def test_producer_descriptor_carries_clickhouse_type_strings_and_logical_types(monkeypatch):
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
    # The descriptor's vendor data types are the exact ClickHouse type strings from the
    # stream header, with wrappers peeled for the logical types.
    assert json.loads(fake.descriptor_bodies[0])['columns'] == [
        {
            'column_name': 'count',
            'vendor_data_type': 'Nullable(UInt64)',
            'logical_type': 'integer',
            'array_element_delimiter': None,
        },
        {
            'column_name': 'name',
            'vendor_data_type': 'LowCardinality(String)',
            'logical_type': 'string',
            'array_element_delimiter': None,
        },
        {'column_name': 'flag', 'vendor_data_type': 'Bool', 'logical_type': 'boolean', 'array_element_delimiter': None},
    ]
    assert page == csv_record([b'null', b'"x"', b'true'])


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


def test_page_split_row_too_large_when_record_exceeds_max_row_bytes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # maxRowBytes bounds one framed source record: the 9-byte record for ['aaaa'] cannot fit 8.
    request = bounded_request(maxRowBytes=len(ROW_RECORD) - 1)
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'row_too_large', 'maxRowBytes')
    assert fake.put_page_calls == []


def test_page_split_row_too_large_when_line_exceeds_the_buffer_ceiling(monkeypatch):
    patch_upload_credentials(monkeypatch)
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


def test_row_line_ceiling_reserves_quote_bytes_for_quoted_numeric_columns(monkeypatch):
    patch_upload_credentials(monkeypatch)
    # Servers that quote 64-bit integers (output_format_json_quote_64bit_integers) deliver
    # each value as a JSON string, and the declared column type normalizes it back to its
    # unquoted number token, so a row line runs two quote bytes per column longer than its
    # framed record. Row lines at that length must pass the read-time ceiling whenever the
    # normalized record still fits maxRowBytes: only the exact record-size gate may reject
    # rows. The row repeats so the later lines accumulate through row-bound-sized reads
    # (the first read is sized by the larger header bound), which is where the ceiling
    # binds.
    names = tuple('c{}'.format(index) for index in range(8))
    quoted_value = '18446744073709551615'
    row = [quoted_value] * len(names)
    record = csv_record([quoted_value.encode('utf-8')] * len(names))
    row_line = compact_json_line(row)
    assert len(row_line) == len(record) + 2 * len(names) + 1
    assert len(row_line) > len(record) + remote_query.REMOTE_QUERY_ROW_LINE_SLACK
    rows = 8

    request = bounded_request(maxRowBytes=len(record), maxFileBytes=2048)
    fake = FakeUploadClient()

    events = collect_events(
        request, make_check(), upload_client=fake, clickhouse_client=quoted_numeric_rows_client(names, row, rows)
    )

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert page == record * rows
    assert event_metadata(events[-1])['upload_receipt']['totalRows'] == rows

    # One byte too many in the normalized record: the exact maxRowBytes gate fails the run
    # on the framed record, with the read-time ceiling out of the way.
    request = bounded_request(maxRowBytes=len(record) - 1, maxFileBytes=2048)

    events = collect_events(
        request,
        make_check(),
        upload_client=FakeUploadClient(),
        clickhouse_client=quoted_numeric_rows_client(names, row, rows),
    )

    assert_failed_event(events, 'row_too_large', 'A single record exceeds maxRowBytes')


def test_stream_fails_closed_on_row_line_larger_than_any_read_chunk(monkeypatch):
    patch_upload_credentials(monkeypatch)
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


def test_stream_uploads_pages_and_finalizes_run_in_order(monkeypatch):
    patch_upload_credentials(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(maxFileBytes=prefix_len + row_object_bound(BOUND_ROW) + len(rq_pages.PAGE_SUFFIX))
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # Pages are uploaded in order, each exactly once, and run finalize is the last call.
    assert [call.batch_index for call in fake.put_page_calls] == [0, 1]
    assert fake.run_finalize_calls == 1
    assert fake.abort_calls == 0


def test_stream_enforces_timeout_with_retryable_error(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1], [2], [3]])
    request = valid_request()
    request['resultDelivery']['limits']['timeoutMs'] = 1000
    # The leading zeros cover every earlier clock read (started_at, the client factory's and
    # settings' remaining-time derivations, both stream-read phase brackets, and the
    # per-row guards) so the wall still expires at the page-close guard, after rows were
    # produced.
    values = iter([0.0] * 18 + [10.0] * 50)
    monkeypatch.setattr(remote_query.time, 'monotonic', lambda: next(values))

    events = collect_events(request, make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert clickhouse_client.stream.closed
    assert clickhouse_client.closed


def test_process_termination_aborts_upload_and_closes_stream(monkeypatch):
    patch_upload_credentials(monkeypatch)
    client = make_client(rows=[[1]], read_error=SystemExit(2))
    uploads = FakeUploadClient()
    with pytest.raises(SystemExit):
        collect_events(valid_request(), make_check(), upload_client=uploads, clickhouse_client=client)
    assert uploads.abort_calls == 1
    assert client.closed
    assert client.stream.closed


def test_stream_maps_server_error_to_query_failed(monkeypatch, caplog):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1]]),
        raw_stream_error=DatabaseError('Code: 60. DB::Exception: Table default.SECRET_DO_NOT_LOG does not exist'),
    )
    fake = FakeUploadClient()

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    # The server's message (table names, query text) never crosses the callback or the logs.
    assert_failed_event(events, 'query_failed')
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    assert fake.abort_calls == 1


def test_stream_maps_mid_stream_connection_drop_to_retryable_timeout(monkeypatch, caplog):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1], [2], [3]]),
        read_error=urllib3.exceptions.ProtocolError('Connection broken: SECRET_DO_NOT_LOG'),
    )

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout', 'interrupted')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert clickhouse_client.stream.closed
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_stream_maps_mid_stream_read_timeout_to_retryable_timeout(monkeypatch):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1], [2], [3]]),
        read_error=urllib3.exceptions.ReadTimeoutError(None, 'http://test', 'timed out'),
    )

    events = collect_events(valid_request(), make_check(), clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout')
    assert event_metadata(events[-1])['error']['retryable'] is True


def test_stream_maps_unexpected_source_failure_to_fixed_query_failed(monkeypatch, caplog):
    """An unexpected mid-stream failure maps to the fixed query_failed error: the exception
    can carry raw row fragments, so neither the event nor the logs echo its text."""
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1], [2], [3], [4], [5]]),
        read_error=ValueError('SECRET_DO_NOT_LOG row fragment'),
        error_at=2,
    )
    fake = FakeUploadClient()

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'query_failed', 'Remote query execution failed')
    assert event_metadata(events[-1])['error']['retryable'] is False
    assert fake.abort_calls == 1
    assert clickhouse_client.stream.closed
    assert clickhouse_client.closed
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


@pytest.mark.parametrize('is_cancelled', [lambda: True, True], ids=['callable', 'bool'])
def test_stream_reports_cancellation_as_retryable(monkeypatch, is_cancelled):
    patch_upload_credentials(monkeypatch)
    clickhouse_client = make_client(rows=[[1], [2]])
    check = make_check()
    # Both runtime shapes: the Agent check object carries a bool ``is_cancelled`` attribute;
    # a callable hook is the other supported shape. Both must fail the run as retryable.
    check.is_cancelled = is_cancelled

    events = collect_events(valid_request(), check, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'cancelled')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert clickhouse_client.stream.closed


def test_entry_propagates_callback_failure_without_upload(monkeypatch, runtime_check):
    patch_upload_credentials(monkeypatch)

    def emit(event_type, metadata_json, payload):
        raise RuntimeError('stop streaming')

    with pytest.raises(RuntimeError, match='stop streaming'):
        runtime_check.run_remote_query(json.dumps(valid_request()), emit)


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
    patch_upload_credentials(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request(maxFileBytes=prefix_len + row_object_bound(BOUND_ROW) + len(rq_pages.PAGE_SUFFIX))
    clickhouse_client = two_row_client()
    fake = FakeUploadClient()
    tracing = RecordingTracing()
    monkeypatch.setattr(rq_tracing, 'open_remote_query_producer_tracing', recording_tracing_factory(tracing))

    events = collect_events(request, make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    # The native spans open at exactly the accumulator's phase boundaries: the root
    # before the run, both setup segments (client creation and stream open through
    # descriptor registration) with the header read's fetch boundary inside, encode around
    # the row loop with one fetch boundary per raw stream read — the second read is the
    # exhaustion read the loop makes after the second row — and the page acknowledgments
    # at the writer's own closes (the first page closes when the overflow row arrives,
    # the final page inside finish), then the finalize span around run finalization,
    # closed by the terminal success and the single close.
    assert tracing.calls == [
        ('factory', None, 'clickhouse'),
        ('open_root', RUN_ID, UPLOAD_ID),
        ('enter', 'database_setup'),
        ('enter', 'database_setup'),
        'fetch',
        ('enter', 'encode_and_page_build'),
        'page_ack',
        'fetch',
        'page_ack',
        'finalize',
        ('succeed', 2),
        'close',
    ]
    # Every raw stream read opened exactly one fetch boundary call.
    assert tracing.calls.count('fetch') == clickhouse_client.stream.read_count


def test_producer_brackets_the_abort_and_fails_the_root_on_a_produce_failure(monkeypatch, caplog):
    """A produce failure brackets the failure tail's upload abort with the abort span and
    closes the root with the same failure code the event carries, never echoing the
    exception's text on any span."""
    patch_upload_credentials(monkeypatch)
    clickhouse_client = FakeClickhouseClient(
        stream_body(('value',), ('UInt8',), [[1], [2], [3]]),
        read_error=urllib3.exceptions.ProtocolError('Connection broken: SECRET_DO_NOT_LOG'),
    )
    fake = FakeUploadClient()
    tracing = RecordingTracing()
    monkeypatch.setattr(rq_tracing, 'open_remote_query_producer_tracing', recording_tracing_factory(tracing))

    caplog.set_level(logging.DEBUG)
    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_failed_event(events, 'timeout', 'interrupted')
    assert event_metadata(events[-1])['error']['retryable'] is True
    assert fake.abort_calls == 1
    assert clickhouse_client.stream.closed
    assert 'SECRET_DO_NOT_LOG' not in str(events)
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
    # The abort span brackets the failure tail's upload abort and closes before the root
    # is marked failed; close runs exactly once, last.
    assert tracing.calls == [
        ('factory', None, 'clickhouse'),
        ('open_root', RUN_ID, UPLOAD_ID),
        ('enter', 'database_setup'),
        ('enter', 'database_setup'),
        'fetch',
        'abort_span:open',
        'abort_span:close',
        ('fail', 'timeout', 0),
        'close',
    ]


def test_producer_fails_the_root_for_an_admission_failure(monkeypatch):
    tracing = RecordingTracing()
    monkeypatch.setattr(rq_tracing, 'open_remote_query_producer_tracing', recording_tracing_factory(tracing))
    request = valid_request()
    request['target'] = {'database_instance': 'Clickhouse/Primary-B'}
    check = make_check(check_database_identifier='Clickhouse/Primary-A')

    events = collect_events(request, check, clickhouse_client=make_client(rows=[[1]]))

    assert_failed_event(events, 'target_not_found')
    # The admission failure still closes the root with the failure code and zero
    # counters; no page, abort, or produce boundary was ever reached.
    assert tracing.calls == [
        ('factory', None, 'clickhouse'),
        ('open_root', RUN_ID, UPLOAD_ID),
        ('fail', 'target_not_found', 0),
        'close',
    ]
