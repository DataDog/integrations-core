# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import csv
import hashlib
import io
import json
import logging
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from datadog_checks.base.utils import remote_queries as rq

AGENT_HOSTNAME = 'rq-proof-agent-a'

# A validated tracing carrier: distinct sentinel values so the no-echo assertions below can
# always find an untouched sentinel in the request whatever the case mutates.
TRACE_ID = '1234567890123456789'
PARENT_ID = '9876543210987654321'


@pytest.fixture
def delivery():
    return rq.RemoteQueryResultDelivery.model_validate(
        {
            'runId': 'run-1',
            'taskId': 'task-1',
            'artifactVersion': 1,
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


def descriptor(columns=(('value', 'text', 'string'),), include_schema=False, agent_hostname=AGENT_HOSTNAME):
    return rq.RemoteQueryUploadDescriptor(
        format_version=rq.REMOTE_QUERY_DESCRIPTOR_FORMAT_VERSION,
        include_schema=include_schema,
        agent_hostname=agent_hostname,
        columns=[
            rq.RemoteQueryDescriptorColumn(column_name=name, vendor_data_type=vendor, logical_type=logical)
            for name, vendor, logical in columns
        ],
    )


def string_cell(text):
    """One encoded string cell: its canonical JSON token and the redactable-leaf final bound."""
    token = json.dumps(text, ensure_ascii=False).encode('utf-8')
    return rq.EncodedCell(token, rq.redactable_leaf_final_bound(token))


def cell(token, final_bound):
    return rq.EncodedCell(token, final_bound)


def csv_field(token):
    """The expected CSV field for one token, computed independently of the producer's framing."""
    if b'"' in token or b',' in token or b'\n' in token:
        return b'"' + token.replace(b'"', b'""') + b'"'
    return token


def csv_record(tokens):
    return b','.join(csv_field(token) for token in tokens) + b'\n'


def envelope_bound(delivery, record_offset, schema_json=None):
    """The final-JSON envelope bound for one page: intake's envelope plus the closing bytes."""
    return len(
        rq.page_prefix(
            run_id=delivery.run_id,
            task_id=delivery.task_id,
            record_offset=record_offset,
            agent_hostname=AGENT_HOSTNAME,
            schema_json=schema_json,
        )
    ) + len(rq.PAGE_SUFFIX)


class Uploads:
    """A fake intake: registers the descriptor and returns intake-derived page receipts."""

    def __init__(
        self,
        final_growth=0,
        put_failure=None,
        receipt_bytes=None,
        receipt_override=None,
        descriptor_response=None,
        finalize_response=None,
    ):
        self.final_growth = final_growth
        self.put_failure = put_failure
        self.receipt_bytes = receipt_bytes
        self.receipt_override = receipt_override
        self.descriptor_response = descriptor_response
        self.finalize_response = finalize_response
        self.descriptor_bodies = []
        self.put_attempts = []
        self.pages = []
        self.finalize_calls = 0
        self.abort_calls = 0

    def register_descriptor(self, creds, body):
        self.descriptor_bodies.append(body)
        if self.descriptor_response is not None:
            return self.descriptor_response
        # Intake's pinned receipt: the registered descriptor's identity plus the sha256 over
        # the canonical registration bytes.
        registered = json.loads(body)
        return {
            'upload_id': creds.upload_id,
            'format_version': registered['format_version'],
            'include_schema': registered['include_schema'],
            'columns': len(registered['columns']),
            'sha256': hashlib.sha256(body).hexdigest(),
        }

    def final_bytes_for(self, page):
        if self.receipt_bytes is not None:
            return self.receipt_bytes(page) + self.final_growth
        return page.source_bytes + self.final_growth

    def put_source_page(self, creds, page, body):
        payload = body.read()
        self.put_attempts.append((page, payload))
        if self.put_failure is not None:
            failure = self.put_failure(page)
            if failure is not None:
                raise failure
        self.pages.append((page, payload))
        if self.receipt_override is not None:
            return self.receipt_override(page)
        return {
            'batch_index': page.batch_index,
            'key': 'agent-intake-test/pages/{}.json'.format(page.batch_index),
            'record_offset': page.record_offset,
            'bytes': self.final_bytes_for(page),
            'rows': page.rows,
            'sha256': hashlib.sha256('final-metadata-{}'.format(page.batch_index).encode('utf-8')).hexdigest(),
        }

    def finalize_run(self, creds):
        self.finalize_calls += 1
        if self.finalize_response is not None:
            return self.finalize_response
        return {
            'upload_id': creds.upload_id,
            'page_count': len(self.pages),
            'total_rows': sum(page.rows for page, _ in self.pages),
            'total_bytes': sum(self.final_bytes_for(page) for page, _ in self.pages),
        }

    def abort(self, creds):
        self.abort_calls += 1


def bounded_delivery(delivery, **limits):
    value = delivery.model_dump(by_alias=True)
    value['limits'].update(limits)
    return rq.RemoteQueryResultDelivery.model_validate(value)


class AdvancingUploads(Uploads):
    """Uploads fake whose calls advance a mutable clock, each by a fixed wall."""

    def __init__(self, clock, put_source_page_seconds, finalize_seconds):
        super().__init__()
        self._clock = clock
        self._put_source_page_seconds = put_source_page_seconds
        self._finalize_seconds = finalize_seconds

    def put_source_page(self, creds, page, body):
        self._clock['now'] += self._put_source_page_seconds
        return super().put_source_page(creds, page, body)

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


def test_source_page_writer_upload_inside_encode_is_excluded_from_encode(delivery, creds):
    # finish() runs inside the encode phase, so the final page's upload and the finalize
    # suspend the encode accumulation instead of leaking into it; the enclosing encode
    # segment between the two (the page receipt verification) stays in the encode bucket.
    clock = {'now': 0.0}
    stats = rq.RemoteQueryRunStats()
    uploads = AdvancingUploads(clock, put_source_page_seconds=0.5, finalize_seconds=0.375)
    timings = rq.RemoteQueryProducerTimings(0.0, clock=lambda: clock['now'])
    writer = rq.SourcePageWriter(delivery, creds, uploads, descriptor(), lambda: None, stats, timings)
    with timings.phase('encode_and_page_build'):
        writer.add_row([string_cell('1')])
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


def make_writer(delivery, creds, uploads, source_descriptor=None, include_schema=False):
    return rq.SourcePageWriter(
        delivery,
        creds,
        uploads,
        source_descriptor if source_descriptor is not None else descriptor(include_schema=include_schema),
        lambda: None,
        rq.RemoteQueryRunStats(),
    )


# ---------------------------------------------------------------------------
# Descriptor registration
# ---------------------------------------------------------------------------


def test_descriptor_request_bytes_are_canonical_and_deterministic():
    def build():
        return descriptor(
            columns=(('value', 'text', 'string'), ('payload', 'bytea', 'binary')),
            include_schema=True,
        )

    expected = (
        b'{"format_version":"csv-json-cell-v1","include_schema":true,'
        b'"agent_hostname":"rq-proof-agent-a","columns":['
        b'{"column_name":"value","vendor_data_type":"text","logical_type":"string"},'
        b'{"column_name":"payload","vendor_data_type":"bytea","logical_type":"binary"}]}'
    )
    assert rq.descriptor_request_bytes(build()) == expected
    # A fresh construction produces a byte-identical registration body for retries.
    assert rq.descriptor_request_bytes(build()) == expected


@pytest.mark.parametrize(
    'columns,include_schema,agent_hostname',
    [
        ((), True, AGENT_HOSTNAME),  # no columns
        ((('value', 'text', 'string'), ('value', 'int4', 'integer')), False, AGENT_HOSTNAME),  # duplicate names
        ((('value', 'text', 'unknown_family'),), False, AGENT_HOSTNAME),  # closed logical-type set
        ((('value', 'text', 'string'),), False, ''),  # empty hostname
        ((('', 'text', 'string'),), False, AGENT_HOSTNAME),  # empty column name
        ((('value', '', 'string'),), False, AGENT_HOSTNAME),  # empty vendor type
    ],
)
def test_descriptor_rejects_malformed_columns(columns, include_schema, agent_hostname):
    with pytest.raises(ValidationError):
        descriptor(columns=columns, include_schema=include_schema, agent_hostname=agent_hostname)


def test_descriptor_accepts_every_closed_logical_type():
    columns = tuple(('c_{}'.format(logical), 'text', logical) for logical in rq.REMOTE_QUERY_LOGICAL_TYPES)
    upload_descriptor = descriptor(columns=columns)
    assert tuple(column.logical_type for column in upload_descriptor.columns) == rq.REMOTE_QUERY_LOGICAL_TYPES


def test_descriptor_request_and_schema_bytes_emit_valid_non_ascii_as_raw_utf8():
    """Intake's canonical encoder emits valid non-ASCII as raw UTF-8, never ``\\uXXXX`` escapes.

    The registration body and the schema bytes it derives from the descriptor must spell
    non-ASCII identically, because intake checksums exactly these canonical bytes.
    """

    def build():
        return descriptor(
            columns=(('colonné', 'véndor', 'string'),),
            include_schema=True,
            agent_hostname='agent-hôte',
        )

    body = rq.descriptor_request_bytes(build())
    assert body == (
        b'{"format_version":"csv-json-cell-v1","include_schema":true,'
        b'"agent_hostname":"agent-h\xc3\xb4te","columns":'
        b'[{"column_name":"colonn\xc3\xa9","vendor_data_type":"v\xc3\xa9ndor","logical_type":"string"}]}'
    )
    assert b'\\u' not in body
    assert rq.descriptor_request_bytes(build()) == body
    assert rq.descriptor_schema_bytes(build()) == (
        b'[{"column_name":"colonn\xc3\xa9","vendor_data_type":"v\xc3\xa9ndor"}]'
    )


@pytest.mark.parametrize(
    'columns,agent_hostname,valid',
    [
        # 255 UTF-8 bytes of a two-byte character (128 characters) pass the name limits.
        ((('a' + 'é' * 127, 'text', 'string'),), AGENT_HOSTNAME, True),
        # 256 bytes is over the byte limit even though 128 characters passes a character count.
        ((('é' * 128, 'text', 'string'),), AGENT_HOSTNAME, False),
        # The vendor-type limit is 1024 bytes.
        ((('value', 'é' * 512, 'string'),), AGENT_HOSTNAME, True),
        ((('value', 'a' + 'é' * 512, 'string'),), AGENT_HOSTNAME, False),
        ((('value', 'text', 'string'),), 'a' + 'é' * 127, True),
        ((('value', 'text', 'string'),), 'é' * 128, False),
    ],
)
def test_descriptor_limits_bound_utf8_bytes_not_character_counts(columns, agent_hostname, valid):
    """The server limits are byte limits: multibyte text within the character count but over
    the byte count is rejected, and text at exactly the byte boundary passes.
    """
    if valid:
        descriptor(columns=columns, agent_hostname=agent_hostname)
    else:
        with pytest.raises(ValidationError):
            descriptor(columns=columns, agent_hostname=agent_hostname)


@pytest.mark.parametrize(
    'columns,agent_hostname',
    [
        ((('a\ud800', 'text', 'string'),), AGENT_HOSTNAME),
        ((('value', 'a\ud800', 'string'),), AGENT_HOSTNAME),
        ((('value', 'text', 'string'),), 'a\ud800'),
    ],
)
def test_descriptor_text_that_cannot_encode_as_utf8_fails_validation(columns, agent_hostname):
    """A lone surrogate cannot ride the UTF-8 wire, so it is rejected at validation instead
    of crashing the canonical JSON encoding mid-upload."""
    with pytest.raises(ValidationError):
        descriptor(columns=columns, agent_hostname=agent_hostname)


def test_descriptor_registration_happens_once_before_any_row(delivery, creds):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('a')])
    writer.finish()
    assert uploads.descriptor_bodies == [rq.descriptor_request_bytes(descriptor())]


def descriptor_receipt(body, **overrides):
    """Intake's pinned descriptor receipt for one registration body, with field overrides."""
    registered = json.loads(body)
    receipt = {
        'upload_id': 'upload-1',
        'format_version': registered['format_version'],
        'include_schema': registered['include_schema'],
        'columns': len(registered['columns']),
        'sha256': hashlib.sha256(body).hexdigest(),
    }
    receipt.update(overrides)
    return receipt


def test_descriptor_receipt_confirms_the_registration_exactly():
    upload_descriptor = descriptor(columns=(('value', 'text', 'string'),), include_schema=True)
    body = rq.descriptor_request_bytes(upload_descriptor)
    rq.verify_descriptor_response(descriptor_receipt(body), 'upload-1', upload_descriptor, body)


@pytest.mark.parametrize(
    'field,bad',
    [
        ('upload_id', None),  # missing
        ('upload_id', 123),  # mistyped
        ('upload_id', 'other-upload'),  # mismatched
        ('format_version', None),
        ('format_version', 2),
        ('format_version', 'csv-json-cell-v2'),
        ('include_schema', None),
        ('include_schema', 0),
        ('include_schema', False),  # flipped against the registered descriptor
        ('columns', None),
        ('columns', '1'),
        ('columns', 2),
        ('sha256', None),
        ('sha256', 'A' * 64),  # the pinned receipt is lowercase hex
        ('sha256', hashlib.sha256(b'other canonical descriptor bytes').hexdigest()),
    ],
)
def test_descriptor_receipt_rejects_missing_mistyped_or_mismatched_fields(field, bad):
    upload_descriptor = descriptor(columns=(('value', 'text', 'string'),), include_schema=True)
    body = rq.descriptor_request_bytes(upload_descriptor)
    receipt = descriptor_receipt(body)
    if bad is None:
        del receipt[field]
    else:
        receipt[field] = bad
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.verify_descriptor_response(receipt, 'upload-1', upload_descriptor, body)
    assert failure.value.code == 'invalid_receipt'


def test_descriptor_receipt_allows_no_keys_beyond_the_pinned_five():
    """The receipt's key set is exactly the five pinned keys: an unknown extra key — even
    alongside five matching values — is unknown intake behavior and fails closed."""
    upload_descriptor = descriptor(columns=(('value', 'text', 'string'),), include_schema=True)
    body = rq.descriptor_request_bytes(upload_descriptor)
    receipt = descriptor_receipt(body)
    rq.verify_descriptor_response(receipt, 'upload-1', upload_descriptor, body)
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        # The legacy provisional echo key is exactly the kind of drift the pinned set rejects.
        rq.verify_descriptor_response(
            {**receipt, 'descriptor_sha256': hashlib.sha256(body).hexdigest()},
            'upload-1',
            upload_descriptor,
            body,
        )
    assert failure.value.code == 'invalid_receipt'


def test_descriptor_receipt_rejects_a_non_object_response():
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.verify_descriptor_response(None, 'upload-1', descriptor(), b'{}')
    assert failure.value.code == 'invalid_receipt'


def test_writer_gates_rows_on_a_descriptor_receipt_that_confirms_the_registration(delivery, creds):
    """The registration gate fails closed before any row flows or the run finalizes."""
    uploads = Uploads(descriptor_response={'upload_id': creds.upload_id, 'sha256': '0' * 64})
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        make_writer(delivery, creds, uploads)
    assert failure.value.code == 'invalid_receipt'
    assert len(uploads.descriptor_bodies) == 1
    assert uploads.pages == []
    assert uploads.finalize_calls == 0


# ---------------------------------------------------------------------------
# Source-page CSV framing
# ---------------------------------------------------------------------------


def test_source_pages_frame_canonical_json_cell_tokens_as_csv(delivery, creds):
    columns = (
        ('null_value', 'text', 'string'),
        ('empty_text', 'text', 'string'),
        ('quoted', 'text', 'string'),
        ('number', 'numeric', 'decimal'),
        ('comma_value', 'text', 'string'),
    )
    tokens = [b'null', b'""', b'"q"', b'123.45', b'"a,b"']
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads, descriptor(columns=columns))
    writer.add_row([cell(token, rq.redactable_leaf_final_bound(token)) for token in tokens])
    result = writer.finish()

    # The pinned dialect: comma delimiter, '"' doubled, LF record endings, no header row.
    (page, payload) = uploads.pages[0]
    assert payload == b'null,"""""","""q""",123.45,"""a,b"""\n' == csv_record(tokens)
    # An independent CSV reader recovers exactly the canonical tokens, cell by cell.
    (fields,) = list(csv.reader([payload.decode('utf-8')]))
    assert [field.encode('utf-8') for field in fields] == tokens
    assert page.batch_index == 0
    assert page.record_offset == 0
    assert page.source_bytes == len(payload)
    assert page.rows == 1
    assert page.sha256_hex == hashlib.sha256(payload).hexdigest()
    assert result['pageCount'] == 1


def test_source_pages_reject_tokens_that_would_corrupt_the_csv_record():
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.frame_csv_record([b'"ok"', b'with\rraw-cr'])
    assert failure.value.code == 'unsupported_value'


def test_string_cell_tokens_emit_valid_non_ascii_as_raw_utf8():
    """A canonical string token spells valid non-ASCII as raw UTF-8, never ``\\uXXXX`` escapes."""
    token, final_bound = rq.string_cell_token('héllo')
    assert token == b'"h\xc3\xa9llo"'
    assert b'\\u' not in token
    # A short multibyte leaf still bounds to the fixed redaction marker; a longer one keeps
    # its own raw UTF-8 token bytes.
    assert final_bound == len(rq.REMOTE_QUERY_REDACTED_MARKER_TOKEN)
    long_token, long_bound = rq.string_cell_token('héllo ' + 'é' * 64)
    assert long_token == b'"h\xc3\xa9llo ' + b'\xc3\xa9' * 64 + b'"'
    assert long_bound == len(long_token)


def test_string_cell_tokens_fail_closed_on_text_that_cannot_encode_as_utf8():
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.string_cell_token('a\ud800')
    assert failure.value.code == 'unsupported_value'


def test_redactable_leaf_bound_reserves_the_marker_for_short_number_tokens():
    """Intake scans number leaves too and substitutes the fixed marker string token for any
    match, so a short number's final bound is the marker size exactly like a short string's;
    a number already longer than the marker keeps its own token bytes.
    """
    marker = len(rq.REMOTE_QUERY_REDACTED_MARKER_TOKEN)
    # Short integer and decimal/float tokens all reserve the marker size.
    for token in (b'1', b'-42', b'0', b'0.1', b'1e+16', b'-0', b'123.45'):
        assert rq.redactable_leaf_final_bound(token) == marker
    long_token = b'12345678901234567890.123456789'
    assert rq.redactable_leaf_final_bound(long_token) == len(long_token)


def test_source_pages_frame_non_ascii_cells_as_raw_utf8_csv(delivery, creds):
    columns = (('text_value', 'text', 'string'), ('note_value', 'text', 'string'))
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads, descriptor(columns=columns))
    writer.add_row([string_cell('héllo'), string_cell('a,bé')])
    result = writer.finish()

    # Raw UTF-8 tokens ride the CSV unchanged: only JSON framing characters (quote, comma)
    # trigger CSV quoting, and multibyte sequences never contain ASCII bytes.
    (page, payload) = uploads.pages[0]
    assert payload == b'"""h\xc3\xa9llo""","""a,b\xc3\xa9"""\n'
    assert payload == csv_record([b'"h\xc3\xa9llo"', b'"a,b\xc3\xa9"'])
    # An independent CSV reader recovers exactly the raw UTF-8 tokens, cell by cell.
    (fields,) = list(csv.reader([payload.decode('utf-8')]))
    assert [field.encode('utf-8') for field in fields] == [b'"h\xc3\xa9llo"', b'"a,b\xc3\xa9"']
    assert page.source_bytes == len(payload)
    assert page.sha256_hex == hashlib.sha256(payload).hexdigest()
    assert result['pageCount'] == 1


# ---------------------------------------------------------------------------
# Page identity, bounds, and splitting


def test_page_prefix_emits_valid_non_ascii_as_raw_utf8():
    prefix = rq.page_prefix(
        run_id='rün-1',
        task_id='täsk-1',
        record_offset=3,
        agent_hostname='agent-hôte',
        schema_json=None,
    )
    assert prefix.startswith(b'{"contract_version":1,"crawl_id":"r\xc3\xbcn-1",')
    assert b'"task_id":"t\xc3\xa4sk-1"' in prefix
    assert b'"agent_hostname":"agent-h\xc3\xb4te"' in prefix
    assert b'"data":[' in prefix
    assert b'\\u' not in prefix


def test_page_bound_counts_column_name_key_tokens_in_canonical_utf8_bytes(delivery, creds):
    """The per-column key bound counts the canonical key token's UTF-8 bytes, exactly.

    The key ``éé`` canonicalizes to a six-byte token (its ``\\u00e9``-escaped spelling is
    fourteen bytes and its character count four), so the byte-exact row bound of 21 admits
    a second row exactly when the page budget covers two rows plus their separator: one
    byte less splits the page, and the exact budget holds both rows on one page.
    """
    columns = (('éé', 'text', 'string'),)
    key_bytes = b'"\xc3\xa9\xc3\xa9"'  # the canonical key token: six UTF-8 bytes
    row_bound = 1 + len(key_bytes) + 2 + len(rq.REMOTE_QUERY_REDACTED_MARKER_TOKEN)
    assert row_bound == 21

    def run(max_file_bytes):
        scoped = bounded_delivery(delivery, maxFileBytes=max_file_bytes, maxSchemaBytes=1)
        uploads = Uploads()
        writer = make_writer(scoped, creds, uploads, descriptor(columns=columns))
        writer.add_row([cell(b'"x"', 12)])
        writer.add_row([cell(b'"x"', 12)])
        writer.finish()
        return [page.rows for page, _ in uploads.pages]

    exact_two_rows = envelope_bound(delivery, 0) + row_bound + 1 + row_bound
    # One byte short of two byte-exact rows: a character-counted key bound (four bytes)
    # would wrongly keep both rows on one page.
    assert run(exact_two_rows - 1) == [1, 1]
    # The exact byte-exact budget holds both rows; an escaped-ASCII key bound (fourteen
    # bytes) would wrongly split here.
    assert run(exact_two_rows) == [2]


# ---------------------------------------------------------------------------


def test_pages_preserve_row_order_offsets_and_source_identity(delivery, creds):
    # One "x" row per page: key bound 7 ("value") plus 1 + 2 + 12 makes a 22-byte row bound.
    delivery = bounded_delivery(delivery, maxFileBytes=envelope_bound(delivery, 0) + 22, maxSchemaBytes=1)
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    rows = ['first', 'second', 'third']
    for row in rows:
        writer.add_row([string_cell(row)])
    result = writer.finish()

    tokens = [json.dumps(row).encode('utf-8') for row in rows]
    assert [page.batch_index for page, _ in uploads.pages] == [0, 1, 2]
    for index, (page, payload) in enumerate(uploads.pages):
        assert payload == csv_record([tokens[index]])
        assert page.record_offset == index
        assert page.source_bytes == len(payload)
        assert page.sha256_hex == hashlib.sha256(payload).hexdigest()
    assert result == {
        'uploadId': 'upload-1',
        'pageCount': 3,
        'totalRows': 3,
        'totalBytes': sum(len(csv_record([token])) for token in tokens),
    }


def test_page_bound_accounts_for_the_redaction_marker(delivery, creds):
    """A short string grows to the fixed marker when redacted, so the split uses that bound.

    Each ``"x"`` cell token is three bytes but bounds to the twelve-byte ``"[REDACTED]"``;
    with a budget that fits exactly two marker-bounded rows, a token-length bound would let a
    third row onto the page and the split would be wrong.
    """
    two_rows = envelope_bound(delivery, 0) + 2 * 22 + 1
    delivery = bounded_delivery(delivery, maxFileBytes=two_rows, maxSchemaBytes=1)
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    for _ in range(3):
        writer.add_row([cell(b'"x"', 12)])
    writer.finish()

    assert [page.rows for page, _ in uploads.pages] == [2, 1]


def test_page_bound_accounts_for_redacted_number_leaves(delivery, creds):
    """A redacted short number grows to the fixed marker, so the split uses that bound.

    Each ``1`` cell token is one byte but bounds to the twelve-byte ``"[REDACTED]"`` marker
    intake substitutes for a matched number leaf; with a budget that fits exactly two
    marker-bounded rows, a token-length bound would pack all three rows onto one page and
    lean on intake's defensive ``final_page_too_large`` rejection instead of splitting
    before upload.
    """
    two_rows = envelope_bound(delivery, 0) + 2 * 22 + 1
    delivery = bounded_delivery(delivery, maxFileBytes=two_rows, maxSchemaBytes=1)
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    for _ in range(3):
        writer.add_row([cell(b'1', 12)])
    writer.finish()

    # The split happened before upload — every page was accepted on its first attempt, so
    # intake never answered final_page_too_large — and the source tokens stay exact numbers.
    assert [(page.rows, payload) for page, payload in uploads.pages] == [(2, b'1\n1\n'), (1, b'1\n')]
    assert len(uploads.put_attempts) == 2


def test_page_limits_fail_closed_without_partial_success(delivery, creds):
    frame = envelope_bound(delivery, 0) + 22  # one "x" row fits exactly

    # A single row plus the envelope exceeds maxFileBytes.
    single_row_delivery = bounded_delivery(delivery, maxFileBytes=frame - 1, maxSchemaBytes=1)
    writer = make_writer(single_row_delivery, creds, Uploads())
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        writer.add_row([cell(b'"x"', 12)])
        writer.finish()
    assert failure.value.code == 'row_too_large'

    # Page count reached maxPages: the first page uploads, the second cannot begin.
    max_pages_delivery = bounded_delivery(delivery, maxFileBytes=frame, maxSchemaBytes=1, maxPages=1)
    uploads = Uploads()
    writer = make_writer(max_pages_delivery, creds, uploads)
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        writer.add_row([cell(b'"x"', 12)])
        writer.add_row([cell(b'"x"', 12)])
        writer.finish()
    assert failure.value.code == 'max_pages_exceeded'
    assert [page.batch_index for page, _ in uploads.pages] == [0]


def test_single_record_exceeding_max_row_bytes_fails_closed(delivery, creds):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        writer.add_row([string_cell('x' * 64)])
    assert failure.value.code == 'row_too_large'
    assert uploads.pages == []


# ---------------------------------------------------------------------------
# Intake-derived receipts, stats, and totals
# ---------------------------------------------------------------------------


def test_stats_and_receipt_come_from_intake_final_metadata_not_source_sizes(delivery, creds):
    uploads = Uploads(final_growth=37)
    stats = rq.RemoteQueryRunStats()
    writer = rq.SourcePageWriter(delivery, creds, uploads, descriptor(), lambda: None, stats)
    for _ in range(3):
        writer.add_row([string_cell('value-text')])
    result = writer.finish()

    source_bytes = sum(page.source_bytes for page, _ in uploads.pages)
    final_bytes = sum(page.source_bytes + 37 for page, _ in uploads.pages)
    assert final_bytes != source_bytes  # the receipts genuinely differ from the source sizes
    # Stats accumulate the receipts' final bytes; the compact receipt repeats intake's totals.
    assert stats.bytes_emitted == final_bytes
    assert stats.rows_emitted == 3
    assert stats.pages_emitted == 1
    assert result == {'uploadId': 'upload-1', 'pageCount': 1, 'totalRows': 3, 'totalBytes': final_bytes}


@pytest.mark.parametrize('field,bad', [('batch_index', 1), ('record_offset', -1), ('rows', True), ('key', '')])
def test_page_receipt_identity_must_match(delivery, creds, field, bad):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('value-text')])
    receipt = {
        'batch_index': 0,
        'key': 'agent-intake-test/pages/0.json',
        'record_offset': 0,
        'bytes': 10,
        'rows': 1,
        'sha256': 'a' * 64,
    }
    uploads.receipt_override = lambda page: {**receipt, field: bad}
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        writer.finish()
    assert failure.value.code == 'invalid_receipt'
    # The unverified page never finalizes the run.
    assert uploads.finalize_calls == 0


@pytest.mark.parametrize('field,bad', [('bytes', 'x'), ('bytes', -1), ('sha256', 'nothex'), ('sha256', 'A' * 64)])
def test_page_receipt_final_metadata_shape_must_be_valid(field, bad):
    page = rq.SourcePageUploadMetadata(0, 0, 10, 1, hashlib.sha256(b'source').hexdigest())
    receipt = {
        'batch_index': 0,
        'key': 'agent-intake-test/pages/0.json',
        'record_offset': 0,
        'bytes': 10,
        'rows': 1,
        'sha256': 'a' * 64,
    }
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.verify_source_page_receipt({**receipt, field: bad}, page)
    assert failure.value.code == 'invalid_receipt'


def test_page_receipt_final_metadata_needs_no_source_agreement():
    """Final bytes and checksum are intake-derived: any valid shape is accepted."""
    page = rq.SourcePageUploadMetadata(0, 0, 10, 1, hashlib.sha256(b'source').hexdigest())
    rq.verify_source_page_receipt(
        {
            'batch_index': 0,
            'key': 'agent-intake-test/pages/0.json',
            'record_offset': 0,
            'bytes': 10_000,
            'rows': 1,
            'sha256': 'f' * 64,
        },
        page,
    )


def test_finalize_totals_are_required_and_authoritative():
    assert rq.finalize_totals({'page_count': 1, 'total_rows': 2, 'total_bytes': 3}) == (1, 2, 3)
    for missing in ({}, {'page_count': 1}, {'page_count': 1, 'total_rows': 2}):
        with pytest.raises(rq.RemoteQueryFailure) as failure:
            rq.finalize_totals(missing)
        assert failure.value.code == 'invalid_receipt'
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.finalize_totals({'page_count': '1', 'total_rows': 0, 'total_bytes': 0})
    assert failure.value.code == 'invalid_receipt'
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.finalize_totals({'page_count': -1, 'total_rows': 0, 'total_bytes': 0})
    assert failure.value.code == 'invalid_receipt'


def test_empty_result_semantics(delivery, creds):
    # include_schema=true: one zero-record source page so intake creates one schema-bearing
    # final page with empty data.
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads, include_schema=True)
    result = writer.finish()
    assert result['pageCount'] == 1
    (page, payload) = uploads.pages[0]
    assert payload == b''
    assert page.rows == 0
    assert page.record_offset == 0
    assert page.source_bytes == 0
    assert page.sha256_hex == hashlib.sha256(b'').hexdigest()

    # include_schema=false: zero pages; only the finalize call happens.
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads, include_schema=False)
    result = writer.finish()
    assert uploads.pages == []
    assert uploads.finalize_calls == 1
    assert result == {'uploadId': 'upload-1', 'pageCount': 0, 'totalRows': 0, 'totalBytes': 0}


def test_result_cap_boundaries_use_receipt_bytes_plus_the_page_bound(delivery, creds):
    row_bound = 22
    frame = envelope_bound(delivery, 0) + row_bound  # one "x" row per page exactly
    final_bytes_per_page = 30

    def run(max_result_bytes):
        scoped = bounded_delivery(
            delivery,
            maxResultBytes=max_result_bytes,
            maxFileBytes=frame,
            maxSchemaBytes=1,
            maxPages=8,
        )
        uploads = Uploads(receipt_bytes=lambda page: final_bytes_per_page)
        writer = make_writer(scoped, creds, uploads)
        for _ in range(4):
            writer.add_row([cell(b'"x"', 12)])
        return writer.finish(), uploads

    # Three committed pages' receipts (90) plus the fourth page's bound fit exactly.
    result, uploads = run(3 * final_bytes_per_page + frame)
    assert result['pageCount'] == 4
    assert result['totalBytes'] == 4 * final_bytes_per_page

    # One byte less: the fourth page cannot be produced under the result cap.
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        run(3 * final_bytes_per_page + frame - 1)
    assert failure.value.code == 'max_result_bytes_exceeded'


# ---------------------------------------------------------------------------
# Oversize rejection: split and retry the same page index
# ---------------------------------------------------------------------------


def test_final_page_too_large_splits_and_retries_the_same_page_index(delivery, creds):
    def reject_wide_pages(page):
        if page.rows > 2:
            return rq.RemoteQueryFailure(
                rq.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake would exceed maxFileBytes'
            )
        return None

    uploads = Uploads(put_failure=reject_wide_pages)
    writer = make_writer(delivery, creds, uploads)
    for text in ('a', 'b', 'c', 'd'):
        writer.add_row([string_cell(text)])
    result = writer.finish()

    # The rejected four-record page is split: the same index is retried with fewer records,
    # and the tail becomes the next page, preserving row order without requerying.
    assert [(page.batch_index, page.rows) for page, _ in uploads.put_attempts] == [(0, 4), (0, 2), (1, 2)]
    tokens = [json.dumps(text).encode('utf-8') for text in ('a', 'b', 'c', 'd')]
    assert [(page.rows, payload) for page, payload in uploads.pages] == [
        (2, b''.join(csv_record([token]) for token in tokens[0:2])),
        (2, b''.join(csv_record([token]) for token in tokens[2:4])),
    ]
    assert uploads.pages[0][0].record_offset == 0
    assert uploads.pages[1][0].record_offset == 2
    assert result['pageCount'] == 2
    assert result['totalRows'] == 4


def test_final_page_too_large_on_a_single_record_fails_closed(delivery, creds):
    uploads = Uploads(
        put_failure=lambda page: rq.RemoteQueryFailure(
            rq.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake would exceed maxFileBytes'
        )
    )
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('a')])
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        writer.finish()
    assert failure.value.code == rq.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE
    assert uploads.finalize_calls == 0


# ---------------------------------------------------------------------------
# Failure release
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('failure', ['upload', 'receipt'])
def test_failed_upload_releases_the_buffered_page(delivery, creds, failure):
    kwargs = {}
    if failure == 'upload':
        kwargs['put_failure'] = lambda page: rq.RemoteQueryFailure('upload_failed', 'unavailable')
    else:
        kwargs['receipt_override'] = lambda page: {
            'batch_index': page.batch_index,
            'key': 'agent-intake-test/pages/{}.json'.format(page.batch_index),
            'record_offset': page.record_offset,
            'bytes': 10,
            'rows': page.rows + 1,
            'sha256': 'a' * 64,
        }
    uploads = Uploads(**kwargs)
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('a')])
    with pytest.raises(rq.RemoteQueryFailure):
        writer.finish()
    writer.discard()
    assert writer._records is None


# ---------------------------------------------------------------------------
# HTTP upload client contract
# ---------------------------------------------------------------------------


def source_page(payload, batch_index=0, record_offset=7):
    return rq.SourcePageUploadMetadata(
        batch_index=batch_index,
        record_offset=record_offset,
        source_bytes=len(payload),
        rows=1,
        sha256_hex=hashlib.sha256(payload).hexdigest(),
    )


def test_http_descriptor_registration_replays_the_identical_body(monkeypatch, creds):
    import requests

    calls = []
    body = rq.descriptor_request_bytes(descriptor())

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data))
        if len(calls) == 1:
            raise requests.exceptions.ConnectionError('response lost')
        return SimpleNamespace(status_code=200, content=json.dumps({'upload_id': creds.upload_id}).encode())

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    assert rq.RequestsUploadClient().register_descriptor(creds, body) == {'upload_id': 'upload-1'}
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('POST', 'https://intake.example/uploads/upload-1/descriptor', body)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'dd-application-key': 'test-app-key',
        'Content-Type': 'application/json',
    }


@pytest.mark.parametrize('trigger', ['lost_response', 'unavailable'])
def test_http_source_page_retry_replays_exact_body_and_headers(monkeypatch, creds, trigger):
    import requests

    calls = []
    payload = b'null,"""x"""\n'
    page = source_page(payload, batch_index=2)

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data.read()))
        if len(calls) == 1:
            if trigger == 'lost_response':
                raise requests.exceptions.ConnectionError('response lost')
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        return SimpleNamespace(
            status_code=200,
            content=json.dumps(
                {
                    'batch_index': 2,
                    'key': 'agent-intake-test/pages/2.json',
                    'record_offset': 7,
                    'bytes': 40,
                    'rows': 1,
                    'sha256': 'a' * 64,
                }
            ).encode(),
        )

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    client = rq.RequestsUploadClient()
    with io.BytesIO(payload) as body:
        receipt = client.put_source_page(creds, page, body)
    assert calls[0] == calls[1]
    method, url, headers, sent = calls[0]
    assert (method, url, sent) == ('PUT', 'https://intake.example/uploads/upload-1/pages/2', payload)
    assert headers == {
        'dd-api-key': 'test-api-key',
        'dd-application-key': 'test-app-key',
        'Content-Type': 'application/vnd.datadog.remote-query.rows+csv;version=1',
        'Content-Length': str(len(payload)),
        'X-DD-Source-Page-Bytes': str(len(payload)),
        'X-DD-Source-Page-Rows': '1',
        'X-DD-Record-Offset': '7',
        'X-DD-Source-Page-SHA256': page.sha256_hex,
    }
    assert receipt['bytes'] == 40  # final metadata, never the source size


def test_http_final_page_too_large_surfaces_as_its_own_code(monkeypatch, creds):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(
            status_code=413, content=b'{"error":{"code":"final_page_too_large","message":"too large"}}'
        )

    monkeypatch.setattr(requests, 'request', request)
    page = source_page(b'null\n')
    with pytest.raises(rq.RemoteQueryFailure) as failure, io.BytesIO(b'null\n') as body:
        rq.RequestsUploadClient().put_source_page(creds, page, body)
    assert failure.value.code == 'final_page_too_large'
    assert not failure.value.retryable
    assert len(calls) == 1  # terminal: the writer splits; the client never retries it


def test_http_terminal_rejections_on_default_mapping_requests_fail_closed(monkeypatch, creds):
    """Descriptor and finalize map no intake error codes: a terminal rejection on either
    must surface as upload_failed, never as an AttributeError from the missing mapping."""
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url))
        return SimpleNamespace(status_code=409, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    client = rq.RequestsUploadClient()
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        client.register_descriptor(creds, b'{}')
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        client.finalize_run(creds)
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert calls == [
        ('POST', 'https://intake.example/uploads/upload-1/descriptor'),
        ('POST', 'https://intake.example/uploads/upload-1/finalize'),
    ]


@pytest.mark.parametrize('status', [400, 403, 409])
def test_http_terminal_rejections_are_not_retried(monkeypatch, creds, status):
    import requests

    calls = []

    def request(*args, **kwargs):
        calls.append(args)
        return SimpleNamespace(status_code=status, content=b'{"error":{"code":"already_exists"}}')

    monkeypatch.setattr(requests, 'request', request)
    page = source_page(b'x')
    with pytest.raises(rq.RemoteQueryFailure) as failure, io.BytesIO(b'x') as body:
        rq.RequestsUploadClient().put_source_page(creds, page, body)
    assert failure.value.code == 'upload_failed'
    assert not failure.value.retryable
    assert len(calls) == 1


def test_http_page_attempt_bound_kills_slow_attempts(monkeypatch, creds):
    import requests

    payload = b'null\n'
    page = source_page(payload, record_offset=0)
    attempts = []
    sent = []

    def request(method, url, headers, data, timeout):
        attempts.append(1)
        sent.append(data.read())
        return SimpleNamespace(status_code=200, content=json.dumps({'key': 'k', 'bytes': 1}).encode())

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
        assert rq.RequestsUploadClient().put_source_page(wall_creds, page, body) == {'key': 'k', 'bytes': 1}
    assert len(attempts) == 2
    # The killed attempt fails its deadline check before any byte leaves; only the rewound
    # second attempt streams the page.
    assert sent == [payload]


def test_http_page_attempt_bound_never_exceeds_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'null\n'
    page = source_page(payload, record_offset=0)
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
        rq.RequestsUploadClient().put_source_page(wall_creds, page, body)
    assert failure.value.code == 'timeout'
    assert failure.value.retryable
    assert len(attempts) == 1


def test_http_retry_sequence_never_extends_the_run_wall(monkeypatch, creds):
    import requests

    payload = b'null\n'
    page = source_page(payload, record_offset=0)
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
        rq.RequestsUploadClient().put_source_page(wall_creds, page, body)
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
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append(method)
        if url.endswith('/descriptor'):
            clock['now'] += 0.5
            registered = json.loads(data)
            return SimpleNamespace(
                status_code=200,
                content=json.dumps(
                    {
                        'upload_id': creds.upload_id,
                        'format_version': registered['format_version'],
                        'include_schema': registered['include_schema'],
                        'columns': len(registered['columns']),
                        'sha256': hashlib.sha256(data).hexdigest(),
                    }
                ).encode(),
            )
        if url.endswith('/finalize'):
            clock['now'] += 0.5
            return SimpleNamespace(
                status_code=200,
                content=json.dumps(
                    {'upload_id': creds.upload_id, 'page_count': 1, 'total_rows': 1, 'total_bytes': stats.bytes_emitted}
                ).encode(),
            )
        if len(calls) == 2:
            clock['now'] += 3.0
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        clock['now'] += 7.0
        # Echo the declared source page metadata so the authoritative receipt verification passes.
        batch_index = int(url.rsplit('/', 1)[-1])
        return SimpleNamespace(
            status_code=200,
            content=json.dumps(
                {
                    'batch_index': batch_index,
                    'key': 'agent-intake-test/pages/{}.json'.format(batch_index),
                    'record_offset': int(headers['X-DD-Record-Offset']),
                    'bytes': int(headers['X-DD-Source-Page-Bytes']),
                    'rows': int(headers['X-DD-Source-Page-Rows']),
                    'sha256': headers['X-DD-Source-Page-SHA256'],
                }
            ).encode(),
        )

    monkeypatch.setattr(requests, 'request', request)
    stats = rq.RemoteQueryRunStats()
    timings = rq.RemoteQueryProducerTimings(0.0)
    client = rq.RequestsUploadClient(timings=timings)
    writer = rq.SourcePageWriter(delivery, creds, client, descriptor(), lambda: None, stats, timings)

    writer.add_row([string_cell('1')])
    result = writer.finish()

    # The descriptor registration precedes the page PUT; finalize is the last call.
    assert calls == ['POST', 'PUT', 'PUT', 'POST']
    assert result == {
        'uploadId': creds.upload_id,
        'pageCount': 1,
        'totalRows': 1,
        'totalBytes': stats.bytes_emitted,
    }
    # The page's upload wall is exactly the failed attempt (3 s) plus the backoff (0.125 s)
    # plus the successful attempt (7 s), each counted once; the descriptor registration and
    # finalize are their own POSTs, so the registration wall lands in the otherMs remainder.
    assert timings.metadata(stats) == {
        'contractVersion': 1,
        'producer': {
            'totalMs': 11125,
            'pageUploadMs': 10125,
            'finalizeMs': 500,
            'otherMs': 500,
            'timeToFirstPageMs': 10625,
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


def test_source_page_writer_emits_identical_source_pages_with_and_without_timings(delivery, creds):
    # Timing collection must never reach the page artifacts: the emitted source page bytes
    # and the compact receipt are identical with the accumulator attached and without it.
    def run(with_timings):
        uploads = Uploads()
        stats = rq.RemoteQueryRunStats()
        timings = rq.RemoteQueryProducerTimings(0.0) if with_timings else None
        writer = rq.SourcePageWriter(delivery, creds, uploads, descriptor(), lambda: None, stats, timings)
        for _ in range(3):
            writer.add_row([string_cell('value-text')])
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


def receipt(page):
    return {
        'batch_index': page.batch_index,
        'record_offset': page.record_offset,
        'bytes': page.source_bytes,
        'rows': page.rows,
        'sha256': page.sha256_hex,
        'key': f'pages/{page.batch_index}.json',
    }


def test_trace_headers_reach_page_finalize_abort_and_retries_without_other_changes(monkeypatch, creds):
    import requests

    page = rq.SourcePageUploadMetadata(0, 0, 1, 1, hashlib.sha256(b'x').hexdigest())
    page_receipt = json.dumps(receipt(page)).encode()
    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, dict(headers)))
        if method == 'PUT' and len(calls) == 1:
            # A transient rejection: the page PUT retries once with the same headers.
            return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')
        if method == 'PUT':
            return SimpleNamespace(status_code=200, content=page_receipt)
        return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    client = rq.RequestsUploadClient()

    def drive(trace_context):
        calls.clear()
        scoped = rq.UploadCredentials(
            creds.base_url, creds.upload_id, creds.api_key, creds.app_key, 'test-intake', trace_context=trace_context
        )
        with io.BytesIO(b'x') as body:
            client.put_source_page(scoped, page, body)
        client.finalize_run(scoped)
        client.abort(scoped)
        return list(calls)

    plain_calls = drive(None)
    traced_calls = drive(
        rq.RemoteQueryTraceContext.model_validate({'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2})
    )

    # The carrier reaches the page PUT (each attempt), finalize, and abort; the retried
    # page PUT replays the same tracing headers byte for byte.
    assert [(method, url) for method, url, _ in traced_calls] == [
        ('PUT', 'https://intake.example/uploads/upload-1/pages/0'),
        ('PUT', 'https://intake.example/uploads/upload-1/pages/0'),
        ('POST', 'https://intake.example/uploads/upload-1/finalize'),
        ('POST', 'https://intake.example/uploads/upload-1/abort'),
    ]
    assert traced_calls[0][2] == traced_calls[1][2]
    expected_trace_headers = {
        'x-datadog-trace-id': TRACE_ID,
        'x-datadog-parent-id': PARENT_ID,
        'x-datadog-sampling-priority': '2',
    }
    for (_, _, traced_headers), (_, _, plain_headers) in zip(traced_calls, plain_calls):
        # Exactly the three tracing headers differ from a context-free run: the auth,
        # integrity, content-length, and Test Drive headers are unchanged, and an absent
        # context preserves the request behavior byte for byte.
        assert traced_headers == {**plain_headers, **expected_trace_headers}


@pytest.mark.parametrize('body', [b'', b'not-json', b'[]', b'null'])
def test_responses_require_json_objects(body):
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.parse_json_object_response(body, 'page upload')
    assert failure.value.code == 'invalid_receipt'


def test_finalize_identity_must_match():
    with pytest.raises(rq.RemoteQueryFailure):
        rq.verify_run_finalize_response({'upload_id': 'other'}, 'upload-1')


# ---------------------------------------------------------------------------
# Request trace context
# ---------------------------------------------------------------------------


def test_request_trace_context_parses_the_agent_carrier(delivery):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
    }
    # Absence is valid for mixed versions: an Agent that never sends the field — and an
    # explicit null — carries no context and the request parses exactly as before.
    assert rq.RemoteQueryRequest.model_validate(request).trace_context is None
    assert rq.RemoteQueryRequest.model_validate({**request, 'traceContext': None}).trace_context is None

    context = rq.RemoteQueryRequest.model_validate(
        {**request, 'traceContext': {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}}
    ).trace_context
    assert (context.trace_id, context.parent_id, context.sampling_priority) == (TRACE_ID, PARENT_ID, 2)

    # The full uint64 range and both positive keep priorities are accepted; a zero-padded
    # spelling of the same value validates to the canonical decimal spelling, so the
    # injected header values are byte-stable.
    context = rq.RemoteQueryRequest.model_validate(
        {**request, 'traceContext': {'traceId': '18446744073709551615', 'parentId': PARENT_ID, 'samplingPriority': 1}}
    ).trace_context
    assert (context.trace_id, context.sampling_priority) == ('18446744073709551615', 1)
    context = rq.RemoteQueryRequest.model_validate(
        {**request, 'traceContext': {'traceId': '00' + TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}}
    ).trace_context
    assert context.trace_id == TRACE_ID


@pytest.mark.parametrize(
    'mutation',
    [
        {'traceId': '0'},
        {'traceId': '00'},
        {'traceId': '18446744073709551616'},
        {'traceId': '-42'},
        {'traceId': '0x2a'},
        {'traceId': '42 '},
        {'traceId': '1.5'},
        {'traceId': ''},
        {'traceId': 12345678901234567890},
        {'parentId': '0'},
        {'parentId': '1e3'},
        {'samplingPriority': 0},
        {'samplingPriority': -1},
        {'samplingPriority': 3},
        {'samplingPriority': '2'},
        {'samplingPriority': 2.0},
        {'samplingPriority': True},
    ],
)
def test_request_trace_context_is_strict_without_echoing_values(delivery, mutation):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
        'traceContext': {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2},
    }
    request['traceContext'].update(mutation)

    with pytest.raises(ValidationError) as failure:
        rq.RemoteQueryRequest.model_validate(request)

    message = rq.validation_message(failure.value)
    assert 'traceContext' in message
    # The carrier is observability metadata; a validation error never echoes its values.
    assert TRACE_ID not in message
    assert PARENT_ID not in message


@pytest.mark.parametrize(
    'carrier',
    [
        {},
        {'traceId': TRACE_ID},
        {'traceId': TRACE_ID, 'parentId': PARENT_ID},
        {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2, 'origin': 'extra'},
        'not-an-object',
        5,
    ],
)
def test_request_trace_context_is_a_closed_shape(delivery, carrier):
    request = {
        'operation': 'produce_json_pages',
        'query': 'SELECT 1',
        'target': {'host': 'db', 'port': 5432, 'dbname': 'db'},
        'resultDelivery': delivery.model_dump(by_alias=True),
        'traceContext': carrier,
    }

    with pytest.raises(ValidationError) as failure:
        rq.RemoteQueryRequest.model_validate(request)

    assert 'traceContext' in rq.validation_message(failure.value)


# ---------------------------------------------------------------------------
# Request and target validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'target',
    [
        {},
        {'host': 'db', 'dbname': 'db'},
        {'database_instance': ' db '},
        {'database_instance': 'db', 'host': 'db'},
        {'database_instance': 'db', 'port': 5432},
        {'database_instance': 'db', 'dbname': 'other'},
        {'database_instance': 'db', 'dbname': None},
        {'database_instance': 'db', 'dbname': ''},
        {'database_instance': 'db', 'dbname': ' '},
        {'host': 'db', 'port': True, 'dbname': 'db'},
    ],
)
def test_target_requires_one_complete_selector(target):
    with pytest.raises(ValueError):
        rq.normalize_target(target)


def test_target_validation_wrapper_keeps_no_path_back_to_the_rejected_request():
    """Pydantic's error object retains the raw request input even though the fixed message
    excludes it, so the wrapper severs the exception chain: a later traceback log of the
    wrapper can only ever see the content-free validation message."""
    with pytest.raises(ValueError) as failure:
        rq.normalize_target({'host': 'db', 'port': 'SECRET_DO_NOT_LOG', 'dbname': 'db'})

    assert failure.value.__cause__ is None
    assert 'SECRET_DO_NOT_LOG' not in str(failure.value)


@pytest.mark.parametrize(
    'path,value',
    [
        (('operation',), None),
        (('includeSchema',), 'true'),
        (('target', 'port'), '5432'),
        (('resultDelivery',), None),
        (('resultDelivery', 'token'), 'scoped-upload-token'),
        (('resultDelivery', 'artifactVersion'), 2),
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


def test_resolve_request_is_target_only():
    request = rq.RemoteQueryResolveRequest.model_validate(
        {'operation': 'resolve_target', 'target': {'host': 'db', 'port': 5432, 'dbname': 'db'}}
    )
    assert request.operation == 'resolve_target'
    assert (request.target.host, request.target.port, request.target.dbname) == ('db', 5432, 'db')


@pytest.mark.parametrize(
    'field,value',
    [
        ('query', 'SELECT 1'),
        ('includeSchema', True),
        ('resultDelivery', {'runId': 'run-1'}),
        ('traceContext', {'traceId': TRACE_ID, 'parentId': PARENT_ID, 'samplingPriority': 2}),
        ('matchFingerprint', 'deadbeef'),
        ('apiKey', 'SECRET_DO_NOT_LOG'),
    ],
)
def test_resolve_request_rejects_execution_fields_without_echoing_values(field, value):
    request = {'operation': 'resolve_target', 'target': {'database_instance': 'Primary/DB'}, field: value}

    with pytest.raises(ValidationError) as failure:
        rq.RemoteQueryResolveRequest.model_validate(request)

    assert field in rq.validation_message(failure.value)
    assert 'SECRET_DO_NOT_LOG' not in rq.validation_message(failure.value)


@pytest.mark.parametrize('operation', ['produce_json_pages', 'resolve', 'RESOLVE_TARGET', ''])
def test_resolve_request_rejects_other_operations(operation):
    request = {'operation': operation, 'target': {'database_instance': 'Primary/DB'}}

    with pytest.raises(ValidationError):
        rq.RemoteQueryResolveRequest.model_validate(request)


def test_result_ceiling_is_the_pinned_server_contract(delivery):
    # The ceiling is 100 binary GiB (stricter than decimal 100 GB): exactly that validates and
    # one byte more is rejected, so the shared ceiling cannot drift from the server-owned
    # contract or silently fall back to a smaller value.
    assert rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES == 100 * 1024**3
    limits = bounded_delivery(delivery, maxResultBytes=rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES).limits
    assert limits.max_result_bytes == rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES
    with pytest.raises(ValidationError):
        bounded_delivery(delivery, maxResultBytes=rq.REMOTE_QUERY_UPLOAD_MAX_RESULT_BYTES + 1)


# ---------------------------------------------------------------------------
# Agent configuration helpers
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Failure hygiene: exception and config detail never reach logs or events
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('trigger', ['transport', 'transient_status'])
def test_retry_exhausted_upload_failure_reports_only_safe_diagnostics(monkeypatch, creds, caplog, trigger):
    """The exhausted retry sequence stays retryable upload_failed, and its diagnostic is the
    fixed failure category or intake's HTTP status — never the caught transport exception,
    whose text carries the URL and request body."""
    import requests

    caplog.set_level(logging.DEBUG)

    def request(*args, **kwargs):
        if trigger == 'transport':
            raise requests.exceptions.ConnectionError('SECRET_DO_NOT_LOG while sending page bytes')
        return SimpleNamespace(status_code=503, content=b'{"error":{"code":"unavailable"}}')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    with pytest.raises(rq.RemoteQueryFailure) as failure:
        rq.RequestsUploadClient().register_descriptor(creds, b'{}')
    assert failure.value.code == 'upload_failed'
    assert failure.value.retryable
    expected_detail = 'transport failure' if trigger == 'transport' else 'HTTP status 503'
    message = failure.value.message
    assert 'failed after {} attempts: {}'.format(rq.REMOTE_QUERY_UPLOAD_MAX_RETRIES + 1, expected_detail) in message
    assert 'SECRET_DO_NOT_LOG' not in message
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_abort_failures_log_fixed_text_only(monkeypatch, creds, caplog):
    """Both best-effort abort paths log fixed diagnostic text: the caught exception can
    quote the URL, the request body, or credentials embedded in its message."""
    import requests

    caplog.set_level(logging.DEBUG)

    def request(*args, **kwargs):
        raise requests.exceptions.ConnectionError('SECRET_DO_NOT_LOG while aborting')

    monkeypatch.setattr(requests, 'request', request)
    monkeypatch.setattr(rq.time, 'sleep', lambda _: None)
    rq.RequestsUploadClient().abort(creds)  # best-effort: never raises

    class ExplodingClient:
        def abort(self, creds):
            raise RuntimeError('SECRET_DO_NOT_LOG while aborting')

    rq.safe_abort(ExplodingClient(), creds)  # best-effort: never raises
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_invalid_test_drive_name_warning_omits_the_configured_value(caplog):
    assert rq.validate_test_drive_name('INVALID_NAME_SECRET_DO_NOT_LOG') is None
    # The verdict and the grammar requirement stay in the warning; only the configured
    # value is dropped.
    assert 'Ignoring invalid remote query intake Test Drive name' in caplog.text
    assert 'lowercase ASCII alphanumerics' in caplog.text
    assert 'SECRET_DO_NOT_LOG' not in caplog.text


def test_agent_config_read_failures_log_fixed_text_only(monkeypatch, caplog):
    """Both config-reading helpers swallow read failures into fixed debug text: the config
    layer's exception can quote configuration values."""
    caplog.set_level(logging.DEBUG)

    def broken_get_config(key):
        raise Exception('SECRET_DO_NOT_LOG in the config layer')

    monkeypatch.setattr(rq.datadog_agent, 'get_config', broken_get_config)
    assert rq.get_agent_config('api_key') == ''
    assert rq.is_query_allowlist_enabled() is True
    assert 'SECRET_DO_NOT_LOG' not in caplog.text
