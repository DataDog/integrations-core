# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import hashlib
import io
import json
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from datadog_checks.base.utils import remote_queries as rq

AGENT_HOSTNAME = 'rq-proof-agent-a'


@pytest.fixture
def delivery():
    return rq.RemoteQueryResultDelivery.model_validate(
        {
            'runId': 'run-1',
            'taskId': 'task-1',
            'artifactVersion': 2,
            'uploadId': 'upload-1',
            'baseUrl': 'https://intake.example',
            'limits': {
                'maxFileBytes': 1024,
                'maxResultBytes': 8192,
                'maxRowBytes': 64,
                'maxColumns': 8,
                'maxSchemaBytes': 256,
                'maxPages': 8,
                'timeoutMs': 5000,
            },
        }
    )


@pytest.fixture
def creds(delivery):
    return rq.UploadCredentials(delivery.base_url, delivery.upload_id, 'test-api-key', 'test-app-key', None)


def receipt(page):
    return {
        'batch_index': page.batch_index,
        'record_offset': page.record_offset,
        'bytes': page.page_bytes,
        'rows': page.rows,
        'sha256': page.sha256_hex,
        'key': f'pages/{page.batch_index}.json',
    }


class Uploads:
    def __init__(self):
        self.pages = []
        self.bodies = []

    def put_page(self, creds, page, body):
        self.pages.append((page, body.read()))
        self.bodies.append(body)
        return receipt(page)

    def finalize_run(self, creds):
        return {'upload_id': creds.upload_id}


def bounded_delivery(delivery, **limits):
    value = delivery.model_dump(by_alias=True)
    value['limits'].update(limits)
    return rq.RemoteQueryResultDelivery.model_validate(value)


class AdvancingUploads(Uploads):
    """Uploads fake whose calls advance a mutable clock, each by a fixed wall."""

    def __init__(self, clock, put_page_seconds, finalize_seconds):
        super().__init__()
        self._clock = clock
        self._put_page_seconds = put_page_seconds
        self._finalize_seconds = finalize_seconds

    def put_page(self, creds, page, body):
        self._clock['now'] += self._put_page_seconds
        return super().put_page(creds, page, body)

    def finalize_run(self, creds):
        self._clock['now'] += self._finalize_seconds
        return super().finalize_run(creds)


def test_phase_nesting_suspends_the_enclosing_accumulation():
    # A scripted accumulator clock: the values below are the reads in order. The fetch runs
    # inside the encode phase, so the fetch's wall must leave the encode bucket and land in
    # its own, and the un-instrumented remainder must land in otherMs.
    values = iter([0.0, 0.5, 0.5, 0.75, 1.0, 1.25, 1.5])
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.phase('database_setup'):
        pass  # exits at 0.5
    with timings.phase('encode_and_page_build'):
        with timings.phase('database_fetch'):
            pass  # 0.75 -> 1.0
        pass  # encode resumes at 1.0 and exits at 1.25
    assert timings.metadata() == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 1500,
            'databaseSetupMs': 500,
            'databaseFetchMs': 250,
            'encodeAndPageBuildMs': 500,
            'otherMs': 250,
        },
    }


def test_page_writer_upload_inside_encode_is_excluded_from_encode(delivery, creds):
    # finish() runs inside the encode phase, so the final page's upload and the finalize
    # suspend the encode accumulation instead of leaking into it; the enclosing encode
    # segment between the two (the page receipt verification) stays in the encode bucket.
    clock = {'now': 0.0}
    stats = rq.RemoteQueryRunStats()
    uploads = AdvancingUploads(clock, put_page_seconds=0.5, finalize_seconds=0.375)
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: clock['now'])
    writer = rq.PageWriter(delivery, creds, uploads, AGENT_HOSTNAME, None, lambda: None, stats, timings)
    with timings.phase('encode_and_page_build'):
        writer.add_row(b'{"value":1}')
        clock['now'] += 0.25  # measured encode work
        writer.finish()
        clock['now'] += 0.125  # page receipt verification back in the encode bucket
    assert timings.metadata(stats) == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 1250,
            'encodeAndPageBuildMs': 375,
            'pageUploadMs': 500,
            'finalizeMs': 375,
            'otherMs': 0,
            'timeToFirstPageMs': 750,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': stats.bytes_emitted,
            'pageUploadMinMs': 500,
            'pageUploadP50Ms': 500,
            'pageUploadP95Ms': 500,
            'pageUploadMaxMs': 500,
        },
    }


@pytest.mark.parametrize(
    'ascending_ms,quantile,expected',
    [
        ([10.0], 0.50, 10.0),
        ([10.0], 0.95, 10.0),
        ([10.0, 20.0], 0.50, 10.0),  # ceil(0.50*2) = 1
        ([10.0, 20.0], 0.95, 20.0),  # ceil(0.95*2) = 2
        ([10.0, 20.0, 30.0], 0.50, 20.0),  # ceil(1.5) = 2
        ([10.0, 20.0, 30.0], 0.95, 30.0),  # ceil(2.85) = 3
        ([float(value) for value in range(1, 21)], 0.50, 10.0),  # ceil(10) = 10
        ([float(value) for value in range(1, 21)], 0.95, 19.0),  # ceil(19) = 19: not the max
    ],
)
def test_nearest_rank_percentile_table(ascending_ms, quantile, expected):
    assert rq.nearest_rank_percentile(ascending_ms, quantile) == expected


def test_page_upload_distribution_uses_nearest_rank_percentiles():
    # Three completed pages with upload walls of 125, 250, and 375 ms. The scripted clock
    # values are the accumulator's reads in order: each page's upload enter/exit pair plus
    # the one acknowledgment read (only the first page's acknowledgment reads the clock, for
    # the first-page time) and the final emission read.
    values = iter([0.0, 0.125, 0.125, 0.125, 0.375, 0.375, 0.75, 1.125])
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.page_upload():
        pass
    timings.note_page_acknowledged()
    with timings.page_upload():
        pass
    timings.note_page_acknowledged()
    with timings.page_upload():
        pass
    timings.note_page_acknowledged()
    assert timings.metadata() == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 1125,
            'pageUploadMs': 750,
            'otherMs': 375,
            'timeToFirstPageMs': 125,
            'pageUploadMinMs': 125,
            'pageUploadP50Ms': 250,
            'pageUploadP95Ms': 375,
            'pageUploadMaxMs': 375,
        },
    }


def test_zero_page_run_omits_the_upload_distribution_fields():
    values = iter([0.0, 0.5, 1.0])
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.phase('finalize'):
        pass
    assert timings.metadata() == {
        'contractVersion': 1,
        'producer': {'totalMs': 1000, 'finalizeMs': 500, 'otherMs': 500},
    }


def test_metadata_reports_only_measured_fields():
    # Nothing ran beyond reading the clock: the minimal shape carries only the measured run
    # wall and its remainder, exactly what a malformed request reports.
    values = iter([0.25])
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    assert timings.metadata() == {'contractVersion': 1, 'producer': {'totalMs': 250, 'otherMs': 250}}


def test_other_ms_clamps_to_zero_when_measured_phases_exceed_the_total():
    # A clock that runs backward between the phase exit and emission would make the measured
    # phases larger than the total; the remainder clamps to zero instead of going negative.
    values = iter([0.0, 1.0, 0.5])
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: next(values))
    with timings.phase('database_fetch'):
        pass
    diagnostics = timings.metadata()
    assert diagnostics['producer']['databaseFetchMs'] == 1000
    assert diagnostics['producer']['otherMs'] == 0


@pytest.mark.parametrize('include_schema', [False, True])
def test_pages_preserve_json_rows_schema_offsets_and_receipts(delivery, creds, include_schema):
    schema = [{'column_name': 'value', 'vendor_data_type': 'text'}]
    schema_json = json.dumps(schema).encode() if include_schema else None
    row = {'value': 'a\n\u2603'}
    encoded = json.dumps(row).encode()
    prefix = rq.page_prefix(
        run_id=delivery.run_id,
        task_id=delivery.task_id,
        record_offset=0,
        agent_hostname=AGENT_HOSTNAME,
        schema_json=schema_json,
    )
    limit = len(prefix) + len(encoded) + len(rq.PAGE_SUFFIX)
    delivery = bounded_delivery(delivery, maxFileBytes=limit, maxSchemaBytes=len(schema_json or b'') or 1)
    uploads = Uploads()
    writer = rq.PageWriter(
        delivery, creds, uploads, AGENT_HOSTNAME, schema_json, lambda: None, rq.RemoteQueryRunStats()
    )
    for _ in range(3):
        writer.add_row(encoded)
    result = writer.finish()

    assert len(uploads.pages) == 3
    for index, (page, payload) in enumerate(uploads.pages):
        envelope = json.loads(payload)
        expected_keys = ['contract_version', 'crawl_id', 'task_id', 'record_offset', 'agent_hostname']
        if include_schema:
            expected_keys.append('schema')
        assert list(envelope) == expected_keys + ['data']
        assert envelope['contract_version'] == rq.REMOTE_QUERY_ARTIFACT_VERSION == 2
        assert envelope['crawl_id'] == delivery.run_id
        assert envelope['task_id'] == delivery.task_id
        assert envelope['agent_hostname'] == AGENT_HOSTNAME
        assert 'run_id' not in envelope
        assert 'batch_index' not in envelope
        assert page.batch_index == index
        assert envelope['record_offset'] == page.record_offset == index
        assert envelope['data'] == [row]
        assert page.rows == 1
        assert page.page_bytes == len(payload) <= limit
        assert page.sha256_hex == hashlib.sha256(payload).hexdigest()
        if include_schema:
            assert envelope['schema'] == schema
        else:
            assert 'schema' not in envelope
    assert result == {
        'uploadId': creds.upload_id,
        'pageCount': 3,
        'totalRows': 3,
        'totalBytes': sum(len(payload) for _, payload in uploads.pages),
    }
    assert all(body.closed for body in uploads.bodies)


@pytest.mark.parametrize('schema,pages', [(None, 0), (b'[{"column_name":"value","vendor_data_type":"int"}]', 1)])
def test_empty_result_keeps_requested_schema(delivery, creds, schema, pages):
    uploads = Uploads()
    writer = rq.PageWriter(delivery, creds, uploads, AGENT_HOSTNAME, schema, lambda: None, rq.RemoteQueryRunStats())
    assert writer.finish()['pageCount'] == pages
    if pages:
        envelope = json.loads(uploads.pages[0][1])
        assert envelope['data'] == []
        assert envelope['agent_hostname'] == AGENT_HOSTNAME


@pytest.mark.parametrize(
    'bound,error', [('page', 'row_too_large'), ('count', 'max_pages_exceeded'), ('total', 'max_result_bytes_exceeded')]
)
def test_page_limits_fail_without_final_success(delivery, creds, bound, error):
    row = b'{"value":1}'
    size = (
        len(
            rq.page_prefix(
                run_id=delivery.run_id,
                task_id=delivery.task_id,
                record_offset=0,
                agent_hostname=AGENT_HOSTNAME,
                schema_json=None,
            )
        )
        + len(row)
        + len(rq.PAGE_SUFFIX)
    )
    delivery = bounded_delivery(
        delivery,
        maxFileBytes=size,
        maxSchemaBytes=1,
        maxPages=1 if bound == 'count' else 8,
        maxResultBytes=size if bound == 'total' else 8192,
    )
    uploads = Uploads()
    writer = rq.PageWriter(delivery, creds, uploads, AGENT_HOSTNAME, None, lambda: None, rq.RemoteQueryRunStats())
    try:
        with pytest.raises(rq.RemoteQueryFailure) as failure:
            writer.add_row(row + b' ' if bound == 'page' else row)
            writer.add_row(row)
            writer.finish()
        assert failure.value.code == error
    finally:
        writer.discard()
    assert all(body.closed for body in uploads.bodies)


@pytest.mark.parametrize('failure', ['upload', 'receipt'])
def test_failed_upload_releases_page(delivery, creds, failure):
    bodies = []

    def put_page(_creds, page, body):
        bodies.append(body)
        if failure == 'upload':
            raise rq.RemoteQueryFailure('upload_failed', 'unavailable')
        return {**receipt(page), 'rows': page.rows + 1}

    writer = rq.PageWriter(
        delivery,
        creds,
        SimpleNamespace(put_page=put_page),
        AGENT_HOSTNAME,
        None,
        lambda: None,
        rq.RemoteQueryRunStats(),
    )
    writer.add_row(b'{"value":1}')
    with pytest.raises(rq.RemoteQueryFailure):
        writer.finish()
    assert bodies[0].closed


@pytest.mark.parametrize('trigger', ['lost_response', 'unavailable', 'in_progress'])
def test_http_page_retry_replays_exact_body_and_headers(monkeypatch, creds, trigger):
    import requests

    calls = []
    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(2, 7, len(payload), 1, hashlib.sha256(payload).hexdigest())

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data.read()))
        if len(calls) == 1:
            if trigger == 'lost_response':
                raise requests.exceptions.ConnectionError('response lost')
            status = 503 if trigger == 'unavailable' else 409
            return SimpleNamespace(status_code=status, content=b'{"error":{"code":"page_upload_in_progress"}}')
        return SimpleNamespace(status_code=200, content=json.dumps(receipt(page)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    client = rq.RequestsUploadClient()
    with io.BytesIO(payload) as body:
        assert client.put_page(creds, page, body) == receipt(page)
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('PUT', 'https://intake.example/uploads/upload-1/pages/2', payload)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'dd-application-key': 'test-app-key',
        'Content-Type': 'application/json',
        'Content-Length': str(len(payload)),
        'X-DD-Page-Bytes': str(len(payload)),
        'X-DD-Page-Rows': '1',
        'X-DD-Record-Offset': '7',
        'X-DD-Page-SHA256': page.sha256_hex,
    }


@pytest.mark.parametrize('status', [400, 403, 409])
def test_http_terminal_rejections_are_not_retried(monkeypatch, creds, status):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(status_code=status, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    page = rq.PageUploadMetadata(0, 0, 1, 1, '0' * 64)
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.RequestsUploadClient().put_page(creds, page, io.BytesIO(b'x'))
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert len(calls) == 1


def test_http_page_attempt_bound_kills_slow_attempts(monkeypatch, creds):
    import requests

    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(0, 0, len(payload), 1, hashlib.sha256(payload).hexdigest())
    attempts = []
    sent = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        sent.append(data.read())
        return SimpleNamespace(status_code=200, content=json.dumps(receipt(page)).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    # The wall is 100 s away, but the per-attempt bound is 55 s: the first attempt's body read
    # happens past it and is killed mid-body; the second, rewound attempt succeeds.
    clock = iter([0.0, 0.0, 56.0, 56.0, 56.0] + [56.0] * 10)
    monkeypatch.setattr(rq.time, 'monotonic', lambda: next(clock))
    wall_creds = rq.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=100.0
    )
    with io.BytesIO(payload) as body:
        assert rq.RequestsUploadClient().put_page(wall_creds, page, body) == receipt(page)
    assert len(attempts) == 2
    assert sent == [payload]


def test_http_page_attempt_bound_never_exceeds_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(0, 0, len(payload), 1, hashlib.sha256(payload).hexdigest())
    attempts = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        data.read()
        return SimpleNamespace(status_code=200, content=b'{}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    # The wall is 50 s away, inside the 55 s attempt bound, so the attempt's own deadline is
    # the wall: a partially consumed budget bounds the page attempt, the killed attempt is not
    # retried past the wall, and the run surfaces the retryable wall timeout.
    clock = iter([0.0, 0.0, 51.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq.time, 'monotonic', lambda: next(clock))
    wall_creds = rq.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=50.0
    )
    with pytest.raises(rq.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq.RequestsUploadClient().put_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_http_retry_sequence_never_extends_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'{"value":1}'
    page = rq.PageUploadMetadata(0, 0, len(payload), 1, hashlib.sha256(payload).hexdigest())
    attempts = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    # A transient rejection followed by an expired wall: the sequence refuses to start another
    # attempt and surfaces the retryable wall timeout instead of uploading past the wall.
    clock = iter([0.0, 0.0, 51.5] + [51.5] * 10)
    monkeypatch.setattr(rq.time, 'monotonic', lambda: next(clock))
    wall_creds = rq.UploadCredentials(
        creds.base_url, creds.upload_id, creds.api_key, creds.app_key, None, wall_deadline=50.0
    )
    with pytest.raises(rq.RemoteQueryFailure) as failure, io.BytesIO(payload) as body:
        rq.RequestsUploadClient().put_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_retry_accounting_includes_failed_attempts_and_backoff_exactly_once(monkeypatch, delivery, creds):
    import requests

    clock = {'now': 0.0}
    monkeypatch.setattr(rq.time, 'monotonic', lambda: clock['now'])

    # The retry backoff advances the same monotonic clock, so the page's upload wall provably
    # includes it. The advance is pinned to a dyadic quarter second (instead of the real 0.1 s
    # first backoff) so the accumulated float arithmetic stays exact; what is under test is
    # that the backoff is counted once, not its exact production value.
    def fake_sleep(seconds):
        clock['now'] += 0.125

    monkeypatch.setattr(rq.time, 'sleep', fake_sleep)
    payload = b'{"value":1}'
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(method)
        if method != 'PUT':
            clock['now'] += 0.5
            return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')
        if len(calls) == 1:
            clock['now'] += 3.0
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        clock['now'] += 7.0
        # Echo the declared page metadata so the authoritative receipt verification passes.
        batch_index = int(url.rsplit('/', 1)[-1])
        return SimpleNamespace(
            status_code=200,
            content=json.dumps(
                {
                    'batch_index': batch_index,
                    'key': 'agent-intake-test/pages/{}.json'.format(batch_index),
                    'record_offset': int(headers['X-DD-Record-Offset']),
                    'bytes': int(headers['X-DD-Page-Bytes']),
                    'rows': int(headers['X-DD-Page-Rows']),
                    'sha256': headers['X-DD-Page-SHA256'],
                }
            ).encode(),
        )

    monkeypatch.setattr(requests, 'request', request)
    stats = rq.RemoteQueryRunStats()
    timings = rq.RemoteQueryProducerTimings(0.0)
    client = rq.RequestsUploadClient(timings=timings)
    writer = rq.PageWriter(delivery, creds, client, AGENT_HOSTNAME, None, lambda: None, stats, timings)

    writer.add_row(payload)
    result = writer.finish()

    assert calls == ['PUT', 'PUT', 'POST']
    assert result == {
        'uploadId': creds.upload_id,
        'pageCount': 1,
        'totalRows': 1,
        'totalBytes': stats.bytes_emitted,
    }
    # The page's upload wall is exactly the failed attempt (3 s) plus the backoff (0.125 s)
    # plus the successful attempt (7 s), each counted once; finalize is its own phase.
    assert timings.metadata(stats) == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 10625,
            'pageUploadMs': 10125,
            'finalizeMs': 500,
            'otherMs': 0,
            'timeToFirstPageMs': 10125,
            'pageCount': 1,
            'rowCount': 1,
            'byteCount': stats.bytes_emitted,
            'uploadAttemptCount': 2,
            'uploadRetryCount': 1,
            'pageUploadMinMs': 10125,
            'pageUploadP50Ms': 10125,
            'pageUploadP95Ms': 10125,
            'pageUploadMaxMs': 10125,
        },
    }


def test_page_writer_emits_identical_page_bytes_with_and_without_timings(delivery, creds):
    # Timing collection must never reach the page artifacts: the emitted page bytes and the
    # compact receipt are identical with the accumulator attached and without it.
    def run(with_timings):
        uploads = Uploads()
        stats = rq.RemoteQueryRunStats()
        timings = rq.RemoteQueryProducerTimings(0.0) if with_timings else None
        writer = rq.PageWriter(delivery, creds, uploads, AGENT_HOSTNAME, None, lambda: None, stats, timings)
        for _ in range(3):
            writer.add_row(b'{"value":1}')
        return uploads, writer.finish()

    uploads_without, receipt_without = run(False)
    uploads_with, receipt_with = run(True)

    assert [body for _, body in uploads_without.pages] == [body for _, body in uploads_with.pages]
    assert receipt_without == receipt_with


def test_finalize_abort_and_test_drive_routing(monkeypatch, creds):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data))
        return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')

    monkeypatch.setattr(requests, 'request', request)
    creds = rq.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, creds.app_key, 'test-intake')
    client = rq.RequestsUploadClient()
    assert client.finalize_run(creds)['upload_id'] == creds.upload_id
    client.abort(creds)
    assert [call[1] for call in calls] == [
        'https://intake.example/uploads/upload-1/finalize',
        'https://intake.example/uploads/upload-1/abort',
    ]
    assert all(
        method == 'POST' and headers['test-drive-test-intake'] == '1' and body == b'{}'
        for method, _, headers, body in calls
    )


@pytest.mark.parametrize(
    'field,bad',
    [('batch_index', 1), ('record_offset', -1), ('bytes', 2), ('rows', True), ('sha256', 'mismatch'), ('key', '')],
)
def test_receipt_must_match_produced_page(field, bad):
    page = rq.PageUploadMetadata(0, 0, 1, 1, '0' * 64)
    with pytest.raises(rq.RemoteQueryFailure, match='response'):
        rq.verify_page_response({**receipt(page), field: bad}, page)


@pytest.mark.parametrize('body', [b'', b'not-json', b'[]', b'null'])
def test_page_receipt_requires_json_object(body):
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.parse_page_receipt_body(body)
    assert failure.value.code == 'invalid_receipt'


def test_finalize_identity_must_match():
    with pytest.raises(rq.RemoteQueryFailure):
        rq.verify_run_finalize_response({'upload_id': 'other'}, 'upload-1')


@pytest.mark.parametrize(
    'target',
    [
        {},
        {'host': 'db', 'dbname': 'db'},
        {'database_instance': ' db '},
        {'database_instance': 'db', 'host': 'db'},
        {'database_instance': 'db', 'port': 5432},
        {'database_instance': 'db', 'dbname': None},
        {'database_instance': 'db', 'dbname': ''},
        {'database_instance': 'db', 'dbname': ' '},
        {'host': 'db', 'port': True, 'dbname': 'db'},
    ],
)
def test_target_requires_one_complete_selector(target):
    with pytest.raises(ValueError):
        rq.normalize_target(target)


def test_database_instance_target_accepts_requested_dbname():
    target = rq.normalize_target({'database_instance': 'Primary/DB', 'dbname': 'other'})
    assert (target.database_instance, target.dbname) == ('Primary/DB', 'other')
    assert target.host is None and target.port is None


@pytest.mark.parametrize(
    'path,value',
    [
        (('operation',), None),
        (('includeSchema',), 'true'),
        (('target', 'port'), '5432'),
        (('resultDelivery',), None),
        (('resultDelivery', 'token'), 'scoped-upload-token'),
        (('resultDelivery', 'artifactVersion'), 1),
        (('resultDelivery', 'limits', 'maxFileBytes'), 128 * 1024**2 + 1),
        (('resultDelivery', 'limits', 'maxResultBytes'), rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1),
        (('resultDelivery', 'limits', 'password'), 'SECRET_DO_NOT_LOG'),
    ],
)
def test_request_validation_rejects_malformed_instructions_without_echoing_values(delivery, path, value):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
    }
    parent = request
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    with pytest.raises(ValidationError) as failure:
        rq.RemoteQueryRequest.model_validate(request)
    message = rq.validation_message(failure.value)
    assert path[-1] in message
    assert 'SECRET_DO_NOT_LOG' not in message


def test_target_normalization():
    target = rq.normalize_target({'host': ' DB.EXAMPLE. ', 'port': 5432, 'dbname': 'db'})
    assert (target.host, target.port, target.dbname) == ('db.example', 5432, 'db')
    assert rq.normalize_target({'database_instance': 'Primary/DB'}).database_instance == 'Primary/DB'


@pytest.mark.parametrize(
    'mutation',
    [{'maxFileBytes': 0}, {'maxRowBytes': 2048}, {'maxSchemaBytes': 2048}, {'maxResultBytes': 512}, {'maxPages': '8'}],
)
def test_limits_reject_invalid_bounds(delivery, mutation):
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, **mutation)


def test_result_ceiling_is_the_pinned_server_contract(delivery):
    # The ceiling is 100 binary GiB (stricter than decimal 100 GB): exactly that validates and
    # one byte more is rejected, so the shared ceiling cannot drift from the server-owned
    # contract or silently fall back to a smaller value.
    assert rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES == 100 * 1024**3
    limits = bounded_delivery(delivery, maxResultBytes=rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES).limits
    assert limits.max_result_bytes == rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, maxResultBytes=rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1)


def test_page_writer_result_cap_boundaries(delivery, creds):
    # One row per page keeps the page arithmetic exact: the frame is sized to a single row, so
    # three rows produce three pages whose byte total is measured, then pinned as the exact
    # cap (the last row lands exactly on it) and one byte below it (cap-plus-one fails).
    row = b'{"value":"aaaa"}'
    frame = (
        len(
            rq.page_prefix(
                run_id=delivery.run_id,
                task_id=delivery.task_id,
                record_offset=0,
                agent_hostname=AGENT_HOSTNAME,
                schema_json=None,
            )
        )
        + len(row)
        + len(rq.PAGE_SUFFIX)
    )
    delivery = bounded_delivery(delivery, maxFileBytes=frame, maxSchemaBytes=frame, maxRowBytes=len(row), maxPages=8)

    def run(max_result_bytes):
        scoped = bounded_delivery(delivery, maxResultBytes=max_result_bytes)
        uploads = Uploads()
        writer = rq.PageWriter(scoped, creds, uploads, AGENT_HOSTNAME, None, lambda: None, rq.RemoteQueryRunStats())
        try:
            for _ in range(3):
                writer.add_row(row)
            return writer.finish(), uploads
        finally:
            writer.discard()

    measured, uploads = run(rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES)
    total = measured['totalBytes']
    assert measured['pageCount'] == 3 == len(uploads.pages)
    assert total == sum(page.page_bytes for page, _ in uploads.pages)

    # Exact cap: the third row lands exactly on maxResultBytes (the last page fits it).
    exact, exact_uploads = run(total)
    assert exact['totalBytes'] == total
    assert [page.batch_index for page, _ in exact_uploads.pages] == [0, 1, 2]

    # Cap-plus-one: one byte less budget fails the row that would cross the cap.
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        run(total - 1)
    assert failure.value.code == 'max_result_bytes_exceeded'
    assert all(body.closed for body in exact_uploads.bodies)


@pytest.mark.parametrize('value,expected', [(None, True), (' yes ', True), ('false', False), (False, False)])
def test_allowlist_default_and_config(monkeypatch, value, expected):
    monkeypatch.setattr(rq.datadog_agent, 'get_config', lambda _: value)
    assert rq.is_query_allowlist_enabled() is expected


@pytest.mark.parametrize(
    'value,expected',
    [
        (' TEST-INTAKE ', 'test-intake'),
        (None, None),
        ('', None),
        ('-intake', None),
        ('a' * 64, None),
        ('x\r\nAuthorization: y', None),
    ],
)
def test_test_drive_name_cannot_inject_headers(value, expected):
    assert rq.validate_test_drive_name(value) == expected
