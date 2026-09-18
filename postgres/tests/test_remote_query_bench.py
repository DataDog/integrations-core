# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

"""Benchmarks for the native COPY CSV source-page producer against a real compose Postgres.

Each benchmark drives the normal ``iter_agent_rpc_stream_events`` path — the never-fetched
DECLARE descriptor, the single ``COPY ... TO STDOUT``, record framing, page buffering, and
page uploads — with a discard upload client: every page body is read and dropped, a
structurally valid receipt is returned, and no HTTP request is made, so the measured wall is
exactly the producer's own phases (COPY generation and fetch, CSV framing, source-page
buffering), never network or intake work.

Two scales run per invocation: a fast multi-page development case and a 256 MiB comparison
case. The producer phase diagnostics (``databaseSetupMs``, ``databaseFetchMs``,
``encodeAndPageBuildMs``, ``pageUploadMs``, …) and derived throughput are recorded in each
benchmark's ``extra_info`` so before/after comparisons can target the phase under change.

The optional ``RQ_SOURCE_PAGE_TARGET_FRACTION`` environment variable overrides the shared
source-page target fraction for target-selection experiments; it has no effect on a
producer that does not consult it.
"""

import hashlib
import json
import os
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils import remote_queries as rq
from datadog_checks.postgres.remote_query import StaticPostgresCheckRegistry, iter_agent_rpc_stream_events

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'
TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'
UPLOAD_ID = 'upload-01k-bench'

# The representative large-result row: an integer and a 1000-byte payload per record, the
# shape the source-page target is selected against.
BENCH_ROW_WIDTH = 1000

MIB = 1024 * 1024

READ_CHUNK_BYTES = 64 * 1024


class DiscardUploadClient:
    """Intake-side fake: reads each page body, drops it, and answers a valid receipt.

    Pages are never retained and no HTTP is made, so the producer's pageUploadMs stays near
    zero and the benchmark measures its own phases only.
    """

    def __init__(self):
        self.descriptor_bodies = []
        self.put_page_calls = []
        self.run_finalize_calls = 0
        self.abort_calls = 0
        self.rows = 0
        self.source_bytes = 0

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
        total = 0
        while chunk := body.read(READ_CHUNK_BYTES):
            total += len(chunk)
        # The body view must expose exactly the declared source bytes.
        assert total == page.source_bytes, (total, page.source_bytes)
        self.put_page_calls.append(
            SimpleNamespace(
                batch_index=page.batch_index,
                record_offset=page.record_offset,
                source_bytes=page.source_bytes,
                rows=page.rows,
            )
        )
        self.rows += page.rows
        self.source_bytes += page.source_bytes
        return {
            'batch_index': page.batch_index,
            'key': 'agent-intake-test/pages/{}.json'.format(page.batch_index),
            'record_offset': page.record_offset,
            'bytes': page.source_bytes,
            'rows': page.rows,
            'sha256': 'a' * 64,
        }

    def finalize_run(self, creds):
        self.run_finalize_calls += 1
        return {
            'upload_id': creds.upload_id,
            'page_count': len({call.batch_index for call in self.put_page_calls}),
            'total_rows': self.rows,
            'total_bytes': self.source_bytes,
        }

    def abort(self, creds):
        self.abort_calls += 1

    def page_count(self):
        return len({call.batch_index for call in self.put_page_calls})


def patch_upload_credentials(monkeypatch):
    # Key-aware: a blanket string return would leak into the check's proxy config lookup
    # during ``integration_check`` and break check initialization.
    def get_config(key):
        if key in ('api_key', 'app_key'):
            return 'TEST_KEY'
        return None

    monkeypatch.setattr(rq.datadog_agent, 'get_config', get_config)


def patch_allowlist_disabled(monkeypatch):
    monkeypatch.setattr(rq, 'is_query_allowlist_enabled', lambda: False)


def patch_source_page_target_fraction(monkeypatch):
    """Apply the optional RQ_SOURCE_PAGE_TARGET_FRACTION experiment knob, when set."""
    fraction = os.environ.get('RQ_SOURCE_PAGE_TARGET_FRACTION')
    if fraction:
        numerator, denominator = float(fraction).as_integer_ratio()
        monkeypatch.setattr(rq, 'REMOTE_QUERY_SOURCE_PAGE_TARGET_NUM', numerator)
        monkeypatch.setattr(rq, 'REMOTE_QUERY_SOURCE_PAGE_TARGET_DEN', denominator)


def bench_request(pg_instance, rows, max_file_bytes, timeout_ms):
    """One complete deterministic query per round: ``generate_series`` plus a fixed payload."""
    query = "SELECT i, repeat('x', {}) AS payload FROM generate_series(1, {}) AS i".format(BENCH_ROW_WIDTH, rows)
    return {
        'operation': 'produce_json_pages',
        'target': {
            'host': pg_instance['host'],
            'port': int(pg_instance['port']),
            'dbname': pg_instance['dbname'],
        },
        'query': query,
        'includeSchema': False,
        'resultDelivery': {
            'runId': RUN_ID,
            'taskId': TASK_ID,
            'artifactVersion': 1,
            'uploadId': UPLOAD_ID,
            'baseUrl': 'https://dd.datad0g.com/api/unstable/its-agent-intake',
            'limits': {
                'maxFileBytes': max_file_bytes,
                'maxResultBytes': 100 * 1024 * 1024 * 1024,
                'maxRowBytes': 1024 * 1024,
                'maxColumns': 1024,
                'maxSchemaBytes': 1024 * 1024,
                'maxPages': 1024,
                'timeoutMs': timeout_ms,
            },
        },
    }


def record_benchmark_info(benchmark, client, final):
    """Record the producer's own phase diagnostics and derived throughput for the run."""
    producer = final['executionDiagnostics']['producer']
    total_seconds = producer['totalMs'] / 1000
    benchmark.extra_info.update(
        {
            'databaseSetupMs': producer.get('databaseSetupMs'),
            'databaseFetchMs': producer.get('databaseFetchMs'),
            'encodeAndPageBuildMs': producer.get('encodeAndPageBuildMs'),
            'pageUploadMs': producer.get('pageUploadMs'),
            'finalizeMs': producer.get('finalizeMs'),
            'otherMs': producer.get('otherMs'),
            'totalMs': producer.get('totalMs'),
            'pageCount': client.page_count(),
            'rowCount': client.rows,
            'sourceBytes': client.source_bytes,
            'sourceMiB': round(client.source_bytes / MIB, 2),
            'sourceMiBPerSecond': round(client.source_bytes / MIB / total_seconds, 2) if total_seconds else None,
            'rowsPerSecond': round(client.rows / total_seconds, 2) if total_seconds else None,
        }
    )


def run_producer(benchmark, integration_check, pg_instance, monkeypatch, rows, max_file_bytes, rounds, timeout_ms):
    patch_upload_credentials(monkeypatch)
    patch_allowlist_disabled(monkeypatch)
    patch_source_page_target_fraction(monkeypatch)
    check = integration_check(pg_instance)
    request = bench_request(pg_instance, rows, max_file_bytes, timeout_ms)

    def produce_once():
        client = DiscardUploadClient()
        events = list(iter_agent_rpc_stream_events(request, StaticPostgresCheckRegistry([check]), client))
        return client, events[-1].metadata

    client, final = benchmark.pedantic(produce_once, rounds=rounds, iterations=1)

    # The benchmark must measure a successful producer run, not a silent failure.
    assert final['status'] == 'SUCCEEDED', final
    assert final['upload_receipt']['totalRows'] == rows
    assert client.rows == rows
    assert client.abort_calls == 0
    record_benchmark_info(benchmark, client, final)
    return client, final


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_producer_pipeline_dev_multibyte(benchmark, integration_check, pg_instance, monkeypatch):
    """A fast multi-page development case: ~20 MB over ~4 MiB page budgets."""
    client, final = run_producer(
        benchmark,
        integration_check,
        pg_instance,
        monkeypatch,
        rows=20_000,
        max_file_bytes=4 * MIB,
        rounds=5,
        timeout_ms=120_000,
    )
    # The case is only meaningful when it actually crosses page boundaries.
    assert client.page_count() > 1


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_producer_pipeline_256mib(benchmark, integration_check, pg_instance, monkeypatch):
    """The 256 MiB comparison case over the normal 100 MiB final-file target."""
    client, final = run_producer(
        benchmark,
        integration_check,
        pg_instance,
        monkeypatch,
        rows=262_144,
        max_file_bytes=100 * MIB,
        rounds=3,
        timeout_ms=600_000,
    )
    assert client.page_count() > 1
