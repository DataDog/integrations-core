# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import io
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import events as rq_events
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import upload as rq_upload

from .helpers import (
    AGENT_HOSTNAME,
    PARENT_ID,
    TRACE_ID,
    as_session_request,
    cell,
    csv_record,
    descriptor,
    make_tracing,
    string_cell,
)

BASE_URL = 'https://intake.example/api/unstable/its-agent-intake'


def delivery_input(**overrides):
    value = {
        'protocol': 'sessionless-v1',
        'runId': 'crawl-1',
        'taskId': 'task-1',
        'artifactVersion': 1,
        'baseUrl': BASE_URL,
        'scanSensitiveData': True,
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
    value.update(overrides)
    return value


@pytest.fixture
def sessionless_delivery():
    return rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(delivery_input())


@pytest.fixture
def sessionless_creds(sessionless_delivery):
    return rq_upload.resolve_upload_credentials(sessionless_delivery, time.monotonic())


class SessionlessIntake:
    """A fake sessionless intake client: each accepted request mints a fresh object id.

    Any session call — registration, finalize, abort — is a test failure, because the
    sessionless protocol has no upload session.
    """

    def __init__(self, put_failure=None, receipt_override=None, canonical_bytes=None):
        self.put_failure = put_failure
        self.receipt_override = receipt_override
        self.canonical_bytes = canonical_bytes
        self.attempts = []
        self.pages = []
        self.object_ids = []

    def post_sessionless_page(self, creds, page, metadata, body):
        payload = body.read()
        self.attempts.append((page, json.loads(metadata), payload))
        if self.put_failure is not None:
            failure = self.put_failure(page)
            if failure is not None:
                raise failure
        self.pages.append((page, json.loads(metadata), payload))
        if self.receipt_override is not None:
            return self.receipt_override(page)
        receipt = page_receipt(page, bytes_=self.canonical_bytes(page) if self.canonical_bytes else page.source_bytes)
        self.object_ids.append(receipt['object_id'])
        return receipt

    def register_descriptor(self, creds, body):
        raise AssertionError('a sessionless run must not register a descriptor')

    def finalize_run(self, creds, expected_page_count):
        raise AssertionError('a sessionless run must not finalize an upload session')

    def abort(self, creds):
        raise AssertionError('a sessionless run must not abort an upload session')


def page_receipt(page, bytes_=None, **overrides):
    receipt = {
        'protocol': 'sessionless-v1',
        'object_id': str(uuid.uuid4()),
        'page_index': page.batch_index,
        'record_offset': page.record_offset,
        'rows': page.rows,
        'bytes': page.source_bytes if bytes_ is None else bytes_,
    }
    receipt.update(overrides)
    return receipt


def make_writer(delivery, creds, client, include_schema=False):
    return rq_pages.SourcePageWriter(
        delivery,
        creds,
        client,
        descriptor(include_schema=include_schema),
        lambda: None,
        rq_contract.RemoteQueryRunStats(),
    )


def bounded(delivery, **limits):
    value = delivery.model_dump(by_alias=True)
    value['limits'].update(limits)
    return rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(value)


# ---------------------------------------------------------------------------
# Delivery contract
# ---------------------------------------------------------------------------


def test_request_selects_the_delivery_model_from_the_protocol_key():
    base = {
        'operation': 'produce_json_pages',
        'target': {'database_instance': 'db'},
        'query': 'select 1',
    }
    sessionless = rq_contract.RemoteQueryRequest.model_validate({**base, 'resultDelivery': delivery_input()})
    assert isinstance(sessionless.result_delivery, rq_contract.RemoteQuerySessionlessResultDelivery)
    assert sessionless.result_delivery.scan_sensitive_data is True

    session_delivery = {
        'runId': 'run-1',
        'taskId': 'task-1',
        'artifactVersion': 1,
        'uploadId': 'upload-1',
        'baseUrl': BASE_URL,
        'limits': delivery_input()['limits'],
    }
    session = rq_contract.RemoteQueryRequest.model_validate({**base, 'resultDelivery': session_delivery})
    assert isinstance(session.result_delivery, rq_contract.RemoteQueryResultDelivery)


@pytest.mark.parametrize(
    'overrides',
    [
        {'protocol': 'sessionless-v2'},  # mixed/unknown version: never read as a session delivery
        {'protocol': None},
        {'uploadId': 'upload-1'},  # no session identity
        {'bucket': 'landing'},  # no destination routing
        {'token': 'secret'},
        {'sts-scanned': True},  # no trusted scan stamp
        {'scanSensitiveData': 'true'},  # strict boolean
        {'scanSensitiveData': 1},
        {'scanSensitiveData': None},
        {'artifactVersion': 2},
        {'runId': ''},
        {'taskId': ''},
        {'baseUrl': ''},
    ],
)
def test_sessionless_delivery_is_strict(overrides):
    with pytest.raises(ValidationError):
        rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(delivery_input(**overrides))
    with pytest.raises(ValidationError):
        rq_contract.RemoteQueryRequest.model_validate(
            {
                'operation': 'produce_json_pages',
                'target': {'database_instance': 'db'},
                'query': 'select 1',
                'resultDelivery': delivery_input(**overrides),
            }
        )


@pytest.mark.parametrize('missing', ['protocol', 'runId', 'taskId', 'artifactVersion', 'baseUrl', 'scanSensitiveData'])
def test_sessionless_delivery_requires_every_field(missing):
    value = delivery_input()
    del value[missing]
    with pytest.raises(ValidationError):
        rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(value)


@pytest.mark.parametrize(
    'limit,value',
    [
        ('maxFileBytes', 16 * 1024 * 1024 + 1),
        ('maxResultBytes', 1024 * 1024 * 1024 + 1),
        ('maxPages', 129),
        ('maxColumns', 1025),
        ('maxSchemaBytes', 1024 * 1024 + 1),
        ('maxRowBytes', 2048),  # a row must fit in one page
        ('unknownLimit', 1),
    ],
)
def test_sessionless_limits_cannot_exceed_the_experiment_ceilings(limit, value):
    limits = {
        **delivery_input()['limits'],
        'maxResultBytes': 1024 * 1024 * 1024,
        'maxSchemaBytes': 1024,
        limit: value,
    }
    with pytest.raises(ValidationError):
        rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(delivery_input(limits=limits))


def test_sessionless_limits_accept_the_ceilings():
    limits = {
        'maxFileBytes': 16 * 1024 * 1024,
        'maxResultBytes': 1024 * 1024 * 1024,
        'maxRowBytes': 16 * 1024 * 1024,
        'maxColumns': 1024,
        'maxSchemaBytes': 1024 * 1024,
        'maxPages': 128,
        'timeoutMs': 5000,
    }
    delivery = rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(delivery_input(limits=limits))
    assert delivery.limits.max_pages == 128


def test_sessionless_run_reports_its_delivery_and_creates_no_session_credentials(sessionless_delivery):
    metadata = rq_events.started_metadata(
        rq_contract.RemoteQueryRequest.model_validate(
            {
                'operation': 'produce_json_pages',
                'target': {'database_instance': 'db'},
                'query': 'select 1',
                'resultDelivery': delivery_input(),
            }
        )
    )
    assert metadata['resultDelivery']['protocol'] == 'sessionless-v1'
    assert metadata['resultDelivery']['scanSensitiveData'] is True
    assert 'uploadId' not in metadata['resultDelivery']

    creds = rq_upload.resolve_upload_credentials(sessionless_delivery, 10.0)
    assert creds.upload_id == ''
    assert creds.base_url == BASE_URL
    assert creds.wall_deadline == 15.0

    class NoAbortClient:
        def abort(self, creds):
            raise AssertionError('there is no sessionless upload session to abort')

    rq_upload.safe_abort(NoAbortClient(), creds)


def test_the_root_span_of_a_sessionless_run_carries_no_upload_id_tag(sessionless_delivery):
    tracing, tracer = make_tracing()
    tracing.open_root(sessionless_delivery)
    tracing.close()
    assert tracer.spans[0].tags['run_id'] == 'crawl-1'
    assert 'upload_id' not in tracer.spans[0].tags


# ---------------------------------------------------------------------------
# Upload -> receipt -> completion proposal
# ---------------------------------------------------------------------------


def one_row_pages_delivery(delivery, **overrides):
    """A delivery whose file budget fits exactly one marker-bounded row per page."""
    envelope = rq_pages.page_prefix(
        run_id=delivery.run_id,
        task_id=delivery.task_id,
        record_offset=0,
        agent_hostname=AGENT_HOSTNAME,
        schema_json=None,
    )
    value = delivery.model_dump(by_alias=True)
    value['limits'].update(maxFileBytes=len(envelope) + len(rq_pages.PAGE_SUFFIX) + 22, maxSchemaBytes=1)
    value.update(overrides)
    return rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(value)


@pytest.mark.parametrize('scan', [True, False])
def test_pages_flow_through_independent_requests_into_the_completion_proposal(scan, sessionless_delivery):
    delivery = one_row_pages_delivery(sessionless_delivery, scanSensitiveData=scan)
    creds = rq_upload.resolve_upload_credentials(delivery, time.monotonic())
    intake = SessionlessIntake(canonical_bytes=lambda page: page.source_bytes + 100)
    stats = rq_contract.RemoteQueryRunStats()
    writer = rq_pages.SourcePageWriter(delivery, creds, intake, descriptor(), lambda: None, stats)
    for text in ('first', 'second', 'third'):
        writer.add_row([string_cell(text)])
    proposal = writer.finish()

    assert len(intake.pages) == 3
    assert [page.batch_index for page, _, _ in intake.pages] == [0, 1, 2]
    assert [page.record_offset for page, _, _ in intake.pages] == [0, 1, 2]
    expected_descriptor = json.loads(rq_contract.descriptor_request_bytes(descriptor()))
    for page, metadata, payload in intake.pages:
        # Every independent request repeats the whole descriptor and carries only the frozen fields.
        assert list(metadata) == [
            'task_id',
            'crawl_id',
            'page_index',
            'record_offset',
            'source_bytes',
            'source_rows',
            'scan_sensitive_data',
            'descriptor',
        ]
        assert metadata['task_id'] == 'task-1'
        assert metadata['crawl_id'] == 'crawl-1'
        assert metadata['scan_sensitive_data'] is scan
        assert metadata['descriptor'] == expected_descriptor
        assert (metadata['page_index'], metadata['record_offset']) == (page.batch_index, page.record_offset)
        assert (metadata['source_bytes'], metadata['source_rows']) == (len(payload), 1)
    assert [payload for _, _, payload in intake.pages] == [
        csv_record([json.dumps(text).encode()]) for text in ('first', 'second', 'third')
    ]

    # The proposal: ids in page order, canonical totals from the receipts, no scan claim.
    assert list(proposal) == ['protocol', 'objectIds', 'pageCount', 'totalRows', 'totalBytes']
    assert proposal['protocol'] == 'sessionless-v1'
    assert proposal['objectIds'] == intake.object_ids
    assert proposal['pageCount'] == 3
    assert proposal['totalRows'] == 3
    assert proposal['totalBytes'] == sum(len(payload) + 100 for _, _, payload in intake.pages)
    assert (stats.pages_emitted, stats.rows_emitted, stats.bytes_emitted) == (3, 3, proposal['totalBytes'])


def test_native_record_framing_without_row_bounds_uploads_through_the_same_protocol(
    sessionless_delivery, sessionless_creds
):
    """The Postgres-style caller hands record ends without final-size bounds to the shared uploader."""
    intake = SessionlessIntake()
    stats = rq_contract.RemoteQueryRunStats()
    uploader = rq_pages.PageUploader(sessionless_delivery, sessionless_creds, intake, descriptor(), lambda: None, stats)
    buffer = bytearray(b'"a"\n"b"\n"c"\n')
    assert uploader.upload(buffer, [4, 8, 12]) == (3, 12)
    proposal = uploader.finalize()

    ((page, _, payload),) = intake.pages
    assert (page.batch_index, page.record_offset, page.rows, payload) == (0, 0, 3, bytes(buffer))
    assert proposal['objectIds'] == intake.object_ids
    assert (proposal['pageCount'], proposal['totalRows'], proposal['totalBytes']) == (1, 3, 12)


def test_split_after_a_too_large_rejection_keeps_one_object_id_per_logical_page(
    sessionless_delivery, sessionless_creds
):
    def reject_wide_pages(page):
        if page.rows > 2:
            return rq_contract.RemoteQueryFailure(
                rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake would exceed the page cap'
            )
        return None

    intake = SessionlessIntake(put_failure=reject_wide_pages)
    writer = make_writer(sessionless_delivery, sessionless_creds, intake)
    for text in ('a', 'b', 'c', 'd'):
        writer.add_row([string_cell(text)])
    proposal = writer.finish()

    assert [(page.batch_index, page.rows) for page, _, _ in intake.attempts] == [(0, 4), (0, 2), (1, 2)]
    assert proposal['pageCount'] == 2
    assert len(proposal['objectIds']) == 2
    assert proposal['totalRows'] == 4


def test_empty_result_without_a_schema_posts_nothing_and_proposes_zero_references(
    sessionless_delivery, sessionless_creds
):
    intake = SessionlessIntake()
    proposal = make_writer(sessionless_delivery, sessionless_creds, intake).finish()
    assert intake.attempts == []
    assert proposal == {'protocol': 'sessionless-v1', 'objectIds': [], 'pageCount': 0, 'totalRows': 0, 'totalBytes': 0}


def test_empty_result_with_a_schema_sends_the_descriptor_and_an_empty_source_as_one_reference(
    sessionless_delivery, sessionless_creds
):
    intake = SessionlessIntake(canonical_bytes=lambda page: 40)
    proposal = make_writer(sessionless_delivery, sessionless_creds, intake, include_schema=True).finish()

    ((page, metadata, payload),) = intake.pages
    assert payload == b''
    assert (page.batch_index, page.record_offset, page.rows, page.source_bytes) == (0, 0, 0, 0)
    assert metadata['descriptor']['include_schema'] is True
    assert proposal['pageCount'] == 1
    assert len(proposal['objectIds']) == 1
    assert (proposal['totalRows'], proposal['totalBytes']) == (0, 40)


@pytest.mark.parametrize(
    'receipt',
    [
        lambda page: {k: v for k, v in page_receipt(page).items() if k != 'object_id'},
        lambda page: {k: v for k, v in page_receipt(page).items() if k != 'bytes'},
        lambda page: page_receipt(page, scan_policy='its-stable-v1'),  # no unknown fields
        lambda page: page_receipt(page, protocol='sessionless-v2'),  # wrong protocol
        lambda page: {k: v for k, v in page_receipt(page).items() if k != 'protocol'},
        lambda page: page_receipt(page, object_id='not-a-uuid'),
        lambda page: page_receipt(page, object_id=str(uuid.uuid4()).upper()),
        lambda page: page_receipt(page, object_id=str(uuid.uuid4()) + '/../x'),
        lambda page: page_receipt(page, object_id=None),
        lambda page: page_receipt(page, page_index=page.batch_index + 1),
        lambda page: page_receipt(page, record_offset=page.record_offset + 1),
        lambda page: page_receipt(page, rows=page.rows + 1),
        lambda page: page_receipt(page, rows=True),
        lambda page: page_receipt(page, rows=str(page.rows)),
        lambda page: page_receipt(page, bytes=-1),
        lambda page: page_receipt(page, bytes=1025),  # beyond maxFileBytes
        lambda page: page_receipt(page, bytes=1.5),
        lambda page: [page_receipt(page)],
    ],
)
def test_malformed_or_mismatched_receipts_fail_the_run(receipt, sessionless_delivery, sessionless_creds):
    intake = SessionlessIntake(receipt_override=receipt)
    writer = make_writer(sessionless_delivery, sessionless_creds, intake)
    writer.add_row([string_cell('a')])
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.finish()
    assert failure.value.code == 'invalid_receipt'


def test_a_receipt_failure_does_not_echo_the_server_value(sessionless_delivery, sessionless_creds):
    intake = SessionlessIntake(receipt_override=lambda page: page_receipt(page, object_id='secret-looking-value'))
    writer = make_writer(sessionless_delivery, sessionless_creds, intake)
    writer.add_row([string_cell('a')])
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.finish()
    assert 'secret-looking-value' not in failure.value.message


def test_accepted_canonical_bytes_are_capped_by_the_result_limit(sessionless_delivery, sessionless_creds):
    delivery = bounded(one_row_pages_delivery(sessionless_delivery), maxResultBytes=200)
    # Each accepted page reports 120 canonical bytes, so the second page crosses maxResultBytes=200.
    intake = SessionlessIntake(canonical_bytes=lambda page: 120)
    writer = make_writer(delivery, sessionless_creds, intake)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        for _ in range(3):
            writer.add_row([cell(b'"x"', 12)])
        writer.finish()
    assert failure.value.code == 'max_result_bytes_exceeded'


def test_page_count_is_capped_by_max_pages(sessionless_delivery, sessionless_creds):
    delivery = bounded(one_row_pages_delivery(sessionless_delivery), maxPages=1)
    intake = SessionlessIntake()
    writer = make_writer(delivery, sessionless_creds, intake)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.add_row([cell(b'"x"', 12)])
        writer.add_row([cell(b'"x"', 12)])
        writer.finish()
    assert failure.value.code == 'max_pages_exceeded'
    assert len(intake.pages) == 1


def test_a_descriptor_beyond_its_cap_is_rejected_before_any_request(sessionless_delivery, sessionless_creds):
    wide = descriptor(columns=[('c%04d' % index, 'v' * 1000, 'string') for index in range(1024)])
    assert len(rq_contract.descriptor_request_bytes(wide)) > rq_contract.REMOTE_QUERY_SESSIONLESS_MAX_DESCRIPTOR_BYTES
    delivery = bounded(sessionless_delivery, maxColumns=1024)
    intake = SessionlessIntake()
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_pages.PageUploader(
            delivery, sessionless_creds, intake, wide, lambda: None, rq_contract.RemoteQueryRunStats()
        )
    assert failure.value.code == 'max_schema_bytes_exceeded'
    assert intake.attempts == []


# ---------------------------------------------------------------------------
# Completion proposal bounds
# ---------------------------------------------------------------------------


def proposal_input(count=2, **overrides):
    value = {
        'protocol': 'sessionless-v1',
        'objectIds': [str(uuid.uuid4()) for _ in range(count)],
        'pageCount': count,
        'totalRows': 5,
        'totalBytes': 50,
    }
    value.update(overrides)
    return value


def test_the_completion_proposal_has_the_exact_wire_shape():
    ids = [str(uuid.uuid4()) for _ in range(2)]
    proposal = rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(objectIds=ids))
    assert proposal.wire() == {
        'protocol': 'sessionless-v1',
        'objectIds': ids,
        'pageCount': 2,
        'totalRows': 5,
        'totalBytes': 50,
    }


@pytest.mark.parametrize(
    'overrides',
    [
        {'objectIds': ['x' * 36, 'y' * 36]},
        {'objectIds': ['9f1b7c2e-0000-4000-8000-000000000000'] * 2},  # duplicate references
        {'pageCount': 3},  # one reference per logical page
        {'protocol': 'sessionless-v2'},
        {'totalRows': -1},
        {'totalBytes': True},
        {'totalRows': '5'},
        {'scanned': True},  # no scan stamp
        {'sts-scanned': True},
    ],
)
def test_the_completion_proposal_rejects_malformed_shapes(overrides):
    with pytest.raises(ValidationError):
        rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(**overrides))


def test_the_completion_proposal_is_capped_at_128_references():
    rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(count=128))
    with pytest.raises(ValidationError):
        rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(count=129))


def test_an_empty_proposal_must_report_zero_totals():
    empty = {'objectIds': [], 'pageCount': 0, 'totalRows': 0, 'totalBytes': 0}
    assert rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(**empty)).wire()['objectIds'] == []
    for field in ('totalRows', 'totalBytes'):
        with pytest.raises(ValidationError):
            rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(**{**empty, field: 1}))


def test_an_oversized_serialized_proposal_fails_closed(monkeypatch):
    proposal = rq_contract.SessionlessCompletionReceipt.model_validate(proposal_input(count=128))
    assert (
        len(rq_contract.canonical_json_bytes(proposal.wire()))
        < rq_contract.REMOTE_QUERY_SESSIONLESS_MAX_COMPLETION_BYTES
    )
    monkeypatch.setattr(rq_contract, 'REMOTE_QUERY_SESSIONLESS_MAX_COMPLETION_BYTES', 100)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        proposal.wire()
    assert failure.value.code == 'invalid_receipt'


def test_a_schema_result_cannot_complete_without_a_page(sessionless_delivery, sessionless_creds):
    protocol = rq_pages.SessionlessUploadProtocol(
        sessionless_delivery, sessionless_creds, SessionlessIntake(), descriptor(include_schema=True)
    )
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        protocol.complete(rq_contract.RemoteQueryRunStats())
    assert failure.value.code == 'invalid_receipt'


# ---------------------------------------------------------------------------
# HTTP framing against a real loopback intake
# ---------------------------------------------------------------------------


def split_multipart(content_type, body):
    """Split a multipart/form-data body into [(headers, content)] by its declared boundary."""
    assert content_type.startswith('multipart/form-data; boundary=')
    delimiter = b'--' + content_type.split('boundary=', 1)[1].encode()
    assert body.startswith(delimiter + b'\r\n')
    assert body.endswith(b'\r\n' + delimiter + b'--\r\n')
    inner = body[len(delimiter) + 2 : -(len(delimiter) + 6)]
    parts = inner.split(b'\r\n' + delimiter + b'\r\n')
    result = []
    for part in parts:
        raw_headers, content = part.split(b'\r\n\r\n', 1)
        headers = dict(line.decode().split(': ', 1) for line in raw_headers.split(b'\r\n'))
        result.append((headers, content))
    return result


class LoopbackIntake:
    """A real HTTP server answering the sessionless page route like intake's receipt contract."""

    def __init__(self, fail_first=0):
        self.fail_first = fail_first
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers['Content-Length'])
                body = self.rfile.read(length)
                outer.requests.append(
                    {
                        'path': self.path,
                        'headers': dict(self.headers),
                        'body': body,
                        'transfer_encoding': self.headers.get('Transfer-Encoding'),
                    }
                )
                if len(outer.requests) <= outer.fail_first:
                    self.send_response(503)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                parts = split_multipart(self.headers['Content-Type'], body)
                metadata = json.loads(parts[0][1])
                receipt = json.dumps(
                    {
                        'protocol': 'sessionless-v1',
                        'object_id': str(uuid.uuid4()),
                        'page_index': metadata['page_index'],
                        'record_offset': metadata['record_offset'],
                        'rows': metadata['source_rows'],
                        'bytes': len(parts[1][1]) + 7,
                    }
                ).encode()
                self.send_response(201)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(receipt)))
                self.end_headers()
                self.wfile.write(receipt)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)

    @property
    def base_url(self):
        return 'http://127.0.0.1:{}/api/unstable/its-agent-intake'.format(self.server.server_address[1])

    def __enter__(self):
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        return self

    def __exit__(self, *exc_info):
        self.server.shutdown()
        self.server.server_close()


def test_pages_stream_as_metadata_first_multipart_with_an_exact_content_length(sessionless_delivery):
    # A source containing CRLF and the multipart dashes must not disturb the framing.
    row = 'line\r\n--not-a-boundary'
    with LoopbackIntake() as intake:
        delivery = rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(
            {**sessionless_delivery.model_dump(by_alias=True), 'baseUrl': intake.base_url + '/'}
        )
        creds = rq_upload.UploadCredentials(
            intake.base_url + '/',
            '',
            'test-api-key',
            'test-intake',
            trace_context=rq_contract.RemoteQueryTraceContext.model_validate(
                {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 1}
            ),
        )
        writer = make_writer(delivery, creds, rq_upload.RequestsUploadClient())
        writer.add_row([string_cell(row)])
        proposal = writer.finish()

    (request,) = intake.requests
    assert request['path'] == '/api/unstable/its-agent-intake/ingest/v1/pages'
    assert request['transfer_encoding'] is None
    assert int(request['headers']['Content-Length']) == len(request['body'])
    assert request['headers']['dd-api-key'] == 'test-api-key'
    assert request['headers']['test-drive-test-intake'] == '1'
    assert request['headers']['x-datadog-trace-id'] == TRACE_ID
    assert 'Content-Encoding' not in request['headers']
    metadata_part, source_part = split_multipart(request['headers']['Content-Type'], request['body'])
    assert metadata_part[0] == {
        'Content-Disposition': 'form-data; name="metadata"',
        'Content-Type': 'application/json',
    }
    assert source_part[0] == {
        'Content-Disposition': 'form-data; name="source"',
        'Content-Type': rq_upload.REMOTE_QUERY_SOURCE_PAGE_CONTENT_TYPE,
    }
    metadata = json.loads(metadata_part[1])
    assert metadata['source_bytes'] == len(source_part[1])
    assert source_part[1] == csv_record([rq_contract.canonical_json_bytes(row)])
    assert proposal['pageCount'] == 1
    assert proposal['totalBytes'] == len(source_part[1]) + 7


def test_a_transient_failure_resends_the_same_page_and_keeps_only_the_accepted_object(
    monkeypatch, sessionless_delivery
):
    monkeypatch.setattr(rq_upload.time, 'sleep', lambda _: None)
    with LoopbackIntake(fail_first=2) as intake:
        delivery = rq_contract.RemoteQuerySessionlessResultDelivery.model_validate(
            {**sessionless_delivery.model_dump(by_alias=True), 'baseUrl': intake.base_url}
        )
        creds = rq_upload.resolve_upload_credentials(delivery, 0.0)
        creds = rq_upload.UploadCredentials(creds.base_url, '', 'test-api-key', None, wall_deadline=None)
        writer = make_writer(delivery, creds, rq_upload.RequestsUploadClient())
        writer.add_row([string_cell('a')])
        proposal = writer.finish()

    # Three requests carried one logical page, byte-identical on every retry; one id is proposed.
    assert len(intake.requests) == 3
    assert len({request['body'] for request in intake.requests}) == 1
    assert proposal['pageCount'] == 1
    assert len(proposal['objectIds']) == 1


def test_page_requests_use_one_post_and_no_session_routes(monkeypatch, sessionless_delivery, sessionless_creds):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url))
        body = data.read()
        metadata = json.loads(split_multipart(headers['Content-Type'], body)[0][1])
        receipt = {
            'protocol': 'sessionless-v1',
            'object_id': str(uuid.uuid4()),
            'page_index': metadata['page_index'],
            'record_offset': metadata['record_offset'],
            'rows': metadata['source_rows'],
            'bytes': 3,
        }
        return SimpleNamespace(status_code=201, content=json.dumps(receipt).encode())

    monkeypatch.setattr(requests.Session, 'request', as_session_request(request))
    writer = make_writer(sessionless_delivery, sessionless_creds, rq_upload.RequestsUploadClient(), include_schema=True)
    writer.add_row([string_cell('a')])
    writer.finish()
    assert calls == [('POST', BASE_URL + '/ingest/v1/pages')]


@pytest.mark.parametrize('status', [200, 202])
def test_only_http_201_accepts_a_page(monkeypatch, sessionless_creds, status):
    import requests

    monkeypatch.setattr(
        requests.Session,
        'request',
        as_session_request(lambda *args, **kwargs: SimpleNamespace(status_code=status, content=b'{}')),
    )
    page = rq_contract.SourcePageUploadMetadata(0, 0, 1, 1)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().post_sessionless_page(sessionless_creds, page, b'{}', io.BytesIO(b'x'))
    assert failure.value.code == 'invalid_receipt'


def test_terminal_too_large_rejection_maps_to_its_failure_code(monkeypatch, sessionless_creds):
    import requests

    body = b'{"error":{"code":"final_page_too_large"}}'
    monkeypatch.setattr(
        requests.Session,
        'request',
        as_session_request(lambda *args, **kwargs: SimpleNamespace(status_code=413, content=body)),
    )
    page = rq_contract.SourcePageUploadMetadata(0, 0, 1, 1)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.RequestsUploadClient().post_sessionless_page(sessionless_creds, page, b'{}', io.BytesIO(b'x'))
    assert failure.value.code == rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE


def test_the_multipart_body_rewinds_for_retries_without_buffering_the_source():
    payload = bytes(range(256)) * 40
    body = rq_upload.sessionless_multipart_body('b', b'{"k":1}', io.BytesIO(payload), len(payload))
    whole = body.read()
    assert len(whole) == body.length
    body.seek(0)
    chunks = []
    while chunk := body.read(333):
        chunks.append(chunk)
    assert b''.join(chunks) == whole
    # A seek into the middle of the source resumes at the right source byte.
    middle = body.length - len(payload) // 2 - 9
    body.seek(middle)
    assert body.read() == whole[middle:]
    assert body.seek(0, 2) == body.length


def test_a_source_shorter_than_declared_fails_closed():
    body = rq_upload.sessionless_multipart_body('b', b'{}', io.BytesIO(b'ab'), 5)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        body.read()
    assert failure.value.code == 'upload_failed'
