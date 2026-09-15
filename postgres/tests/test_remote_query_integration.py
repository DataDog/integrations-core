# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""E2E tests for the remote query source-page producer against a real Postgres.

The upload client is a fake: these tests pin the producer side (server-side cursor, value
normalization, descriptor with the real pg_catalog.format_type output and logical types,
CSV source-page records) without needing a live its-agent-intake.
"""

import hashlib
import json
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils import remote_queries as rq
from datadog_checks.postgres.remote_query import StaticPostgresCheckRegistry, iter_agent_rpc_stream_events

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k'


class FakeUploadClient:
    def __init__(self):
        self.descriptor_bodies = []
        self.put_page_calls = []
        self.run_finalize_calls = 0
        self.abort_calls = 0

    def register_descriptor(self, creds, body):
        self.descriptor_bodies.append(body)
        return {'upload_id': creds.upload_id, 'descriptor_sha256': hashlib.sha256(body).hexdigest()}

    def put_source_page(self, creds, page, body):
        payload = body.read()
        self.put_page_calls.append(
            SimpleNamespace(
                batch_index=page.batch_index,
                record_offset=page.record_offset,
                source_bytes=page.source_bytes,
                rows=page.rows,
                sha256_hex=page.sha256_hex,
                payload=payload,
            )
        )
        return {
            'batch_index': page.batch_index,
            'key': 'agent-intake-test/pages/{}.json'.format(page.batch_index),
            'record_offset': page.record_offset,
            'bytes': page.source_bytes,
            'rows': page.rows,
            'sha256': page.sha256_hex,
        }

    def finalize_run(self, creds):
        self.run_finalize_calls += 1
        return {
            'upload_id': creds.upload_id,
            'page_count': len(self.put_page_calls),
            'total_rows': sum(call.rows for call in self.put_page_calls),
            'total_bytes': sum(call.source_bytes for call in self.put_page_calls),
        }

    def abort(self, creds):
        self.abort_calls += 1

    def pages(self):
        return {call.batch_index: call.payload for call in self.put_page_calls}


def patch_upload_credentials(monkeypatch):
    # Key-aware: a blanket string return would leak into the check's proxy config lookup
    # during ``integration_check`` and break check initialization.
    def get_config(key):
        if key in ('api_key', 'app_key'):
            return 'TEST_KEY'
        return None

    monkeypatch.setattr(rq.datadog_agent, 'get_config', get_config)


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


def csv_record(tokens):
    """The expected framed CSV record for one row of canonical tokens, pinned independently."""
    fields = []
    for token in tokens:
        fields.append(
            '"' + token.replace('"', '""') + '"' if ('"' in token or ',' in token or '\n' in token) else token
        )
    return (','.join(fields) + '\n').encode('utf-8')


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
    (descriptor_body,) = client.descriptor_bodies
    descriptor = json.loads(descriptor_body)
    assert descriptor['format_version'] == 'csv-json-cell-v1'
    assert descriptor['include_schema'] is True
    assert descriptor['columns'] == [
        {'column_name': 'city', 'vendor_data_type': 'character varying(255)', 'logical_type': 'string'},
        {'column_name': 'country', 'vendor_data_type': 'character varying(255)', 'logical_type': 'string'},
    ]
    # The source page carries one CSV record per row: canonical JSON tokens, no envelope.
    pages = client.pages()
    assert list(pages) == [0]
    assert pages[0] == csv_record([json.dumps('Beautiful city of lights'), json.dumps('France')]) + csv_record(
        [json.dumps('New York'), json.dumps('USA')]
    )
    # One complete page uploaded as one direct PUT: exact whole-page identity, rows tracked.
    (page_call,) = client.put_page_calls
    assert page_call.batch_index == 0
    assert page_call.record_offset == 0
    assert page_call.source_bytes == len(pages[0])
    assert page_call.rows == 2
    assert page_call.sha256_hex == hashlib.sha256(pages[0]).hexdigest()
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
def test_remote_query_normalizes_real_postgres_values(integration_check, pg_instance, monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(
        pg_instance,
        "SELECT decode('00ff80', 'hex') AS payload",
        include_schema=True,
    )

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    # bytea -> base64 string token (the exact 3-byte payload, no padding), and the
    # descriptor identifies bytea as binary.
    assert page == csv_record([json.dumps('AP+A')])
    assert json.loads(client.descriptor_bodies[0])['columns'] == [
        {'column_name': 'payload', 'vendor_data_type': 'bytea', 'logical_type': 'binary'}
    ]


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_remote_query_select_one_and_zero_row_schema_page(integration_check, pg_instance, monkeypatch):
    patch_upload_credentials(monkeypatch)
    check = integration_check(pg_instance)
    request = remote_query_request(pg_instance, 'SELECT 1 AS value', include_schema=True)

    events, client = run_producer(request, check)

    assert_success(events)
    (page,) = client.pages().values()
    assert page == csv_record(['1'])
    assert json.loads(client.descriptor_bodies[0])['columns'] == [
        {'column_name': 'value', 'vendor_data_type': 'integer', 'logical_type': 'integer'}
    ]

    # The zero-row query is not allowlisted; the E2E producer path is under test here.
    monkeypatch.setattr(rq, 'is_query_allowlist_enabled', lambda: False)
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
    # Tiny maxRowBytes trips row_too_large for the 1 MiB proof query: the framed source
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
    assert ok_page == csv_record(['1'])
    assert ok_final['upload_receipt']['totalRows'] == 1
