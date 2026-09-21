# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""E2E tests for the native COPY CSV source-page producer against a real Postgres.

The upload client is a fake: these tests pin the producer side (the never-fetched DECLARE
descriptor, the pinned session output settings, the single COPY execution, native COPY CSV
records, bounded split/retry) without needing a live its-agent-intake.
"""

import json

import pytest

from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.postgres.remote_query import iter_agent_rpc_stream_events

from .remote_query_fakes import (
    FakeUploadClient,
    assert_success,
    event_metadata,
    native_record,
    patch_allowlist_disabled,
)

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'


def patch_upload_credentials(monkeypatch):
    # Key-aware: a blanket string return would leak into the check's proxy config lookup
    # during ``integration_check`` and break check initialization.
    def get_config(key):
        if key in ('api_key', 'app_key'):
            return 'TEST_KEY'
        return None

    monkeypatch.setattr(rq_events.datadog_agent, 'get_config', get_config)


def remote_query_request(pg_instance, query, include_schema=False, **limits):
    return {
        'operation': 'produce_json_pages',
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': query,
        'includeSchema': include_schema,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 1,
            'uploadId': UPLOAD_ID,
            'baseUrl': 'https://dd.datad0g.com/api/unstable/its-agent-intake',
            'limits': {
                'maxFileBytes': limits.pop('maxFileBytes', 1024 * 1024),
                'maxResultBytes': limits.pop('maxResultBytes', 16 * 1024 * 1024),
                'maxRowBytes': limits.pop('maxRowBytes', 1024 * 1024),
                'maxColumns': limits.pop('maxColumns', 1024),
                'maxSchemaBytes': limits.pop('maxSchemaBytes', 1024 * 1024),
                'maxPages': limits.pop('maxPages', 128),
                'timeoutMs': limits.pop('timeoutMs', 5000),
            },
        },
    }


def run_producer(request, check):
    client = FakeUploadClient()
    events = list(iter_agent_rpc_stream_events(request, check, client))
    return events, client


def run_producer_with_rejections(request, check):
    client = FakeUploadClient(reject_first_page_too_large=True)
    events = list(iter_agent_rpc_stream_events(request, check, client))
    return events, client


def assert_registered_descriptor(client, include_schema, columns):
    (descriptor_body,) = client.descriptor_bodies
    descriptor = json.loads(descriptor_body)
    assert descriptor['format_version'] == 'postgres-copy-csv-v1'
    assert descriptor['include_schema'] is include_schema
    assert descriptor['columns'] == columns


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_registers_real_descriptor_and_sends_source_pages(integration_check, pg_instance, monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(
        pg_instance,
        'SELECT city, country FROM cities ORDER BY city',
        include_schema=True,
    )

    events, client = run_producer(request, check)

    final = assert_success(events)
    # One registration with the real pg_catalog.format_type output (the varchar typmod is
    # preserved) and the deterministic logical types, before any page is uploaded.
    assert_registered_descriptor(
        client,
        True,
        [
            {
                'column_name': 'city',
                'vendor_data_type': 'character varying(255)',
                'logical_type': 'string',
                'array_element_delimiter': None,
            },
            {
                'column_name': 'country',
                'vendor_data_type': 'character varying(255)',
                'logical_type': 'string',
                'array_element_delimiter': None,
            },
        ],
    )
    # The source page carries the native COPY CSV records verbatim: every field quoted by
    # FORCE_QUOTE *, no JSON token, no envelope.
    pages = client.pages()
    assert list(pages) == [0]
    assert pages[0] == native_record('Beautiful city of lights', 'France') + native_record('New York', 'USA')
    # One complete page uploaded as one direct PUT: exact whole-page identity, rows tracked.
    (page_call,) = client.put_page_calls
    assert page_call.batch_index == 0
    assert page_call.record_offset == 0
    assert page_call.source_bytes == len(pages[0])
    assert page_call.rows == 2
    assert client.run_finalize_calls == 1
    # The compact receipt repeats intake's finalize totals, never local source accounting.
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 1,
        'totalRows': 2,
        'totalBytes': len(pages[0]),
    }
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_native_csv_keeps_value_spellings_distinguishable(integration_check, pg_instance, monkeypatch):
    """NULL, empty string, and a literal \\N stay distinct bytes, and embedded commas,
    quotes, CR/LF, and UTF-8 ride the record raw."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    check = integration_check(pg_instance)
    with check.db_pool.get_connection(pg_instance['dbname']) as conn, conn.cursor() as cur:
        cur.execute('SHOW server_encoding')
        server_encoding = cur.fetchone()[0]
    # The multibyte value is built from chr() so the query text itself stays pure ASCII:
    # SQL_ASCII servers cannot carry a non-ASCII literal over psycopg at all, and the
    # native record carries the value in the server's own encoding bytes either way.
    request = remote_query_request(
        pg_instance,
        "SELECT NULL::text AS null_value, ''::text AS empty_value, '\\N'::text AS literal_marker, "
        "'a,b' AS comma_value, 'He said \"Hi\"' AS quote_value, "
        "concat('line1', chr(10), 'line2') AS newline_value, concat('cr', chr(13), chr(10), 'lf') AS crlf_value, "
        "concat('h', chr(233), 'llo') AS utf8_value",
    )

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    # Unquoted \N is NULL; "" is the empty string; "\N" is the literal text. Commas, doubled
    # quotes, and raw LF/CR bytes inside quoted fields all ride raw; the multibyte value
    # arrives as the server's own encoding bytes.
    # The multibyte value's field bytes are the server's own encoding: two UTF-8 bytes on
    # a UTF8 database, the raw single byte on SQL_ASCII (where a non-ASCII literal cannot
    # even be sent over psycopg, hence the chr()-built query text).
    utf8_field = '"héllo"'.encode('utf-8') if server_encoding == 'UTF8' else b'"h\xe9llo"'
    expected_page = (
        native_record(None, '', '\\N', 'a,b', 'He said "Hi"', 'line1\nline2', 'cr\r\nlf')[:-1]
        + b','
        + utf8_field
        + b'\n'
    )
    assert page == expected_page
    assert page.count(b'\n') == 3  # the two embedded newlines plus the record terminator
    assert [column['column_name'] for column in json.loads(client.descriptor_bodies[0])['columns']] == [
        'null_value',
        'empty_value',
        'literal_marker',
        'comma_value',
        'quote_value',
        'newline_value',
        'crlf_value',
        'utf8_value',
    ]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_native_csv_type_families(integration_check, pg_instance, monkeypatch):
    """The pinned session settings make the native text a pure function of the values:
    UTC timestamptz, ISO dates, postgres intervals, hex bytea, and the server's exact
    numeric spellings (floats in shortest round-trip text)."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(
        pg_instance,
        "SELECT 1 AS int_value, 9223372036854775807 AS bigint_value, "
        "12345678901234567890.123456789::numeric AS numeric_value, 'NaN'::numeric AS nan_value, "
        "'Infinity'::float8 AS infinity_value, 0.1::float8 AS float_value, 0.1::float4 AS real_value, "
        "true AS true_value, false AS false_value, "
        "'2026-08-28'::date AS date_value, '12:34:56.123456'::time AS time_value, "
        "'2026-08-28 12:34:56.123456'::timestamp AS timestamp_value, "
        "'2026-08-28 12:34:56.123456+02'::timestamptz AS timestamptz_value, "
        "'12:34:56.123456+02'::timetz AS timetz_value, "
        "'1 year 2 mons 3 days 04:05:06'::interval AS interval_value, "
        "decode('00ff80', 'hex') AS bytea_value, "
        "'{\"nested\": [1, null, true], \"price\": 1.10}'::json AS json_value, "
        "'{\"price\": 1.10}'::jsonb AS jsonb_value, "
        "'8b6fb1b5-94dd-447b-95a4-91f4ef118f4b'::uuid AS uuid_value, '192.168.1.0/24'::cidr AS cidr_value, "
        "ARRAY[1, 2, NULL] AS int_array, ARRAY['a,b', 'He said \"Hi\"'] AS text_array, "
        "ARRAY[true, false] AS bool_array, ARRAY['2026-08-28'::date, '2026-08-29'::date] AS date_array, "
        "ARRAY['(1,2),(3,4)'::box, '(5,6),(7,8)'::box] AS box_array",
    )

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    assert page == native_record(
        '1',  # int
        '9223372036854775807',  # bigint
        '12345678901234567890.123456789',  # numeric keeps the exact database text
        'NaN',  # non-finite numeric is the documented text, not a JSON number
        'Infinity',  # non-finite float8
        '0.1',  # float8 shortest round-trip text
        '0.1',  # float4 shortest round-trip text
        't',  # boolean
        'f',
        '2026-08-28',  # date, ISO
        '12:34:56.123456',  # time
        '2026-08-28 12:34:56.123456',  # timestamp, ISO
        '2026-08-28 10:34:56.123456+00',  # timestamptz: the +02 input renders in pinned UTC
        '12:34:56.123456+02',  # timetz keeps its zone
        '1 year 2 mons 3 days 04:05:06',  # interval, postgres style
        '\\x00ff80',  # bytea, hex
        '{"nested": [1, null, true], "price": 1.10}',  # json keeps its stored text
        '{"price": 1.10}',  # jsonb is the server's normalized text
        '8b6fb1b5-94dd-447b-95a4-91f4ef118f4b',  # uuid
        '192.168.1.0/24',  # cidr keeps its exact server text
        '{1,2,NULL}',  # arrays are the native text, one field
        '{"a,b","He said \\"Hi\\""}',  # array elements escape quotes with backslashes
        '{t,f}',
        '{2026-08-28,2026-08-29}',
        '{(3,4),(1,2);(7,8),(5,6)}',  # box[]: semicolon-delimited elements, commas ride as data
    )
    descriptor = json.loads(client.descriptor_bodies[0])
    assert [
        (column['column_name'], column['logical_type'], column['array_element_delimiter'])
        for column in descriptor['columns']
    ] == [
        ('int_value', 'integer', None),
        ('bigint_value', 'integer', None),
        ('numeric_value', 'decimal', None),
        ('nan_value', 'decimal', None),
        ('infinity_value', 'float', None),
        ('float_value', 'float', None),
        ('real_value', 'float', None),
        ('true_value', 'boolean', None),
        ('false_value', 'boolean', None),
        ('date_value', 'temporal', None),
        ('time_value', 'temporal', None),
        ('timestamp_value', 'temporal', None),
        ('timestamptz_value', 'temporal', None),
        ('timetz_value', 'temporal', None),
        ('interval_value', 'temporal', None),
        ('bytea_value', 'binary', None),
        ('json_value', 'json', None),
        ('jsonb_value', 'json', None),
        ('uuid_value', 'string', None),
        ('cidr_value', 'vendor', None),
        # Every array column declares its element type's own catalog delimiter: the common
        # comma, and box's own semicolon.
        ('int_array', 'json', ','),
        ('text_array', 'json', ','),
        ('bool_array', 'json', ','),
        ('date_array', 'json', ','),
        ('box_array', 'json', ';'),
    ]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_pins_the_session_time_zone_for_native_text(integration_check, pg_instance, monkeypatch):
    """The producer's UTC pin overrides the pooled session's ambient time zone inside its
    read-only transaction, and the closing ROLLBACK restores the session state."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    check = integration_check(pg_instance)
    dbname = pg_instance['dbname']
    with check.db_pool.get_connection(dbname) as conn, conn.cursor() as cur:
        cur.execute("SET TimeZone = 'America/New_York'")
        cur.execute('SHOW TimeZone')
        assert cur.fetchone()[0] == 'America/New_York'
    try:
        request = remote_query_request(pg_instance, "SELECT '2026-08-28 12:34:56.123456+00'::timestamptz AS ts")
        events, client = run_producer(request, check)

        assert_success(events)
        (page,) = client.pages().values()
        # Native UTC text with a +00 offset: without the pin the same instant would render
        # in the session's zone (2026-08-28 08:34:56.123456-04 under America/New_York).
        assert page == native_record('2026-08-28 12:34:56.123456+00')
    finally:
        with check.db_pool.get_connection(dbname) as conn, conn.cursor() as cur:
            cur.execute('RESET TimeZone')


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_evaluates_the_query_values_exactly_once(integration_check, pg_instance, monkeypatch):
    """The never-fetched DECLARE plans the query without evaluating it; the single COPY
    evaluates it exactly once, proven by the run's own walls: the rows sleep a fixed total
    in the database, so exactly one evaluation fits the measured fetch and run walls while
    a second evaluation (a cursor fetch or a double COPY) would exceed them."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(
        pg_instance,
        'SELECT pg_sleep(0.4), i FROM generate_series(1, 3) AS i',
        timeoutMs=8000,
    )

    events, client = run_producer(request, check)

    final = assert_success(events)
    (page,) = client.pages().values()
    # pg_sleep returns void: an empty quoted field next to each row's value.
    assert page == b'"","1"\n' + b'"","2"\n' + b'"","3"\n'
    assert final['upload_receipt']['totalRows'] == 3
    producer = final['executionDiagnostics']['producer']
    # The three rows sleep a fixed 1.2 s in the database, and exactly one evaluation
    # produced them: the database walls carry the sleep exactly once — some server
    # versions deliver it in the COPY dispatch (setup) and others in the reads (fetch), so
    # the bound covers both — while a second evaluation (a cursor fetch or a double COPY)
    # would carry it twice, and the whole run stays below a second evaluation's wall.
    database_ms = producer['databaseSetupMs'] + producer['databaseFetchMs']
    assert 1200 <= database_ms < 2400, producer
    assert producer['totalMs'] < 4000, producer


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_final_page_too_large_splits_and_retries_without_requery(
    integration_check, pg_instance, monkeypatch
):
    """Intake's defensive final_page_too_large rejection splits the buffered records in
    half and retries the same page index byte-identically — every row is still declared
    exactly once across the page PUTs, in order, from the one buffered COPY result."""
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    check = integration_check(pg_instance)
    # A budget that fits exactly three records per page (their bounds plus the two
    # in-page separators).
    names = ['i']
    record = native_record('1')
    key_bound = sum(len(json.dumps(name, ensure_ascii=False).encode('utf-8')) for name in names)
    controls = len(record) - len(record.translate(None, bytes(range(0x20))))
    record_bound = (
        1
        + key_bound
        + 2 * len(names)
        + (
            len(record)
            + record.count(b'\\')
            + 5 * controls
            + len(rq_pages.REMOTE_QUERY_REDACTED_MARKER_TOKEN) * len(names)
        )
    )
    envelope = len(
        rq_pages.page_prefix(
            run_id=RUN_ID,
            task_id=TASK_ID,
            record_offset=0,
            agent_hostname=check.hostname,
            schema_json=None,
        )
    )
    request = remote_query_request(
        pg_instance,
        'SELECT i FROM generate_series(1, 8) AS i',
        maxFileBytes=envelope + len(rq_pages.PAGE_SUFFIX) + 3 * record_bound + 2,
        maxRowBytes=64,
        maxSchemaBytes=1,
    )
    events, client = run_producer_with_rejections(request, check)

    final = assert_success(events)
    # Page 0 was attempted with its three buffered records, rejected as too large, and
    # retried at the same index with the halved prefix — a pure re-send of buffered bytes.
    assert client.put_attempts.count(0) == 2
    assert client.put_attempts[0] == 0 and client.put_attempts[1] == 0
    # Every row rides exactly one page, in order, exactly once across the split.
    pages = client.pages()
    joined = b''.join(pages[index] for index in sorted(pages))
    assert joined == b''.join(native_record(str(value)) for value in range(1, 9))
    assert final['upload_receipt']['totalRows'] == 8


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_bytea_and_select_one_pages(integration_check, pg_instance, monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(pg_instance, "SELECT decode('00ff80', 'hex') AS payload", include_schema=True)

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    # bytea rides as its native hex text; intake converts it to the final JSON binary
    # representation from the descriptor's binary logical type.
    assert page == native_record('\\x00ff80')
    assert_registered_descriptor(
        client,
        True,
        [
            {
                'column_name': 'payload',
                'vendor_data_type': 'bytea',
                'logical_type': 'binary',
                'array_element_delimiter': None,
            }
        ],
    )


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_select_one_and_zero_row_schema_page(integration_check, pg_instance, monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(pg_instance, 'SELECT 1 AS value', include_schema=True)

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    assert page == native_record('1')
    assert_registered_descriptor(
        client,
        True,
        [
            {
                'column_name': 'value',
                'vendor_data_type': 'integer',
                'logical_type': 'integer',
                'array_element_delimiter': None,
            }
        ],
    )

    # The zero-row query is not allowlisted; the E2E producer path is under test here.
    patch_allowlist_disabled(monkeypatch)
    zero_row_request = remote_query_request(pg_instance, 'SELECT 1 AS value WHERE 1 = 0', include_schema=True)
    zero_events, zero_client = run_producer(zero_row_request, check)

    zero_final = assert_success(zero_events)
    # Zero-row query with schema requested: one zero-record source page, so intake creates
    # the schema-bearing final page with empty data.
    (zero_page,) = zero_client.pages().values()
    assert zero_page == b''
    (zero_call,) = zero_client.put_page_calls
    assert (zero_call.batch_index, zero_call.rows, zero_call.source_bytes) == (0, 0, 0)
    assert zero_final['upload_receipt']['pageCount'] == 1
    assert zero_final['upload_receipt']['totalRows'] == 0
    assert 'password' not in json.dumps(zero_row_request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_splits_pages_and_reuses_pool_after_failure(integration_check, pg_instance, monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = integration_check(pg_instance)
    # Tiny maxRowBytes trips row_too_large for the 1 MiB proof query: the native source
    # record is far larger than the record budget.
    oversized_request = remote_query_request(
        pg_instance,
        "SELECT repeat('x', 1048576) AS payload",
        maxRowBytes=1024,
    )

    events, client = run_producer(oversized_request, check)

    assert events[-1].event_type == 'error'
    assert event_metadata(events[-1])['error']['code'] == 'row_too_large'
    assert client.put_page_calls == []
    assert client.abort_calls == 1

    # The pool connection remains reusable after the failed read-only transaction.
    ok_request = remote_query_request(pg_instance, 'SELECT 1 AS value')
    ok_events, ok_client = run_producer(ok_request, check)
    ok_final = assert_success(ok_events)
    (ok_page,) = ok_client.pages().values()
    assert ok_page == native_record('1')
    assert ok_final['upload_receipt']['totalRows'] == 1
