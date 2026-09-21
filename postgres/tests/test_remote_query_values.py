# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import json

import pytest

from datadog_checks.postgres import remote_query

from .remote_query_fakes import (
    FakeColumn,
    FakePool,
    FakeUploadClient,
    assembled_pages,
    assert_failed_event,
    assert_success,
    bounded_request,
    collect_events,
    make_check,
    native_record,
    patch_allowlist_disabled,
    patch_upload_credentials,
    valid_request,
)


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
