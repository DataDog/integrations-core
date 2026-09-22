# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query pages."""

from __future__ import annotations

import csv
import io
import time
from array import array
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from .contract import (
    REMOTE_QUERY_PAGE_CONTRACT_VERSION,
    RemoteQueryFailure,
    RemoteQueryResultDelivery,
    RemoteQueryRunStats,
    RemoteQueryUploadDescriptor,
    SourcePageUploadMetadata,
    canonical_json_bytes,
    descriptor_request_bytes,
    descriptor_schema_bytes,
)
from .timing import RemoteQueryProducerTimings
from .tracing import NULL_PRODUCER_TRACING, RemoteQueryProducerTracing
from .upload import (
    REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE,
    UploadClient,
    UploadCredentials,
    finalize_totals,
    verify_descriptor_response,
    verify_run_finalize_response,
    verify_source_page_receipt,
)

PAGE_SUFFIX = b']}'


REMOTE_QUERY_REDACTED_MARKER_TOKEN = b'"[REDACTED]"'


def redactable_leaf_final_bound(token: bytes | bytearray) -> int:
    """A redactable scalar leaf's final bytes: its own token or the marker, whichever is larger.

    Intake scans string and number leaves alike and substitutes the fixed marker string token
    for any match, so both families bound against the marker; booleans and null are never
    scanned and keep their exact token bounds at the encoding call sites.
    """
    return max(len(token), len(REMOTE_QUERY_REDACTED_MARKER_TOKEN))


def string_cell_token(text: str) -> tuple[bytes, int]:
    """A scalar string cell: its canonical JSON token and the redactable-leaf final bound."""
    token = canonical_json_bytes(text)
    return token, redactable_leaf_final_bound(token)


@dataclass(frozen=True)
class EncodedCell:
    """One canonical JSON value token plus the conservative bound on its final JSON bytes.

    `token` is the pinned value-contract encoding of the cell. `final_bound` bounds the
    bytes intake can emit for the cell after redaction: every scalar string or number leaf
    either keeps its token or is replaced by the fixed `[REDACTED]` marker, whichever is
    longer; booleans and null are never scanned and keep their exact token bounds.
    """

    token: bytes
    final_bound: int


def page_prefix(
    *,
    run_id: str,
    task_id: str,
    record_offset: int,
    agent_hostname: str,
    schema_json: bytes | None,
) -> bytes:
    """The envelope bytes through the opening of `data`, with no trailing space."""
    head = b''.join(
        (
            b'{"contract_version":',
            canonical_json_bytes(REMOTE_QUERY_PAGE_CONTRACT_VERSION),
            b',"crawl_id":',
            canonical_json_bytes(run_id),
            b',"task_id":',
            canonical_json_bytes(task_id),
            b',"record_offset":%d,"agent_hostname":' % record_offset,
            canonical_json_bytes(agent_hostname),
            b',',
        )
    )
    parts = [head]
    if schema_json is not None:
        parts.append(b'"schema":')
        parts.append(schema_json)
        parts.append(b',')
    parts.append(b'"data":[')
    return b''.join(parts)


def frame_csv_record(tokens: Sequence[bytes]) -> bytes:
    """Frame canonical cell tokens as one source-page CSV record."""
    for token in tokens:
        if b'\r' in token:
            raise RemoteQueryFailure('unsupported_value', 'A canonical cell token carried a raw carriage return.')
    sink = io.StringIO()
    csv.writer(sink, lineterminator='\n').writerow([token.decode('utf-8') for token in tokens])
    return sink.getvalue().encode('utf-8')


class _SourcePageBody:
    """A seekable read-only view over the active page buffer's first `end` bytes."""

    __slots__ = ('_buf', '_end', '_pos')

    def __init__(self, buf: bytearray, end: int):
        self._buf = buf
        self._end = end
        self._pos = 0

    def read(self, amount: int | None = -1) -> bytes:
        if amount is None or amount < 0:
            amount = self._end - self._pos
        else:
            amount = max(0, min(amount, self._end - self._pos))
        data = bytes(memoryview(self._buf)[self._pos : self._pos + amount])
        self._pos += amount
        return data

    def seek(self, offset: int, whence: int = 0) -> int:
        if whence == 0:
            self._pos = offset
        elif whence == 1:
            self._pos += offset
        elif whence == 2:
            self._pos = self._end + offset
        else:
            raise ValueError('invalid whence ({!r}, should be 0, 1 or 2).'.format(whence))
        self._pos = max(0, min(self._pos, self._end))
        return self._pos

    def tell(self) -> int:
        return self._pos

    def __iter__(self):
        # requests streams a body that exposes `__iter__`; the HTTP sender consumes the
        # body through `read` alone, so iteration itself never happens.
        raise TypeError('the source-page body is a byte stream, not an iterable.')


class PageUploader:
    """Upload complete CSV records; retry oversized pages at a record boundary.

    Callers own their buffers and supply record ends. Optional row bounds describe
    final JSON sizes; otherwise only source sizes are known until intake finalizes.
    """

    def __init__(
        self,
        delivery: RemoteQueryResultDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
        timings: RemoteQueryProducerTimings,
        tracing: RemoteQueryProducerTracing | None = None,
    ):
        self.delivery, self.creds, self.client = delivery, creds, client
        self.descriptor, self.guard, self.stats, self.timings = descriptor, guard, stats, timings
        self.tracing = tracing if tracing is not None else NULL_PRODUCER_TRACING
        self.schema_json = descriptor_schema_bytes(descriptor)
        limits = delivery.limits
        if len(descriptor.columns) > limits.max_columns:
            raise RemoteQueryFailure('max_columns_exceeded', 'Descriptor exceeds maxColumns.')
        if self.schema_json is not None and len(self.schema_json) > limits.max_schema_bytes:
            raise RemoteQueryFailure('max_schema_bytes_exceeded', 'Encoded schema exceeds maxSchemaBytes.')
        if self.page_bound(0, ()) > limits.max_file_bytes:
            raise RemoteQueryFailure(
                'max_file_bytes_exceeded', 'The repeated schema plus the minimal page envelope exceeds maxFileBytes.'
            )
        body = descriptor_request_bytes(descriptor)
        verify_descriptor_response(client.register_descriptor(creds, body), creds.upload_id, descriptor, body)

    def page_bound(self, offset: int, row_bounds: Sequence[int]) -> int:
        prefix = page_prefix(
            run_id=self.delivery.run_id,
            task_id=self.delivery.task_id,
            record_offset=offset,
            agent_hostname=self.descriptor.agent_hostname,
            schema_json=self.schema_json,
        )
        return len(prefix) + len(PAGE_SUFFIX) + sum(row_bounds) + max(0, len(row_bounds) - 1)

    def upload(
        self, buffer: bytearray, record_ends: Sequence[int], row_bounds: Sequence[int] | None = None
    ) -> tuple[int, int]:
        """Return the accepted record count and byte count; leave the buffer untouched."""
        stats, limits = self.stats, self.delivery.limits
        if stats.pages_emitted >= limits.max_pages:
            raise RemoteQueryFailure('max_pages_exceeded', 'Page count reached maxPages.')
        count = len(record_ends)
        while True:
            end = record_ends[count - 1] if count else 0
            bound = end if row_bounds is None else self.page_bound(stats.rows_emitted, row_bounds[:count])
            if stats.bytes_emitted + bound > limits.max_result_bytes:
                raise RemoteQueryFailure('max_result_bytes_exceeded', 'Result pages exceed maxResultBytes.')
            page = SourcePageUploadMetadata(stats.pages_emitted, stats.rows_emitted, end, count)
            try:
                self.guard()
                with self.timings.page_upload():
                    receipt = self.client.put_source_page(self.creds, page, _SourcePageBody(buffer, end))
                verify_source_page_receipt(receipt, self.creds.upload_id, page)
            except RemoteQueryFailure as error:
                if error.code != REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE or count <= 1:
                    raise
                count //= 2
                continue
            stats.pages_emitted += 1
            stats.rows_emitted += count
            stats.bytes_emitted += bound
            self.timings.note_page_acknowledged()
            # The root span's time_to_first_page_ms counts the same first-page boundary.
            self.tracing.note_page_acknowledged()
            return count, end

    def finalize(self) -> dict[str, Any]:
        # The finalize span is also the injection parent of the finalize requests.
        with self.tracing.finalize_span():
            with self.timings.phase('finalize'):
                response = self.client.finalize_run(self.creds, self.stats.pages_emitted)
                verify_run_finalize_response(response, self.creds.upload_id)
                pages, rows, size = finalize_totals(response)
        self.stats.pages_emitted, self.stats.rows_emitted, self.stats.bytes_emitted = pages, rows, size
        return {'uploadId': self.creds.upload_id, 'pageCount': pages, 'totalRows': rows, 'totalBytes': size}


class SourcePageWriter:
    """Buffer canonical JSON cells as CSV, bounded by their final JSON sizes."""

    def __init__(
        self,
        delivery: RemoteQueryResultDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
        timings: RemoteQueryProducerTimings | None = None,
        tracing: RemoteQueryProducerTracing | None = None,
    ):
        timings = timings or RemoteQueryProducerTimings(time.monotonic())
        self._uploader = PageUploader(delivery, creds, client, descriptor, guard, stats, timings, tracing)
        self._limits = delivery.limits
        self._columns = len(descriptor.columns)
        self._key_bound = sum(len(canonical_json_bytes(c.column_name)) for c in descriptor.columns)
        self._buf = bytearray()
        self._record_ends = array('q')
        self._record_bounds = array('q')
        self._page_bound = self._uploader.page_bound(stats.rows_emitted, ())

    def add_row(self, cells: Sequence[EncodedCell]) -> None:
        if len(cells) != self._columns:
            raise RemoteQueryFailure('query_failed', 'Result row width does not match the described columns.')
        record = frame_csv_record([cell.token for cell in cells])
        if len(record) > self._limits.max_row_bytes:
            raise RemoteQueryFailure('row_too_large', 'A single record exceeds maxRowBytes.')
        row_bound = 1 + self._key_bound + 2 * len(cells) + sum(cell.final_bound for cell in cells)
        while True:
            needed = self._page_bound + bool(self._record_ends) + row_bound
            if needed > self._limits.max_file_bytes and self._record_ends:
                self._close_page()
                continue
            if needed > self._limits.max_file_bytes:
                raise RemoteQueryFailure('row_too_large', 'A single row plus the page envelope exceeds maxFileBytes.')
            if self._uploader.stats.bytes_emitted + needed > self._limits.max_result_bytes:
                raise RemoteQueryFailure('max_result_bytes_exceeded', 'Result pages exceed maxResultBytes.')
            break
        self._buf += record
        self._record_ends.append(len(self._buf))
        self._record_bounds.append(row_bound)
        self._page_bound = needed

    def _close_page(self) -> None:
        count, consumed = self._uploader.upload(self._buf, self._record_ends, self._record_bounds)
        del self._buf[:consumed]
        self._record_ends = array('q', (end - consumed for end in self._record_ends[count:]))
        del self._record_bounds[:count]
        self._page_bound = self._uploader.page_bound(self._uploader.stats.rows_emitted, self._record_bounds)

    def finish(self) -> dict[str, Any]:
        while self._record_ends:
            self._close_page()
        if self._uploader.descriptor.include_schema and not self._uploader.stats.pages_emitted:
            self._uploader.upload(self._buf, (), ())
        return self._uploader.finalize()

    def discard(self) -> None:
        self._buf.clear()
        del self._record_ends[:]
        del self._record_bounds[:]
