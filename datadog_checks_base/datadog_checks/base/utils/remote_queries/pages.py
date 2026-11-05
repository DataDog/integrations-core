# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""Remote query pages."""

from __future__ import annotations

import csv
import io
from array import array
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, BinaryIO, Protocol

from .contract import (
    REMOTE_QUERY_PAGE_CONTRACT_VERSION,
    REMOTE_QUERY_SESSIONLESS_MAX_DESCRIPTOR_BYTES,
    RemoteQueryDelivery,
    RemoteQueryFailure,
    RemoteQueryRunStats,
    RemoteQuerySessionlessResultDelivery,
    RemoteQueryUploadDescriptor,
    SessionlessCompletionReceipt,
    SourcePageUploadMetadata,
    canonical_json_bytes,
    descriptor_request_bytes,
    descriptor_schema_bytes,
    sessionless_page_metadata_bytes,
)
from .tracing import NULL_PRODUCER_TRACING, RemoteQueryProducerTracing
from .upload import (
    REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE,
    UploadClient,
    UploadCredentials,
    finalize_totals,
    verify_descriptor_response,
    verify_run_finalize_response,
    verify_sessionless_page_receipt,
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


class UploadProtocol(Protocol):
    """The protocol-specific half of a page uploader, chosen from the delivery.

    `PageUploader` owns the shared page loop: limits, record-boundary splitting of an
    oversized page, and run accounting. A protocol owns what crosses the wire: how the run
    begins, how one page is sent and its receipt verified, and how the run is completed.
    """

    def begin(self) -> None: ...

    def send_page(self, page: SourcePageUploadMetadata, body: BinaryIO, bound: int) -> int:
        """Send one page and return the bytes the run accounts for it."""
        ...

    def complete(self, stats: RemoteQueryRunStats) -> dict[str, Any]: ...


class SessionUploadProtocol:
    """The default session-backed protocol: register once, PUT pages, finalize for the totals."""

    def __init__(
        self,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
        tracing: RemoteQueryProducerTracing,
    ):
        self._creds, self._client, self._descriptor, self._tracing = creds, client, descriptor, tracing

    def begin(self) -> None:
        body = descriptor_request_bytes(self._descriptor)
        verify_descriptor_response(
            self._client.register_descriptor(self._creds, body), self._creds.upload_id, self._descriptor
        )

    def send_page(self, page: SourcePageUploadMetadata, body: BinaryIO, bound: int) -> int:
        receipt = self._client.put_source_page(self._creds, page, body)
        verify_source_page_receipt(receipt, self._creds.upload_id, page)
        # Only the conservative bound is known until finalization reports the authoritative totals.
        return bound

    def complete(self, stats: RemoteQueryRunStats) -> dict[str, Any]:
        # The finalize span is also the injection parent of the finalize requests.
        with self._tracing.finalize_span():
            response = self._client.finalize_run(self._creds, stats.pages_emitted)
            verify_run_finalize_response(response, self._creds.upload_id)
            pages, rows, size = finalize_totals(response)
        stats.pages_emitted, stats.rows_emitted, stats.bytes_emitted = pages, rows, size
        return {'uploadId': self._creds.upload_id, 'pageCount': pages, 'totalRows': rows, 'totalBytes': size}


class SessionlessUploadProtocol:
    """The opt-in sessionless protocol: independent self-describing pages, no session calls.

    Each logical page is one multipart request carrying the descriptor and its identity, and
    its receipt supplies one object id. Only the accepted request's id is kept: a transport
    retry sends a fresh request, so an earlier attempt whose response was lost can leave an
    orphaned stored object that is never referenced. Completion makes no request: it reports
    the ordered ids and the canonical totals accumulated from the verified receipts. No scan
    stamp is read or reported; whether a page was scanned is intake's own stored record.
    """

    def __init__(
        self,
        delivery: RemoteQuerySessionlessResultDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
    ):
        self._delivery, self._creds, self._client, self._descriptor = delivery, creds, client, descriptor
        self._descriptor_json = descriptor_request_bytes(descriptor)
        self._object_ids: list[str] = []

    def begin(self) -> None:
        if len(self._descriptor_json) > REMOTE_QUERY_SESSIONLESS_MAX_DESCRIPTOR_BYTES:
            raise RemoteQueryFailure('max_schema_bytes_exceeded', 'The encoded descriptor exceeds its size limit.')

    def send_page(self, page: SourcePageUploadMetadata, body: BinaryIO, bound: int) -> int:
        metadata = sessionless_page_metadata_bytes(self._delivery, page, self._descriptor_json)
        response = self._client.post_sessionless_page(self._creds, page, metadata, body)
        receipt = verify_sessionless_page_receipt(response, page, self._delivery.limits.max_file_bytes)
        self._object_ids.append(receipt.object_id)
        return receipt.bytes

    def complete(self, stats: RemoteQueryRunStats) -> dict[str, Any]:
        if self._descriptor.include_schema and not self._object_ids:
            # The empty schema page is the only artifact that carries the schema: it is never optional.
            raise RemoteQueryFailure('invalid_receipt', 'A schema-bearing result completed without a page.')
        try:
            proposal = SessionlessCompletionReceipt(
                objectIds=tuple(self._object_ids),
                pageCount=stats.pages_emitted,
                totalRows=stats.rows_emitted,
                totalBytes=stats.bytes_emitted,
            )
        except ValueError:
            raise RemoteQueryFailure(
                'invalid_receipt', 'The sessionless completion proposal is inconsistent.'
            ) from None
        return proposal.wire()


def create_upload_protocol(
    delivery: RemoteQueryDelivery,
    creds: UploadCredentials,
    client: UploadClient,
    descriptor: RemoteQueryUploadDescriptor,
    tracing: RemoteQueryProducerTracing,
) -> UploadProtocol:
    """Choose the wire protocol from the validated `session_info`: no `uploadId` means sessionless."""
    if isinstance(delivery, RemoteQuerySessionlessResultDelivery):
        return SessionlessUploadProtocol(delivery, creds, client, descriptor)
    return SessionUploadProtocol(creds, client, descriptor, tracing)


class PageUploader:
    """Upload complete CSV records; retry oversized pages at a record boundary.

    Callers own their buffers and supply record ends. Optional row bounds describe
    final JSON sizes; otherwise only source sizes are known until the protocol reports
    its authoritative totals (session finalize) or verified per-page receipts (sessionless).
    """

    def __init__(
        self,
        delivery: RemoteQueryDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
        tracing: RemoteQueryProducerTracing | None = None,
    ):
        self.delivery, self.creds, self.client = delivery, creds, client
        self.descriptor, self.guard, self.stats = descriptor, guard, stats
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
        self.protocol = create_upload_protocol(delivery, creds, client, descriptor, self.tracing)
        self.protocol.begin()

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
                accepted_bytes = self.protocol.send_page(page, _SourcePageBody(buffer, end), bound)
                if stats.bytes_emitted + accepted_bytes > limits.max_result_bytes:
                    raise RemoteQueryFailure('max_result_bytes_exceeded', 'Result pages exceed maxResultBytes.')
            except RemoteQueryFailure as error:
                if error.code != REMOTE_QUERY_FINAL_PAGE_TOO_LARGE_ERROR_CODE or count <= 1:
                    raise
                count //= 2
                continue
            stats.pages_emitted += 1
            stats.rows_emitted += count
            stats.bytes_emitted += accepted_bytes
            # The root span's time_to_first_page_ms counts the first receipt-verified,
            # counted page.
            self.tracing.note_page_acknowledged()
            return count, end

    def finalize(self) -> dict[str, Any]:
        return self.protocol.complete(self.stats)


class SourcePageWriter:
    """Buffer canonical JSON cells as CSV, bounded by their final JSON sizes."""

    def __init__(
        self,
        delivery: RemoteQueryDelivery,
        creds: UploadCredentials,
        client: UploadClient,
        descriptor: RemoteQueryUploadDescriptor,
        guard: Callable[[], None],
        stats: RemoteQueryRunStats,
        tracing: RemoteQueryProducerTracing | None = None,
    ):
        self._uploader = PageUploader(delivery, creds, client, descriptor, guard, stats, tracing)
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
