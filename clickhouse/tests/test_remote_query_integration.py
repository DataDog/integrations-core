# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import csv
import json

import pytest

from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.clickhouse import remote_query
from datadog_checks.clickhouse.remote_query import iter_agent_rpc_stream_events

from .remote_query_fakes import (
    BASE_URL,
    RUN_ID,
    TASK_ID,
    UPLOAD_ID,
    FakeUploadClient,
    assembled_pages,
    assert_success,
    csv_record,
    valid_limits,
)

UNSUPPORTED_REMOTE_QUERY_VERSIONS = {'18', '19', '20', '21.8'}


def _is_remote_query_supported():
    from .common import CLICKHOUSE_VERSION

    if CLICKHOUSE_VERSION == 'latest':
        return True
    return CLICKHOUSE_VERSION not in UNSUPPORTED_REMOTE_QUERY_VERSIONS


pytestmark_integration = pytest.mark.skipif(
    not _is_remote_query_supported(),
    reason='Remote queries need the JSONCompactEachRowWithNamesAndTypes format (ClickHouse 22.7+)',
)


def real_server_request(instance, query, include_schema=False):
    """A request whose limits admit single-row multi-MiB proof payloads.

    ``maxRowBytes``/``maxFileBytes`` are sized for one 32 MiB payload row plus its envelope,
    and the timeout allows the largest payload to stream through.
    """
    limits = valid_limits(maxRowBytes=40 * 1024 * 1024, maxFileBytes=64 * 1024 * 1024, timeoutMs=30_000)
    request = {
        'operation': 'produce_json_pages',
        'target': {'host': instance['server'], 'port': int(instance['port']), 'dbname': 'default'},
        'query': query,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 1,
            'uploadId': UPLOAD_ID,
            'baseUrl': BASE_URL,
            'limits': limits,
        },
    }
    if include_schema:
        request['includeSchema'] = True
    return request


def patch_real_check(monkeypatch, instance):
    """Configure Agent credentials and build a real check for the running fixture."""
    from datadog_checks.clickhouse import ClickhouseCheck

    def get_config(key):
        if key == 'api_key':
            return 'TEST_API_KEY'
        if key == 'app_key':
            return 'TEST_APP_KEY'
        return None

    monkeypatch.setattr(rq_events.datadog_agent, 'get_config', get_config)
    return ClickhouseCheck('clickhouse', {}, [instance])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
def test_remote_query_registers_descriptor_and_sends_source_pages_against_real_clickhouse(instance, monkeypatch):
    """End-to-end producer path against a real server: descriptor, CSV source page, receipt."""
    check = patch_real_check(monkeypatch, instance)

    request = {
        'operation': 'produce_json_pages',
        'target': {'host': instance['server'], 'port': int(instance['port']), 'dbname': 'default'},
        'query': 'SELECT 1 AS value',
        'includeSchema': True,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 1,
            'uploadId': UPLOAD_ID,
            'baseUrl': BASE_URL,
            'limits': valid_limits(),
        },
    }
    fake = FakeUploadClient()

    # No client factory is injected: the real check creates the per-run client itself.
    events = list(iter_agent_rpc_stream_events(request, check, fake, None))

    final = assert_success(events)
    pages = assembled_pages(fake)
    assert list(pages) == [0]
    assert pages[0] == b'1\n'
    # One registration with the stream header's real type string and logical type, before
    # any page is uploaded.
    (descriptor_body,) = fake.descriptor_bodies
    assert json.loads(descriptor_body)['columns'] == [
        {
            'column_name': 'value',
            'vendor_data_type': 'UInt8',
            'logical_type': 'integer',
            'array_element_delimiter': None,
        }
    ]
    # One complete page uploaded as one direct PUT: exact whole-page identity, rows exact.
    (page_call,) = fake.put_page_calls
    assert page_call.batch_index == 0
    assert page_call.record_offset == 0
    assert page_call.source_bytes == len(pages[0])
    assert page_call.rows == 1
    assert fake.run_finalize_calls == 1
    assert final['upload_receipt'] == {
        'uploadId': UPLOAD_ID,
        'pageCount': 1,
        'totalRows': 1,
        'totalBytes': len(pages[0]),
    }


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
def test_remote_query_binary_proof_query_preserves_nul_payload_against_real_clickhouse(instance, monkeypatch):
    """The binary proof query's NUL payload survives the real server's JSON stream exactly."""
    check = patch_real_check(monkeypatch, instance)
    fake = FakeUploadClient()

    request = real_server_request(instance, remote_query.REMOTE_QUERY_BINARY_QUERY)
    events = list(iter_agent_rpc_stream_events(request, check, fake, None))

    assert_success(events)
    (page,) = assembled_pages(fake).values()
    # The payload is the exact three bytes NUL, 'a', 'b': the source page carries the
    # cell's canonical token with the NUL escaped exactly as the server rendered it.
    assert page == csv_record([b'"\\u0000ab"'])


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
@pytestmark_integration
@pytest.mark.parametrize(
    'query, expected_payload_bytes, include_schema',
    [
        (remote_query.REMOTE_QUERY_SEED_QUERY, None, False),
        (remote_query.REMOTE_QUERY_IDENTITY_QUERY, None, True),
        (remote_query.REMOTE_QUERY_BINARY_QUERY, None, False),
    ]
    + [
        (remote_query._proof_payload_query(size_bytes), size_bytes, False)
        for size_bytes in remote_query.REMOTE_QUERY_PROOF_PAYLOAD_SIZES_BYTES
    ],
    ids=['seed', 'identity-schema', 'binary', '1mib', '2mib', '4mib', '8mib', '16mib', '32mib'],
)
def test_remote_query_allowlisted_proof_queries_execute_against_real_clickhouse(
    instance, monkeypatch, query, expected_payload_bytes, include_schema
):
    """Every allowlisted proof query executes on a real server and produces one exact row."""
    check = patch_real_check(monkeypatch, instance)
    fake = FakeUploadClient()

    request = real_server_request(instance, query, include_schema=include_schema)
    events = list(iter_agent_rpc_stream_events(request, check, fake, None))

    final = assert_success(events)
    pages = assembled_pages(fake)
    # Every proof query is a single row: one page uploaded as one direct PUT, bounded by
    # maxFileBytes, with the exact whole-page identity declared on the request.
    assert list(pages) == [0]
    assert final['upload_receipt']['totalRows'] == 1
    assert final['upload_receipt']['totalBytes'] == len(pages[0])
    (page_call,) = fake.put_page_calls
    assert page_call.source_bytes == len(pages[0])
    assert page_call.source_bytes <= 64 * 1024 * 1024
    assert page_call.rows == 1
    assert fake.run_finalize_calls == 1
    # The single row is one CSV record: an independent reader recovers the canonical cell
    # token, and its JSON value is the exact row. The payload fields run to 32 MiB, far
    # past csv.reader's default 128 KiB field limit, so the limit is raised for this one
    # decode and restored afterwards.
    previous_field_limit = csv.field_size_limit()
    csv.field_size_limit(max(previous_field_limit, 64 * 1024 * 1024))
    try:
        (record,) = csv.reader([pages[0].decode('utf-8')])
    finally:
        csv.field_size_limit(previous_field_limit)
    if expected_payload_bytes is not None:
        # The single payload column carries exactly the intended byte count of 'x' bytes.
        assert record == [json.dumps('x' * expected_payload_bytes)]
    elif query == remote_query.REMOTE_QUERY_IDENTITY_QUERY:
        # The identity query proves the matched server without a fixture: real host, user,
        # and version strings ride through the pinned String value contract.
        assert len(record) == 3
        assert all(isinstance(json.loads(token), str) and json.loads(token) for token in record)
    elif query == remote_query.REMOTE_QUERY_BINARY_QUERY:
        # The binary payload is the exact three bytes NUL, 'a', 'b': the server renders
        # the NUL as the JSON escape in the record's single field (the dedicated
        # NUL-payload test pins the same token against the page bytes).
        assert record == [json.dumps('\x00ab')]
    else:
        assert len(record) == 1
        assert json.loads(record[0]) == 1
