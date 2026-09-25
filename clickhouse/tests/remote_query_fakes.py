# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from __future__ import annotations

import hashlib
import json
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import upload as rq_upload
from datadog_checks.clickhouse.remote_query import ClickhouseRemoteQueryHandler

RUN_ID = '383d34aa-0766-472f-9e27-9190d9a52ab6'


TASK_ID = '603f58a7-04cf-4ffe-860b-3885457f885c'


UPLOAD_ID = 'upload-01k'


BASE_URL = 'https://dd.datad0g.com/api/unstable/its-agent-intake'


AGENT_HOSTNAME = 'rq-proof-agent-a'


def stream_body(names, types, rows):
    """A JSONCompactEachRowWithNamesAndTypes body: names row, types row, then data rows."""
    lines = [json.dumps(list(names)), json.dumps(list(types))]
    lines.extend(json.dumps(list(row)) for row in rows)
    return ('\n'.join(lines) + '\n').encode('utf-8')


def raw_stream_body(*lines):
    """A body from raw lines, for malformed-stream cases."""
    return b'\n'.join(line if isinstance(line, bytes) else line.encode('utf-8') for line in lines) + b'\n'


def compact_json_line(values):
    """One stream line rendered with ClickHouse's compact JSON separators (no spaces).

    The shared ``stream_body`` helper uses ``json.dumps`` default separators, whose spaces
    do not exist on the real wire; byte-exact line arithmetic needs the compact form.
    """
    return json.dumps(list(values), separators=(',', ':')).encode('utf-8')


class FakeStream:
    """urllib3 HTTPResponse stand-in: bounded reads over the body, close tracking."""

    def __init__(self, body, chunk_size=32, read_error=None, error_at=None, read_log=None):
        self._body = body
        self._offset = 0
        self._chunk_size = chunk_size
        self.read_count = 0
        self.read_sizes = []
        self.closed = False
        self.read_error = read_error
        self.error_at = error_at
        self.read_log = read_log

    def read(self, amount):
        self.read_count += 1
        self.read_sizes.append(amount)
        if self.read_log is not None:
            self.read_log.append(('read', self._offset))
        if self.read_error is not None and (self.error_at is None or self.read_count >= self.error_at):
            raise self.read_error
        chunk = self._body[self._offset : self._offset + amount]
        self._offset += len(chunk)
        return chunk

    def close(self):
        self.closed = True

    @property
    def offset(self):
        return self._offset

    @property
    def exhausted(self):
        return self._offset >= len(self._body)


class FakeClickhouseClient:
    """Per-run client stand-in: one raw_stream call returning the configured stream."""

    def __init__(
        self,
        body,
        readonly_level=0,
        chunk_size=32,
        raw_stream_error=None,
        read_error=None,
        error_at=None,
        read_log=None,
    ):
        self.server_settings = (
            {'readonly': SimpleNamespace(value=str(readonly_level))} if readonly_level is not None else {}
        )
        self._body = body
        self._chunk_size = chunk_size
        self._raw_stream_error = raw_stream_error
        self._read_error = read_error
        self._error_at = error_at
        self._read_log = read_log
        self.raw_stream_calls = []
        self.stream = None
        self.closed = False

    def raw_stream(self, query, settings=None, fmt=None):
        self.raw_stream_calls.append({'query': query, 'settings': dict(settings or {}), 'fmt': fmt})
        if self._raw_stream_error is not None:
            raise self._raw_stream_error
        self.stream = FakeStream(
            self._body,
            chunk_size=self._chunk_size,
            read_error=self._read_error,
            error_at=self._error_at,
            read_log=self._read_log,
        )
        return self.stream

    def close(self):
        self.closed = True


class FakeUploadClient:
    """Intake-side fake: one descriptor registration, page acceptance receipts, finalize totals.

    Page PUTs answer the pinned acceptance receipt — no per-page final metadata exists at
    acceptance — and the default finalize returns authoritative totals over the recorded
    pages, so the producer's stats and compact receipt come from finalization.
    """

    def __init__(
        self,
        put_page_response=None,
        put_log=None,
    ):
        # SimpleNamespace(batch_index, record_offset, source_bytes, rows, payload)
        self.descriptor_bodies = []
        self.put_page_calls = []
        self.run_finalize_calls = 0
        self.finalize_expected_page_counts = []
        self.abort_calls = 0
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


def make_check(
    server='localhost',
    port=8123,
    db='default',
    pool_manager=None,
    check_database_identifier=None,
    hostname=AGENT_HOSTNAME,
):
    check = SimpleNamespace(
        _config=SimpleNamespace(server=server, port=port, db=db),
        _pool_manager=pool_manager if pool_manager is not None else object(),
        hostname=hostname,
    )
    if check_database_identifier is not None:
        check.database_identifier = check_database_identifier
    return check


def make_client(names=('value',), types=('UInt8',), rows=(), readonly_level=0, **stream_kwargs):
    return FakeClickhouseClient(stream_body(names, types, rows), readonly_level=readonly_level, **stream_kwargs)


def valid_request(query='SELECT 1 AS value', include_schema=False, **extra):
    target = {
        'host': extra.pop('host', 'LOCALHOST.'),
        'port': extra.pop('port', 8123),
        'dbname': extra.pop('dbname', 'default'),
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
    # Overrides may shrink maxFileBytes below the default schema budget; the executor
    # rejects a schema budget beyond the page budget, so keep the pair consistent.
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


class ExplodingCheck:
    """A check that fails any test touching it: request validation must reject first."""

    def __getattr__(self, name):
        pytest.fail('check must not be touched before request validation completes')


def collect_events(request, check, upload_client=None, clickhouse_client=None):
    """Run the producer with fakes and collect its events.

    ``clickhouse_client`` is injected as the per-run client factory result. With no
    client injected, a default body (``SELECT 1 AS value``) is used, so tests that need a
    specific result stream always pass one explicitly.
    """
    client_factory = None
    if clickhouse_client is not None:

        def client_factory(_check, _limits):
            return clickhouse_client

    if upload_client is None:
        upload_client = FakeUploadClient()
    return list(
        ClickhouseRemoteQueryHandler(check).execute(
            request, http_client=upload_client, clickhouse_client_factory=client_factory
        )
    )


def event_metadata(event):
    return event.metadata


def assert_failed_event(events, code, message_contains=None):
    assert events[-1].event_type == 'error'
    assert event_metadata(events[-1])['status'] == 'FAILED'
    assert event_metadata(events[-1])['error']['code'] == code
    if message_contains is not None:
        assert message_contains in event_metadata(events[-1])['error']['message']


def resolve_request(**target):
    """A strict resolve_target request: operation and target only."""
    if 'database_instance' in target:
        selector = {'database_instance': target['database_instance']}
    else:
        selector = {
            'host': target.pop('host', 'LOCALHOST.'),
            'port': target.pop('port', 8123),
            'dbname': target.pop('dbname', 'default'),
        }
    return {'operation': 'resolve_target', 'target': selector}


def collect_resolve_events(request, check):
    return list(ClickhouseRemoteQueryHandler(check).resolve(request))


def assert_matched_verdict(events):
    """A verdict is exactly one MATCHED final event with no payload and no STARTED event."""
    assert len(events) == 1
    event = events[0]
    assert event.event_type == 'final'
    assert event.payload == b''
    metadata = event_metadata(event)
    assert metadata['status'] == 'MATCHED'
    return metadata['match']


def forbidding_client_factory():
    """A check-side client factory that fails any test touching it: resolve must not create clients."""

    def factory(**_kwargs):
        pytest.fail('resolve must not create a query client')

    return factory


def assert_success(events):
    assert events[-1].event_type == 'final'
    assert event_metadata(events[-1])['status'] == 'SUCCEEDED'
    return event_metadata(events[-1])


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


def row_object_bound(row):
    """The conservative final-JSON bound of one row object, computed independently.

    Mirrors the intake envelope arithmetic without reusing the producer's implementation:
    braces plus commas, each descriptor key plus its colon, and each scalar string or number
    leaf at its own token length or the fixed redaction marker, whichever is larger.
    """
    bound = 2 + (len(row) - 1)
    for name, value in row.items():
        bound += len(json.dumps(name, ensure_ascii=False).encode('utf-8')) + 1
        bound += rq_pages.redactable_leaf_final_bound(json.dumps(value, ensure_ascii=False).encode('utf-8'))
    return bound


def csv_field(token):
    """The expected CSV field for one canonical token, computed independently of the producer."""
    if b'"' in token or b',' in token or b'\n' in token:
        return b'"' + token.replace(b'"', b'""') + b'"'
    return token


def csv_record(tokens):
    """The expected framed CSV record for one row of canonical tokens."""
    return b','.join(csv_field(token) for token in tokens) + b'\n'


BOUND_ROW = {'payload': 'aaaa'}


ROW_RECORD = csv_record([b'"aaaa"'])


def two_row_boundary_request(monkeypatch, extra_bound_bytes=0):
    """A budget that fits exactly two bound rows in one page (minus the extra bytes)."""
    patch_upload_credentials(monkeypatch)
    prefix_len = len(prefix_bytes())
    request = bounded_request()
    limits = request['resultDelivery']['limits']
    row_bound = row_object_bound(BOUND_ROW)
    limits['maxFileBytes'] = prefix_len + row_bound + 1 + row_bound + len(rq_pages.PAGE_SUFFIX) + extra_bound_bytes
    # Same constraint as bounded_request: the schema budget must stay within the page budget.
    limits['maxSchemaBytes'] = min(limits['maxSchemaBytes'], limits['maxFileBytes'])
    return request


def two_row_client(**stream_kwargs):
    return make_client(names=('payload',), types=('String',), rows=[['aaaa'], ['aaaa']], **stream_kwargs)


def quoted_numeric_rows_client(names, row, row_count):
    """A client whose stream repeats one quoted-numeric row on the real compact wire."""
    body = raw_stream_body(
        compact_json_line(names), compact_json_line(('UInt64',) * len(names)), *[compact_json_line(row)] * row_count
    )
    return FakeClickhouseClient(body)
