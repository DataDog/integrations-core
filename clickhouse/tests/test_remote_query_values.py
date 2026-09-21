# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json

import pytest

from datadog_checks.clickhouse import remote_query

from .remote_query_fakes import (
    FakeClickhouseClient,
    FakeUploadClient,
    assembled_pages,
    assert_failed_event,
    assert_success,
    bounded_request,
    collect_events,
    compact_json_line,
    csv_record,
    make_check,
    make_client,
    patch_allowlist_disabled,
    patch_upload_credentials,
    raw_stream_body,
    valid_request,
)


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


@pytest.mark.parametrize(
    'type_string, wire, expected',
    [
        ('UInt64', b'[18446744073709551615]', b'18446744073709551615'),
        ('Int64', b'[-42]', b'-42'),
        ('UInt64', b'["18446744073709551615"]', b'18446744073709551615'),
        ('Int64', b'["-42"]', b'-42'),
        ('UInt64', b'["not-a-number"]', b'"not-a-number"'),
        ('UInt64', b'["007"]', b'"007"'),
        ('Float64', b'[0.000000001]', b'0.000000001'),
        ('Float64', b'[1e-7]', b'1e-7'),
        ('Float64', b'[1E+2]', b'1E+2'),
        ('Int64', b'[-0]', b'-0'),
        ('Float64', b'["0.1"]', b'0.1'),
        ('Decimal(9, 9)', b'["0.000000001"]', b'0.000000001'),
        ('Decimal(38, 10)', b'["12345678901234567890.1234567890"]', b'12345678901234567890.1234567890'),
        ('Nullable(Float64)', b'[null]', b'null'),
        ('Float64', b'[null]', b'null'),
        ('Float64', b'["inf"]', b'"inf"'),
        ('Float64', b'["-nan"]', b'"-nan"'),
        ('String', b'["12345"]', b'"12345"'),
        ('Bool', b'[true]', b'true'),
        ('Bool', b'[0]', b'false'),
        ('Bool', b'[1]', b'true'),
        ('Bool', b'["false"]', b'false'),
        ('Bool', b'["0"]', b'false'),
        ('Bool', b'["1"]', b'true'),
        ('String', b'["he said \\"hi\\"\\nend"]', b'"he said \\"hi\\"\\nend"'),
        ('Nullable(String)', b'[null]', b'null'),
        ('Date', b'["2026-08-28"]', b'"2026-08-28"'),
        ('UUID', b'["8b6fb1b5-94dd-447b-95a4-91f4ef118f4b"]', b'"8b6fb1b5-94dd-447b-95a4-91f4ef118f4b"'),
        ('Array(String)', b'[["x",null,"y"]]', b'["x",null,"y"]'),
        ('Map(String, UInt64)', b'[{"k":1}]', b'{"k":1}'),
        ('Tuple(UInt8, String)', b'[null]', b'null'),
        ('Tuple(UInt8, String)', b'[[1,"x"]]', b'[1,"x"]'),
        ('JSON', b'[{"nested":[1,true]}]', b'{"nested":[1,true]}'),
        ('Array(Array(Nullable(UInt8)))', b'[[[1,null],[]]]', b'[[1,null],[]]'),
        ('Float64', b'[NaN]', b'"NaN"'),
        ('Float64', b'[Infinity]', b'"Infinity"'),
        ('Float64', b'[-Infinity]', b'"-Infinity"'),
    ],
)
def test_value_contract_encodes_server_rows(type_string, wire, expected):
    values = remote_query._parse_json_line(wire)
    columns = remote_query.build_columns(['v'], [type_string])
    assert remote_query.encode_row(values, columns)[0].token == expected


@pytest.mark.parametrize(
    'type_string, value, expected_bound',
    [
        # Booleans and null are never scanned: their exact token bounds stay exact.
        ('Bool', True, 4),
        ('Bool', False, 5),
        ('Nullable(String)', None, 4),
        # Short integer, float, and decimal tokens reserve the twelve-byte marker intake
        # substitutes for a matched number leaf, quoted big-int spellings included.
        ('UInt8', 1, 12),
        ('Int64', -42, 12),
        ('Float64', 0.1, 12),
        ('Float64', '0.1', 12),
        ('Decimal(38, 10)', 1.10, 12),
        # A number longer than the marker keeps its own token bytes.
        ('UInt64', '18446744073709551615', 20),
        # A short string leaf bounds to the twelve-byte redaction marker; a longer one keeps
        # its own token length.
        ('String', 'x', 12),
        # Nested numbers contribute marker bounds inside arrays, maps, and JSON values,
        # while nested booleans and null keep their exact tokens.
        ('Array(UInt8)', [1, None], 2 + 12 + 1 + 4),
        ('Map(String, UInt64)', {'k': 1}, 2 + 12 + 1 + 12),
        ('JSON', {'nested': [1, True]}, 2 + 12 + 1 + 2 + 12 + 1 + 4),
    ],
)
def test_cell_final_bounds_account_for_the_redaction_marker(type_string, value, expected_bound):
    values = remote_query._parse_json_line(compact_json_line([value]))
    (cell,) = remote_query.encode_row(values, remote_query.build_columns(['v'], [type_string]))
    assert cell.final_bound == expected_bound


def test_value_contract_producer_emits_pinned_source_page_csv(monkeypatch):
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
    # Every cell rides the page as its exact canonical JSON token, CSV-framed: the tokens
    # pin exact numeric lexemes, typed normalization, temporal strings, nested JSON,
    # arrays, and maps.
    tokens = [
        b'null',
        b'true',
        b'42',
        b'18446744073709551615',
        b'0.1',
        b'12345678901234567890.1234567890',
        '"héllo \\"quoted\\""'.encode('utf-8'),
        b'"2026-08-28"',
        b'{"nested":[1,null,true],"price":1.1}',
        b'["x",null,["y","z"]]',
        b'{"a":1}',
    ]
    assert page == csv_record(tokens)
    descriptor = json.loads(fake.descriptor_bodies[0])
    assert [
        (column['column_name'], column['vendor_data_type'], column['logical_type']) for column in descriptor['columns']
    ] == [
        ('null_value', 'Nullable(String)', 'string'),
        ('bool_value', 'Bool', 'boolean'),
        ('int_value', 'Int64', 'integer'),
        ('big_int_value', 'UInt64', 'integer'),
        ('float_value', 'Float64', 'float'),
        ('decimal_value', 'Decimal(38, 10)', 'decimal'),
        ('text_value', 'String', 'string'),
        ('date_value', 'Date', 'temporal'),
        ('json_value', 'JSON', 'json'),
        ('array_value', 'Array(Nullable(String))', 'json'),
        ('map_value', 'Map(String, UInt64)', 'json'),
    ]


def test_value_contract_preserves_exact_server_numeric_lexemes(monkeypatch):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    # One row on the real compact wire whose numeric lexemes no int()/Decimal/repr
    # round-trip could reproduce: a sub-1e-6 decimal, exponent spellings (case and sign),
    # negative zero, and numbers nested inside a composite. The parse hooks carry every
    # lexeme through byte-exact, and the quoted-spelling normalization removes only the
    # quotes after the family's grammar check.
    row_line = b'[0.000000001,"0.000000001",1e-7,-0,[0.000000001,1E+2]]'
    clickhouse_client = FakeClickhouseClient(
        raw_stream_body(
            compact_json_line(('tiny', 'quoted_tiny', 'exponent', 'negative_zero', 'nested')),
            compact_json_line(('Float64', 'Decimal(9, 9)', 'Float64', 'Int64', 'Array(Float64)')),
            row_line,
        )
    )
    fake = FakeUploadClient()

    events = collect_events(valid_request(), make_check(), upload_client=fake, clickhouse_client=clickhouse_client)

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    assert page == csv_record(
        [
            b'0.000000001',
            b'0.000000001',
            b'1e-7',
            b'-0',
            b'[0.000000001,1E+2]',
        ]
    )


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


@pytest.mark.parametrize(
    'type_string, expected',
    [
        ('UInt64', 'integer'),
        ('Int128', 'integer'),
        ('Nullable(UInt64)', 'integer'),
        ('LowCardinality(Nullable(Int128))', 'integer'),
        ('SimpleAggregateFunction(sum, UInt64)', 'integer'),
        ('Decimal(10, 2)', 'decimal'),
        ('Decimal128(4)', 'decimal'),
        ('Nullable(Decimal(38, 10))', 'decimal'),
        ('Float64', 'float'),
        ('Nullable(Float32)', 'float'),
        ('Bool', 'boolean'),
        ('String', 'string'),
        ('FixedString(16)', 'string'),
        ('Date', 'temporal'),
        ('Date32', 'temporal'),
        ('DateTime64(3)', 'temporal'),
        ('UUID', 'string'),
        ("Enum8('a' = 1)", 'string'),
        ('IPv4', 'vendor'),
        ('IPv6', 'vendor'),
        ('JSON', 'json'),
        ('Array(UInt64)', 'json'),
        ('Map(String, UInt64)', 'json'),
        ('Tuple(UInt8, String)', 'json'),
        ('Nested(x UInt8)', 'json'),
        ('AggregateFunction(any, UInt8)', 'vendor'),
        ('Point', 'vendor'),
    ],
)
def test_logical_type_mapping_is_deterministic(type_string, expected):
    assert remote_query.logical_type_for_type_string(type_string) == expected
