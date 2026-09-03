# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""E2E tests for the remote query JSON page producer against a real Postgres.

The upload client is a fake: these tests pin the producer side (server-side cursor,
value normalization, schema via the real pg_catalog.format_type, page envelope) without
needing a live its-agent-intake.
"""

import json

import pytest

from datadog_checks.postgres import remote_query
from datadog_checks.postgres.remote_query import StaticPostgresCheckRegistry, iter_agent_rpc_stream_events

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'


class FakeUploadClient:
    def __init__(self):
        self.put_part_calls = []
        self.page_finalize_calls = []
        self.run_finalize_calls = 0
        self.abort_calls = 0

    def put_part(self, creds, batch_index, part_number, payload, sha256_hex, rows):
        self.put_part_calls.append((batch_index, part_number, payload, sha256_hex, rows))

    def finalize_page(self, creds, batch_index):
        self.page_finalize_calls.append(batch_index)

    def finalize_run(self, creds):
        self.run_finalize_calls += 1
        return {'upload_id': UPLOAD_ID}

    def abort(self, creds):
        self.abort_calls += 1

    def pages(self):
        parts = {}
        for batch_index, _part_number, payload, _sha256_hex, _rows in self.put_part_calls:
            parts.setdefault(batch_index, []).append(payload)
        return {batch_index: b''.join(payloads) for batch_index, payloads in parts.items()}


def remote_query_request(pg_instance, query, include_schema=False, part_bytes=1024, **limits):
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
            'token': 'scoped-upload-token',
            'partBytes': part_bytes,
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


def event_metadata(event):
    return event.metadata


def run_producer(request, check):
    client = FakeUploadClient()
    events = list(iter_agent_rpc_stream_events(request, StaticPostgresCheckRegistry([check]), client))
    return events, client


def assert_success(events):
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    return event_metadata(events[-1])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_produces_json_page_with_real_schema(integration_check, pg_instance, monkeypatch):
    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', lambda key: 'TEST_KEY')
    check = integration_check(pg_instance)
    request = remote_query_request(
        pg_instance,
        'SELECT city, country FROM cities ORDER BY city',
        include_schema=True,
        part_bytes=32,
    )

    events, client = run_producer(request, check)

    final = assert_success(events)
    pages = client.pages()
    assert list(pages) == [0]
    page = json.loads(pages[0])
    assert page['version'] == 1
    assert page['run_id'] == RUN_ID
    assert page['task_id'] == TASK_ID
    assert page['batch_index'] == 0
    assert page['record_offset'] == 0
    # Real pg_catalog.format_type output, with the varchar typmod preserved.
    assert page['schema'] == [
        {'column_name': 'city', 'vendor_data_type': 'character varying(255)'},
        {'column_name': 'country', 'vendor_data_type': 'character varying(255)'},
    ]
    assert page['data']['items'] == [
        {'city': 'Beautiful city of lights', 'country': 'France'},
        {'city': 'New York', 'country': 'USA'},
    ]
    # Page bytes streamed in bounded parts, part 1-based and contiguous, rows tracked.
    assert [call[1] for call in client.put_part_calls] == list(range(1, len(client.put_part_calls) + 1))
    assert sum(call[4] for call in client.put_part_calls) == 2
    assert client.page_finalize_calls == [0]
    assert client.run_finalize_calls == 1
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 1,
        'totalRows': 2,
        'totalBytes': len(pages[0]),
    }
    assert 'password' not in json.dumps(request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_normalizes_real_postgres_values(integration_check, pg_instance, monkeypatch):
    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', lambda key: 'TEST_KEY')
    check = integration_check(pg_instance)
    request = remote_query_request(
        pg_instance,
        "SELECT decode('00ff80', 'hex') AS payload",
        include_schema=True,
    )

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    parsed = json.loads(page)
    # bytea -> base64 string, and the schema identifies bytea.
    assert parsed['data']['items'] == [{'payload': 'AP+AA=='}]
    assert parsed['schema'] == [{'column_name': 'payload', 'vendor_data_type': 'bytea'}]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_select_one_and_zero_row_schema_page(integration_check, pg_instance, monkeypatch):
    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', lambda key: 'TEST_KEY')
    check = integration_check(pg_instance)
    request = remote_query_request(pg_instance, 'SELECT 1 AS value', include_schema=True)

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    parsed = json.loads(page)
    assert parsed['schema'] == [{'column_name': 'value', 'vendor_data_type': 'integer'}]
    assert parsed['data']['items'] == [{'value': 1}]

    # The zero-row query is not allowlisted; the E2E producer path is under test here.
    monkeypatch.setattr(remote_query, '_is_query_allowlist_enabled', lambda: False)
    zero_row_request = remote_query_request(pg_instance, 'SELECT 1 AS value WHERE 1 = 0', include_schema=True)
    zero_events, zero_client = run_producer(zero_row_request, check)

    zero_final = assert_success(zero_events)
    (zero_page,) = zero_client.pages().values()
    zero_parsed = json.loads(zero_page)
    # Zero-row query with schema requested: one schema-bearing empty page.
    assert zero_parsed['data']['items'] == []
    assert zero_parsed['schema'] == [{'column_name': 'value', 'vendor_data_type': 'integer'}]
    assert zero_final['upload_receipt']['pageCount'] == 1
    assert zero_final['upload_receipt']['totalRows'] == 0
    assert 'password' not in json.dumps(zero_row_request).lower()


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_splits_pages_and_reuses_pool_after_failure(integration_check, pg_instance, monkeypatch):
    monkeypatch.setattr(remote_query.datadog_agent, 'get_config', lambda key: 'TEST_KEY')
    check = integration_check(pg_instance)
    # Tiny maxRowBytes trips row_too_large for the 1 MiB proof query.
    oversized_request = remote_query_request(
        pg_instance,
        "SELECT repeat('x', 1048576) AS payload",
        maxRowBytes=1024,
    )

    events, client = run_producer(oversized_request, check)

    assert events[-1].event_type == 'error'
    assert event_metadata(events[-1])['error']['code'] == 'row_too_large'
    assert client.put_part_calls == []
    assert client.abort_calls == 1

    # The pool connection remains reusable after the failed read-only transaction.
    ok_request = remote_query_request(pg_instance, 'SELECT 1 AS value')
    ok_events, ok_client = run_producer(ok_request, check)
    ok_final = assert_success(ok_events)
    (ok_page,) = ok_client.pages().values()
    assert json.loads(ok_page)['data']['items'] == [{'value': 1}]
    assert ok_final['upload_receipt']['totalRows'] == 1
