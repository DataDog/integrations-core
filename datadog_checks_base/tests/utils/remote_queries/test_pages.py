# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import csv
import json
from types import SimpleNamespace

import pytest

from datadog_checks.base.utils.remote_queries import contract as rq_contract
from datadog_checks.base.utils.remote_queries import pages as rq_pages
from datadog_checks.base.utils.remote_queries import upload as rq_upload

from .helpers import (
    Uploads,
    acceptance_receipt,
    bounded_delivery,
    cell,
    csv_record,
    descriptor,
    envelope_bound,
    make_writer,
    string_cell,
)


def test_descriptor_registration_happens_once_before_any_row(delivery, creds):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('a')])
    writer.finish()
    assert uploads.descriptor_bodies == [rq_contract.descriptor_request_bytes(descriptor())]


def test_writer_gates_rows_on_a_descriptor_receipt_that_confirms_the_registration(delivery, creds):
    """The registration gate fails closed before any row flows or the run finalizes."""
    uploads = Uploads(descriptor_response={'upload_id': creds.upload_id, 'sha256': '0' * 64})
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        make_writer(delivery, creds, uploads)
    assert failure.value.code == 'invalid_receipt'
    assert len(uploads.descriptor_bodies) == 1
    assert uploads.pages == []
    assert uploads.finalize_calls == 0


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
    writer.add_row([cell(token, rq_pages.redactable_leaf_final_bound(token)) for token in tokens])
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
    assert result['pageCount'] == 1


def test_source_pages_reject_tokens_that_would_corrupt_the_csv_record():
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_pages.frame_csv_record([b'"ok"', b'with\rraw-cr'])
    assert failure.value.code == 'unsupported_value'


def test_source_page_body_streams_chunks_and_never_pins_the_buffer():
    """The upload body view copies only the chunk each read asks for, reports its exact
    remaining length through requests' own super_len, rewinds on seek(0), and never holds a
    buffer export between calls — so the writer can compact the buffer after any read."""
    import requests

    buf = bytearray(b'0123456789')
    body = rq_pages._SourcePageBody(buf, 6)
    assert requests.utils.super_len(body) == 6
    assert body.read(2) == b'01'
    assert requests.utils.super_len(body) == 4
    body.seek(0)
    assert body.read() == b'012345'
    body.seek(-2, 2)
    assert body.tell() == 4
    assert body.read() == b'45'
    body.seek(0)
    chunk = body.read(3)
    # A retained chunk is a copy, not a view: compacting the shared buffer stays possible.
    del buf[:6]
    assert chunk == b'012'


def test_string_cell_tokens_emit_valid_non_ascii_as_raw_utf8():
    """A canonical string token spells valid non-ASCII as raw UTF-8, never ``\\uXXXX`` escapes."""
    token, final_bound = rq_pages.string_cell_token('héllo')
    assert token == b'"h\xc3\xa9llo"'
    assert b'\\u' not in token
    # A short multibyte leaf still bounds to the fixed redaction marker; a longer one keeps
    # its own raw UTF-8 token bytes.
    assert final_bound == len(rq_pages.REMOTE_QUERY_REDACTED_MARKER_TOKEN)
    long_token, long_bound = rq_pages.string_cell_token('héllo ' + 'é' * 64)
    assert long_token == b'"h\xc3\xa9llo ' + b'\xc3\xa9' * 64 + b'"'
    assert long_bound == len(long_token)


def test_string_cell_tokens_fail_closed_on_text_that_cannot_encode_as_utf8():
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_pages.string_cell_token('a\ud800')
    assert failure.value.code == 'unsupported_value'


def test_redactable_leaf_bound_reserves_the_marker_for_short_number_tokens():
    """Intake scans number leaves too and substitutes the fixed marker string token for any
    match, so a short number's final bound is the marker size exactly like a short string's;
    a number already longer than the marker keeps its own token bytes.
    """
    marker = len(rq_pages.REMOTE_QUERY_REDACTED_MARKER_TOKEN)
    # Short integer and decimal/float tokens all reserve the marker size.
    for token in (b'1', b'-42', b'0', b'0.1', b'1e+16', b'-0', b'123.45'):
        assert rq_pages.redactable_leaf_final_bound(token) == marker
    long_token = b'12345678901234567890.123456789'
    assert rq_pages.redactable_leaf_final_bound(long_token) == len(long_token)


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
    assert result['pageCount'] == 1


def test_page_prefix_emits_valid_non_ascii_as_raw_utf8():
    prefix = rq_pages.page_prefix(
        run_id='rün-1',
        task_id='täsk-1',
        record_offset=3,
        agent_hostname='agent-hôte',
        schema_json=None,
    )
    assert prefix.startswith(b'{"contract_version":"1.0.0","crawl_id":"r\xc3\xbcn-1",')
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
    row_bound = 1 + len(key_bytes) + 2 + len(rq_pages.REMOTE_QUERY_REDACTED_MARKER_TOKEN)
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
    # Sequential production advances on acceptance: each page uploads only after the
    # previous page's 202, at the next index and offset, and finalize declares exactly
    # the accepted count.
    assert [page.batch_index for page, _ in uploads.pages] == [0, 1, 2]
    for index, (page, payload) in enumerate(uploads.pages):
        assert payload == csv_record([tokens[index]])
        assert page.record_offset == index
        assert page.source_bytes == len(payload)
    assert uploads.finalize_expected_counts == [3]
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
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.add_row([cell(b'"x"', 12)])
        writer.finish()
    assert failure.value.code == 'row_too_large'

    # Page count reached maxPages: the first page uploads, the second cannot begin.
    max_pages_delivery = bounded_delivery(delivery, maxFileBytes=frame, maxSchemaBytes=1, maxPages=1)
    uploads = Uploads()
    writer = make_writer(max_pages_delivery, creds, uploads)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.add_row([cell(b'"x"', 12)])
        writer.add_row([cell(b'"x"', 12)])
        writer.finish()
    assert failure.value.code == 'max_pages_exceeded'
    assert [page.batch_index for page, _ in uploads.pages] == [0]


def test_single_record_exceeding_max_row_bytes_fails_closed(delivery, creds):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.add_row([string_cell('x' * 64)])
    assert failure.value.code == 'row_too_large'
    assert uploads.pages == []


def test_stats_and_receipt_come_from_intake_finalization_not_local_sizes(delivery, creds):
    uploads = Uploads(final_growth=37)
    stats = rq_contract.RemoteQueryRunStats()
    writer = rq_pages.SourcePageWriter(delivery, creds, uploads, descriptor(), lambda: None, stats)
    for _ in range(3):
        writer.add_row([string_cell('value-text')])
    result = writer.finish()

    source_bytes = sum(page.source_bytes for page, _ in uploads.pages)
    final_bytes = sum(page.source_bytes + 37 for page, _ in uploads.pages)
    assert final_bytes != source_bytes  # finalize's totals genuinely differ from the source sizes
    # Stats and the compact receipt mirror intake's finalization totals: the producer's own
    # conservative page accounting is replaced by the authoritative totals, never merged.
    assert stats.bytes_emitted == final_bytes
    assert stats.rows_emitted == 3
    assert stats.pages_emitted == 1
    assert result == {'uploadId': 'upload-1', 'pageCount': 1, 'totalRows': 3, 'totalBytes': final_bytes}
    # The finalize request declared exactly the accepted page count.
    assert uploads.finalize_expected_counts == [1]


@pytest.mark.parametrize(
    'field,bad',
    [
        ('upload_id', 'other-upload'),
        ('batch_index', 1),
        ('record_offset', -1),
        ('source_rows', True),
        ('source_rows', 2),
        ('status', 'processing'),
    ],
)
def test_page_acceptance_receipt_identity_must_match(delivery, creds, field, bad):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('value-text')])
    receipt = acceptance_receipt(0, 0, 1)
    uploads.receipt_override = lambda page: {**receipt, field: bad}
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.finish()
    assert failure.value.code == 'invalid_receipt'
    # The unverified page never finalizes the run.
    assert uploads.finalize_calls == 0


@pytest.mark.parametrize('field', ['upload_id', 'batch_index', 'record_offset', 'source_rows', 'status'])
def test_page_acceptance_receipt_fields_are_required(delivery, creds, field):
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('value-text')])
    receipt = acceptance_receipt(0, 0, 1)
    del receipt[field]
    uploads.receipt_override = lambda page: receipt
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.finish()
    assert failure.value.code == 'invalid_receipt'
    assert uploads.finalize_calls == 0


def test_page_receipt_rejects_unknown_fields(creds):
    page = rq_contract.SourcePageUploadMetadata(0, 0, 10, 1)
    receipt = {**acceptance_receipt(0, 0, 1), 'unexpected': True}
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        rq_upload.verify_source_page_receipt(receipt, creds.upload_id, page)
    assert failure.value.code == 'invalid_receipt'


def test_empty_result_semantics(delivery, creds):
    # include_schema=true: one zero-record source page so intake creates one schema-bearing
    # final page with empty data.
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads, include_schema=True)
    result = writer.finish()
    assert result['pageCount'] == 1
    assert uploads.finalize_expected_counts == [1]  # the zero-record schema page was accepted
    (page, payload) = uploads.pages[0]
    assert payload == b''
    assert page.rows == 0
    assert page.record_offset == 0
    assert page.source_bytes == 0

    # include_schema=false: zero pages; only the finalize call happens.
    uploads = Uploads()
    writer = make_writer(delivery, creds, uploads, include_schema=False)
    result = writer.finish()
    assert uploads.pages == []
    assert uploads.finalize_calls == 1
    assert uploads.finalize_expected_counts == [0]
    assert result == {'uploadId': 'upload-1', 'pageCount': 0, 'totalRows': 0, 'totalBytes': 0}


def test_result_cap_boundaries_use_the_conservative_page_bounds(delivery, creds):
    """The cumulative result cap uses the producer's own conservative page bounds: no
    per-page final bytes exist before finalization, so each closed page contributes the
    bound it was split under and the active page its bound with the new row."""
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

    # Three closed pages' bounds plus the fourth page's bound fit exactly.
    result, uploads = run(4 * frame)
    assert result['pageCount'] == 4
    # The receipt totals still come from intake's finalization, never the conservative bounds.
    assert result['totalBytes'] == 4 * final_bytes_per_page

    # One byte less: the fourth page cannot be produced under the result cap.
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        run(4 * frame - 1)
    assert failure.value.code == 'max_result_bytes_exceeded'


def test_final_page_too_large_splits_and_retries_the_same_page_index(delivery, creds):
    def reject_wide_pages(page):
        if page.rows > 2:
            return rq_contract.RemoteQueryFailure(
                rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake would exceed maxFileBytes'
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
        put_failure=lambda page: rq_contract.RemoteQueryFailure(
            rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake would exceed maxFileBytes'
        )
    )
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('a')])
    with pytest.raises(rq_contract.RemoteQueryFailure) as failure:
        writer.finish()
    assert failure.value.code == rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE
    assert uploads.finalize_calls == 0


def test_page_bound_survives_an_oversize_split(delivery, creds):
    """A page assembled after an oversize split still splits by the retained tail's bound.

    The defensive final_page_too_large rejection halves the buffered page and leaves the
    uncommitted tail as the active page with its bound recomputed; a later append must
    still see that bound, so the page it completes respects maxFileBytes instead of
    leaning on another intake rejection.
    """
    rejected = []

    def reject_the_first_page(page):
        if not rejected:
            rejected.append(page.batch_index)
            return rq_contract.RemoteQueryFailure(
                rq_upload.REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE, 'intake would exceed maxFileBytes'
            )
        return None

    def row_bound(text):
        token = json.dumps(text).encode('utf-8')
        return 1 + len(b'"value"') + 2 + rq_pages.redactable_leaf_final_bound(token)

    small, wide = row_bound('a' * 10), row_bound('b' * 60)
    # The budget holds the two wide rows plus one small row exactly: the fourth row never
    # fits the page they opened.
    scoped = bounded_delivery(
        delivery,
        maxFileBytes=envelope_bound(delivery, 0) + wide + wide + small + 2,
        maxRowBytes=128,
        maxSchemaBytes=1,
    )
    uploads = Uploads(put_failure=reject_the_first_page)
    writer = make_writer(scoped, creds, uploads)
    for text in ('a' * 10, 'b' * 60, 'c' * 60, 'd' * 10, 'e' * 10):
        writer.add_row([string_cell(text)])
    result = writer.finish()

    # The rejected three-row page is halved, its acknowledged prefix leaves the tail — still
    # carrying the two wide rows — and the two later small rows split exactly as the budget
    # prescribes instead of joining one page whose bound exceeds maxFileBytes.
    assert [(page.batch_index, page.rows) for page, _ in uploads.put_attempts] == [(0, 3), (0, 1), (1, 3), (2, 1)]
    assert [page.rows for page, _ in uploads.pages] == [1, 3, 1]
    assert [page.record_offset for page, _ in uploads.pages] == [0, 1, 4]
    assert result['totalRows'] == 5


@pytest.mark.parametrize('failure', ['upload', 'receipt'])
def test_failed_upload_releases_the_buffered_page(delivery, creds, failure):
    kwargs = {}
    if failure == 'upload':
        kwargs['put_failure'] = lambda page: rq_contract.RemoteQueryFailure('upload_failed', 'unavailable')
    else:
        kwargs['receipt_override'] = lambda page: acceptance_receipt(
            page.batch_index, page.record_offset, page.rows + 1
        )
    uploads = Uploads(**kwargs)
    writer = make_writer(delivery, creds, uploads)
    writer.add_row([string_cell('a')])
    with pytest.raises(rq_contract.RemoteQueryFailure):
        writer.finish()
    writer.discard()


def test_finalize_abort_and_test_drive_routing(monkeypatch, creds):
    import requests

    calls = []

    def request(method, url, headers, data, timeout):
        calls.append((method, url, headers, data))
        return SimpleNamespace(status_code=200, content=b'{"upload_id":"upload-1"}')

    monkeypatch.setattr(requests, 'request', request)
    creds = rq_upload.UploadCredentials(creds.base_url, creds.upload_id, creds.api_key, creds.app_key, 'test-intake')
    client = rq_upload.RequestsUploadClient()
    assert client.finalize_run(creds, 3)['upload_id'] == creds.upload_id
    client.abort(creds)
    assert [call[1] for call in calls] == [
        'https://intake.example/uploads/upload-1/finalize',
        'https://intake.example/uploads/upload-1/abort',
    ]
    # Finalize declares the accepted page count; abort stays an empty body.
    assert calls[0][3] == b'{"expected_page_count":3}'
    assert calls[1][3] == b'{}'
    assert all(method == 'POST' and headers['test-drive-test-intake'] == '1' for method, _, headers, _ in calls)
